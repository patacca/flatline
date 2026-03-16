"""Bridge session abstraction and fallback implementation.

Internal bridge-session boundary between the stable Python public API and the
unstable native bridge implementation (specs.md section 6). The BridgeSession
protocol and its implementations are private; only the public Python API is
stable (specs.md section 3, ADR-002).
"""

from __future__ import annotations

import importlib
from collections.abc import Mapping, Sequence
from os import fspath
from typing import TYPE_CHECKING, Protocol

from flatline._errors import ERROR_CATEGORIES, ConfigurationError, InternalError
from flatline._models import (
    VALID_WARNING_PHASES,
    AnalysisBudget,
    CallSiteInfo,
    DecompileResult,
    DiagnosticFlags,
    ErrorItem,
    FunctionInfo,
    FunctionPrototype,
    JumpTableInfo,
    LanguageCompilerPair,
    ParameterInfo,
    StorageInfo,
    TypeInfo,
    VariableInfo,
    WarningItem,
)
from flatline._runtime_data import enumerate_runtime_data_language_compilers
from flatline._version import DECOMPILER_VERSION

if TYPE_CHECKING:
    from typing import Any

    from flatline._models import DecompileRequest


class BridgeSession(Protocol):
    """Internal bridge session protocol used by DecompilerSession."""

    def close(self) -> None:
        """Release bridge/native resources owned by this session."""

    def list_language_compilers(self) -> list[LanguageCompilerPair]:
        """List valid language/compiler pairs known to the runtime data."""

    def decompile_function(self, request: DecompileRequest) -> DecompileResult:
        """Run one decompile request through the bridge."""


class _FallbackBridgeSession:
    """Pure-Python fallback until the native bridge is available.

    Keeps the public API usable while returning deterministic structured
    error responses for unimplemented native operations.
    """

    def __init__(
        self,
        runtime_data_dir: str | None = None,
        *,
        runtime_data_pairs: Sequence[LanguageCompilerPair] = (),
    ) -> None:
        self._runtime_data_dir = runtime_data_dir
        self._runtime_data_pairs = tuple(runtime_data_pairs)
        self._closed = False

    def close(self) -> None:
        self._closed = True

    def list_language_compilers(self) -> list[LanguageCompilerPair]:
        if self._closed:
            return []
        return list(self._runtime_data_pairs)

    def decompile_function(self, request: DecompileRequest) -> DecompileResult:
        if self._closed:
            return _internal_error_result(request, "bridge session is closed")

        return _configuration_error_result(
            request,
            "native bridge is not implemented in this build",
        )


class _NativeBridgeSession:
    """Adapter around native bridge sessions.

    Normalizes native payloads to stable Python dataclasses at the bridge
    boundary so the public API remains contract-shaped.
    """

    def __init__(
        self,
        native_session: Any,
        *,
        runtime_data_pairs: Sequence[LanguageCompilerPair] = (),
    ) -> None:
        self._native_session = native_session
        self._runtime_data_pairs = tuple(runtime_data_pairs)

    def close(self) -> None:
        self._native_session.close()

    def list_language_compilers(self) -> list[LanguageCompilerPair]:
        try:
            raw_pairs = self._native_session.list_language_compilers()
            native_pairs = [_coerce_language_compiler_pair(item) for item in raw_pairs]
            if native_pairs:
                return native_pairs
            return list(self._runtime_data_pairs)
        except Exception as exc:  # pragma: no cover - exercised with bridge doubles
            raise InternalError(
                f"native list_language_compilers failed: {exc}"
            ) from exc

    def decompile_function(self, request: DecompileRequest) -> DecompileResult:
        request_payload = _request_to_native_payload(request)
        try:
            target_error = self._validate_target_selection(request)
            if target_error is not None:
                return target_error
            raw_result = self._native_session.decompile_function(request_payload)
            return _coerce_decompile_result(raw_result, request)
        except Exception as exc:
            return _internal_error_result(
                request,
                f"native decompile failed: {exc}",
            )

    def _validate_target_selection(self, request: DecompileRequest) -> DecompileResult | None:
        known_pairs = self.list_language_compilers()
        compilers_by_language: dict[str, set[str]] = {}
        for pair in known_pairs:
            if pair.language_id not in compilers_by_language:
                compilers_by_language[pair.language_id] = set()
            compilers_by_language[pair.language_id].add(pair.compiler_spec)

        available_compilers = compilers_by_language.get(request.language_id)
        if available_compilers is None:
            return _unsupported_target_result(
                request,
                f"unsupported language_id: {request.language_id!r}",
            )

        if request.compiler_spec is None:
            return None

        if request.compiler_spec not in available_compilers:
            return _unsupported_target_result(
                request,
                (
                    f"unsupported compiler_spec {request.compiler_spec!r} "
                    f"for language_id {request.language_id!r}"
                ),
            )

        return None


