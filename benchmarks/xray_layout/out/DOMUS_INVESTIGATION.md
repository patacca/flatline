# DOMUS Investigation Notes

> Companion to `REPORT.md`. The auto-generated report is regenerated from
> `out/runs/*.json` by `bench report`; this file is hand-written and persists
> the narrative behind the DOMUS results.

## TL;DR

After three rounds of fixes (adapter degree-cap removal, SVG polyline
parser, extractor IOP/CFG augmentation), DOMUS produces a valid layout for
**1 of 5 fixtures** (`small_loop`). The remaining four fail in two
distinct ways that are properties of DOMUS itself, not of the input graphs:

| Fixture              | Nodes / Edges | Result    | Cause                                                                   |
|----------------------|---------------|-----------|-------------------------------------------------------------------------|
| tiny_branch          | 20 / 37       | error     | `std::bad_optional_access` at `drawing_builder.cpp:616` (`make_topological_ordering` returns `nullopt` on cyclic internal Ordering graph) |
| small_loop           | 45 / 72       | **ok**    | -                                                                       |
| medium_switch        | 50 / 79       | error     | Same `bad_optional_access` site (`drawing_builder.cpp:616`) |
| large_nested         | 191 / 334     | timeout   | Glucose SAT solver does not converge within 60 s (also fails at 600 s standalone) |
| xlarge_state_machine | 405 / 754     | timeout   | Same SAT scalability ceiling                                            |

**Recommendation: DOMUS is not a viable Tier 1 candidate for xray.** It
collapses on common topologies (the `bad_optional_access` reproduces on a
20-node graph) and does not scale past ~100 nodes. xray must routinely
handle functions with hundreds of pcode operations.

## Initial state

A first sweep showed `domus 0/5`. Failures fell in two buckets:

- 4 binaries: uncaught `DisconnectedGraphError` from
  `compute_cycle_basis` (`graphs_algorithms.cpp:118`).
- 1 binary: harness assertion `DOMUS emitted N edge lines for M encoded edges`.

The original adapter applied an artificial **degree-4 cap** on the input
(silently dropping every edge after the fourth at any node) and then parsed
the SVG by counting `<line>` elements.

## Fix 1 - Remove the degree cap

The cap was rationalised in the adapter as "DOMUS evaluation dataset is
limited to max degree 4". Reading the DOMUS source
(`drawing_builder.cpp:285-336, 563-629`) confirmed this is a **dataset
property, not an algorithm constraint**: `add_green_blue_nodes`
port-expands every vertex of degree > 4 internally. The cap was
indefensible for binary CFGs, where 5+ in/out edges at a single op are
routine.

Edits in `bench/adapters/domus_adapter.py::_encode_graph`:

- Removed the degree-4 truncation loop.
- Kept self-loop suppression (DOMUS does not support them).
- Kept parallel-edge collapse (DOMUS expects simple graphs).
- Added an explicit `nx.is_connected` precheck that raises a clear
  `RuntimeError` instead of crashing inside DOMUS.

DOMUS does **not** require planarity (verified empirically and from source);
it does require the input to be a single connected component
(`compute_cycle_basis` asserts this).

## Fix 2 - SVG polyline reconstruction

DOMUS emits each edge as a chain of orthogonal `<line>` segments separated
by tiny "bend" rectangles, not as one `<line>` per edge. The original
parser counted lines and asserted equality with the encoded edge count,
which trips on every nontrivial layout.

Rewrote `_parse_svg` to:

1. Quantise all segment endpoints to the nearest 0.5 px to merge
   floating-point duplicates.
2. Build a graph of segments and walk from the centre of each real-vertex
   rectangle through degree-2 interior vertices until reaching the next
   real vertex.
3. Cap walks at 1024 steps and return `None` on junctions, surfacing
   parser errors loudly.

Helpers: `_reconstruct_polylines`, `_walk_to_real_node`.

## Fix 3 - Extend the graph extractor with IOP and CFG edges

After Fixes 1-2, DOMUS still failed every binary on `DisconnectedGraphError`.
Investigation revealed this was an **extractor artefact**, not a real binary
property: `bench/graph_extract.py` only emitted `pcode_dataflow` edges. For
xlarge_state_machine the graph contained 480 dataflow edges and 0 of
anything else, leaving execution-order and branching information
implicit.

Real binary CFGs are connected. The extractor was the bug.

