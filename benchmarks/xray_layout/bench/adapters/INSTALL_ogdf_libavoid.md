# INSTALL_ogdf_libavoid

## Status
DEFERRED (gated on both OGDF and libavoid)

## Repo URL
- OGDF: https://github.com/ogdf/ogdf (Python: https://github.com/N-Coder/ogdf-python)
- libavoid: https://github.com/Adaptagrams/adaptagrams (cola/libavoid/)

## Commands Tried
None directly. This adapter is a pure composition of `OgdfAdapter` and
`LibavoidAdapter`; install_check() delegates to both.

See:
- `INSTALL_ogdf.md` -- ogdf-python wheel installs but libOGDF/libCOIN
  are missing system-wide.
- `INSTALL_libavoid.md` -- no PyPI distribution exists.

## Result
DEFERRED: gated on both component adapters. As soon as both report
INSTALLED, this combo's install_check() will flip to True with no code
changes here.

## System Dependencies
Union of OGDF and libavoid system requirements.

## Combo Strategy (>= 200 words)

The combination strategy splits the orthogonal-drawing problem along
its two natural axes: **node placement** and **edge routing**. Each
candidate engine in this benchmark is strong on one axis but weaker on
the other, so a combo lets us pair complementary strengths.

**Phase 1 -- node placement via OGDF.** OGDF's `PlanarizationLayout`
(or `OrthoLayout`) produces a high-quality 2-D embedding with bend-aware
compaction. We keep its node coordinates and the implied bounding-box
sizes but **discard** OGDF's edge polylines, because libavoid will
recompute them. The motivation: OGDF's planarization minimizes
crossings, which dominates the visual quality of dense graphs.

**Phase 2 -- edge routing via libavoid.** We instantiate
`Avoid::Router(OrthogonalRouting)`, register an `Avoid::Rectangle` for
each OGDF-placed node, then register an `Avoid::ConnRef` for each edge
in the input graph. libavoid handles port assignment, obstacle
avoidance, nudging, and ordering. We call `Router::processTransaction()`
and read back the polylines (`displayRoute().ps`) as the canonical
edge routes.

**Phase 3 -- result assembly.** The `LayoutResult` is built by
combining OGDF-sourced `node_positions` and `node_sizes` with the
libavoid-sourced `edge_routes`. The wall-clock budget is the sum of
both phases plus marshalling. Because OGDF and libavoid both expose
their geometry in pixel-equivalent units, no global rescaling is
required; only the y-axis convention (libavoid uses y-down) needs
flipping at the seam.

**Risks.** Two ABIs to maintain; libavoid expects rectangles in
absolute coordinates so an offset must be applied if OGDF reports
center-relative positions; large graphs may stress libavoid's
`processTransaction` runtime (the harness 60 s per-layout timeout will
catch this).

## Recommendation
Wait until both OGDF and libavoid clear their respective install gates,
then implement Phase 1-3 in `OgdfLibavoidAdapter.layout()`. The combo
should be the most interesting Wave-2 result, since it is the only
pairing that explicitly separates placement from routing.
