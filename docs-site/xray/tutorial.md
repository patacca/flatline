# X-Ray Tutorial

This tutorial shows how to launch `flatline-xray` on a tiny raw memory image
that you create yourself. It uses the same inputs as the Python API, so you can
move between code and GUI without changing the underlying contract.

## 1. Install the viewer

Install flatline normally to get the viewer:

```bash
pip install flatline
```

The viewer uses Ghidra's Sleigh disassembly natively, so `pip install flatline`
is enough for decoded instructions.

## 2. Pick a target

List the language/compiler pairs available in your installation:

```bash
flatline-xray --list-targets
```

You should see pairs such as `x86:LE:64:default gcc` and other target values
that match your runtime data.

## 3. Create a tiny raw image

This example writes four bytes for a simple x86-64 function, then pads the rest
of the image with zeros so the decompiler has enough bytes to inspect:

```bash
python - <<'PY'
from pathlib import Path

Path("demo.bin").write_bytes(bytes.fromhex("8d0437c3") + b"\x00" * 16)
PY
```

The bytes are `lea eax, [rdi + rsi]; ret`, which is enough for a minimal GUI
demo.

## 4. Launch X-Ray

Run the viewer with the raw image, explicit addresses, and a target pair:

```bash
flatline-xray demo.bin \
  --base-address 0x1000 \
  --function-address 0x1000 \
  --language-id x86:LE:64:default \
  --compiler-spec gcc
```

`python -m flatline.xray` is equivalent if you prefer module invocation:

```bash
python -m flatline.xray demo.bin \
  --base-address 0x1000 \
  --function-address 0x1000 \
  --language-id x86:LE:64:default \
  --compiler-spec gcc
```

## 5. Read the panels

After launch, the window shows three coordinated views. You can resize these by dragging the vertical dividers between them.

- **The graph view** (Center) shows p-code ops and varnodes with edges for def-use relationships.
    - Click a node to focus it: this highlights the node, mutes unrelated nodes, and populates the inspector.
    - The assembly panel automatically scrolls to the related instruction.
    - Press **Ctrl+0** to reset the zoom and re-center the graph.
- **The assembly panel** (Left) lists the recovered instruction addresses and decoded instructions.
    - Selecting an assembly line highlights all related p-code nodes in the graph.
- **The inspector panel** (Right) provides a structured view of the selected node's metadata:
    - **Function & Metadata**: Address, size, and basic block info.
    - **Recovered C**: The specific C-code fragment for this operation.
    - **Usage**: Detailed use-def links and varnode flags.

Clicking any element in one panel synchronizes the highlights and focus across all three views, ensuring you always have the full context for the current p-code operation.

## 6. Enable the CPG overlay

The Code Property Graph (CPG) mode adds control-flow and reference edges on top of the default data-flow graph.

Launch the viewer with the `--cpg` flag:

```bash
flatline-xray demo.bin \
  --base-address 0x1000 \
  --function-address 0x1000 \
  --language-id x86:LE:64:default \
  --compiler-spec gcc \
  --cpg
```

In this mode, several new elements appear:

- **Control-flow edges**: Solid lines connecting branch operations to their targets. Green indicates the true branch; red indicates the false branch.
- **Reference edges**: Amber dashed lines connecting internal operation pointers (IOPs) to their target operations.
- **Call targets**: Purple dashed lines connecting call operations to virtual nodes labeled with the destination address.

The inspector panel now includes an **Edge Visibility** section at the bottom. Use the checkboxes to toggle the visibility of each overlay edge type.

For a detailed breakdown of edge types and inspector changes, see the [CPG Overlay reference](cpg.md).

## Troubleshooting

If the viewer refuses to start because `tkinter` is missing, install the Python
package that provides it for your platform, then rerun `flatline-xray`.

If the viewer rejects an address, check that `--base-address` and
`--function-address` are valid integers. Hex values must include the `0x`
prefix if you want base-16 parsing.

If the target is unsupported, rerun `flatline-xray --list-targets` and choose a
pair that matches your architecture and runtime data.

If runtime data is not being discovered automatically, pass
`--runtime-data-dir /path/to/ghidra/runtime/data` so the viewer can find the
Sleigh assets.