def _request_to_native_payload(request: DecompileRequest) -> dict[str, Any]:
    return {
        "memory_image": bytes(request.memory_image),
        "base_address": request.base_address,
        "function_address": request.function_address,
        "language_id": request.language_id,
        "compiler_spec": request.compiler_spec,
        "runtime_data_dir": request.runtime_data_dir,
        "function_size_hint": request.function_size_hint,
        "analysis_budget": _analysis_budget_to_native_payload(request.analysis_budget),
    }


def _analysis_budget_to_native_payload(
    budget: AnalysisBudget | None,
) -> dict[str, int] | None:
    if budget is None:
        return None
    return {
        "max_instructions": budget.max_instructions,
    }


def _coerce_language_compiler_pair(raw_item: Any) -> LanguageCompilerPair:
    if isinstance(raw_item, LanguageCompilerPair):
        return raw_item

    if isinstance(raw_item, Mapping):
        return LanguageCompilerPair(
            language_id=_require_str(raw_item.get("language_id"), "language_id"),
            compiler_spec=_require_str(raw_item.get("compiler_spec"), "compiler_spec"),
        )

    if _is_sequence_like(raw_item):
        if len(raw_item) != 2:
            raise InternalError("native language/compiler pair sequence must have length 2")
        return LanguageCompilerPair(
            language_id=_require_str(raw_item[0], "language_id"),
            compiler_spec=_require_str(raw_item[1], "compiler_spec"),
        )

    raise InternalError(
        f"native language/compiler pair has unsupported shape: {type(raw_item).__name__}"
    )


def _coerce_decompile_result(raw_result: Any, request: DecompileRequest) -> DecompileResult:
    if isinstance(raw_result, DecompileResult):
        return raw_result

    raw_map = _require_mapping(raw_result, "decompile_result")
    c_code = raw_map.get("c_code")
    if c_code is not None and not isinstance(c_code, str):
        raise InternalError("decompile_result.c_code must be str or None")

    function_info = _coerce_function_info(raw_map.get("function_info"))
    warnings = _coerce_warning_items(raw_map.get("warnings"))
    error = _coerce_error_item(raw_map.get("error"))
    metadata = _coerce_metadata(raw_map.get("metadata"), request)

    if error is not None:
        c_code = None
        function_info = None
    else:
        if c_code is None:
            raise InternalError("decompile_result.c_code must be set when error is None")
        if function_info is None:
            raise InternalError("decompile_result.function_info must be set when error is None")

    return DecompileResult(
        c_code=c_code,
        function_info=function_info,
        warnings=warnings,
        error=error,
        metadata=metadata,
    )


def _coerce_warning_items(raw_warnings: Any) -> list[WarningItem]:
    if raw_warnings is None:
        return []
    if not _is_sequence_like(raw_warnings):
        raise InternalError("decompile_result.warnings must be a sequence")
    return [_coerce_warning_item(item) for item in raw_warnings]


def _coerce_warning_item(raw_warning: Any) -> WarningItem:
    if isinstance(raw_warning, WarningItem):
        return raw_warning
    warning_map = _require_mapping(raw_warning, "warning_item")
    phase = _require_str(warning_map.get("phase"), "warning.phase")
    if phase not in VALID_WARNING_PHASES:
        raise InternalError(f"warning.phase must be one of {sorted(VALID_WARNING_PHASES)}")
    return WarningItem(
        code=_require_str(warning_map.get("code"), "warning.code"),
        message=_require_str(warning_map.get("message"), "warning.message"),
        phase=phase,
    )