Per user direction ("There is no need for block reconstruction. IOP edges
should point to a specific node, CFG edges should be there only on CBRANCH
and similar, going to any node that is part of the instruction at the
address that is a target of the CBRANCH"):

- `_add_iop_edges`: sort all ops by `(sequence_time, sequence_order)` and
  link each consecutive pair with a single `edge_type="iop"` edge.
- `_add_cfg_edges`: for any op exposing non-`None`
  `true_target_address` / `false_target_address` (accessed via `getattr`
  to avoid coupling to `BranchOp`), emit one `edge_type="cfg"` edge to
  every op whose `instruction_address` matches the target.

Both helpers wired into `extract()` after `_augment_graph`. Op nodes use
the existing `("op", op.id)` key shape from `Pcode.to_graph()`.

Result: every fixture now produces a single connected component.

| Fixture              | dataflow | iop | cfg | Total edges | Components |
|----------------------|----------|-----|-----|-------------|------------|
| tiny_branch          | 22       | 8   | 7   | 37          | 1          |
| small_loop           | 45       | 17  | 10  | 72          | 1          |
| medium_switch        | 49       | 19  | 11  | 79          | 1          |
| large_nested         | 210      | 79  | 45  | 334         | 1          |
| xlarge_state_machine | 480      | 172 | 102 | 754         | 1          |

## Remaining failures

### `bad_optional_access` (tiny_branch, medium_switch)

Pinpointed via an `-O0 -g3 -fno-inline` rebuild of DOMUS plus gdb on
`/tmp/domus_tiny/graph.txt`. The failing call is at
`drawing_builder.cpp:616` inside `add_green_blue_nodes`:

```cpp
// drawing_builder.cpp:614,616 (add_green_blue_nodes)
auto topo_x = algorithms::make_topological_ordering(ordering_x).value();
...
auto topo_y = algorithms::make_topological_ordering(ordering_y).value();  // <-- throws
```

`make_topological_ordering` (`graphs_algorithms.cpp:154-178`) returns
`std::nullopt` when its input graph contains a cycle. The graph passed
in is DOMUS's internally-constructed `EquivalenceClasses::Ordering`, not
the user input - DOMUS builds it during port-expansion of high-degree
vertices and, on these fixtures, the construction yields a cyclic
ordering. The failure is therefore an **algorithmic limitation of
DOMUS's port-expansion phase**, not a missing null-check at the call
site:

- A `.value_or({})` fallback would silently emit a structurally broken
  layout (wrong vertical ordering of green/blue helper nodes), not a
  correct one.
- The same unguarded pattern exists at `drawing_builder.cpp:357,359` in
  the sibling `build_nodes_positions` cold path; not exercised by these
  fixtures but vulnerable to the same root cause.
- A speculative defensive patch was attempted on the unrelated
  `find_edges_to_fix` block (`drawing_builder.cpp:471-483`) and reverted
  - it compiled cleanly but the crash still reproduced, confirming
  those calls are not the trigger.

Negative reproductions previously gathered remain instructive:

- Degree-5 star + extra edge: passes.
- Degree-8 star: passes.

So high degree alone is insufficient; the trigger is high-degree
vertices combined with cycle structure that defeats DOMUS's internal
ordering construction. Both failing fixtures contain at least one
degree-6+ node embedded in a cycle. Fixing this requires redesigning
DOMUS's `EquivalenceClasses::Ordering` construction so it cannot become
cyclic - an upstream change that is out of scope for this evaluation
and reinforces the recommendation to drop DOMUS as a candidate.

### Timeouts (large_nested 191 nodes, xlarge_state_machine 405 nodes)

The 60-second harness budget expires inside DOMUS's Glucose SAT loop.
Standalone runs against `/tmp/domus_large/graph.txt` with a 600-second
timeout produce continuous "Try to adapt solver strategies" output without
finishing. The complexity is intrinsic to DOMUS's SAT-based bend
minimisation phase and is not improved by larger budgets within any
reasonable time.

## Files modified

- `benchmarks/xray_layout/bench/adapters/domus_adapter.py`
  - `_encode_graph`: removed degree cap, added connectedness precheck.
  - `_parse_svg`: rewrote with `_reconstruct_polylines` /
    `_walk_to_real_node` for chained-segment edges.
- `benchmarks/xray_layout/bench/graph_extract.py`
  - Added `_add_iop_edges` and `_add_cfg_edges`.
  - Wired both into `extract()`; updated module docstring.

## Verification

- `tox` lint and unit tests: not re-run (changes are confined to
  `benchmarks/xray_layout/`, which lives outside the main flatline test
  surface, on a research branch flagged DO-NOT-MERGE).
- Benchmark sweep: `python -m benchmarks.xray_layout.bench run --candidate
  domus --binary <ELF> --entry target_func` for each of the 5 fixtures.
  Results persisted in `out/runs/domus__*__target_func.json` and rolled up
  by `bench report` into `REPORT.md`.

## Standalone reproductions (preserved)

Kept under `/tmp/` for any future upstream bug report:

- `/tmp/domus_tiny/graph.txt` - reproduces `bad_optional_access`.
- `/tmp/domus_med/graph.txt`  - reproduces `bad_optional_access` (dumps core).
- `/tmp/domus_large/graph.txt` - reproduces SAT-loop timeout.
- `/tmp/domus_minrep/`, `/tmp/domus_d8/` - negative reproducers proving
  high degree alone is not sufficient to trigger the crash.

## Conclusion

The investigation answered the original question definitively: the DOMUS
results are not an artefact of the adapter or the extractor. With a
faithful, realistic input graph (CFG + IOP + dataflow, no degree cap)
and a correct SVG parser, DOMUS still fails on the majority of xray-shaped
inputs. It crashes on small graphs with mixed degree/cycle topology and
does not scale past ~100 nodes. Per the user's stated criterion - "if
this is an unsolvable problem, then domus shouldn't be a viable option" -
DOMUS should be dropped from xray's candidate list.
