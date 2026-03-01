// Native nanobind bridge for flatline -- P2-Step-3a.
// Wires Ghidra decompiler library startup and language/compiler pair enumeration.
// Decompile pipeline remains a stub (internal_error) until subsequent step.

#include <nanobind/nanobind.h>
#include <nanobind/stl/pair.h>
#include <nanobind/stl/string.h>
#include <nanobind/stl/vector.h>

#include <cstdint>
#include <mutex>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

// Ghidra headers -- sleigh_arch.hh gives us SleighArchitecture, LanguageDescription,
// CompilerTag without pulling in the console/test/rulecompile headers that
// libdecomp.hh would transitively include.
#include "sleigh_arch.hh"

// Forward-declare the library init function from libdecomp.cc so we avoid
// including libdecomp.hh (which drags in ifacedecomp.hh -> callgraph.hh etc.).
namespace ghidra {
extern void startDecompilerLibrary(const char *sleighhome);
}

namespace nb = nanobind;

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

// -- MemoryLoadImageSkeleton (retained for future decompile pipeline) ---------

class MemoryLoadImageSkeleton {
public:
    MemoryLoadImageSkeleton(std::uint64_t base_address, nb::bytes memory_image)
        : base_address_(base_address), memory_image_(nb::cast<std::string>(memory_image)) {}

    nb::bytes read(std::uint64_t address, std::size_t size) const {
        const std::uint64_t start = base_address_;
        const std::uint64_t end = base_address_ + memory_image_.size();
        if (address < start || address + size > end) {
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
            const auto &descriptions =
                ghidra::SleighArchitecture::getDescriptions();
            for (const auto &lang : descriptions) {
                const std::string &lang_id = lang.getId();
                int num_compilers = lang.numCompilers();
                for (int i = 0; i < num_compilers; ++i) {
                    pairs.emplace_back(lang_id, lang.getCompiler(i).getId());
                }
            }
        } catch (const ghidra::LowlevelError &) {
            // Return empty list on failure -- bridge layer falls back to
            // runtime_data_pairs enumeration.
            return {};
        }
        return pairs;
    }

    nb::dict decompile_function(const nb::dict &request) const {
        nb::dict metadata;
        metadata["decompiler_version"] = "";
        if (request.contains("language_id")) {
            metadata["language_id"] = request["language_id"];
        } else {
            metadata["language_id"] = "";
        }
        if (request.contains("compiler_spec")) {
            metadata["compiler_spec"] = request["compiler_spec"];
        } else {
            metadata["compiler_spec"] = "";
        }
        metadata["diagnostics"] = nb::dict();

        nb::dict error;
        error["category"] = "internal_error";
        error["message"] = "native decompile pipeline not yet implemented";
        error["retryable"] = false;

        nb::dict result;
        result["c_code"] = nb::none();
        result["function_info"] = nb::none();
        result["warnings"] = nb::list();
        result["error"] = error;
        result["metadata"] = metadata;
        return result;
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