def _coerce_error_item(raw_error: Any) -> ErrorItem | None:
    if raw_error is None:
        return None
    if isinstance(raw_error, ErrorItem):
        return raw_error
    error_map = _require_mapping(raw_error, "error_item")
    category = _require_str(error_map.get("category"), "error.category")
    if category not in ERROR_CATEGORIES:
        raise InternalError(f"error.category is unsupported: {category!r}")
    return ErrorItem(
        category=category,
        message=_require_str(error_map.get("message"), "error.message"),
        retryable=_require_bool(error_map.get("retryable"), "error.retryable"),
    )


def _coerce_metadata(raw_metadata: Any, request: DecompileRequest) -> dict[str, Any]:
    if raw_metadata is None:
        metadata: dict[str, Any] = {}
    else:
        metadata = dict(_require_mapping(raw_metadata, "metadata"))

    diagnostics = metadata.get("diagnostics", {})
    if not isinstance(diagnostics, Mapping):
        diagnostics = {}

    decompiler_version = metadata.get("decompiler_version")
    if decompiler_version is None:
        decompiler_version = DECOMPILER_VERSION
    language_id = metadata.get("language_id")
    if language_id is None:
        language_id = request.language_id
    compiler_spec = metadata.get("compiler_spec")
    if compiler_spec is None:
        compiler_spec = request.compiler_spec or ""

    metadata["decompiler_version"] = _require_str(
        decompiler_version,
        "metadata.decompiler_version",
    )
    metadata["language_id"] = _require_str(
        language_id,
        "metadata.language_id",
    )
    metadata["compiler_spec"] = _require_str(
        compiler_spec,
        "metadata.compiler_spec",
    )
    metadata["diagnostics"] = dict(diagnostics)
    return metadata


def _coerce_function_info(raw_info: Any) -> FunctionInfo | None:
    if raw_info is None:
        return None
    if isinstance(raw_info, FunctionInfo):
        return raw_info

    info_map = _require_mapping(raw_info, "function_info")
    return FunctionInfo(
        name=_require_str(info_map.get("name"), "function_info.name"),
        entry_address=_require_int(info_map.get("entry_address"), "function_info.entry_address"),
        size=_require_int(info_map.get("size"), "function_info.size"),
        is_complete=_require_bool(info_map.get("is_complete"), "function_info.is_complete"),
        prototype=_coerce_function_prototype(info_map.get("prototype")),
        local_variables=_coerce_variable_info_list(info_map.get("local_variables")),
        call_sites=_coerce_call_site_list(info_map.get("call_sites")),
        jump_tables=_coerce_jump_table_list(info_map.get("jump_tables")),
        diagnostics=_coerce_diagnostic_flags(info_map.get("diagnostics")),
        varnode_count=_require_int(info_map.get("varnode_count"), "function_info.varnode_count"),
    )


def _coerce_function_prototype(raw_prototype: Any) -> FunctionPrototype:
    if isinstance(raw_prototype, FunctionPrototype):
        return raw_prototype
    prototype_map = _require_mapping(raw_prototype, "function_prototype")
    calling_convention = prototype_map.get("calling_convention")
    if calling_convention is not None:
        calling_convention = _require_str(
            calling_convention,
            "function_prototype.calling_convention",
        )
    return FunctionPrototype(
        calling_convention=calling_convention,
        parameters=_coerce_parameter_info_list(prototype_map.get("parameters")),
        return_type=_coerce_type_info(prototype_map.get("return_type")),
        is_noreturn=_require_bool(
            prototype_map.get("is_noreturn"),
            "function_prototype.is_noreturn",
        ),
        has_this_pointer=_require_bool(
            prototype_map.get("has_this_pointer"),
            "function_prototype.has_this_pointer",
        ),
        has_input_errors=_require_bool(
            prototype_map.get("has_input_errors"),
            "function_prototype.has_input_errors",
        ),
        has_output_errors=_require_bool(
            prototype_map.get("has_output_errors"),
            "function_prototype.has_output_errors",
        ),
    )


def _coerce_parameter_info_list(raw_parameters: Any) -> list[ParameterInfo]:
    if raw_parameters is None:
        return []
    if not _is_sequence_like(raw_parameters):
        raise InternalError("function_prototype.parameters must be a sequence")
    return [_coerce_parameter_info(item) for item in raw_parameters]


