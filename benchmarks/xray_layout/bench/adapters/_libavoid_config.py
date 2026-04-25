"""Shared orthogonal libavoid router configuration.

Used by exactly 3 adapters: libavoid, ogdf_libavoid, sugiyama_libavoid.
Values pinned per _SPEC.md; do NOT tune at runtime.
"""
import adaptagrams as A

# Penalty for edge crossings - high value discourages but does not forbid crossings
_CROSSING_PENALTY = 10000.0
# Penalty per additional segment - encourages fewer bends
_SEGMENT_PENALTY = 50.0
# Penalty for fixed shared path - discourages shared routing
_FIXED_SHARED_PATH_PENALTY = 110.0
# Minimum clearance the router must keep between any orthogonal segment and a
# shape's bounding box. libavoid's default is 0.0, which lets segments slide
# flush against (and visually appear to pass through) node boundaries when
# the visibility graph aligns. Pinning a non-zero buffer forces the router
# to maintain a routing channel around every shape -- without this, edges
# from centre-pin ConnEnds (and any segment whose visibility ray grazes a
# node corner) get drawn through node bodies. 8.0 is well below our
# _LAYER_DISTANCE=30 so it does not collapse Sugiyama's rank gaps.
_SHAPE_BUFFER_DISTANCE = 8.0
# Tolerance for axis-alignment check in orthogonal_segment_ratio metric
_ORTHO_TOL = 1e-6


def apply_orthogonal_config(router: "A.Router") -> None:
    """Apply pinned orthogonal routing config to an existing Router instance."""
    router.setRoutingPenalty(A.crossingPenalty, _CROSSING_PENALTY)
    router.setRoutingPenalty(A.segmentPenalty, _SEGMENT_PENALTY)
    router.setRoutingPenalty(A.fixedSharedPathPenalty, _FIXED_SHARED_PATH_PENALTY)
    router.setRoutingParameter(A.shapeBufferDistance, _SHAPE_BUFFER_DISTANCE)
    router.setRoutingOption(A.nudgeOrthogonalSegmentsConnectedToShapes, True)
    router.setRoutingOption(A.nudgeOrthogonalTouchingColinearSegments, True)
    router.setRoutingOption(A.nudgeSharedPathsWithCommonEndPoint, True)
    router.setRoutingOption(A.improveHyperedgeRoutesMovingJunctions, True)


def make_orthogonal_router() -> "A.Router":
    """Create a new orthogonal Router with pinned config already applied."""
    router = A.Router(A.OrthogonalRouting)
    apply_orthogonal_config(router)
    return router


def add_all_directions_pin(shape: "A.ShapeRef") -> None:
    """Register a centre connection pin allowing routing on all four sides.

    libavoid REQUIRES a ShapeConnectionPin for ConnEnd to anchor on a shape;
    without one, ``ConnEnd(shape, ConnDirAll)`` is silently misinterpreted
    (the second arg is a pin class id in the SWIG binding, NOT direction
    flags) and the router falls back to a single straight segment between
    shape centres regardless of ``OrthogonalRouting`` / ``ConnType_Orthogonal``.

    The pin is anchored at ``ATTACH_POS_CENTRE``, ``ATTACH_POS_CENTRE`` (i.e.
    the shape's geometric centre) with ``proportional=True`` so it tracks the
    shape if it moves. ``ConnDirAll`` lets libavoid pick whichever side
    minimises bend count for each connector. Class id is
    ``CONNECTIONPIN_CENTRE`` so call sites can reference it via
    ``ConnEnd(shape, CONNECTIONPIN_CENTRE)``.
    """
    A.ShapeConnectionPin(
        shape,
        A.CONNECTIONPIN_CENTRE,
        A.ATTACH_POS_CENTRE,
        A.ATTACH_POS_CENTRE,
        True,  # proportional anchor (tracks shape on move)
        0.0,   # insideOffset (unused for centre pins)
        A.ConnDirAll,
    )


if __name__ == "__main__":
    r = make_orthogonal_router()
    print(f"Router created: {type(r).__name__}")
    print("apply_orthogonal_config: OK")
    print("make_orthogonal_router: OK")
