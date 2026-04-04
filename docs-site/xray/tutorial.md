# X-Ray Tutorial

This tutorial shows how to launch `flatline-xray` on a tiny raw memory image
that you create yourself. It uses the same inputs as the Python API, so you can
move between code and GUI without changing the underlying contract.

## 1. Install the viewer

Install flatline with the optional X-Ray extra:

```bash
pip install "flatline[xray]"
```

If you only need the core library, `pip install flatline` is enough. The X-Ray
extra adds optional disassembly support via `capstone`.

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

After launch, the window shows three coordinated views:

- The graph view shows p-code ops and varnodes as a tree with edges for
  def-use relationships.
- The assembly panel lists the recovered instruction addresses, and decoded
  instructions when `capstone` is installed.
- The inspector panel shows details for the selected node, including flags,
  use-def links, and address metadata.

Click a node in the graph to focus its details. Select an assembly line to
highlight the related p-code nodes.

## 6. Understand degraded success

If `capstone` is not installed, X-Ray still opens. The assembly panel falls
back to addresses only, and the viewer prints a startup note that suggests:

```bash
pip install "flatline[xray]"
```

That is expected degraded behavior, not a failure.

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

