# X-Ray

`flatline-xray` is the shipped interactive viewer for flatline's memory-image
contract. It opens the same kind of request you use from Python, then adds a
graph view, an assembly browser, and a node inspector on top of the recovered
p-code.

This is a convenience layer, not a separate product model. You still provide:

- raw memory image bytes
- a base address
- a function address
- target metadata (`language_id` and optional `compiler_spec`)

## What it is for

Use X-Ray when you want to inspect one function interactively instead of
writing code around `DecompileResult` and `Enriched.pcode`.

The viewer features a three-panel layout designed for high-density analysis:

- **Graph View** (Center): The dominant pane displaying p-code operations and varnode nodes. It uses a vertical Sugiyama-layered layout with orthogonal edge routing. In CPG mode, it displays an additional overlay of control-flow and reference edges.
- **Assembly Panel** (Left): Shows the decoded instructions for the function.
- **Inspector Panel** (Right): Provides detailed metadata for the currently selected node or instruction. It also contains edge visibility toggles when the CPG overlay is active.

All panes are resizable by dragging the vertical dividers between them. The graph pane automatically expands to fill available space when the window is resized.

### Layout Pipeline

The viewer employs a two-stage layout pipeline designed for high-density p-code graphs:

1.  **Sugiyama Layering (via OGDF)**: Nodes are organized into discrete horizontal ranks to minimize edge crossings and highlight the top-to-bottom data flow.
2.  **Orthogonal Routing (via libavoid)**: Edges are drawn as polylines using only horizontal and vertical segments. This prevents visual clutter and ensures edges do not overlap nodes.

Self-loops (an operation whose output is used as an input to the same operation) are rendered as distinctive right-side U-bend polylines to clearly separate them from standard data-flow edges.

The layout is computed once on function load. Toggling edge visibility via checkboxes merely hides or shows the elements; it does not trigger a relayout, ensuring a stable visual context during analysis.

Performance is optimized for interactive use:
- **Median latency**: ≤200ms
- **p95 latency**: ≤1s (for extremely large functions)

It is useful for:

- first-pass reverse engineering on caller-provided bytes
- visual inspection of p-code use-def structure
- checking how the decompiler recovered a function before you embed the result
  in tooling
- analyzing control-flow and internal operation references using the CPG overlay

## Installation and runtime

Install flatline normally to get the viewer:

```bash
pip install flatline
```

The viewer uses Ghidra's Sleigh disassembly natively, so no extra install is
needed for decoded instructions.

`tkinter` is part of the standard library, but some Python distributions ship
it separately. If the viewer says `tkinter` is missing, install the package for
your platform and try again.

## Tutorial

Start with the [step-by-step tutorial](tutorial.md).
