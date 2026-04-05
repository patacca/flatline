# Ghidra Varnode Internals

Reference analysis of varnode structure, flags, and address spaces as found in
the Ghidra decompiler source (`third_party/ghidra/.../decompile/cpp/`).

Primary sources: `varnode.hh`, `space.hh`, `fspec.hh`.

## Varnode core attributes

A varnode is formally a triple: (address space, offset, size).

Internal fields on the C++ `Varnode` object:

| Field            | Type              | Description                                        |
|------------------|-------------------|----------------------------------------------------|
| `flags`          | `uint4`           | Primary boolean flags (32-bit bitmask)             |
| `addlflags`      | `uint2`           | Additional flags (16-bit bitmask)                  |
| `size`           | `int4`            | Size in bytes                                      |
| `loc`            | `Address`         | Storage location = space + offset                  |
| `def`            | `PcodeOp *`       | Defining op (null if input/constant)               |
| `descend`        | `list<PcodeOp *>` | All ops using this varnode as input                |
| `high`           | `HighVariable *`  | High-level variable this instantiates              |
| `type`           | `Datatype *`      | Associated datatype                                |
| `mapentry`       | `SymbolEntry *`   | Cached symbol/database entry                       |
| `cover`          | `Cover *`         | Address range covered by def-to-use                |
| `create_index`   | `uint4`           | Unique creation index                              |
| `mergegroup`     | `int2`            | Forced-merge group ID                              |

## Type interpretations

Operations force varnodes into one of three type interpretations:

- **Integer**: twos-complement, endianness from the address space.
- **Boolean**: single byte, 0 (false) or 1 (true).
- **Floating-point**: processor-specific encoding, typically IEEE 754.

## Address spaces (7 types)

From `enum spacetype` in `space.hh`:

| Enum              | Value | Description                                              |
|-------------------|-------|----------------------------------------------------------|
| `IPTR_CONSTANT`   | 0     | Constants/immediates (no real storage)                   |
| `IPTR_PROCESSOR`  | 1     | Normal processor-modeled spaces (`ram`, `register`)      |
| `IPTR_SPACEBASE`  | 2     | Offsets relative to a base register (e.g. `stack`)       |
| `IPTR_INTERNAL`   | 3     | Temporary/unique registers (decompiler-internal)         |
| `IPTR_FSPEC`      | 4     | Internal FuncCallSpecs pointer (see below)               |
| `IPTR_IOP`        | 5     | Internal PcodeOp reference                               |
| `IPTR_JOIN`       | 6     | Virtual space for split variables (pieces joined)        |

Named spaces typically seen on exported varnodes: `const`, `register`, `ram`,
`stack`, `unique`.

## Primary flags (`varnode_flags`) -- 32 flags, all 32 bits used

From `varnode.hh`:

| Flag                | Bit          | Description                                          |
|---------------------|--------------|------------------------------------------------------|
| `mark`              | `0x01`       | Prevents infinite loops during traversal             |
| `constant`          | `0x02`       | Varnode is a constant                                |
| `annotation`        | `0x04`       | Annotation only, no dataflow                         |
| `input`             | `0x08`       | Has no ancestor (function input)                     |
| `written`           | `0x10`       | Has a defining op                                    |
| `insert`            | `0x20`       | Inserted in VarnodeBank tree                         |
| `implied`           | `0x40`       | Temporary variable (no named var in C output)        |
| `explict`           | `0x80`       | CANNOT be temporary (Ghidra typo, not `explicit`)    |
| `typelock`          | `0x100`      | Datatype is locked                                   |
| `namelock`          | `0x200`      | Name is locked                                       |
| `nolocalalias`      | `0x400`      | No aliases point here                                |
| `volatil`           | `0x800`      | Value is volatile (avoids C++ keyword)               |
| `externref`         | `0x1000`     | Address specially mapped by loader                   |
| `readonly`          | `0x2000`     | Stored at read-only location                         |
| `persist`           | `0x4000`     | Persists before and after function (global/register) |
| `addrtied`          | `0x8000`     | High-level variable tied to address                  |
| `unaffected`        | `0x10000`    | Input unaffected by function                         |
| `spacebase`         | `0x20000`    | Base register for an address space                   |
| `indirectonly`      | `0x40000`    | All uses are inputs to INDIRECT ops                  |
| `directwrite`       | `0x80000`    | Could be directly affected by valid input            |
| `addrforce`         | `0x100000`   | Forces variable into an address                      |
| `mapped`            | `0x200000`   | Has a database/symbol entry                          |
| `indirect_creation` | `0x400000`   | Value created indirectly                             |
| `return_address`    | `0x800000`   | Storage for a return address                         |
| `coverdirty`        | `0x1000000`  | Cover info is stale                                  |
| `precislo`          | `0x2000000`  | Low part of double-precision value                   |
| `precishi`          | `0x4000000`  | High part of double-precision value                  |
| `indirectstorage`   | `0x8000000`  | Stores pointer to actual symbol                      |
| `hiddenretparm`     | `0x10000000` | Points to return value storage                       |
| `incidental_copy`   | `0x20000000` | Copies happen as side-effect                         |
| `autolive_hold`     | `0x40000000` | Temporarily blocks dead-code removal                 |
| `proto_partial`     | `0x80000000` | Being PIECEd into unmapped structure                 |

