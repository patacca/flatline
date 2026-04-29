// Native nanobind bridge for flatline.
// P2-Step-3b: wire per-request decompile pipeline with structured errors.

#include <libavoid/connectionpin.h>
#include <libavoid/connector.h>
#include <libavoid/geomtypes.h>
#include <libavoid/router.h>
#include <libavoid/shape.h>
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

Avoid::Point polygon_point_at(const Avoid::Polygon& polygon, int index) {
    const int size = static_cast<int>(polygon.size());
    if (index < 0) {
        index += size;
    }
    if (index < 0 || index >= size) {
        throw nb::index_error("Polygon index out of range");
    }
    return polygon.ps[static_cast<size_t>(index)];
}

void bind_avoid_router(nb::module_& avoid_mod) {
    nb::enum_<Avoid::RouterFlag>(avoid_mod, "RouterFlag", nb::is_arithmetic())
        .value("OrthogonalRouting", Avoid::OrthogonalRouting)
        .value("PolyLineRouting", Avoid::PolyLineRouting);

    // Visibility / arrival direction flags for ShapeConnectionPin and ConnEnd.
    // Constraining a pin's visDirs forces libavoid's orthogonal router to
    // approach (or leave) the pin from the chosen sides only - this is how
    // we enforce "top-anchored edges must arrive vertically downward"
    // natively, instead of post-processing the polyline in Python.
    nb::enum_<Avoid::ConnDirFlag>(avoid_mod, "ConnDirFlag")
        .value("ConnDirNone", Avoid::ConnDirNone)
        .value("ConnDirUp", Avoid::ConnDirUp)
        .value("ConnDirDown", Avoid::ConnDirDown)
        .value("ConnDirLeft", Avoid::ConnDirLeft)
        .value("ConnDirRight", Avoid::ConnDirRight)
        .value("ConnDirAll", Avoid::ConnDirAll);

    nb::enum_<Avoid::RoutingParameter>(avoid_mod, "RoutingParameter")
        .value("segmentPenalty", Avoid::segmentPenalty)
        .value("anglePenalty", Avoid::anglePenalty)
        .value("crossingPenalty", Avoid::crossingPenalty)
        .value("clusterCrossingPenalty", Avoid::clusterCrossingPenalty)
        .value("fixedSharedPathPenalty", Avoid::fixedSharedPathPenalty)
        .value("portDirectionPenalty", Avoid::portDirectionPenalty)
        .value("shapeBufferDistance", Avoid::shapeBufferDistance)
        .value("idealNudgingDistance", Avoid::idealNudgingDistance)
        .value("reverseDirectionPenalty", Avoid::reverseDirectionPenalty);

    nb::enum_<Avoid::RoutingOption>(avoid_mod, "RoutingOption")
        .value("nudgeOrthogonalSegmentsConnectedToShapes",
               Avoid::nudgeOrthogonalSegmentsConnectedToShapes)
        .value("improveHyperedgeRoutesMovingJunctions",
               Avoid::improveHyperedgeRoutesMovingJunctions)
        .value("penaliseOrthogonalSharedPathsAtConnEnds",
               Avoid::penaliseOrthogonalSharedPathsAtConnEnds)
        .value("nudgeOrthogonalTouchingColinearSegments",
               Avoid::nudgeOrthogonalTouchingColinearSegments)
        .value("performUnifyingNudgingPreprocessingStep",
               Avoid::performUnifyingNudgingPreprocessingStep)
        .value("improveHyperedgeRoutesMovingAddingAndDeletingJunctions",
               Avoid::improveHyperedgeRoutesMovingAddingAndDeletingJunctions)
        .value("nudgeSharedPathsWithCommonEndPoint", Avoid::nudgeSharedPathsWithCommonEndPoint);

    nb::class_<Avoid::Router>(avoid_mod, "Router")
        .def(nb::new_([](Avoid::RouterFlag flags) {
            return new Avoid::Router(static_cast<unsigned int>(flags));
        }))
        .def(nb::new_([](unsigned int flags) { return new Avoid::Router(flags); }))
        .def("processTransaction", &Avoid::Router::processTransaction)
        .def("setRoutingParameter", &Avoid::Router::setRoutingParameter)
        .def("setRoutingOption", &Avoid::Router::setRoutingOption);

    nb::class_<Avoid::Point>(avoid_mod, "Point")
        .def(nb::init<double, double>())
        .def_rw("x", &Avoid::Point::x)
        .def_rw("y", &Avoid::Point::y);

    nb::class_<Avoid::Polygon>(avoid_mod, "Polygon")
        .def(nb::init<>())
        .def_prop_ro("size", [](const Avoid::Polygon& polygon) { return polygon.size(); })
        .def("__getitem__", &polygon_point_at);

    nb::class_<Avoid::Rectangle, Avoid::Polygon>(avoid_mod, "Rectangle")
        .def(nb::init<Avoid::Point, Avoid::Point>());

    nb::class_<Avoid::ShapeRef>(avoid_mod, "ShapeRef", nb::never_destruct())
        .def(nb::new_([](Avoid::Router& router, Avoid::Polygon& polygon) {
                 return new Avoid::ShapeRef(&router, polygon);
             }),
             nb::rv_policy::reference);

    nb::class_<Avoid::ShapeConnectionPin>(avoid_mod, "ShapeConnectionPin", nb::never_destruct())
        .def(nb::new_([](Avoid::ShapeRef& shape, unsigned int class_id, double x_offset,
                         double y_offset, double inside_offset, Avoid::ConnDirFlag vis_dirs) {
                 return new Avoid::ShapeConnectionPin(&shape, class_id, x_offset, y_offset,
                                                      inside_offset,
                                                      static_cast<Avoid::ConnDirFlags>(vis_dirs));
             }),
             nb::rv_policy::reference, nb::arg("shape"), nb::arg("classId"), nb::arg("xOffset"),
             nb::arg("yOffset"), nb::arg("insideOffset") = 0.0,
             nb::arg("visDirs") = Avoid::ConnDirAll)
        .def("setExclusive", &Avoid::ShapeConnectionPin::setExclusive);

    nb::class_<Avoid::ConnEnd>(avoid_mod, "ConnEnd")
        .def(nb::init<Avoid::ShapeRef*, unsigned int>());

    nb::class_<Avoid::ConnRef>(avoid_mod, "ConnRef", nb::never_destruct())
        .def(nb::new_([](Avoid::Router& router, const Avoid::ConnEnd& source,
                         const Avoid::ConnEnd& target) {
                 return new Avoid::ConnRef(&router, source, target);
             }),
             nb::rv_policy::reference)
        .def("displayRoute", [](Avoid::ConnRef& conn) { return conn.displayRoute(); });
}

}  // namespace

// -- Module definition --------------------------------------------------------

NB_MODULE(_flatline_native, m) {
    m.doc() = "flatline native bridge (nanobind + Ghidra decompiler)";

    nb::module_ native_layout = m.def_submodule("_native_layout", "Internal layout bindings");
    nb::module_ ogdf_mod = native_layout.def_submodule("ogdf", "OGDF Sugiyama layout bindings");
    bind_ogdf_layout(ogdf_mod);
    nb::module_ avoid_mod =
        native_layout.def_submodule("avoid", "libavoid orthogonal router bindings");
    bind_avoid_router(avoid_mod);

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
