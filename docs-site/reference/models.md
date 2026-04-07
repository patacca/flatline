# Data Models

All data models are frozen dataclasses.  Fields are populated on successful
decompilation; see [`DecompileResult`][flatline.DecompileResult] for how
`None` values are used on error.

## Enums

These enums provide type-safe string constants for pcode opcodes and varnode
spaces.

::: flatline.PcodeOpcode

::: flatline.VarnodeSpace

## Function Structure

::: flatline.FunctionInfo

::: flatline.FunctionPrototype

::: flatline.DiagnosticFlags

## Pcode Operation Hierarchy

Pcode operations are represented by a hierarchy of classes inheriting from
[`PcodeOpInfo`][flatline.PcodeOpInfo]. These are organized into categories
reflecting their functional purpose.

### Category Base Classes

- `ArithmeticOp`
- `BitwiseOp`
- `BooleanOp`
- `BranchOp`
- `CallOp`
- `ComparisonOp`
- `CopyOp`
- `DataflowOp`
- `HighLevelOp`
- `MemoryOp`

### Leaf Operations

There are 72 specific operation classes (e.g., `IntAdd`, `Load`, `Copy`). These
can be accessed via the `OPCODE_TO_CLASS` dispatch table or imported from
`flatline.models.pcode_ops`.

## Varnode Hierarchy

Varnodes are represented by specialized subclasses of
[`VarnodeInfo`][flatline.VarnodeInfo] based on their address space.

- `ConstVarnode`
- `RegisterVarnode`
- `UniqueVarnode`
- `RamVarnode`
- `FspecVarnode`
- `IopVarnode`
- `JoinVarnode`
- `StackVarnode`

The `SPACE_TO_CLASS` dispatch table maps space strings to these subclasses.

## Leaf Types

::: flatline.TypeInfo

::: flatline.ParameterInfo

::: flatline.VariableInfo

::: flatline.CallSiteInfo

::: flatline.JumpTableInfo

::: flatline.StorageInfo