## Additional flags (`addl_flags`) -- 13 flags

| Flag                     | Bit      | Description                                       |
|--------------------------|----------|---------------------------------------------------|
| `activeheritage`         | `0x01`   | Actively being heritaged                          |
| `writemask`              | `0x02`   | Not considered a write in heritage                |
| `vacconsume`             | `0x04`   | Vacuous consume                                   |
| `lisconsume`             | `0x08`   | In consume worklist                               |
| `ptrcheck`               | `0x10`   | Value is NOT a pointer                            |
| `ptrflow`                | `0x20`   | Flows to/from a pointer                           |
| `unsignedprint`          | `0x40`   | Must print as unsigned token                      |
| `longprint`              | `0x80`   | Must print as long integer token                  |
| `stack_store`            | `0x100`  | Created by explicit STORE                         |
| `locked_input`           | `0x200`  | Input exists even if unused                       |
| `spacebase_placeholder`  | `0x400`  | Artificial insertion to track register value       |
| `stop_uppropagation`     | `0x800`  | Block data-type upward propagation                |
| `has_implied_field`      | `0x1000` | Implied but has data-type needing resolution      |

**Total: 32 primary + 13 additional = 45 boolean flags.**

## IPTR_FSPEC: the fspec space

`FspecSpace` (`fspec.hh:339-357`) is a special address space that encodes a
pointer to a C++ `FuncCallSpecs` object as a varnode address. The varnode's
offset field is the raw in-process pointer value, which is meaningless after
the decompiler exits.

These varnodes appear as **input slot 0** of `CALL`/`CALLIND` pcode ops.

The `FuncCallSpecs` object behind the pointer carries:

| Field                | Description                                            |
|----------------------|--------------------------------------------------------|
| `name`               | Callee function name                                   |
| `entryaddress`       | Callee entry address (the real call target)            |
| `fd`                 | Full Funcdata of callee (if resolved)                  |
| `effective_extrapop` | Bytes the call pops off the stack                      |
| `stackoffset`        | Stack-pointer offset relative to function entry        |
| `activeinput`        | ParamActive: input parameter recovery state            |
| `activeoutput`       | ParamActive: output parameter recovery state           |
| `inputConsume`       | Bytes consumed per input parameter                     |
| `matchCallCount`     | Call count within the caller                           |
| `isbadjumptable`     | Whether this was an unrecoverable jump table           |

Plus inherited `FuncProto` fields: calling convention, parameter list, return
type, `dotdotdot` (variadic), `is_constructor`, `is_destructor`,
`has_thisptr`, `is_noreturn`.

**Implication for flatline**: the offset exported on fspec varnodes is a
dangling heap pointer. The real callee address must be recovered at extraction
time via `FuncCallSpecs::getFspecFromConst()` before the decompiler tears down.
See TODO item for resolution plan.

## IPTR_IOP: the iop space

Similar internal-reference trick: encodes a pointer to a `PcodeOp` object as
a varnode address. Used for annotation varnodes that tag pcode operations
(e.g. for INDIRECT ops). Same dangling-pointer problem as fspec.

## flatline's current exposure

`VarnodeFlags` exposes 8 of the 45 flags:

- `is_constant` (primary `constant`)
- `is_input` (primary `input`)
- `is_free` (derived: not written, not input, not constant)
- `is_implied` (primary `implied`)
- `is_explicit` (primary `explict`)
- `is_read_only` (primary `readonly`)
- `is_persist` (primary `persist`)
- `is_addr_tied` (primary `addrtied`)

`VarnodeInfo.space` is the string name of the address space (`const`,
`register`, `ram`, `stack`, `unique`, `fspec`, `iop`, `join`).
