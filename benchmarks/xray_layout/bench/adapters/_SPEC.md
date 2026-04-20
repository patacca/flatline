# Frozen Spec: libavoid orthogonal config + pin positions

## Router Option Names (verified via SWIG introspection)

### Penalty Options
- `crossingPenalty` - penalty for edge crossings
- `segmentPenalty` - penalty for each segment
- `fixedSharedPathPenalty` - penalty for fixed shared paths
- `anglePenalty` - penalty for angles
- `clusterCrossingPenalty` - penalty for crossing cluster boundaries
- `portDirectionPenalty` - penalty for port direction changes
- `reverseDirectionPenalty` - penalty for reverse direction

### Nudge Options
- `nudgeOrthogonalSegmentsConnectedToShapes` - nudge segments connected to shapes
- `nudgeOrthogonalTouchingColinearSegments` - nudge touching colinear segments
- `nudgeSharedPathsWithCommonEndPoint` - nudge shared paths with common endpoint

### Improvement Options
- `improveHyperedgeRoutesMovingJunctions` - improve hyperedge routes by moving junctions
- `improveHyperedgeRoutesMovingAddingAndDeletingJunctions` - improve by moving/adding/deleting junctions

### Other Options
- `penaliseOrthogonalSharedPathsAtConnEnds` - penalize shared paths at connection ends
- `sortOrdAlignsByPenalty` - sort orthogonal aligns by penalty

### Transaction Phases
- `TransactionPhaseOrthogonalNudgingX` - X-axis nudging phase
- `TransactionPhaseOrthogonalNudgingY` - Y-axis nudging phase
- `TransactionPhaseOrthogonalVisibilityGraphScanX` - X-axis visibility graph scan
- `TransactionPhaseOrthogonalVisibilityGraphScanY` - Y-axis visibility graph scan

### Routing Types
- `OrthogonalRouting` - orthogonal routing mode
- `ConnType_Orthogonal` - orthogonal connection type
- `OrthogonalEdgeConstraint` - orthogonal edge constraint

## Pinned Constants

```python
_ORTHO_TOL = 1e-6
_CROSSING_PENALTY = 10000.0
_SEGMENT_PENALTY = 50.0
_FIXED_SHARED_PATH_PENALTY = 110.0
```

## Pin Positions (sugiyama_libavoid Baseline A)

Source pins (bottom edge):
  classID=1 (true branch):    propX=0.25, propY=1.0, ATTACH_POS_BOTTOM
  classID=2 (false branch):   propX=0.75, propY=1.0, ATTACH_POS_BOTTOM
  classID=3 (default branch): propX=0.5,  propY=1.0, ATTACH_POS_BOTTOM

Target pin (top center):
  classID=10:                 propX=0.5,  propY=0.0, ATTACH_POS_TOP

## Edge Kind -> classID Mapping

"true" -> 1, "false" -> 2, "default" -> 3, anything else -> 3

## SIGALRM / time_budget verification

**STATUS: Inner adapters use HARDCODED SIGALRM**

All three inner adapters (libavoid_adapter.py, hola_adapter.py, ogdf_libavoid_adapter.py)
use hardcoded `_LAYOUT_TIMEOUT_SECONDS = 60` with their own SIGALRM handlers.

They do NOT read the outer time_budget from the harness. Each adapter:
1. Installs its own SIGALRM handler
2. Sets `signal.alarm(_LAYOUT_TIMEOUT_SECONDS)` where _LAYOUT_TIMEOUT_SECONDS = 60
3. Restores the previous handler in a finally block

This is documented behavior - the adapters surface clean TimeoutError before the
harness's outer SIGALRM fires.

## Pin Constants (verified via SWIG introspection)

- `ATTACH_POS_TOP` - attach to top edge
- `ATTACH_POS_BOTTOM` - attach to bottom edge
- `ATTACH_POS_LEFT` - attach to left edge
- `ATTACH_POS_RIGHT` - attach to right edge
- `ATTACH_POS_CENTRE` - attach to center
- `ATTACH_POS_MIN_OFFSET` - minimum offset constant
- `ATTACH_POS_MAX_OFFSET` - maximum offset constant
- `ShapeConnectionPin` - shape connection pin class
- `kShapeConnectionPin` - shape connection pin constant
