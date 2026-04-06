# Varnode/Pcode Enrichment Wish-List

## Register Varnodes

We should expose register names for varnodes in the register address space. Look up `(space, offset, size)` via Ghidra's `Translate::getRegisterName()` to get human-readable names like "RAX", "ESP", "X0". This requires architecture-specific lookup from the SLEIGH processor specification. Handle overlapping registers (AL, AX, EAX, RAX share offset 0 with different sizes). Expose as `register_name: str|None` on VarnodeInfo, only populated when `space == "register"`.

Open question: For overlapping registers, prefer largest enclosing register or exact match?

## Symbol Integration (Exploratory)

Explore whether users can provide symbol information during decompilation to enable `getSymbolEntry()` for RAM varnodes. Questions: How does Ghidra use SymbolEntry during decompilation? Can we pass symbol tables/prototypes via API? Would need language-specific demangling, type parsing, address-to-symbol mapping. Benefits: symbol names for RAM varnodes, better type propagation, improved decompilation output. Complexity: requires integration with LoadImage, symbol table management, architecture-specific handling.

## INPUT Varnodes

We should add `parameter_index: int|None` to VarnodeInfo for INPUT varnodes. Currently INPUT varnodes and ParameterInfo exist separately with no linkage. Both use `storage` (space+offset+size) as a potential join key. Match by storage location to associate each INPUT varnode with its corresponding parameter from FunctionPrototype.parameters.

We should add more VarnodeFlags for INPUT varnodes: `is_unaffected` (callee-saved registers preserved across function), `is_indirect_storage` (parameter passed by pointer), `is_hidden_return` (hidden return value pointer). These are available in Ghidra's Varnode flags but not exposed. For xray visualization, `is_unaffected` could be distinguished (e.g., different color for preserved inputs).

We should review `offset` semantics for INPUT varnodes. Currently offset is raw storage location: register number for register space, stack offset for stack parameters. The semantics vary by address space and calling convention. Consider whether to reinterpret or expose additional context (e.g., stack offset relative to what base?).

Open questions: (1) Should `parameter_index` be added to VarnodeInfo or `varnode_id` added to ParameterInfo? (2) Storage matching: exact match or allow size overlaps? (3) How to handle parameters split across multiple varnodes (e.g., large structs)?