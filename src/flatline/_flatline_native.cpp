// Native nanobind bridge for flatline.
// P2-Step-3b: wire per-request decompile pipeline with structured errors.

#include <nanobind/nanobind.h>
#include <nanobind/stl/pair.h>
#include <nanobind/stl/string.h>
#include <nanobind/stl/vector.h>

#include <cstdint>
#include <cstring>
#include <iomanip>
#include <limits>
#include <memory>
#include <mutex>
#include <optional>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <typeinfo>
#include <utility>
#include <vector>

#include "action.hh"
#include "comment.hh"
#include "database.hh"
#include "funcdata.hh"
#include "jumptable.hh"
#include "loadimage.hh"
#include "sleigh_arch.hh"
#include "type.hh"
#include "xml.hh"

// Forward-declare library startup from libdecomp.cc to avoid including
// libdecomp.hh (which drags in console/rulecompile headers not compiled here).
namespace ghidra {
extern void startDecompilerLibrary(const char *sleighhome);
}

namespace nb = nanobind;

namespace {

struct NativeRequest {
    std::string memory_image;
    std::uint64_t base_address;
    std::uint64_t function_address;
    std::string language_id;
    std::optional<std::string> compiler_spec;
    std::uint32_t max_instructions;
};

constexpr std::uint32_t kDefaultMaxInstructions = 100000;

static std::string to_lower_ascii(std::string value) {
    for (char &ch : value) {
        if (ch >= 'A' && ch <= 'Z') {
            ch = static_cast<char>(ch - 'A' + 'a');
        }
    }
    return value;
}

static bool contains_case_insensitive(const std::string &haystack, const std::string &needle) {
    if (needle.empty()) {
        return true;
    }
    std::string lower_haystack = to_lower_ascii(haystack);
    std::string lower_needle = to_lower_ascii(needle);
    return lower_haystack.find(lower_needle) != std::string::npos;
}

static bool checked_add_u64(std::uint64_t left, std::uint64_t right, std::uint64_t *result) {
    if (right > (std::numeric_limits<std::uint64_t>::max() - left)) {
        return false;
    }
    *result = left + right;
    return true;
}

static std::string require_string_field(const nb::dict &request, const char *field_name) {
    if (!request.contains(field_name)) {
        throw std::invalid_argument(std::string("missing required field: ") + field_name);
    }
    return nb::cast<std::string>(request[field_name]);
}

static std::uint64_t require_u64_field(const nb::dict &request, const char *field_name) {
    if (!request.contains(field_name)) {
        throw std::invalid_argument(std::string("missing required field: ") + field_name);
    }
    std::int64_t value = nb::cast<std::int64_t>(request[field_name]);
    if (value < 0) {
        throw std::invalid_argument(std::string(field_name) + " must be non-negative");
    }
    return static_cast<std::uint64_t>(value);
}

static std::optional<std::string> optional_string_field(const nb::dict &request, const char *field_name) {
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

static std::uint32_t require_positive_u32_value(nb::handle value, const char *field_name) {
    std::int64_t parsed_value = nb::cast<std::int64_t>(value);
    if (parsed_value <= 0) {
        throw std::invalid_argument(std::string(field_name) + " must be positive");
    }
    if (parsed_value > static_cast<std::int64_t>(std::numeric_limits<std::uint32_t>::max())) {
        throw std::invalid_argument(std::string(field_name) + " exceeds supported range");
    }
    return static_cast<std::uint32_t>(parsed_value);
}

static std::uint32_t parse_max_instructions(const nb::dict &request) {
    if (!request.contains("analysis_budget")) {
        return kDefaultMaxInstructions;
    }

    nb::object raw_budget = request["analysis_budget"];
    if (raw_budget.is_none()) {
        return kDefaultMaxInstructions;
    }

    nb::dict budget = nb::cast<nb::dict>(raw_budget);
    std::set<std::string> unsupported_keys;
    for (const auto &item : budget) {
        const std::string key = nb::cast<std::string>(item.first);
        if (key != "max_instructions") {
            unsupported_keys.insert(key);
        }
    }
    if (!unsupported_keys.empty()) {
        std::string joined;
        for (const auto &key : unsupported_keys) {
            if (!joined.empty()) {
                joined += ", ";
            }
            joined += key;
        }
        throw std::invalid_argument(
            "analysis_budget contains unsupported fields: " + joined
        );
    }

    if (!budget.contains("max_instructions")) {
        return kDefaultMaxInstructions;
    }
    return require_positive_u32_value(
        budget["max_instructions"],
        "analysis_budget.max_instructions"
    );
}

static NativeRequest parse_request(const nb::dict &request) {
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
    return parsed;
}

static std::string make_function_name(std::uint64_t address) {
    std::ostringstream stream;
    stream << "func_" << std::hex << std::nouppercase << address;
    return stream.str();
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

static nb::dict type_info_to_dict(const ghidra::Datatype *datatype) {
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

static nb::object storage_info_from_address(const ghidra::Address &address, std::int64_t size) {
    if (address.isInvalid() || address.getSpace() == nullptr || size <= 0) {
        return nb::none();
    }
    nb::dict storage;
    storage["space"] = address.getSpace()->getName();
    storage["offset"] = static_cast<std::uint64_t>(address.getOffset());
    storage["size"] = size;
    return storage;
}

static nb::object storage_info_from_symbol(const ghidra::Symbol *symbol) {
    if (symbol == nullptr) {
        return nb::none();
    }
    ghidra::SymbolEntry *entry = symbol->getFirstWholeMap();
    if (entry == nullptr) {
        return nb::none();
    }
    return storage_info_from_address(entry->getAddr(), entry->getSize());
}

static nb::dict diagnostics_to_dict(const ghidra::Funcdata &function) {
    nb::dict diagnostics;
    diagnostics["is_complete"] = function.isProcComplete();
    diagnostics["has_unreachable_blocks"] = function.hasUnreachableBlocks();
    diagnostics["has_unimplemented"] = function.hasUnimplemented();
    diagnostics["has_bad_data"] = function.hasBadData();
    diagnostics["has_no_code"] = function.hasNoCode();
    return diagnostics;
}

static nb::list warnings_from_comment_database(const ghidra::Funcdata &function, const ghidra::Architecture &architecture) {
    nb::list warnings;
    if (architecture.commentdb == nullptr) {
        return warnings;
    }
    const ghidra::Address &function_address = function.getAddress();
    ghidra::CommentSet::const_iterator iter = architecture.commentdb->beginComment(function_address);
    ghidra::CommentSet::const_iterator end = architecture.commentdb->endComment(function_address);
    for (; iter != end; ++iter) {
        const ghidra::Comment *comment = *iter;
        if (comment == nullptr) {
            continue;
        }
        if ((comment->getType() & (ghidra::Comment::warning | ghidra::Comment::warningheader)) == 0) {
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

static nb::list call_sites_to_list(const ghidra::Funcdata &function) {
    nb::list call_sites;
    const int call_count = function.numCalls();
    for (int index = 0; index < call_count; ++index) {
        ghidra::FuncCallSpecs *call_spec = function.getCallSpecs(index);
        if (call_spec == nullptr) {
            continue;
        }
        nb::dict call_site;
        ghidra::PcodeOp *call_op = call_spec->getOp();
        if (call_op != nullptr && !call_op->getAddr().isInvalid()) {
            call_site["instruction_address"] = static_cast<std::uint64_t>(call_op->getAddr().getOffset());
        } else {
            call_site["instruction_address"] = static_cast<std::uint64_t>(function.getAddress().getOffset());
        }

        const ghidra::Address &target = call_spec->getEntryAddress();
        if (!target.isInvalid()) {
            call_site["target_address"] = static_cast<std::uint64_t>(target.getOffset());
        } else {
            call_site["target_address"] = nb::none();
        }
        call_sites.append(call_site);
    }
    return call_sites;
}

static nb::list jump_tables_to_list(ghidra::Funcdata &function) {
    nb::list jump_tables;
    const int jump_table_count = function.numJumpTables();
    for (int index = 0; index < jump_table_count; ++index) {
        ghidra::JumpTable *jump_table = function.getJumpTable(index);
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
        const ghidra::Address &switch_address = jump_table->getOpAddress();
        if (!switch_address.isInvalid()) {
            jump_table_item["switch_address"] = static_cast<std::uint64_t>(switch_address.getOffset());
        } else {
            jump_table_item["switch_address"] = static_cast<std::uint64_t>(function.getAddress().getOffset());
        }
        jump_table_item["target_count"] = static_cast<int>(target_addresses.size());
        jump_table_item["target_addresses"] = target_addresses;
        jump_tables.append(jump_table_item);
    }
    return jump_tables;
}

static nb::list local_variables_to_list(const ghidra::Funcdata &function) {
    nb::list local_variables;
    const ghidra::ScopeLocal *local_scope = function.getScopeLocal();
    if (local_scope == nullptr) {
        return local_variables;
    }

    std::set<std::uint64_t> seen_symbol_ids;
    for (ghidra::MapIterator iter = local_scope->begin(); iter != local_scope->end(); ++iter) {
        const ghidra::SymbolEntry *entry = *iter;
        if (entry == nullptr) {
            continue;
        }
        ghidra::Symbol *symbol = entry->getSymbol();
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
        if (dynamic_cast<ghidra::FunctionSymbol *>(symbol) != nullptr) {
            continue;
        }

        nb::dict variable;
        std::string variable_name = symbol->getName();
        if (variable_name.empty()) {
            variable_name = "local_" + std::to_string(local_variables.size());
        }
        variable["name"] = variable_name;
        variable["type"] = type_info_to_dict(symbol->getType());
        variable["storage"] = storage_info_from_symbol(symbol);
        local_variables.append(variable);
    }
    return local_variables;
}

static nb::dict prototype_to_dict(const ghidra::FuncProto &prototype) {
    nb::dict prototype_info;
    prototype_info["calling_convention"] = prototype.getModelName();

    nb::list parameters;
    const int parameter_count = prototype.numParams();
    for (int index = 0; index < parameter_count; ++index) {
        ghidra::ProtoParameter *parameter = prototype.getParam(index);
        if (parameter == nullptr) {
            continue;
        }

        nb::dict parameter_item;
        std::string parameter_name = parameter->getName();
        if (parameter_name.empty()) {
            parameter_name = "param_" + std::to_string(index);
        }
        parameter_item["name"] = parameter_name;
        parameter_item["type"] = type_info_to_dict(parameter->getType());
        parameter_item["index"] = index;
        parameter_item["storage"] = storage_info_from_address(parameter->getAddress(), parameter->getSize());
        parameters.append(parameter_item);
    }

    prototype_info["parameters"] = parameters;
    prototype_info["return_type"] = type_info_to_dict(prototype.getOutputType());
    prototype_info["is_noreturn"] = prototype.isNoReturn();
    prototype_info["has_this_pointer"] = prototype.hasThisPointer();
    prototype_info["has_input_errors"] = prototype.hasInputErrors();
    prototype_info["has_output_errors"] = prototype.hasOutputErrors();
    return prototype_info;
}

static nb::dict function_info_to_dict(ghidra::Funcdata &function) {
    nb::dict function_info;
    function_info["name"] = function.getName();
    function_info["entry_address"] = static_cast<std::uint64_t>(function.getAddress().getOffset());
    function_info["size"] = function.getSize();
    function_info["is_complete"] = function.isProcComplete();
    function_info["prototype"] = prototype_to_dict(function.getFuncProto());
    function_info["local_variables"] = local_variables_to_list(function);
    function_info["call_sites"] = call_sites_to_list(function);
    function_info["jump_tables"] = jump_tables_to_list(function);
    function_info["diagnostics"] = diagnostics_to_dict(function);
    function_info["varnode_count"] = function.numVarnodes();
    return function_info;
}

static std::string classifier_for_lowlevel_error(const std::string &message) {
    if (contains_case_insensitive(message, "no sleigh specification")
        || contains_case_insensitive(message, "architecture string does not look like sleigh id")) {
        return "unsupported_target";
    }
    if (contains_case_insensitive(message, "outside memory_image")
        || contains_case_insensitive(message, "outside memory image")
        || contains_case_insensitive(message, "no function at this offset")
        || contains_case_insensitive(message, "no function in scope")) {
        return "invalid_address";
    }
    return "decompile_failed";
}

static std::string decompiler_version_string() {
    std::ostringstream stream;
    stream << "ghidra-" << ghidra::ArchitectureCapability::getMajorVersion()
           << "." << ghidra::ArchitectureCapability::getMinorVersion();
    return stream.str();
}

static nb::dict metadata_dict(
    const std::string &decompiler_version,
    const std::string &language_id,
    const std::string &compiler_spec,
    const nb::dict &diagnostics
) {
    nb::dict metadata;
    metadata["decompiler_version"] = decompiler_version;
    metadata["language_id"] = language_id;
    metadata["compiler_spec"] = compiler_spec;
    metadata["diagnostics"] = diagnostics;
    return metadata;
}

static nb::dict error_result(
    const std::string &category,
    const std::string &message,
    const std::string &decompiler_version,
    const std::string &language_id,
    const std::string &compiler_spec
) {
    nb::dict error;
    error["category"] = category;
    error["message"] = message;
    error["retryable"] = false;

    nb::dict result;
    result["c_code"] = nb::none();
    result["function_info"] = nb::none();
    result["warnings"] = nb::list();
    result["error"] = error;
    result["metadata"] = metadata_dict(
        decompiler_version,
        language_id,
        compiler_spec,
        nb::dict()
    );
    return result;
}

static nb::dict success_result(
    const std::string &c_code,
    const nb::dict &function_info,
    const nb::list &warnings,
    const std::string &decompiler_version,
    const std::string &language_id,
    const std::string &compiler_spec,
    const nb::dict &diagnostics
) {
    nb::dict result;
    result["c_code"] = c_code;
    result["function_info"] = function_info;
    result["warnings"] = warnings;
    result["error"] = nb::none();
    result["metadata"] = metadata_dict(
        decompiler_version,
        language_id,
        compiler_spec,
        diagnostics
    );
    return result;
}

class FlatlineMemoryLoadImage : public ghidra::LoadImage {
public:
    FlatlineMemoryLoadImage(
        std::string filename,
        std::string arch_type,
        std::uint64_t base_address,
        std::string memory_image
    )
        : ghidra::LoadImage(std::move(filename)),
          arch_type_(std::move(arch_type)),
          base_address_(base_address),
          memory_image_(std::move(memory_image)) {}

    void loadFill(ghidra::uint1 *ptr, ghidra::int4 size, const ghidra::Address &address) override {
        if (size < 0) {
            throw ghidra::DataUnavailError("negative load size is invalid");
        }
        if (size == 0) {
            return;
        }
        if (address.isInvalid()) {
            throw ghidra::DataUnavailError("invalid address requested");
        }

        const std::uint64_t requested_start = static_cast<std::uint64_t>(address.getOffset());
        std::uint64_t requested_end = 0;
        if (!checked_add_u64(requested_start, static_cast<std::uint64_t>(size), &requested_end)) {
            throw ghidra::DataUnavailError("requested address range overflow");
        }

        std::uint64_t image_end = 0;
        if (!checked_add_u64(base_address_, static_cast<std::uint64_t>(memory_image_.size()), &image_end)) {
            throw ghidra::DataUnavailError("memory image bounds overflow");
        }
        if (requested_start < base_address_ || requested_end > image_end) {
            throw ghidra::DataUnavailError("requested address range is outside memory_image");
        }

        const std::size_t offset = static_cast<std::size_t>(requested_start - base_address_);
        std::memcpy(ptr, memory_image_.data() + offset, static_cast<std::size_t>(size));
    }

    std::string getArchType() const override {
        return arch_type_;
    }

    void adjustVma(long adjust) override {
        if (adjust >= 0) {
            base_address_ += static_cast<std::uint64_t>(adjust);
            return;
        }
        base_address_ -= static_cast<std::uint64_t>(-adjust);
    }

private:
    std::string arch_type_;
    std::uint64_t base_address_;
    std::string memory_image_;
};

class FlatlineSleighArchitecture : public ghidra::SleighArchitecture {
public:
    FlatlineSleighArchitecture(
        std::string target_id,
        std::string language_id,
        std::uint64_t base_address,
        std::string memory_image,
        std::ostream *error_stream
    )
        : ghidra::SleighArchitecture("<flatline-memory>", std::move(target_id), error_stream),
          language_id_(std::move(language_id)),
          base_address_(base_address),
          memory_image_(std::move(memory_image)) {}

protected:
    void buildLoader(ghidra::DocumentStorage &store) override {
        (void)store;
        ghidra::SleighArchitecture::collectSpecFiles(*errorstream);
        loader = new FlatlineMemoryLoadImage(
            "<flatline-memory>",
            language_id_,
            base_address_,
            memory_image_
        );
    }

private:
    std::string language_id_;
    std::uint64_t base_address_;
    std::string memory_image_;
};

}  // namespace

// -- Process-global one-time initialization -----------------------------------

static std::once_flag g_init_flag;

static void ensure_library_initialized(const std::string &runtime_data_dir) {
    std::call_once(g_init_flag, [&runtime_data_dir]() {
        if (runtime_data_dir.empty()) {
            ghidra::startDecompilerLibrary(nullptr);
        } else {
            ghidra::startDecompilerLibrary(runtime_data_dir.c_str());
        }
    });
}

// -- MemoryLoadImageSkeleton (public helper kept for compatibility) ----------

class MemoryLoadImageSkeleton {
public:
    MemoryLoadImageSkeleton(std::uint64_t base_address, nb::bytes memory_image)
        : base_address_(base_address), memory_image_(memory_image.c_str(), memory_image.size()) {}

    nb::bytes read(std::uint64_t address, std::size_t size) const {
        std::uint64_t end = 0;
        if (!checked_add_u64(base_address_, static_cast<std::uint64_t>(memory_image_.size()), &end)) {
            throw nb::value_error("memory_image bounds overflow");
        }
        std::uint64_t requested_end = 0;
        if (!checked_add_u64(address, static_cast<std::uint64_t>(size), &requested_end)) {
            throw nb::value_error("requested address range overflow");
        }
        if (address < base_address_ || requested_end > end) {
            throw nb::value_error("requested address range is outside memory_image");
        }

        const std::size_t offset = static_cast<std::size_t>(address - base_address_);
        return nb::bytes(memory_image_.data() + offset, size);
    }

private:
    std::uint64_t base_address_;
    std::string memory_image_;
};

// -- NativeSession ------------------------------------------------------------

class NativeSession {
public:
    explicit NativeSession(std::string runtime_data_dir)
        : runtime_data_dir_(std::move(runtime_data_dir)) {
        ensure_library_initialized(runtime_data_dir_);
    }

    std::vector<std::pair<std::string, std::string>> list_language_compilers() const {
        std::vector<std::pair<std::string, std::string>> pairs;
        try {
            const auto &descriptions = ghidra::SleighArchitecture::getDescriptions();
            for (const auto &language : descriptions) {
                const std::string &language_id = language.getId();
                const int compiler_count = language.numCompilers();
                for (int index = 0; index < compiler_count; ++index) {
                    pairs.emplace_back(language_id, language.getCompiler(index).getId());
                }
            }
        } catch (const ghidra::LowlevelError &) {
            // Bridge layer will fall back to runtime-data enumeration.
            return {};
        }
        return pairs;
    }

    nb::dict decompile_function(const nb::dict &request) const {
        const std::string fallback_decompiler_version = decompiler_version_string();
        std::string fallback_language_id;
        std::string fallback_compiler_spec;
        try {
            fallback_language_id = require_string_field(request, "language_id");
        } catch (...) {
            fallback_language_id.clear();
        }
        try {
            std::optional<std::string> compiler_spec = optional_string_field(request, "compiler_spec");
            fallback_compiler_spec = compiler_spec.value_or("");
        } catch (...) {
            fallback_compiler_spec.clear();
        }

        try {
            NativeRequest native_request = parse_request(request);
            const std::string selected_compiler = native_request.compiler_spec.value_or("default");

            std::uint64_t memory_end = 0;
            if (!checked_add_u64(
                    native_request.base_address,
                    static_cast<std::uint64_t>(native_request.memory_image.size()),
                    &memory_end
                )) {
                return error_result(
                    "invalid_argument",
                    "memory_image range overflows 64-bit address space",
                    fallback_decompiler_version,
                    native_request.language_id,
                    selected_compiler
                );
            }
            if (native_request.function_address < native_request.base_address
                || native_request.function_address >= memory_end) {
                return error_result(
                    "invalid_address",
                    "function_address is outside memory_image range",
                    fallback_decompiler_version,
                    native_request.language_id,
                    selected_compiler
                );
            }

            const std::string target_id = native_request.language_id + ":" + selected_compiler;
            std::ostringstream ghidra_errors;
            FlatlineSleighArchitecture architecture(
                target_id,
                native_request.language_id,
                native_request.base_address,
                std::move(native_request.memory_image),
                &ghidra_errors
            );

            ghidra::DocumentStorage store;
            architecture.init(store);
            architecture.max_instructions = native_request.max_instructions;
            architecture.setPrintLanguage("c-language");

            ghidra::Scope *global_scope = architecture.symboltab->getGlobalScope();
            if (global_scope == nullptr) {
                return error_result(
                    "internal_error",
                    "global scope is unavailable",
                    fallback_decompiler_version,
                    native_request.language_id,
                    selected_compiler
                );
            }

            const ghidra::Address function_entry(
                architecture.getDefaultCodeSpace(),
                native_request.function_address
            );
            ghidra::Funcdata *function = global_scope->findFunction(function_entry);
            if (function == nullptr) {
                ghidra::FunctionSymbol *symbol = global_scope->addFunction(
                    function_entry,
                    make_function_name(native_request.function_address)
                );
                if (symbol == nullptr) {
                    return error_result(
                        "internal_error",
                        "unable to create function symbol",
                        fallback_decompiler_version,
                        native_request.language_id,
                        selected_compiler
                    );
                }
                function = symbol->getFunction();
            }
            if (function == nullptr) {
                return error_result(
                    "internal_error",
                    "function object is unavailable",
                    fallback_decompiler_version,
                    native_request.language_id,
                    selected_compiler
                );
            }

            ghidra::Action *action = architecture.allacts.getCurrent();
            if (action == nullptr) {
                return error_result(
                    "internal_error",
                    "decompile action pipeline is unavailable",
                    fallback_decompiler_version,
                    native_request.language_id,
                    selected_compiler
                );
            }

            action->reset(*function);
            const int status = action->perform(*function);

            std::ostringstream output_stream;
            architecture.print->setMarkup(false);
            architecture.print->setOutputStream(&output_stream);
            architecture.print->docFunction(function);

            nb::dict diagnostics = diagnostics_to_dict(*function);
            nb::dict function_info = function_info_to_dict(*function);
            nb::list warnings = warnings_from_comment_database(*function, architecture);
            if (status < 0) {
                nb::dict warning;
                warning["code"] = "analyze.W002";
                warning["message"] = "decompile action pipeline returned partial result";
                warning["phase"] = "analyze";
                warnings.append(warning);
            }

            return success_result(
                output_stream.str(),
                function_info,
                warnings,
                fallback_decompiler_version,
                native_request.language_id,
                selected_compiler,
                diagnostics
            );
        } catch (const std::invalid_argument &error) {
            return error_result(
                "invalid_argument",
                error.what(),
                fallback_decompiler_version,
                fallback_language_id,
                fallback_compiler_spec
            );
        } catch (const ghidra::DataUnavailError &error) {
            return error_result(
                "invalid_address",
                error.explain,
                fallback_decompiler_version,
                fallback_language_id,
                fallback_compiler_spec
            );
        } catch (const ghidra::DecoderError &error) {
            return error_result(
                "decompile_failed",
                error.explain,
                fallback_decompiler_version,
                fallback_language_id,
                fallback_compiler_spec
            );
        } catch (const ghidra::LowlevelError &error) {
            return error_result(
                classifier_for_lowlevel_error(error.explain),
                error.explain,
                fallback_decompiler_version,
                fallback_language_id,
                fallback_compiler_spec
            );
        } catch (const std::bad_cast &error) {
            return error_result(
                "decompile_failed",
                std::string("native decompile type error: ") + error.what(),
                fallback_decompiler_version,
                fallback_language_id,
                fallback_compiler_spec
            );
        } catch (const std::exception &error) {
            return error_result(
                "internal_error",
                std::string("native exception: ") + error.what(),
                fallback_decompiler_version,
                fallback_language_id,
                fallback_compiler_spec
            );
        } catch (...) {
            return error_result(
                "internal_error",
                "native exception: unknown error",
                fallback_decompiler_version,
                fallback_language_id,
                fallback_compiler_spec
            );
        }
    }

    void close() {}

private:
    std::string runtime_data_dir_;
};

// -- Module definition --------------------------------------------------------

NB_MODULE(_flatline_native, m) {
    m.doc() = "flatline native bridge (nanobind + Ghidra decompiler)";

    nb::class_<MemoryLoadImageSkeleton>(m, "MemoryLoadImageSkeleton")
        .def(nb::init<std::uint64_t, nb::bytes>())
        .def("read", &MemoryLoadImageSkeleton::read);

    nb::class_<NativeSession>(m, "NativeSession")
        .def(nb::init<std::string>())
        .def("list_language_compilers", &NativeSession::list_language_compilers)
        .def("decompile_function", &NativeSession::decompile_function)
        .def("close", &NativeSession::close);

    m.def(
        "create_session",
        [](const nb::object &runtime_data_dir_obj) {
            if (runtime_data_dir_obj.is_none()) {
                return NativeSession("");
            }
            return NativeSession(nb::cast<std::string>(runtime_data_dir_obj));
        },
        nb::arg("runtime_data_dir") = nb::none()
    );
}
