# Enriched Output

flatline provides an opt-in "enriched" output mode that exposes the post-simplification
p-code IR used by the decompiler. This enables data-flow analysis, graph traversal,
and deep inspection of decompiler internals without parsing C code.

## Requesting enriched output

To receive p-code and instruction metadata, set `enriched=True` in your
`DecompileRequest`. The results are available in `result.enriched`.

The `pcode` object provides O(1) lookup for operations and varnodes by their
stable IDs.

```python
from flatline import DecompileRequest, decompile_function

request = DecompileRequest(
    memory_image=code_bytes,
    base_address=0x1000,
    function_address=0x1000,
    language_id="x86:LE:64:default",
    enriched=True,  # Opt-in to enriched payload
)

result = decompile_function(request)

if result.enriched and result.enriched.pcode:
    pcode = result.enriched.pcode
    
    # Access all operations and varnodes
    ops = pcode.pcode_ops
    vns = pcode.varnodes
    
    # O(1) lookup by ID
    op = pcode.get_pcode_op(ops[0].id)
    vn = pcode.get_varnode(vns[0].id)
```

For graph-based analysis, you can project the p-code IR into a
`networkx.MultiDiGraph`:

```python
# Returns a bipartite graph (ops and varnodes as nodes)
graph = pcode.to_graph()
```

## Following fspec varnodes to call sites

In the decompiler's IR, calls are often represented using varnodes in the `fspec`
address space. These varnodes don't represent data but rather metadata about a
specific call site.

The `offset` of an `fspec` varnode is always `0`. The meaningful value is
`call_site_index`, which you can use to look up the corresponding
`CallSiteInfo` in the `FunctionInfo`.

```python
# Find all fspec (call-specification) varnodes
fspec_vns = [vn for vn in pcode.varnodes if vn.space == "fspec"]

for vn in fspec_vns:
    if vn.call_site_index is not None:
        # Resolve to the structured call site information
        call_site = result.function_info.call_sites[vn.call_site_index]
        print(f"Call at 0x{call_site.instruction_address:x}")
        if call_site.target_address:
            print(f"  Target: 0x{call_site.target_address:x}")
```

## Resolving IOP varnodes

`iop` (Internal Op Pointer) varnodes are used to reference other p-code operations
directly. This is common in `BRANCH`, `CBRANCH`, and `CALLIND` operations.

The `offset` of an `iop` varnode is `0`. Use `target_op_id` to retrieve the
referenced operation from the `pcode` object.

```python
# Find all iop (internal op pointer) varnodes
iop_vns = [vn for vn in pcode.varnodes if vn.space == "iop"]

for vn in iop_vns:
    if vn.target_op_id is not None:
        # Resolve the internal pointer to the target p-code operation
        target_op = pcode.get_pcode_op(vn.target_op_id)
        print(f"Pointer to {target_op.opcode} at 0x{target_op.instruction_address:x}")
```

## Inspecting CBRANCH targets

`CBRANCH` operations represent conditional branches. Unlike raw assembly branches,
the enriched `PcodeOpInfo` provides semantically resolved branch targets that
account for decompiler simplifications and condition inversions.

```python
# Find all CBRANCH operations
cbranch_ops = [op for op in pcode.pcode_ops if op.opcode == "CBRANCH"]

for op in cbranch_ops:
    # true_target_address and false_target_address are the start addresses
    # of the basic blocks entered based on the condition.
    print(f"CBRANCH at 0x{op.instruction_address:x}:")
    print(f"  If True:  0x{op.true_target_address:x}")
    print(f"  If False: 0x{op.false_target_address:x}")
```

## Understanding address spaces

Varnodes exist within specific address spaces. The `space` attribute determines how
to interpret the `offset` and `size`.

| Space | Offset Interpretation | Size Meaning |
|-------|-----------------------|--------------|
| `const` | The literal constant value. | Value width in bytes. |
| `register` | Processor-specific register number. | Register width. |
| `ram` | Virtual memory address. | Access width. |
| `stack` | Stack-frame offset. | Variable width. |
| `unique` | Internal temporary ID (opaque). | Temporary width. |
| `fspec` | Metadata index; use `call_site_index`. | N/A (usually 4 or 8). |
| `iop` | Metadata index; use `target_op_id`. | N/A (usually 4 or 8). |
| `join` | Merged variable storage (opaque). | Combined width. |

For a complete description of all fields, see the [VarnodeInfo API Reference](../reference/enriched.md#flatline.VarnodeInfo).
