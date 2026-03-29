# API Reference

Auto-generated from source docstrings and type annotations.  Every public
symbol exported by the `flatline` package is documented here.

## Quick Lookup

| Symbol | Page | Description |
|---|---|---|
| [`DecompilerSession`][flatline.DecompilerSession] | [Session](session.md) | Long-lived session; amortizes startup across calls |
| [`decompile_function()`][flatline.decompile_function] | [Session](session.md) | One-shot decompile convenience wrapper |
| [`list_language_compilers()`][flatline.list_language_compilers] | [Session](session.md) | One-shot language enumeration wrapper |
| [`get_version_info()`][flatline.get_version_info] | [Session](session.md) | Runtime version query |
| [`DecompileRequest`][flatline.DecompileRequest] | [Request & Result](request-result.md) | Input payload for decompilation |
| [`DecompileResult`][flatline.DecompileResult] | [Request & Result](request-result.md) | Output payload with C code and metadata |
| [`AnalysisBudget`][flatline.AnalysisBudget] | [Request & Result](request-result.md) | Per-request resource limits |
| [`WarningItem`][flatline.WarningItem] | [Request & Result](request-result.md) | One decompiler warning |
| [`ErrorItem`][flatline.ErrorItem] | [Request & Result](request-result.md) | Structured error in result |
| [`FunctionInfo`][flatline.FunctionInfo] | [Data Models](models.md) | Structured function data |
| [`FunctionPrototype`][flatline.FunctionPrototype] | [Data Models](models.md) | Recovered function signature |
| [`TypeInfo`][flatline.TypeInfo] | [Data Models](models.md) | Recovered type descriptor |
| [`ParameterInfo`][flatline.ParameterInfo] | [Data Models](models.md) | Function parameter |
| [`VariableInfo`][flatline.VariableInfo] | [Data Models](models.md) | Local variable |
| [`CallSiteInfo`][flatline.CallSiteInfo] | [Data Models](models.md) | Call instruction |
| [`JumpTableInfo`][flatline.JumpTableInfo] | [Data Models](models.md) | Recovered jump table |
| [`DiagnosticFlags`][flatline.DiagnosticFlags] | [Data Models](models.md) | Decompiler diagnostic flags |
| [`StorageInfo`][flatline.StorageInfo] | [Data Models](models.md) | Variable/parameter storage location |
| [`Enriched`][flatline.Enriched] | [Enriched Output](enriched.md) | Optional enriched companion payload |
| [`Pcode`][flatline.Pcode] | [Enriched Output](enriched.md) | Pcode container with lookup and graph |
| [`PcodeOpInfo`][flatline.PcodeOpInfo] | [Enriched Output](enriched.md) | One pcode operation |
| [`VarnodeInfo`][flatline.VarnodeInfo] | [Enriched Output](enriched.md) | One varnode |
| [`VarnodeFlags`][flatline.VarnodeFlags] | [Enriched Output](enriched.md) | Varnode boolean flags |
| [`FlatlineError`](errors.md) | [Errors](errors.md) | Base exception and full error hierarchy |
