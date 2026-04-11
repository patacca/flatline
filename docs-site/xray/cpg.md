# CPG Overlay

The Code Property Graph (CPG) mode provides an interactive overlay of control-flow and internal reference edges on top of the standard p-code data-flow graph.

## Enabling CPG mode

CPG mode is opt-in. Enable it via the CLI:

```bash
flatline-xray demo.bin \
  --base-address 0x1000 \
  --function-address 0x1000 \
  --language-id x86:LE:64:default \
  --compiler-spec gcc \
  --cpg
```

In the Python API, pass `cpg=True` when initializing an `XrayWindow`.

## Edge types

Three additional edge types are available in CPG mode. All edges use orthogonal Manhattan routing.

### Control-flow edges

These connect p-code trees containing branch operations to their targets.

- **True branch**: Solid green line.
- **False branch**: Solid red line.

### IOP reference edges

These connect nodes referencing internal operation pointers (IOPs) to the tree containing the target operation.

- **Appearance**: Amber dashed line.

### Call-target edges

These connect call operations to virtual nodes representing the callee address.

- **Appearance**: Purple dashed line.
- **Virtual node**: A purple rectangle showing the target address in hex.
- **Limitation**: Indirect calls with unresolvable targets are not drawn.

## Edge visibility

The inspector panel contains an **Edge Visibility** section at the bottom. Use these checkboxes to toggle the visibility of each overlay type:

- **Control-flow edges**: Toggles CBRANCH overlay lines.
- **IOP reference edges**: Toggles IOP overlay lines.
- **Call target edges**: Toggles fspec overlay lines and their virtual nodes.

If the viewer is launched without the `--cpg` flag, the control-flow checkbox is disabled.

## Inspector details

Selecting specific node types in CPG mode populates additional fields in the inspector panel.

### IOP Varnodes
When an IOP varnode is selected, the **IOP Target** section displays the target operation ID.

### Call Site Varnodes
When an fspec (call-site) varnode is selected, the **Call Site** section displays the site index.
