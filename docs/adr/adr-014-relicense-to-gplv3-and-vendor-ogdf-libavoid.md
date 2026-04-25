# ADR-014 Relicense to GPLv3 and Vendor OGDF/libavoid

- Status: accepted
- First needed: P7.0 layout engine implementation

## Context

The project requires a high-quality layout engine to support interactive graph visualization and data-flow analysis of pcode IR. After evaluating several options, the Open Graph Drawing Framework (OGDF) and the libavoid library (part of Adaptagrams) were selected for their maturity, robustness, and performance characteristics.

However, incorporating these libraries introduces specific licensing and architectural constraints. OGDF is licensed under GPL-2.0-or-later (effectively GPL-3.0-or-later in modern versions) and libavoid is LGPL-2.1-or-later. Static linking of these components into the flatline native bridge makes the resulting binary wheels a derivative work, necessitating a shift to a strong-copyleft license for the entire project to ensure compliance.

The project needs a solution that maintains high performance, avoids complex IPC mechanisms, and provides a predictable build and distribution process for binary wheels.

## Decision

Relicense flatline from Apache-2.0 to GPL-3.0-or-later. Simultaneously, introduce a native layout engine by vendoring OGDF and libavoid as static dependencies.

### Native Vendor Strategy

The layout engine is implemented in C++ and exposed through the `flatline._native_layout` internal module using nanobind. This approach follows the established pattern of the Ghidra decompiler bridge:

- Components are built as static libraries using Meson and linked into the final native extension via `link_whole`.
- Direct C++ integration avoids the overhead and complexity of subprocess IPC or external Python wrappers like `ogdf-python`.
- The OGDF dependency excludes COIN-OR components (OptimalHierarchyLayout) to avoid additional licensing and build complexity.

This strategy ensures that the layout engine is tightly integrated with the core decompilation logic, allowing for low-latency interactions and a unified build system.

### Pinned Dependencies

The specific versions of the vendored libraries are pinned to ensure reproducible builds and stability:

- **OGDF**: tag `foxglove-202510` (SHA: `5b6795655399b9d8e2921afec9d97bab9107d5ee`)
- **libavoid**: Adaptagrams commit (SHA: `840ebcff20dbba36ad03a2160edf7cbaf9859984`)

These pins are managed in the Meson build files and are updated as part of the project's maintenance cycle.

### Performance and Size Constraints

The native layout engine must operate within strict performance and footprint boundaries:

- **Performance Budget**: median latency ≤ 200 ms, p95 ≤ 1 s, hard ceiling ≤ 5 s.
- **Wheel Cap**: Maximum per-wheel size is restricted to 80 MiB. This is enforced by `tools/footprint.py --max-wheel-size`.

These constraints are critical for maintaining a responsive user experience and ensuring that the package remains manageable for distribution and installation.

### Layout Logic and Caching

- **Visual Semantics**: The `sugiyama_libavoid` composite layout pipeline was chosen for its strict layered-by-rank visual semantics. While it has a higher composite score (691) compared to `ogdf_libavoid` (284), the preservation of rank-based structure is prioritized over raw compactness.
- **Accepted Regression**: The decision to accept the higher composite score of 691 for `sugiyama_libavoid` (versus 284 for `ogdf_libavoid`) is justified by the requirement for layered visual semantics. This priority ensures that the data-flow hierarchy is intuitive and navigable for the user, even if it results in a less compact layout.
- **Self-loops**: Handled via a right-side U-polyline specification with 5 vertices.
- **Caching**: Layout results are cached using the `id(pcode_graph)` as the key. Toggling UI checkboxes does not trigger a relayout.

## Consequences

