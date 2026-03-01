// Experimental nanobind bridge skeleton for P2-Step-2.
// This is intentionally minimal: it establishes the extension-module boundary,
// a session object, and a LoadImage-like memory reader helper.

#include <nanobind/nanobind.h>
#include <nanobind/stl/pair.h>
#include <nanobind/stl/string.h>
#include <nanobind/stl/vector.h>

#include <cstdint>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace nb = nanobind;

class MemoryLoadImageSkeleton {
public:
    MemoryLoadImageSkeleton(std::uint64_t base_address, nb::bytes memory_image)
        : base_address_(base_address), memory_image_(static_cast<std::string>(memory_image)) {}

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

class SessionSkeleton {
public:
    explicit SessionSkeleton(std::string runtime_data_dir)
        : runtime_data_dir_(std::move(runtime_data_dir)) {}

    std::vector<std::pair<std::string, std::string>> list_language_compilers() const {
        return {};
    }

    nb::dict decompile_function(const nb::dict &request) const {
        nb::dict metadata;
        metadata["decompiler_version"] = "";
        metadata["language_id"] = request.contains("language_id") ? request["language_id"] : "";
        metadata["compiler_spec"] = request.contains("compiler_spec") ? request["compiler_spec"] : "";
        metadata["diagnostics"] = nb::dict();

        nb::dict error;
        error["category"] = "internal_error";
        error["message"] = "native bridge skeleton: decompile pipeline not implemented";
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

NB_MODULE(_flatline_native, m) {
    m.doc() = "flatline native bridge skeleton (nanobind)";

    nb::class_<MemoryLoadImageSkeleton>(m, "MemoryLoadImageSkeleton")
        .def(nb::init<std::uint64_t, nb::bytes>())
        .def("read", &MemoryLoadImageSkeleton::read);

    nb::class_<SessionSkeleton>(m, "SessionSkeleton")
        .def(nb::init<std::string>())
        .def("list_language_compilers", &SessionSkeleton::list_language_compilers)
        .def("decompile_function", &SessionSkeleton::decompile_function)
        .def("close", &SessionSkeleton::close);

    m.def(
        "create_session",
        [](const nb::object &runtime_data_dir_obj) {
            if (runtime_data_dir_obj.is_none()) {
                return SessionSkeleton("");
            }
            return SessionSkeleton(nb::cast<std::string>(runtime_data_dir_obj));
        },
        nb::arg("runtime_data_dir") = nb::none()
    );
}
