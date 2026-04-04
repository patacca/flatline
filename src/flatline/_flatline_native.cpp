// Native nanobind bridge for flatline.
// P2-Step-3b: wire per-request decompile pipeline with structured errors.

#include <nanobind/nanobind.h>

#include "_flatline_native_memory.h"
#include "_flatline_native_session.h"

namespace nb = nanobind;

// -- Module definition --------------------------------------------------------

NB_MODULE(_flatline_native, m) {
    m.doc() = "flatline native bridge (nanobind + Ghidra decompiler)";

    nb::class_<MemoryLoadImageSkeleton>(m, "MemoryLoadImageSkeleton")
        .def(nb::init<std::uint64_t, nb::bytes, nb::object>(), nb::arg("base_address"),
             nb::arg("memory_image"), nb::arg("tail_padding") = nb::none())
        .def("read", &MemoryLoadImageSkeleton::read);

    nb::class_<NativeSession>(m, "NativeSession")
        .def(nb::init<std::string>())
        .def("list_language_compilers", &NativeSession::list_language_compilers)
        .def("decompile_function", &NativeSession::decompile_function)
        .def("close", &NativeSession::close);

    m.def(
        "create_session",
        [](const nb::object& runtime_data_dir_obj) {
            if (runtime_data_dir_obj.is_none()) {
                return NativeSession("");
            }
            return NativeSession(nb::cast<std::string>(runtime_data_dir_obj));
        },
        nb::arg("runtime_data_dir") = nb::none());
}