def _coerce_parameter_info(raw_parameter: Any) -> ParameterInfo:
    if isinstance(raw_parameter, ParameterInfo):
        return raw_parameter
    parameter_map = _require_mapping(raw_parameter, "parameter_info")
    return ParameterInfo(
        name=_require_str(parameter_map.get("name"), "parameter_info.name"),
        type=_coerce_type_info(parameter_map.get("type")),
        index=_require_int(parameter_map.get("index"), "parameter_info.index"),
        storage=_coerce_storage_info_optional(parameter_map.get("storage")),
    )


def _coerce_variable_info_list(raw_variables: Any) -> list[VariableInfo]:
    if raw_variables is None:
        return []
    if not _is_sequence_like(raw_variables):
        raise InternalError("function_info.local_variables must be a sequence")
    return [_coerce_variable_info(item) for item in raw_variables]


def _coerce_variable_info(raw_variable: Any) -> VariableInfo:
    if isinstance(raw_variable, VariableInfo):
        return raw_variable
    variable_map = _require_mapping(raw_variable, "variable_info")
    return VariableInfo(
        name=_require_str(variable_map.get("name"), "variable_info.name"),
        type=_coerce_type_info(variable_map.get("type")),
        storage=_coerce_storage_info_optional(variable_map.get("storage")),
    )


def _coerce_type_info(raw_type: Any) -> TypeInfo:
    if isinstance(raw_type, TypeInfo):
        return raw_type
    type_map = _require_mapping(raw_type, "type_info")
    return TypeInfo(
        name=_require_str(type_map.get("name"), "type_info.name"),
        size=_require_int(type_map.get("size"), "type_info.size"),
        metatype=_require_str(type_map.get("metatype"), "type_info.metatype"),
    )


def _coerce_storage_info_optional(raw_storage: Any) -> StorageInfo | None:
    if raw_storage is None:
        return None
    return _coerce_storage_info(raw_storage)


def _coerce_storage_info(raw_storage: Any) -> StorageInfo:
    if isinstance(raw_storage, StorageInfo):
        return raw_storage
    storage_map = _require_mapping(raw_storage, "storage_info")
    return StorageInfo(
        space=_require_str(storage_map.get("space"), "storage_info.space"),
        offset=_require_int(storage_map.get("offset"), "storage_info.offset"),
        size=_require_int(storage_map.get("size"), "storage_info.size"),
    )


def _coerce_call_site_list(raw_call_sites: Any) -> list[CallSiteInfo]:
    if raw_call_sites is None:
        return []
    if not _is_sequence_like(raw_call_sites):
        raise InternalError("function_info.call_sites must be a sequence")
    return [_coerce_call_site(item) for item in raw_call_sites]


def _coerce_call_site(raw_call_site: Any) -> CallSiteInfo:
    if isinstance(raw_call_site, CallSiteInfo):
        return raw_call_site
    call_site_map = _require_mapping(raw_call_site, "call_site")
    target_address = call_site_map.get("target_address")
    if target_address is not None:
        target_address = _require_int(target_address, "call_site.target_address")
    return CallSiteInfo(
        instruction_address=_require_int(
            call_site_map.get("instruction_address"),
            "call_site.instruction_address",
        ),
        target_address=target_address,
    )


def _coerce_jump_table_list(raw_jump_tables: Any) -> list[JumpTableInfo]:
    if raw_jump_tables is None:
        return []
    if not _is_sequence_like(raw_jump_tables):
        raise InternalError("function_info.jump_tables must be a sequence")
    return [_coerce_jump_table(item) for item in raw_jump_tables]


def _coerce_jump_table(raw_jump_table: Any) -> JumpTableInfo:
    if isinstance(raw_jump_table, JumpTableInfo):
        return raw_jump_table
    jump_table_map = _require_mapping(raw_jump_table, "jump_table")
    raw_targets = jump_table_map.get("target_addresses", [])
    if not _is_sequence_like(raw_targets):
        raise InternalError("jump_table.target_addresses must be a sequence")
    target_addresses = [
        _require_int(address, "jump_table.target_addresses[]")
        for address in raw_targets
    ]
    return JumpTableInfo(
        switch_address=_require_int(
            jump_table_map.get("switch_address"),
            "jump_table.switch_address",
        ),
        target_count=_require_int(jump_table_map.get("target_count"), "jump_table.target_count"),
        target_addresses=target_addresses,
    )


