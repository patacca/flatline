#include "session.h"

#include <cstdint>
#include <cstring>
#include <mutex>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>

#include "action.hh"
#include "capability.hh"
#include "database.hh"
#include "funcdata.hh"
#include "loadimage.hh"
#include "shared.h"
#include "sleigh_arch.hh"
#include "xml.hh"

namespace nb = nanobind;

// Forward-declare library startup from libdecomp.cc to avoid including
// libdecomp.hh (which drags in console/rulecompile headers not compiled here).
namespace ghidra {
extern void startDecompilerLibrary(const char* sleighhome);
}

namespace {

// -- Process-global one-time initialization -----------------------------------

static std::once_flag g_init_flag;

static void ensure_library_initialized(const std::string& runtime_data_dir) {
    std::call_once(g_init_flag, [runtime_data_dir]() {
        if (runtime_data_dir.empty()) {
            ghidra::startDecompilerLibrary(nullptr);
        } else {
            ghidra::startDecompilerLibrary(runtime_data_dir.c_str());
        }
    });
}

static std::string decompiler_version_string() {
    std::ostringstream stream;
    stream << "ghidra-" << ghidra::ArchitectureCapability::getMajorVersion() << "."
           << ghidra::ArchitectureCapability::getMinorVersion();
    return stream.str();
}

static std::string make_function_name(std::uint64_t address) {
    std::ostringstream stream;
    stream << "func_" << std::hex << std::nouppercase << address;
    return stream.str();
}

class FlatlineMemoryLoadImage : public ghidra::LoadImage {
   public:
    FlatlineMemoryLoadImage(std::string filename, std::string arch_type,
                            std::uint64_t base_address, std::string memory_image,
                            std::optional<std::string> tail_padding)
        : ghidra::LoadImage(std::move(filename)),
          arch_type_(std::move(arch_type)),
          base_address_(base_address),
          memory_image_(std::move(memory_image)),
          tail_padding_(std::move(tail_padding)) {}

    void loadFill(ghidra::uint1* ptr, ghidra::int4 size, const ghidra::Address& address) override {
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
        if (!flatline::native_bridge::checked_add_u64(
                requested_start, static_cast<std::uint64_t>(size), &requested_end)) {
            throw ghidra::DataUnavailError("requested address range overflow");
        }

        std::uint64_t image_end = 0;
        if (!flatline::native_bridge::checked_add_u64(
                base_address_, static_cast<std::uint64_t>(memory_image_.size()), &image_end)) {
            throw ghidra::DataUnavailError("memory image bounds overflow");
        }
        if (requested_start < base_address_ || requested_start >= image_end) {
            throw ghidra::DataUnavailError("requested address range is outside memory_image");
        }

        const std::size_t offset = static_cast<std::size_t>(requested_start - base_address_);
        if (requested_end > image_end) {
            if (!tail_padding_.has_value()) {
                throw ghidra::DataUnavailError("requested address range is outside memory_image");
            }
            const std::size_t available_size =
                static_cast<std::size_t>(image_end - requested_start);
            std::memcpy(ptr, memory_image_.data() + offset, available_size);
            flatline::native_bridge::fill_repeating_bytes(
                reinterpret_cast<std::uint8_t*>(ptr + available_size),
                static_cast<std::size_t>(size) - available_size, *tail_padding_);
            return;
        }

        std::memcpy(ptr, memory_image_.data() + offset, static_cast<std::size_t>(size));
    }

    std::string getArchType() const override { return arch_type_; }

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
    std::optional<std::string> tail_padding_;
};

class FlatlineSleighArchitecture : public ghidra::SleighArchitecture {
   public:
    FlatlineSleighArchitecture(std::string target_id, std::string language_id,
                               std::uint64_t base_address, std::string memory_image,
                               std::optional<std::string> tail_padding, std::ostream* error_stream)
        : ghidra::SleighArchitecture("<flatline-memory>", std::move(target_id), error_stream),
          language_id_(std::move(language_id)),
          base_address_(base_address),
          memory_image_(std::move(memory_image)),
          tail_padding_(std::move(tail_padding)) {}

   protected:
    void buildLoader(ghidra::DocumentStorage& store) override {
        (void)store;
        ghidra::SleighArchitecture::collectSpecFiles(*errorstream);
        loader = new FlatlineMemoryLoadImage("<flatline-memory>", language_id_, base_address_,
                                             memory_image_, tail_padding_);
    }

   private:
    std::string language_id_;
    std::uint64_t base_address_;
    std::string memory_image_;
    std::optional<std::string> tail_padding_;
};

}  // namespace

NativeSession::NativeSession(std::string runtime_data_dir)
    : runtime_data_dir_(std::move(runtime_data_dir)) {
    ensure_library_initialized(runtime_data_dir_);
}

std::vector<std::pair<std::string, std::string>> NativeSession::list_language_compilers() const {
    std::vector<std::pair<std::string, std::string>> pairs;
    try {
        const auto& descriptions = ghidra::SleighArchitecture::getDescriptions();
        for (const auto& language : descriptions) {
            const std::string& language_id = language.getId();
            const int compiler_count = language.numCompilers();
            for (int index = 0; index < compiler_count; ++index) {
                pairs.emplace_back(language_id, language.getCompiler(index).getId());
            }
        }
    } catch (const ghidra::LowlevelError&) {
        // Bridge layer will fall back to runtime-data enumeration.
        return {};
    }
    return pairs;
}

