#include "_flatline_native_shared.h"

#include <algorithm>
#include <cstring>
#include <list>
#include <limits>
#include <set>
#include <sstream>
#include <stdexcept>
#include <typeinfo>
#include <unordered_map>

#include "comment.hh"
#include "database.hh"
#include "funcdata.hh"
#include "jumptable.hh"
#include "loadimage.hh"
#include "type.hh"

namespace nb = nanobind;

namespace flatline::native_bridge {
namespace {

static std::string require_string_field(const nb::dict& request, const char* field_name) {
    if (!request.contains(field_name)) {
        throw std::invalid_argument(std::string("missing required field: ") + field_name);
    }
    return nb::cast<std::string>(request[field_name]);
}

static std::uint64_t require_u64_field(const nb::dict& request, const char* field_name) {
    if (!request.contains(field_name)) {
        throw std::invalid_argument(std::string("missing required field: ") + field_name);
    }
    std::int64_t value = nb::cast<std::int64_t>(request[field_name]);
    if (value < 0) {
        throw std::invalid_argument(std::string(field_name) + " must be non-negative");
    }
    return static_cast<std::uint64_t>(value);
}

static std::optional<std::string> optional_string_field(const nb::dict& request,
                                                        const char* field_name) {
    if (!request.contains(field_name)) {
        return std::nullopt;
    }
    nb::object field_value = request[field_name];
    if (field_value.is_none()) {
        return std::nullopt;
    }
    std::string value = nb::cast<std::string>(field_value);
    if (value.empty()) {
        return std::nullopt;
    }
    return value;
}

static std::optional<std::string> optional_bytes_field(const nb::dict& request,
                                                       const char* field_name,
                                                       std::optional<std::string> default_value) {
    if (!request.contains(field_name)) {
        return default_value;
    }
    nb::object field_value = request[field_name];
    if (field_value.is_none()) {
        return std::nullopt;
    }
    nb::bytes raw_bytes = nb::cast<nb::bytes>(field_value);
    std::string value(raw_bytes.c_str(), raw_bytes.size());
    if (value.empty()) {
        return std::nullopt;
    }
    return value;
}

static bool optional_bool_field(const nb::dict& request, const char* field_name,
                                bool default_value) {
    if (!request.contains(field_name)) {
        return default_value;
    }
    nb::object field_value = request[field_name];
    if (field_value.is_none()) {
        return default_value;
    }
    return nb::cast<bool>(field_value);
}

static std::uint32_t require_positive_u32_value(nb::handle value, const char* field_name) {
    std::int64_t parsed_value = nb::cast<std::int64_t>(value);
    if (parsed_value <= 0) {
        throw std::invalid_argument(std::string(field_name) + " must be positive");
    }
    if (parsed_value > static_cast<std::int64_t>(std::numeric_limits<std::uint32_t>::max())) {
        throw std::invalid_argument(std::string(field_name) + " exceeds supported range");
    }
    return static_cast<std::uint32_t>(parsed_value);
}

static bool contains_case_insensitive(const std::string& haystack, const std::string& needle) {
    if (needle.empty()) {
        return true;
    }
    std::string lower_haystack = haystack;
    std::string lower_needle = needle;
    for (char& ch : lower_haystack) {
        if (ch >= 'A' && ch <= 'Z') {
            ch = static_cast<char>(ch - 'A' + 'a');
        }
    }
    for (char& ch : lower_needle) {
        if (ch >= 'A' && ch <= 'Z') {
            ch = static_cast<char>(ch - 'A' + 'a');
        }
    }
    return lower_haystack.find(lower_needle) != std::string::npos;
}

static std::string map_metatype_to_string(ghidra::type_metatype metatype) {
    switch (metatype) {
        case ghidra::TYPE_VOID:
            return "void";
        case ghidra::TYPE_BOOL:
            return "bool";
        case ghidra::TYPE_INT:
            return "int";
        case ghidra::TYPE_UINT:
            return "uint";
        case ghidra::TYPE_FLOAT:
            return "float";
        case ghidra::TYPE_PTR:
            return "pointer";
        case ghidra::TYPE_ARRAY:
            return "array";
        case ghidra::TYPE_STRUCT:
            return "struct";
        case ghidra::TYPE_UNION:
            return "union";
        case ghidra::TYPE_CODE:
            return "code";
        case ghidra::TYPE_ENUM_INT:
        case ghidra::TYPE_ENUM_UINT:
            return "enum";
        case ghidra::TYPE_UNKNOWN:
        case ghidra::TYPE_PTRREL:
        case ghidra::TYPE_SPACEBASE:
        case ghidra::TYPE_PARTIALSTRUCT:
        case ghidra::TYPE_PARTIALUNION:
        case ghidra::TYPE_PARTIALENUM:
        default:
            return "unknown";
    }
}

static nb::dict type_info_to_dict_impl(const ghidra::Datatype* datatype) {
    nb::dict type_info;
    if (datatype == nullptr) {
        type_info["name"] = "unknown";
        type_info["size"] = 0;
        type_info["metatype"] = "unknown";
        return type_info;
    }

    std::string name = datatype->getName();
    if (name.empty()) {
        name = "unknown";
    }
    type_info["name"] = name;
    type_info["size"] = datatype->getSize();
    type_info["metatype"] = map_metatype_to_string(datatype->getMetatype());
    return type_info;
}

static nb::object storage_info_from_address_impl(const ghidra::Address& address, std::int64_t size) {
    if (address.isInvalid() || address.getSpace() == nullptr || size <= 0) {
        return nb::none();
    }
    nb::dict storage;
    storage["space"] = address.getSpace()->getName();
    storage["offset"] = static_cast<std::uint64_t>(address.getOffset());
    storage["size"] = size;
    return storage;
}

static nb::object storage_info_from_symbol_impl(const ghidra::Symbol* symbol) {
    if (symbol == nullptr) {
        return nb::none();
    }
    ghidra::SymbolEntry* entry = symbol->getFirstWholeMap();
    if (entry == nullptr) {
        return nb::none();
    }
    return storage_info_from_address_impl(entry->getAddr(), entry->getSize());
}

static nb::dict diagnostics_to_dict_impl(const ghidra::Funcdata& function) {
    nb::dict diagnostics;
    diagnostics["is_complete"] = function.isProcComplete();
    diagnostics["has_unreachable_blocks"] = function.hasUnreachableBlocks();
    diagnostics["has_unimplemented"] = function.hasUnimplemented();
    diagnostics["has_bad_data"] = function.hasBadData();
    diagnostics["has_no_code"] = function.hasNoCode();
    return diagnostics;
}

static nb::list warnings_from_comment_database_impl(const ghidra::Funcdata& function,
                                                    const ghidra::Architecture& architecture) {
    nb::list warnings;
    if (architecture.commentdb == nullptr) {
        return warnings;
    }
    const ghidra::Address& function_address = function.getAddress();
    ghidra::CommentSet::const_iterator iter =
        architecture.commentdb->beginComment(function_address);
    ghidra::CommentSet::const_iterator end = architecture.commentdb->endComment(function_address);
    for (; iter != end; ++iter) {
        const ghidra::Comment* comment = *iter;
        if (comment == nullptr) {
            continue;
        }
        if ((comment->getType() & (ghidra::Comment::warning | ghidra::Comment::warningheader)) ==
            0) {
            continue;
        }
        nb::dict warning;
        warning["code"] = "analyze.W001";
        warning["message"] = comment->getText();
        warning["phase"] = "analyze";
        warnings.append(warning);
    }
    return warnings;
}

static nb::list call_sites_to_list_impl(const ghidra::Funcdata& function) {
    nb::list call_sites;
    const int call_count = function.numCalls();
    for (int index = 0; index < call_count; ++index) {
        ghidra::FuncCallSpecs* call_spec = function.getCallSpecs(index);
        if (call_spec == nullptr) {
            continue;
        }
        nb::dict call_site;
        ghidra::PcodeOp* call_op = call_spec->getOp();
        if (call_op != nullptr && !call_op->getAddr().isInvalid()) {
            call_site["instruction_address"] =
                static_cast<std::uint64_t>(call_op->getAddr().getOffset());
        } else {
            call_site["instruction_address"] =
                static_cast<std::uint64_t>(function.getAddress().getOffset());
        }

        const ghidra::Address& target = call_spec->getEntryAddress();
        if (!target.isInvalid()) {
            call_site["target_address"] = static_cast<std::uint64_t>(target.getOffset());
        } else {
            call_site["target_address"] = nb::none();
        }
        call_sites.append(call_site);
    }
    return call_sites;
}

static nb::list jump_tables_to_list_impl(ghidra::Funcdata& function) {
    nb::list jump_tables;
    const int jump_table_count = function.numJumpTables();
    for (int index = 0; index < jump_table_count; ++index) {
        ghidra::JumpTable* jump_table = function.getJumpTable(index);
        if (jump_table == nullptr) {
            continue;
        }
        nb::list target_addresses;
        const int table_size = jump_table->numEntries();
        for (int entry_index = 0; entry_index < table_size; ++entry_index) {
            const ghidra::Address target_address = jump_table->getAddressByIndex(entry_index);
            if (target_address.isInvalid()) {
                continue;
            }
            target_addresses.append(static_cast<std::uint64_t>(target_address.getOffset()));
        }

        nb::dict jump_table_item;
        const ghidra::Address& switch_address = jump_table->getOpAddress();
        if (!switch_address.isInvalid()) {
            jump_table_item["switch_address"] =
                static_cast<std::uint64_t>(switch_address.getOffset());
        } else {
            jump_table_item["switch_address"] =
                static_cast<std::uint64_t>(function.getAddress().getOffset());
        }
        jump_table_item["target_count"] = static_cast<int>(target_addresses.size());
        jump_table_item["target_addresses"] = target_addresses;
        jump_tables.append(jump_table_item);
    }
    return jump_tables;
}

static nb::list local_variables_to_list_impl(const ghidra::Funcdata& function) {
    nb::list local_variables;
    const ghidra::ScopeLocal* local_scope = function.getScopeLocal();
    if (local_scope == nullptr) {
        return local_variables;
    }

    std::set<std::uint64_t> seen_symbol_ids;
    for (ghidra::MapIterator iter = local_scope->begin(); iter != local_scope->end(); ++iter) {
        const ghidra::SymbolEntry* entry = *iter;
        if (entry == nullptr) {
            continue;
        }
        ghidra::Symbol* symbol = entry->getSymbol();
        if (symbol == nullptr) {
            continue;
        }

        const std::uint64_t symbol_id = static_cast<std::uint64_t>(symbol->getId());
        if (!seen_symbol_ids.insert(symbol_id).second) {
            continue;
        }
        if (symbol->getCategory() != ghidra::Symbol::no_category) {
            continue;
        }
        if (dynamic_cast<ghidra::FunctionSymbol*>(symbol) != nullptr) {
            continue;
        }

        nb::dict variable;
        std::string variable_name = symbol->getName();
        if (variable_name.empty()) {
            variable_name = "local_" + std::to_string(local_variables.size());
        }
        variable["name"] = variable_name;
        variable["type"] = type_info_to_dict_impl(symbol->getType());
        variable["storage"] = storage_info_from_symbol_impl(symbol);
        local_variables.append(variable);
    }
    return local_variables;
}

static nb::dict prototype_to_dict_impl(const ghidra::FuncProto& prototype) {
    nb::dict prototype_info;
    prototype_info["calling_convention"] = prototype.getModelName();

    nb::list parameters;
    const int parameter_count = prototype.numParams();
    for (int index = 0; index < parameter_count; ++index) {
        ghidra::ProtoParameter* parameter = prototype.getParam(index);
        if (parameter == nullptr) {
            continue;
        }

        nb::dict parameter_item;
        std::string parameter_name = parameter->getName();
        if (parameter_name.empty()) {
            parameter_name = "param_" + std::to_string(index);
        }
        parameter_item["name"] = parameter_name;
        parameter_item["type"] = type_info_to_dict_impl(parameter->getType());
        parameter_item["index"] = index;
        parameter_item["storage"] =
            storage_info_from_address_impl(parameter->getAddress(), parameter->getSize());
        parameters.append(parameter_item);
    }

    prototype_info["parameters"] = parameters;
    prototype_info["return_type"] = type_info_to_dict_impl(prototype.getOutputType());
    prototype_info["is_noreturn"] = prototype.isNoReturn();
    prototype_info["has_this_pointer"] = prototype.hasThisPointer();
    prototype_info["has_input_errors"] = prototype.hasInputErrors();
    prototype_info["has_output_errors"] = prototype.hasOutputErrors();
    return prototype_info;
}

static nb::dict function_info_to_dict_impl(ghidra::Funcdata& function) {
    nb::dict function_info;
    function_info["name"] = function.getName();
    function_info["entry_address"] = static_cast<std::uint64_t>(function.getAddress().getOffset());
    function_info["size"] = function.getSize();
    function_info["is_complete"] = function.isProcComplete();
    function_info["prototype"] = prototype_to_dict_impl(function.getFuncProto());
    function_info["local_variables"] = local_variables_to_list_impl(function);
    function_info["call_sites"] = call_sites_to_list_impl(function);
    function_info["jump_tables"] = jump_tables_to_list_impl(function);
    function_info["diagnostics"] = diagnostics_to_dict_impl(function);
    function_info["varnode_count"] = function.numVarnodes();
    return function_info;
}

static std::uint32_t parse_max_instructions(const nb::dict& request) {
    constexpr std::uint32_t kDefaultMaxInstructions = 100000;
    if (!request.contains("analysis_budget")) {
        return kDefaultMaxInstructions;
    }

    nb::object raw_budget = request["analysis_budget"];
    if (raw_budget.is_none()) {
        return kDefaultMaxInstructions;
    }

    nb::dict budget = nb::cast<nb::dict>(raw_budget);
    std::set<std::string> unsupported_keys;
    for (const auto& item : budget) {
        const std::string key = nb::cast<std::string>(item.first);
        if (key != "max_instructions") {
            unsupported_keys.insert(key);
        }
    }
    if (!unsupported_keys.empty()) {
        std::string joined;
        for (const auto& key : unsupported_keys) {
            if (!joined.empty()) {
                joined += ", ";
            }
            joined += key;
        }
        throw std::invalid_argument("analysis_budget contains unsupported fields: " + joined);
    }

    if (!budget.contains("max_instructions")) {
        return kDefaultMaxInstructions;
    }
    return require_positive_u32_value(budget["max_instructions"],
                                      "analysis_budget.max_instructions");
}

}  // namespace

NativeRequest parse_request(const nb::dict& request) {
    NativeRequest parsed{};

    if (!request.contains("memory_image")) {
        throw std::invalid_argument("missing required field: memory_image");
    }
    nb::bytes raw_bytes = nb::cast<nb::bytes>(request["memory_image"]);
    parsed.memory_image = std::string(raw_bytes.c_str(), raw_bytes.size());
    if (parsed.memory_image.empty()) {
        throw std::invalid_argument("memory_image must not be empty");
    }

    parsed.base_address = require_u64_field(request, "base_address");
    parsed.function_address = require_u64_field(request, "function_address");
    parsed.language_id = require_string_field(request, "language_id");
    if (parsed.language_id.empty()) {
        throw std::invalid_argument("language_id must not be empty");
    }
    parsed.compiler_spec = optional_string_field(request, "compiler_spec");
    parsed.max_instructions = parse_max_instructions(request);
    parsed.enriched = optional_bool_field(request, "enriched", false);
    parsed.tail_padding = optional_bytes_field(request, "tail_padding", std::string("\0", 1));
    return parsed;
}

nb::dict type_info_to_dict(const ghidra::Datatype* datatype) {
    return type_info_to_dict_impl(datatype);
}

nb::object storage_info_from_address(const ghidra::Address& address, std::int64_t size) {
    return storage_info_from_address_impl(address, size);
}

nb::object storage_info_from_symbol(const ghidra::Symbol* symbol) {
    return storage_info_from_symbol_impl(symbol);
}

nb::dict diagnostics_to_dict(const ghidra::Funcdata& function) {
    return diagnostics_to_dict_impl(function);
}

nb::list warnings_from_comment_database(const ghidra::Funcdata& function,
                                        const ghidra::Architecture& architecture) {
    return warnings_from_comment_database_impl(function, architecture);
}

nb::list call_sites_to_list(const ghidra::Funcdata& function) {
    return call_sites_to_list_impl(function);
}

nb::list jump_tables_to_list(ghidra::Funcdata& function) {
    return jump_tables_to_list_impl(function);
}

nb::list local_variables_to_list(const ghidra::Funcdata& function) {
    return local_variables_to_list_impl(function);
}

nb::dict prototype_to_dict(const ghidra::FuncProto& prototype) {
    return prototype_to_dict_impl(prototype);
}

nb::dict function_info_to_dict(ghidra::Funcdata& function) {
    return function_info_to_dict_impl(function);
}

nb::dict metadata_dict(const std::string& decompiler_version, const std::string& language_id,
                       const std::string& compiler_spec, const nb::dict& diagnostics) {
    nb::dict metadata;
    metadata["decompiler_version"] = decompiler_version;
    metadata["language_id"] = language_id;
    metadata["compiler_spec"] = compiler_spec;
    metadata["diagnostics"] = diagnostics;
    return metadata;
}

nb::dict error_result(const std::string& category, const std::string& message,
                      const std::string& decompiler_version, const std::string& language_id,
                      const std::string& compiler_spec) {
    nb::dict error;
    error["category"] = category;
    error["message"] = message;
    error["retryable"] = false;

    nb::dict result;
    result["c_code"] = nb::none();
    result["function_info"] = nb::none();
    result["warnings"] = nb::list();
    result["error"] = error;
    result["metadata"] = metadata_dict(decompiler_version, language_id, compiler_spec, nb::dict());
    result["enriched"] = nb::none();
    return result;
}

nb::dict success_result(const std::string& c_code, const nb::dict& function_info,
                        const nb::list& warnings, const std::string& decompiler_version,
                        const std::string& language_id, const std::string& compiler_spec,
                        const nb::dict& diagnostics, const nb::object& enriched) {
    nb::dict result;
    result["c_code"] = c_code;
    result["function_info"] = function_info;
    result["warnings"] = warnings;
    result["error"] = nb::none();
    result["metadata"] =
        metadata_dict(decompiler_version, language_id, compiler_spec, diagnostics);
    result["enriched"] = enriched;
    return result;
}

std::string classifier_for_lowlevel_error(const std::string& message) {
    if (contains_case_insensitive(message, "no sleigh specification") ||
        contains_case_insensitive(message, "architecture string does not look like sleigh id")) {
        return "unsupported_target";
    }
    if (contains_case_insensitive(message, "outside memory_image") ||
        contains_case_insensitive(message, "outside memory image") ||
        contains_case_insensitive(message, "no function at this offset") ||
        contains_case_insensitive(message, "no function in scope")) {
        return "invalid_address";
    }
    return "decompile_failed";
}

void fill_repeating_bytes(std::uint8_t* ptr, std::size_t size, const std::string& pattern) {
    if (size == 0 || pattern.empty()) {
        return;
    }

    const std::size_t pattern_size = pattern.size();
    std::size_t copied = 0;
    while (copied < size) {
        const std::size_t chunk_size = std::min(pattern_size, size - copied);
        std::memcpy(ptr + copied, pattern.data(), chunk_size);
        copied += chunk_size;
    }
}

bool checked_add_u64(std::uint64_t left, std::uint64_t right, std::uint64_t* result) {
    if (right > (std::numeric_limits<std::uint64_t>::max() - left)) {
        return false;
    }
    *result = left + right;
    return true;
}

}  // namespace flatline::native_bridge
