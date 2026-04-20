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
# Tolerance for axis-alignment check in orthogonal_segment_ratio metric
_ORTHO_TOL = 1e-6


def apply_orthogonal_config(router: "A.Router") -> None:
    """Apply pinned orthogonal routing config to an existing Router instance."""
    router.setRoutingPenalty(A.crossingPenalty, _CROSSING_PENALTY)
    router.setRoutingPenalty(A.segmentPenalty, _SEGMENT_PENALTY)
    router.setRoutingPenalty(A.fixedSharedPathPenalty, _FIXED_SHARED_PATH_PENALTY)
    router.setRoutingOption(A.nudgeOrthogonalSegmentsConnectedToShapes, True)
    router.setRoutingOption(A.nudgeOrthogonalTouchingColinearSegments, True)
    router.setRoutingOption(A.nudgeSharedPathsWithCommonEndPoint, True)
    router.setRoutingOption(A.improveHyperedgeRoutesMovingJunctions, True)


def make_orthogonal_router() -> "A.Router":
    """Create a new orthogonal Router with pinned config already applied."""
    router = A.Router(A.OrthogonalRouting)
    apply_orthogonal_config(router)
    return router


if __name__ == "__main__":
    r = make_orthogonal_router()
    print(f"Router created: {type(r).__name__}")
    print("apply_orthogonal_config: OK")
    print("make_orthogonal_router: OK")