nb::dict NativeSession::decompile_function(const nb::dict& request) const {
    const std::string fallback_decompiler_version = decompiler_version_string();
    std::string fallback_language_id;
    std::string fallback_compiler_spec;
    try {
        fallback_language_id = nb::cast<std::string>(request["language_id"]);
    } catch (...) {
        fallback_language_id.clear();
    }
    try {
        if (request.contains("compiler_spec") && !request["compiler_spec"].is_none()) {
            fallback_compiler_spec = nb::cast<std::string>(request["compiler_spec"]);
        }
    } catch (...) {
        fallback_compiler_spec.clear();
    }

    try {
        flatline::native_bridge::NativeRequest native_request =
            flatline::native_bridge::parse_request(request);
        const std::string selected_compiler = native_request.compiler_spec.value_or("default");

        std::uint64_t memory_end = 0;
        if (!flatline::native_bridge::checked_add_u64(
                native_request.base_address,
                static_cast<std::uint64_t>(native_request.memory_image.size()), &memory_end)) {
            return flatline::native_bridge::error_result(
                "invalid_argument", "memory_image range overflows 64-bit address space",
                fallback_decompiler_version, native_request.language_id, selected_compiler);
        }
        if (native_request.function_address < native_request.base_address ||
            native_request.function_address >= memory_end) {
            return flatline::native_bridge::error_result(
                "invalid_address", "function_address is outside memory_image range",
                fallback_decompiler_version, native_request.language_id, selected_compiler);
        }

        const std::string target_id = native_request.language_id + ":" + selected_compiler;
        std::ostringstream ghidra_errors;
        FlatlineSleighArchitecture architecture(
            target_id, native_request.language_id, native_request.base_address,
            std::move(native_request.memory_image), std::move(native_request.tail_padding),
            &ghidra_errors);

        ghidra::DocumentStorage store;
        architecture.init(store);
        architecture.max_instructions = native_request.max_instructions;
        architecture.setPrintLanguage("c-language");

        ghidra::Scope* global_scope = architecture.symboltab->getGlobalScope();
        if (global_scope == nullptr) {
            return flatline::native_bridge::error_result(
                "internal_error", "global scope is unavailable", fallback_decompiler_version,
                native_request.language_id, selected_compiler);
        }

        const ghidra::Address function_entry(architecture.getDefaultCodeSpace(),
                                             native_request.function_address);
        ghidra::Funcdata* function = global_scope->findFunction(function_entry);
        if (function == nullptr) {
            ghidra::FunctionSymbol* symbol = global_scope->addFunction(
                function_entry, make_function_name(native_request.function_address));
            if (symbol == nullptr) {
                return flatline::native_bridge::error_result(
                    "internal_error", "unable to create function symbol",
                    fallback_decompiler_version, native_request.language_id, selected_compiler);
            }
            function = symbol->getFunction();
        }
        if (function == nullptr) {
            return flatline::native_bridge::error_result(
                "internal_error", "function object is unavailable", fallback_decompiler_version,
                native_request.language_id, selected_compiler);
        }

        ghidra::Action* action = architecture.allacts.getCurrent();
        if (action == nullptr) {
            return flatline::native_bridge::error_result(
                "internal_error", "decompile action pipeline is unavailable",
                fallback_decompiler_version, native_request.language_id, selected_compiler);
        }

        action->reset(*function);
        const int status = action->perform(*function);

        std::ostringstream output_stream;
        architecture.print->setMarkup(false);
        architecture.print->setOutputStream(&output_stream);
        architecture.print->docFunction(function);

        nb::dict diagnostics = flatline::native_bridge::diagnostics_to_dict(*function);
        nb::dict function_info = flatline::native_bridge::function_info_to_dict(*function);
        nb::list warnings =
            flatline::native_bridge::warnings_from_comment_database(*function, architecture);
        nb::object enriched = nb::none();
        if (native_request.enriched) {
            nb::dict enriched_dict;
            enriched_dict["pcode"] = flatline::native_bridge::pcode_to_dict(*function);
            enriched = enriched_dict;
        }
        if (status < 0) {
            nb::dict warning;
            warning["code"] = "analyze.W002";
            warning["message"] = "decompile action pipeline returned partial result";
            warning["phase"] = "analyze";
            warnings.append(warning);
        }

        return flatline::native_bridge::success_result(
            output_stream.str(), function_info, warnings, fallback_decompiler_version,
            native_request.language_id, selected_compiler, diagnostics, enriched);
    } catch (const std::invalid_argument& error) {
        return flatline::native_bridge::error_result("invalid_argument", error.what(),
                                                     fallback_decompiler_version,
                                                     fallback_language_id, fallback_compiler_spec);
    } catch (const ghidra::DataUnavailError& error) {
        return flatline::native_bridge::error_result("invalid_address", error.explain,
                                                     fallback_decompiler_version,
                                                     fallback_language_id, fallback_compiler_spec);
    } catch (const ghidra::DecoderError& error) {
        return flatline::native_bridge::error_result("decompile_failed", error.explain,
                                                     fallback_decompiler_version,
                                                     fallback_language_id, fallback_compiler_spec);
    } catch (const ghidra::LowlevelError& error) {
        return flatline::native_bridge::error_result(
            flatline::native_bridge::classifier_for_lowlevel_error(error.explain), error.explain,
            fallback_decompiler_version, fallback_language_id, fallback_compiler_spec);
    } catch (const std::bad_cast& error) {
        return flatline::native_bridge::error_result(
            "decompile_failed", std::string("native decompile type error: ") + error.what(),
            fallback_decompiler_version, fallback_language_id, fallback_compiler_spec);
    } catch (const std::exception& error) {
        return flatline::native_bridge::error_result(
            "internal_error", std::string("native exception: ") + error.what(),
            fallback_decompiler_version, fallback_language_id, fallback_compiler_spec);
    } catch (...) {
        return flatline::native_bridge::error_result(
            "internal_error", "native exception: unknown error", fallback_decompiler_version,
            fallback_language_id, fallback_compiler_spec);
    }
}

void NativeSession::close() {}
