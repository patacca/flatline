// Native nanobind bridge for flatline.
// P2-Step-3b: wire per-request decompile pipeline with structured errors.

#include <nanobind/nanobind.h>
#include <ogdf/basic/Graph.h>
#include <ogdf/basic/GraphAttributes.h>
#include <ogdf/basic/basic.h>
#include <ogdf/layered/BarycenterHeuristic.h>
#include <ogdf/layered/FastHierarchyLayout.h>
#include <ogdf/layered/OptimalRanking.h>
#include <ogdf/layered/SugiyamaLayout.h>

#include "memory.h"
#include "session.h"

namespace nb = nanobind;

namespace {

long default_graph_attributes() {
    return ogdf::GraphAttributes::nodeGraphics | ogdf::GraphAttributes::edgeGraphics;
}

void bind_ogdf_layout(nb::module_& ogdf_mod) {
    nb::class_<ogdf::NodeElement>(ogdf_mod, "node");
    nb::class_<ogdf::EdgeElement>(ogdf_mod, "edge");

    nb::class_<ogdf::Graph>(ogdf_mod, "Graph")
        .def(nb::init<>())
        .def(
            "newNode", [](ogdf::Graph& graph) { return graph.newNode(); },
            nb::rv_policy::reference_internal)
        .def(
            "newEdge",
            [](ogdf::Graph& graph, ogdf::node source, ogdf::node target) {
                return graph.newEdge(source, target);
            },
            nb::rv_policy::reference_internal)
        .def("numberOfNodes", &ogdf::Graph::numberOfNodes)
        .def("numberOfEdges", &ogdf::Graph::numberOfEdges);

    nb::class_<ogdf::GraphAttributes>(ogdf_mod, "GraphAttributes")
        .def(nb::init<const ogdf::Graph&, long>(), nb::arg("G"),
             nb::arg("initAttributes") = default_graph_attributes())
        .def_static("nodeGraphics_flag",
                    []() { return static_cast<long>(ogdf::GraphAttributes::nodeGraphics); })
        .def_static("edgeGraphics_flag",
                    []() { return static_cast<long>(ogdf::GraphAttributes::edgeGraphics); })
        .def("x",
             [](ogdf::GraphAttributes& attributes, ogdf::node node) { return attributes.x(node); })
        .def("y",
             [](ogdf::GraphAttributes& attributes, ogdf::node node) { return attributes.y(node); })
        .def("width", [](ogdf::GraphAttributes& attributes,
                         ogdf::node node) { return attributes.width(node); })
        .def("height", [](ogdf::GraphAttributes& attributes,
                          ogdf::node node) { return attributes.height(node); })
        .def("setWidth", [](ogdf::GraphAttributes& attributes, ogdf::node node,
                            double width) { attributes.width(node) = width; })
        .def("setHeight", [](ogdf::GraphAttributes& attributes, ogdf::node node, double height) {
            attributes.height(node) = height;
        });

    ogdf_mod.attr("nodeGraphics") = static_cast<long>(ogdf::GraphAttributes::nodeGraphics);
    ogdf_mod.attr("edgeGraphics") = static_cast<long>(ogdf::GraphAttributes::edgeGraphics);

    nb::class_<ogdf::FastHierarchyLayout>(ogdf_mod, "FastHierarchyLayout")
        .def(nb::init<>())
        .def("layerDistance", [](ogdf::FastHierarchyLayout& layout,
                                 double distance) { layout.layerDistance(distance); })
        .def("nodeDistance", [](ogdf::FastHierarchyLayout& layout, double distance) {
            layout.nodeDistance(distance);
        });

    nb::class_<ogdf::OptimalRanking>(ogdf_mod, "OptimalRanking").def(nb::init<>());
    nb::class_<ogdf::BarycenterHeuristic>(ogdf_mod, "BarycenterHeuristic").def(nb::init<>());

    nb::class_<ogdf::SugiyamaLayout>(ogdf_mod, "SugiyamaLayout")
        .def(nb::init<>())
        .def("setRuns", [](ogdf::SugiyamaLayout& layout, int runs) { layout.runs(runs); })
        .def("call", [](ogdf::SugiyamaLayout& layout, ogdf::GraphAttributes& attributes) {
            layout.call(attributes);
        });

    ogdf_mod.def("setSeed", [](int seed) { ogdf::setSeed(seed); });
}

}  // namespace

// -- Module definition --------------------------------------------------------

NB_MODULE(_flatline_native, m) {
    m.doc() = "flatline native bridge (nanobind + Ghidra decompiler)";

    nb::module_ native_layout = m.def_submodule("_native_layout", "Internal layout bindings");
    nb::module_ ogdf_mod = native_layout.def_submodule("ogdf", "OGDF Sugiyama layout bindings");
    bind_ogdf_layout(ogdf_mod);

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