- **Licensing Change**: Downstream users who cannot accept GPL-3.0-or-later (e.g., those using flatline in Apache/MIT/BSD-licensed proprietary projects) will be blocked from updating to version 0.1.3 and later.
- **Wheel Growth**: The inclusion of OGDF and libavoid increases the wheel size, though it remains within the 80 MiB cap.
- **Maintenance**: Vendoring native libraries increases the build complexity and maintenance burden for the project. The build system must now handle the compilation and linking of these substantial dependencies across all supported platforms.
- **Feature Set**: The addition of a robust layout engine enables sophisticated graph-based analysis and visualization tools, fulfilling a core requirement for P7.0.
- **Performance**: The performance budget ensures that the user experience remains responsive, with a median latency of 200 ms and a strict 5 s ceiling for complex layouts.

## Alternatives Considered

- **ogdf-python wrapper**: Rejected due to `cppyy` overhead and lack of control over the wheel distribution process. The project needs a solution that doesn't introduce large runtime dependencies like `cppyy`.
- **Subprocess IPC**: Rejected because of high latency and the complexity of managing a separate layout process. The overhead of serializing and deserializing graph data across a process boundary would violate the performance budget.
- **SVG export**: Rejected as it does not support the required interactive layout and manipulation features. The user needs to be able to interact with the graph in real-time.
- **BSD `drag` library**: Rejected because it lacked the Sugiyama-style layered layout necessary for clear data-flow visualization.
- **ogdf_libavoid**: Rejected in favor of `sugiyama_libavoid` to maintain strict visual semantics despite the performance and compactness trade-off.

## Detailed Rationale for sugiyama_libavoid

The primary objective of the layout engine is to clarify the structure of decompiled pcode. The `sugiyama_libavoid` pipeline excels at presenting hierarchical relationships through its layered-by-rank approach. Although `ogdf_libavoid` produces more compact layouts, it often obscures the rank-based structure that is essential for understanding data-flow and control-flow in a decompilation context. The regression in the composite score is therefore a deliberate and accepted trade-off for superior visual semantics.

The layered-by-rank approach mirrors the natural flow of instructions and data in a program, making it easier for human analysts to follow the logic. This visual clarity is a fundamental goal of the flatline project.

## Technical Implementation Details

The implementation utilizes Meson's static library support to vendor the source code of OGDF and libavoid. This ensures that the build process is self-contained and does not depend on system-wide installations of these libraries, which can be difficult to manage across different operating systems. The use of `link_whole` ensures that all necessary symbols are included in the final shared object, while `nanobind` provides a high-performance, low-overhead bridge to the Python environment.

The layout cache is designed to be efficient, using the object ID of the pcode graph to avoid redundant calculations. This is particularly important for interactive sessions where the graph structure is static but the user might be toggling various metadata views or adjusting visualization parameters.

## Amendment to ADR-013

This decision amends the wheel distribution strategy established in ADR-013. A hard cap of 80 MiB per-wheel is now enforced to manage the footprint growth caused by native vendoring. This constraint ensures that the package remains portable and does not exceed the practical limits for public distribution on PyPI or other package repositories.

The 80 MiB cap was determined based on an analysis of the binary size of the compiled native components across the target platforms. It provides enough room for the current dependencies while imposing a necessary limit on future growth.

## Compliance and Auditing

To maintain compliance with the new GPL-3.0-or-later license, all redistribution of flatline must include the full source code or an offer to provide it. The `tools/compliance.py` script will be updated to reflect the new licensing requirements and verify the presence of the required license and notice files.

The footprint of the wheels will be monitored as part of the CI/CD pipeline, ensuring that the 80 MiB limit is never exceeded. Any violation of this limit will trigger a build failure, requiring a review of the included native components and potential optimization of the binary size. This proactive auditing is essential for maintaining the project's standards for package quality and distribution.

## Future Considerations

As the project evolves, the layout engine may be further optimized or expanded. Any changes that significantly impact the licensing, performance, or wheel size will be documented in subsequent ADRs. The project remains committed to providing a high-quality, open-source decompilation environment that prioritizes user convenience and technical excellence.

The transition to GPL-3.0-or-later is a significant step that reflects the project's reliance on powerful open-source components and its commitment to ensuring that flatline remains freely available and improvable by the community.