def _coerce_diagnostic_flags(raw_diagnostics: Any) -> DiagnosticFlags:
    if isinstance(raw_diagnostics, DiagnosticFlags):
        return raw_diagnostics
    diagnostics_map = _require_mapping(raw_diagnostics, "diagnostics")
    return DiagnosticFlags(
        is_complete=_require_bool(diagnostics_map.get("is_complete"), "diagnostics.is_complete"),
        has_unreachable_blocks=_require_bool(
            diagnostics_map.get("has_unreachable_blocks"),
            "diagnostics.has_unreachable_blocks",
        ),
        has_unimplemented=_require_bool(
            diagnostics_map.get("has_unimplemented"),
            "diagnostics.has_unimplemented",
        ),
        has_bad_data=_require_bool(
            diagnostics_map.get("has_bad_data"),
            "diagnostics.has_bad_data",
        ),
        has_no_code=_require_bool(diagnostics_map.get("has_no_code"), "diagnostics.has_no_code"),
    )


def _internal_error_result(request: DecompileRequest, message: str) -> DecompileResult:
    return _error_result(
        request,
        category="internal_error",
        message=message,
        retryable=False,
    )


def _unsupported_target_result(request: DecompileRequest, message: str) -> DecompileResult:
    return _error_result(
        request,
        category="unsupported_target",
        message=message,
        retryable=False,
    )


def _configuration_error_result(request: DecompileRequest, message: str) -> DecompileResult:
    return _error_result(
        request,
        category="configuration_error",
        message=message,
        retryable=False,
    )


def _error_result(
    request: DecompileRequest,
    *,
    category: str,
    message: str,
    retryable: bool,
) -> DecompileResult:
    if category not in ERROR_CATEGORIES:
        raise InternalError(f"unsupported error category for result: {category!r}")

    return DecompileResult(
        c_code=None,
        function_info=None,
        warnings=[],
        error=ErrorItem(
            category=category,
            message=message,
            retryable=retryable,
        ),
        metadata=_default_error_metadata(request),
    )


def _default_error_metadata(request: DecompileRequest) -> dict[str, Any]:
    return {
        "decompiler_version": DECOMPILER_VERSION,
        "language_id": request.language_id,
        "compiler_spec": request.compiler_spec or "",
        "diagnostics": {},
    }


def _require_mapping(raw_value: Any, field_name: str) -> Mapping[str, Any]:
    if not isinstance(raw_value, Mapping):
        raise InternalError(f"{field_name} must be a mapping")
    return raw_value


def _require_str(raw_value: Any, field_name: str) -> str:
    if not isinstance(raw_value, str):
        raise InternalError(f"{field_name} must be a string")
    return raw_value


def _require_int(raw_value: Any, field_name: str) -> int:
    if not isinstance(raw_value, int) or isinstance(raw_value, bool):
        raise InternalError(f"{field_name} must be an integer")
    return raw_value


def _require_bool(raw_value: Any, field_name: str) -> bool:
    if not isinstance(raw_value, bool):
        raise InternalError(f"{field_name} must be a bool")
    return raw_value


def _is_sequence_like(raw_value: Any) -> bool:
    return isinstance(raw_value, Sequence) and not isinstance(raw_value, (str, bytes, bytearray))


def create_bridge_session(runtime_data_dir: str | None = None) -> BridgeSession:
    """Create a bridge session.

    Tries to use a compiled native bridge when available. Falls back to a
    deterministic pure-Python skeleton implementation otherwise.
    """
    normalized_runtime_data_dir = None
    if runtime_data_dir is not None:
        normalized_runtime_data_dir = fspath(runtime_data_dir)

    runtime_data_pairs = enumerate_runtime_data_language_compilers(normalized_runtime_data_dir)
    try:
        native_bridge = importlib.import_module("flatline._flatline_native")
    except ImportError:
        return _FallbackBridgeSession(
            runtime_data_dir=normalized_runtime_data_dir,
            runtime_data_pairs=runtime_data_pairs,
        )
    try:
        native_session = native_bridge.create_session(normalized_runtime_data_dir)
    except Exception as exc:
        if isinstance(exc, ConfigurationError):
            raise
        raise InternalError(
            f"native bridge session startup failed: {exc}"
        ) from exc
    return _NativeBridgeSession(
        native_session,
        runtime_data_pairs=runtime_data_pairs,
    )
