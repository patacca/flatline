# Enriched Output

Enriched output is opt-in: set
[`DecompileRequest.enriched`][flatline.DecompileRequest] to `True` to receive
post-simplification pcode operations and varnode use-def graph data alongside
the standard decompilation result.

## Container

::: flatline.Enriched

## Pcode

::: flatline.Pcode
    options:
      group_by_category: true
      show_category_heading: true
      members:
        - pcode_ops
        - varnodes
        - get_pcode_op
        - get_varnode
        - to_graph

## Pcode Hierarchy

Flatline provides a typed hierarchy for pcode operations and varnodes. This
allows for clean filtering and inspection using standard Python `isinstance`
checks and enums.

### Opcodes and Spaces

All pcode operations use the `PcodeOpcode` enum for their `opcode` field, and
varnodes use the `VarnodeSpace` enum for their `space` field. These are
`StrEnum` types, meaning they are backward compatible with string comparisons
while providing type-safe constants.

```python
from flatline import PcodeOpcode, VarnodeSpace

# Enum matching
if op.opcode == PcodeOpcode.CALL:
    handle_call(op)

# Backward compatibility (still works)
if vn.space == "register":
    is_reg = True
```

### Operation Hierarchy

The `pcode_ops` list contains specialized subclasses of `PcodeOpInfo`. You can
filter by broad categories (e.g., `ArithmeticOp`) or specific leaf operations
(e.g., `IntAdd`).

```python
from flatline.models.pcode_ops import ArithmeticOp, IntAdd, BranchOp

# Category filtering with isinstance
arithmetic_ops = [op for op in pcode.pcode_ops if isinstance(op, ArithmeticOp)]

# Leaf filtering with isinstance
int_adds = [op for op in pcode.pcode_ops if isinstance(op, IntAdd)]

# Iterating and filtering branches
for op in result.enriched.pcode.pcode_ops:
    if isinstance(op, BranchOp):
        print(f"Branch at {op.instruction_address:x}")
```

### Varnode Hierarchy

The `varnodes` list contains specialized subclasses of `VarnodeInfo` based on
the address space they reside in.

```python
from flatline.models.varnodes import RegisterVarnode, ConstVarnode

# Space-based filtering
registers = [vn for vn in pcode.varnodes if isinstance(vn, RegisterVarnode)]
constants = [vn for vn in pcode.varnodes if isinstance(vn, ConstVarnode)]
```

### Import Paths

- **Enums**: `from flatline import PcodeOpcode, VarnodeSpace`
- **Ops**: `from flatline.models.pcode_ops import IntAdd, ArithmeticOp, ...`
- **Varnodes**: `from flatline.models.varnodes import RegisterVarnode, ...`

## Pcode Types

::: flatline.PcodeOpInfo

::: flatline.VarnodeInfo

::: flatline.VarnodeFlags
