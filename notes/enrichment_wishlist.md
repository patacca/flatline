# Varnode/Pcode Enrichment Wish-List

## Fspec Varnodes

We should reinterpret fspec varnodes which currently expose useless pointer offsets. The `offset` field should become a `call_site_index` into `function_info.call_sites`, letting users correlate CALL/CALLIND ops with their call specifications. Options: (A) reuse `offset` field with new semantics, or (B) add dedicated `call_site_index: int|None` field. Filtering fspec varnodes entirely is an alternative but breaks SSA input[0] structure.

We should expose operation semantics from Ghidra's PcodeOp flags: `is_branch`, `is_call`, `is_return` for control flow, `is_dead` for dead code, `is_marker` for MULTIEQUAL/INDIRECT SSA nodes, and `has_call_spec` for CALL ops with attached FuncCallSpecs. Also consider `is_commutative` and arity flags (`is_unary`, `is_binary`, `is_ternary`).

We should add varnode flags: `is_volatile` for volatile storage, `is_unaffected` for preserved registers, `is_written` (has def), `is_annotation` (internal), and `is_spacebase` (stack pointer base).

We should extend CallSiteInfo with: `target_name` (callee), `stack_adjustment` (extrapop), `is_direct`, `is_noreturn`.

We should add `BasicBlockInfo` with op indices and CFG edges, plus `basic_block_id` on PcodeOpInfo.

We should expose varnode types: `type_name`, `type_size`, `type_metatype` from Ghidra's Datatype.

Open questions: (1) Reinterpret `offset` or add `call_site_index` field? (2) Keep fspec/iop varnodes or filter them? (3) Curated flag subset or expose all 60+?

## Register Varnodes

We should expose register names for varnodes in the register address space. Look up `(space, offset, size)` via Ghidra's `Translate::getRegisterName()` to get human-readable names like "RAX", "ESP", "X0". This requires architecture-specific lookup from the SLEIGH processor specification. Handle overlapping registers (AL, AX, EAX, RAX share offset 0 with different sizes). Expose as `register_name: str|None` on VarnodeInfo, only populated when `space == "register"`.

Open question: For overlapping registers, prefer largest enclosing register or exact match?

## Varnode Documentation

We should document address space semantics in VarnodeInfo docstrings: (1) TEMP/unique space: offset is meaningless allocation ID, internal temporary storage. (2) CONST space: offset IS the constant value. (3) FSPEC space: offset encodes FuncCallSpecs pointer, reinterpret as call_site_index. (4) IOP space: offset encodes PcodeOp pointer for branch targets. (5) JOIN space: represents split/merged variables. (6) Register space: offset is register number, add register_name lookup.

## Symbol Integration (Exploratory)

Explore whether users can provide symbol information during decompilation to enable `getSymbolEntry()` for RAM varnodes. Questions: How does Ghidra use SymbolEntry during decompilation? Can we pass symbol tables/prototypes via API? Would need language-specific demangling, type parsing, address-to-symbol mapping. Benefits: symbol names for RAM varnodes, better type propagation, improved decompilation output. Complexity: requires integration with LoadImage, symbol table management, architecture-specific handling.

## CBRANCH Operations

We should expose branch semantics for CBRANCH operations. Currently users see the opcode and two input varnodes but cannot determine which path is taken on TRUE vs FALSE. Ghidra tracks this via `boolean_flip` and `fallthru_true` flags, but these are internal implementation details tracking different transformations. Expose a single `branch_on_false: bool` flag (or equivalently `fallthrough_on_true: bool`) that conveys the practical meaning: whether the branch is taken when the condition evaluates to FALSE.

We should expose resolved branch target addresses. The `input[0]` varnode contains the target, but resolving it requires Ghidra's `branchTarget()` and `fallthruOp()` functions. Expose `branch_target: int|None` and `fallthrough_target: int|None` on PcodeOpInfo for CBRANCH/BRANCH ops. For BRANCHIND (indirect branches), `branch_target` would be None since the target is computed at runtime.

Open questions: (1) Compute targets eagerly or lazily? (2) How to handle BRANCHIND where target is not statically known? (3) Should xray visualize true/false edges differently?

## INPUT Varnodes

We should add `parameter_index: int|None` to VarnodeInfo for INPUT varnodes. Currently INPUT varnodes and ParameterInfo exist separately with no linkage. Both use `storage` (space+offset+size) as a potential join key. Match by storage location to associate each INPUT varnode with its corresponding parameter from FunctionPrototype.parameters.

We should add more VarnodeFlags for INPUT varnodes: `is_unaffected` (callee-saved registers preserved across function), `is_indirect_storage` (parameter passed by pointer), `is_hidden_return` (hidden return value pointer). These are available in Ghidra's Varnode flags but not exposed. For xray visualization, `is_unaffected` could be distinguished (e.g., different color for preserved inputs).

We should review `offset` semantics for INPUT varnodes. Currently offset is raw storage location: register number for register space, stack offset for stack parameters. The semantics vary by address space and calling convention. Consider whether to reinterpret or expose additional context (e.g., stack offset relative to what base?).

Open questions: (1) Should `parameter_index` be added to VarnodeInfo or `varnode_id` added to ParameterInfo? (2) Storage matching: exact match or allow size overlaps? (3) How to handle parameters split across multiple varnodes (e.g., large structs)?

## IOP Varnodes

We should resolve IOP varnodes at extraction time to expose the pointed-to PcodeOp instead of the raw C++ pointer. The `offset` field currently contains a meaningless heap pointer that becomes invalid after decompiler exit. Ghidra resolves this with `PcodeOp::getOpFromConst(addr)` - a trivial cast. Replace the useless offset with `target_op_id: int|None` referencing the actual PcodeOp in the pcode list.

IOP varnodes appear in: (1) BRANCH/CBRANCH input[0] - the branch target, (2) INDIRECT input[1] - the op causing indirect effect (e.g., CALL, STORE). For branch operations, the target op's address gives the actual branch destination. For INDIRECT, it identifies which operation causes the indirect memory effect.

This is simpler than fspec: IOP resolution requires only a cast, while fspec requires FuncCallSpecs lookup. Resolution must happen in native bridge at extraction time before the PcodeOp pointer becomesinvalid.

Open questions: (1) Expose `target_op_id` or also `target_address`? (2) Filter IOP varnodes entirely and just expose target info on the parent PcodeOp?