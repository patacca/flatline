# Ghidra Decompiler API Inventory (Pinned)

Source root:
- `third_party/ghidra/Ghidra/Features/Decompiler/src/decompile/cpp`

Pinned upstream for this inventory:
- Tag: `Ghidra_12.0.3_build`
- Commit: `09f14c92d3da6e5d5f6b7dea115409719db3cce1`
- Commit date: `2026-02-10`

## Strict Minimal Callable Contract (Ghidra C++ Only)

| Symbol name | File path | Kind | Inputs/outputs | Ownership/lifetime | Required initialization order | Error propagation mechanism | Thread-safety notes | MVP relevance | Pin reference |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `startDecompilerLibrary` overload set: `(const char*)`, `(const vector<string>&)`, `(const char*, const vector<string>&)` | `libdecomp.hh` / `libdecomp.cc` | function | In: optional sleigh root and/or extra paths. Out: initialized `AttributeId`, `ElementId`, capability registry, and `specpaths` updates. | Process-global initialization; no returned object. | Must run before constructing decompiler `Architecture` instances. | May propagate lower-level exceptions from filesystem/path scanning. | Mutates global statics (`CapabilityPoint`, `ArchitectureCapability`, `SleighArchitecture::specpaths`). | `required` | `Ghidra_12.0.3_build` |
| `shutdownDecompilerLibrary(void)` | `libdecomp.hh` / `libdecomp.cc` | function | In: none. Out: library shutdown hook (currently no-op in pinned source). | Process-global hook. | Called at library teardown. | No throws in current implementation. | Same global lifecycle constraints as startup. | `required` | `Ghidra_12.0.3_build` |
| `SleighArchitecture::scanForSleighDirectories(const string&)` | `sleigh_arch.hh` / `sleigh_arch.cc` | static function | In: root path. Out: appends discovered language directories to static `specpaths`. | Global mutable path registry. | Use when not relying on `startDecompilerLibrary(sleighhome)` for path setup. | Path discovery failures surface later during spec load/resolve. | Not safe for concurrent mutation. | `optional` | `Ghidra_12.0.3_build` |
| `SleighArchitecture::getDescriptions(void)` | `sleigh_arch.hh` / `sleigh_arch.cc` | static function | Out: `const vector<LanguageDescription>&`. | Reference to static cache. | Requires `specpaths` and readable `.ldefs` (it calls `collectSpecFiles`). | Throws `LowlevelError` if parse warnings were collected. | Read-mostly after init; initial call should be serialized. | `optional` | `Ghidra_12.0.3_build` |
| `LanguageDescription::getCompiler(const string&) const` | `sleigh_arch.hh` / `sleigh_arch.cc` | method | In: compiler id. Out: matching `CompilerTag` or default/first fallback. | Returned reference owned by `LanguageDescription`. | Used by `buildSpecFile`. | No throw for unknown compiler id; fallback behavior is part of contract. | Read-only. | `required` | `Ghidra_12.0.3_build` |
| `SleighArchitecture::SleighArchitecture(const string&,const string&,ostream*)` | `sleigh_arch.hh` / `sleigh_arch.cc` | constructor | In: filename label, target language id/selector string, error stream pointer. Out: base `SleighArchitecture` state for derived classes. | The architecture instance owns subcomponents after `init()`. | Construct concrete subclass, then call `init(DocumentStorage&)`. | Constructor path is non-throwing in pinned source; `init()` path can throw. | Per-instance object plus shared static language/translator caches. | `required` | `Ghidra_12.0.3_build` |
| `DocumentStorage` (`parseDocument`, `openDocument`, `registerTag`, `getTag`) | `xml.hh` | class | XML container passed to init path and spec loaders. | Owns parsed `Document*` list for init lifetime. | Create before `Architecture::init()` and keep alive through init/spec restore. | XML parse/open can throw decoder/xml exceptions. | Not documented as thread-safe. | `required` | `Ghidra_12.0.3_build` |
| `Architecture::init(DocumentStorage&)` | `architecture.hh` / `architecture.cc` | method | In: initialized `DocumentStorage`. Out: fully initialized loader/translator/context/type/comment/db/actions/print state. | `Architecture` owns created subsystems. | Exact order in code: loader -> resolve -> spec -> context/type/comment/string/const/db -> restoreFromSpec -> core types -> print init -> symbols -> postSpec -> instructions -> readonly ranges. | Can throw `LowlevelError`, `SleighError`, `DecoderError` (via callees). | Instance mutation only; not safe to call concurrently on same object. | `required` | `Ghidra_12.0.3_build` |
| `Architecture` public fields required by direct callers: `symboltab` (Database*, :190), `types` (TypeFactory*, :197), `commentdb` (CommentDatabase*, :202), `print` (PrintLanguage*, :205), `allacts` (ActionDatabase, :212), `max_implied_ref` (int4, :171), `readonlypropagate` (bool, :177), `max_instructions` (uint4, :185, default 100000) | `architecture.hh` | public data layout | Direct callers may write config fields and read subsystem pointers for lookup/action/printing. | Raw pointer/public-field ABI coupling; no ownership transfer. `allacts` is embedded (not a pointer). | Valid only after `Architecture` construction; pointer fields are populated by `init()`. | Null/invalid pointers if accessed before init. | ABI-sensitive C++ layout dependency; reordering/removal is breaking. | `required` | `Ghidra_12.0.3_build` |
| `AddrSpaceManager::getDefaultCodeSpace(void) const` | `translate.hh` | inline method | Out: default code `AddrSpace*` used to build `Address` for function lookup. | Returned pointer owned by architecture/translator space manager. | Valid after translator/space setup in `init()`. | No throws. | Read-only accessor. | `required` | `Ghidra_12.0.3_build` |
| `Database::getGlobalScope(void) const` + `Scope::findFunction(const Address&) const` | `database.hh` | methods | In: function entry `Address`. Out: `Funcdata*` for decompile target. | `Funcdata` owned by symbol database/scope. | Requires database population by `buildDatabase`/symbol import. | Null return if function absent. | Scope/database mutation is not synchronized by default. | `required` | `Ghidra_12.0.3_build` |
| `Scope::addFunction(const Address&, const string&)` + `FunctionSymbol::getFunction(void)` | `database.hh` / `database.cc` | methods | In: function entry `Address` and name. Out: `FunctionSymbol*` (database.hh:781); then `FunctionSymbol::getFunction()` → `Funcdata*`. | Function object owned by `FunctionSymbol`/scope database. | Use when target function is not already present in scope before `findFunction`. | Can throw on invalid overlap/creation paths from scope/database operations. | Mutates symbol database; external synchronization required. | `required` | `Ghidra_12.0.3_build` |
| `Architecture::setPrintLanguage(const string&)` | `architecture.hh` / `architecture.cc` | method | In: print capability name. Out: active `print` instance switched/created and initialized. | `Architecture` owns `print` object(s). | Call after `init()` (printlist and architecture data ready). | Throws `LowlevelError` for unknown language capability. | Mutates printer state, not thread-safe on shared instance. | `required` | `Ghidra_12.0.3_build` |
| `ActionDatabase::getCurrent()` + `Action::reset(Funcdata&)` + `Action::perform(Funcdata&)` | `action.hh` / `action.cc` | methods | In: selected `Funcdata`. Out: transformed/decompiled state; `perform` returns change-count or `<0` for partial/break. | No ownership transfer. | `reset` then `perform` per invocation. | `perform` can propagate decompile exceptions raised by actions/rules. | Action object stateful; do not share same instance unsafely across threads. | `required` | `Ghidra_12.0.3_build` |
| `PrintLanguage::setOutputStream(ostream*)`, `setMarkup(bool)`, `docFunction(const Funcdata*)` | `printlanguage.hh` | methods | Configure output sink/markup and emit decompiled function text. | Printer owned by architecture; output stream owned by caller. | Call after `setPrintLanguage` and action `perform`. | `docFunction` may throw on inconsistent function/printer state. | Printer is mutable; single-thread use per architecture instance. | `required` | `Ghidra_12.0.3_build` |
| `Funcdata::warningHeader(const string&) const` | `funcdata.hh` / `funcdata.cc` | method | In: warning text. Out: `Comment::warningheader` insertion in active comment DB. | Comment ownership stays with comment DB. | Available after function resolution; used for warning surfacing. | No throw on normal path. | Depends on shared `commentdb` synchronization policy. | `optional` | `Ghidra_12.0.3_build` |
| `Funcdata::encode(Encoder&,uint8,bool) const` | `funcdata.hh` | method | In: encoder + id + tree flag. Out: XML-encoded function payload. | Encoder owned by caller. | Optional XML output mode after decompile. | Can throw encoding/serialization errors. | Read-only over `Funcdata`, but requires stable function state. | `optional` | `Ghidra_12.0.3_build` |
| `LoadImage` virtual interface (`loadFill`, `getArchType`, `adjustVma`, and optionally `getReadonly`) | `loadimage.hh` | abstract interface | Loader contract used by architecture init + flow decode + readonly propagation. | Concrete loader owned by architecture. | Required when implementing a custom Architecture/loader bridge. | Unreadable regions usually propagate `DataUnavailError`/`LowlevelError`. | Backend-specific thread-safety; caller must serialize as needed. | `required` | `Ghidra_12.0.3_build` |

## Post-Decompilation Contract

After `Action::perform(Funcdata&)` returns successfully (return value >= 0), the `Funcdata` object and the `Architecture` subsystems expose the objects documented below. All references are to `Ghidra_12.0.3_build`.

**Validity window**: All pointers and iterators remain valid until `Architecture::clearAnalysis(Funcdata*)` is called, or the `Funcdata`/`Architecture` is destroyed. Decompiling a different function does NOT invalidate results from a previous decompile — each `Funcdata` instance is independent.

**Thread-safety default**: None of these objects are internally synchronized. All access must be externally serialized per `Architecture` instance. Read-only access to a single `Funcdata` from multiple threads is safe only if no other thread is mutating the owning `Architecture`.

**MVP relevance key**:
- `required` — needed for C text output, function metadata, and basic diagnostics
- `optional` — IR/P-code access, structured blocks, detailed type exploration, serialization
- `ignore` — internal analysis bookkeeping, debug printing, heritage tracking

### 1) Decompile Entrypoints & Result Container

| Class::method(s) | Semantic role | Extractable data | Extraction signature | Ownership / lifetime | Errors / diagnostics | Thread-safety | MVP |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Funcdata` (class) | Central result container for one decompiled function | CFG, IR graph, symbols, types, prototype, jump-tables, diagnostics | Obtained via `Scope::findFunction` or `FunctionSymbol::getFunction` | Owned by `FunctionSymbol` in the `Database`; valid until scope/database cleared | N/A | Default | `required` |
| `Funcdata::getName()` / `getDisplayName()` | Function name | `const string&` | `const string& getName() const` | Reference to internal string; stable while `Funcdata` lives | No throws | Read-only | `required` |
| `Funcdata::getAddress()` | Function entry point address | `const Address&` | `const Address& getAddress() const` | Reference to internal `Address`; stable | No throws | Read-only | `required` |
| `Funcdata::getSize()` | Function body size in bytes | `int4` | `int4 getSize() const` | Value copy | No throws | Read-only | `required` |
| `Funcdata::getArch()` | Back-pointer to owning Architecture | `Architecture*` | `Architecture* getArch() const` | Pointer to parent; do not delete | No throws | Read-only | `required` |
| `Funcdata::getFuncProto()` | Function prototype (calling convention, params, return type) | `FuncProto&` with model name, param types, return type, flags | `FuncProto& getFuncProto()` / `const FuncProto& getFuncProto() const` | Reference to embedded member; stable while `Funcdata` lives | Check `hasInputErrors()`, `hasOutputErrors()` for incomplete recovery | Default | `required` |
| `Funcdata::getScopeLocal()` | Local variable scope | `ScopeLocal*` | `ScopeLocal* getScopeLocal()` | Pointer to embedded scope; stable while `Funcdata` lives | No throws | Default | `required` |
| `Funcdata::isProcComplete()` | Whether decompilation completed fully | `bool` | `bool isProcComplete() const` | Value copy | N/A | Read-only | `required` |

- `FuncProto` exposes: `getModelName()`, `isNoReturn()`, `isInline()`, `isConstructor()`, `isDestructor()`, `hasThisPointer()`, `isInputLocked()`, `isOutputLocked()`, `getExtraPop()`, `hasInputErrors()`, `hasOutputErrors()`. Parameters are accessed via internal `ProtoStore`; the printer handles parameter rendering.
- `Funcdata::getSymbol()` (funcdata.hh:145) returns `FunctionSymbol*` linking back to the scope/database.
- `Funcdata::numVarnodes()` (funcdata.hh:279) returns total Varnode count as `int4` — useful for complexity metrics.
- `Funcdata::getFirstReturnOp()` (funcdata.hh:448) returns a representative `PcodeOp*` with opcode `CPUI_RETURN`, or null if none.

### 2) C/Text Output Generation (Pretty Printer)

| Class::method(s) | Semantic role | Extractable data | Extraction signature | Ownership / lifetime | Errors / diagnostics | Thread-safety | MVP |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `PrintLanguage::setOutputStream(ostream*)` | Set destination stream for C output | N/A (configuration) | `void setOutputStream(ostream* t)` | Stream owned by caller; printer holds non-owning reference | No throws | Mutates printer | `required` |
| `PrintLanguage::setMarkup(bool)` | Toggle XML markup in output | N/A (configuration) | `void setMarkup(bool val)` | N/A | No throws | Mutates printer | `required` |
| `PrintLanguage::docFunction(const Funcdata*)` | Emit complete decompiled C function | Full C source text (declaration + body) written to output stream | `virtual void docFunction(const Funcdata* fd) = 0` | Output written to previously-set stream; no ownership transfer | May throw on inconsistent printer/function state | Not thread-safe; single printer per architecture | `required` |
| `PrintLanguage::docAllGlobals()` | Emit all global variable declarations | Global declarations text | `virtual void docAllGlobals() = 0` | Output to stream | May throw | Default | `optional` |
| `PrintLanguage::docTypeDefinitions(const TypeFactory*)` | Emit type definitions (structs, enums, typedefs) | Type declaration text | `virtual void docTypeDefinitions(const TypeFactory* typegrp) = 0` | Output to stream | May throw | Default | `optional` |
| `Architecture::setPrintLanguage(const string&)` | Switch active print language (e.g., `"c-language"`) | N/A (configuration) | `void setPrintLanguage(const string& nm)` | Architecture owns created printer objects | Throws `LowlevelError` for unknown language | Mutates architecture | `required` |
| `Architecture::print` | Direct access to active printer | `PrintLanguage*` | Public field | Pointer owned by Architecture; valid after `init()` | Null if not initialized | Default | `required` |

- `Emit` / `EmitMarkup` / `EmitPrettyPrint` are internal to `PrintLanguage`; the bridge only calls `PrintLanguage` methods.
- `PrintC` (the C-language backend) adds options: `setNULLPrinting(bool)`, `setInplaceOps(bool)`, `setNoCastPrinting(bool)`, `setConvention(bool)`, `setCStyleComments()`, `setCPlusPlusStyleComments()`.
- `PrintLanguage::setMaxLineSize(int4)`, `setIndentIncrement(int4)`, `setNamespaceStrategy(namespace_strategy)` control formatting.
- When `setMarkup(true)` is active, output includes XML markup tokens via `EmitMarkup`. Syntax highlight categories: `keyword_color`, `comment_color`, `type_color`, `funcname_color`, `var_color`, `const_color`, `param_color`, `global_color`, `error_color`, `special_color`.

### 3) Function IR Graph (P-code Ops / Varnodes / Blocks)

| Class::method(s) | Semantic role | Extractable data | Extraction signature | Ownership / lifetime | Errors / diagnostics | Thread-safety | MVP |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Funcdata::getBasicBlocks()` | Raw CFG (unstructured basic blocks) | `const BlockGraph&` | `const BlockGraph& getBasicBlocks() const` | Reference to internal graph; stable while `Funcdata` lives | No throws | Read-only | `optional` |
| `Funcdata::getStructure()` | Structured block hierarchy (if/while/switch/etc.) | `const BlockGraph&` | `const BlockGraph& getStructure() const` | As above | No throws | Read-only | `optional` |
| `Funcdata::beginOpAlive()` / `endOpAlive()` | Iterate all live PcodeOps | `list<PcodeOp*>::const_iterator` range | `list<PcodeOp*>::const_iterator beginOpAlive() const` | Iterators valid while `Funcdata` stable | No throws | Read-only | `optional` |
| `Funcdata::beginOpAll()` / `endOpAll()` | Iterate all PcodeOps sorted by SeqNum | `PcodeOpTree::const_iterator` range | `PcodeOpTree::const_iterator beginOpAll() const` | As above | No throws | Read-only | `optional` |
| `Funcdata::beginOp(OpCode)` / `endOp(OpCode)` | PcodeOps of a specific opcode | `list<PcodeOp*>::const_iterator` range | `list<PcodeOp*>::const_iterator beginOp(OpCode opc) const` | As above | No throws | Read-only | `optional` |
| `Funcdata::beginOp(Address)` / `endOp(Address)` | PcodeOps at a specific instruction address | `PcodeOpTree::const_iterator` range | `PcodeOpTree::const_iterator beginOp(const Address& addr) const` | As above | No throws | Read-only | `optional` |
| `PcodeOp::code()` | Opcode enum for this operation | `OpCode` | `OpCode code() const` (inline, delegates to `opcode->getOpcode()`) | Value copy | No throws | Read-only | `optional` |
| `PcodeOp::getIn(slot)` / `getOut()` / `numInput()` | Input/output Varnodes | `Varnode*`, `int4` | `Varnode* getIn(int4 slot)`, `Varnode* getOut()`, `int4 numInput() const` | Pointers owned by `Funcdata` | `getOut()` null if no assignment | Read-only | `optional` |
| `PcodeOp::getAddr()` / `getSeqNum()` | Original instruction address and sequence | `const Address&`, `const SeqNum&` | `const Address& getAddr() const`, `const SeqNum& getSeqNum() const` | References to internal members | No throws | Read-only | `optional` |
| `PcodeOp::getParent()` | Containing basic block | `BlockBasic*` | `BlockBasic* getParent()` | Pointer into CFG; valid while `Funcdata` lives | No throws | Read-only | `optional` |
| `PcodeOp` flag queries | Semantic flags | `bool` | `isCall()`, `isBranch()`, `isDead()`, `isMarker()`, `isAssignment()`, `isBoolOutput()` | Value copies | No throws | Read-only | `optional` |
| `Funcdata::beginLoc()` / `endLoc()` | Iterate all Varnodes by storage location | `VarnodeLocSet::const_iterator` range | Overloads: `()`, `(AddrSpace*)`, `(Address)`, `(int4 s, Address)` | Iterators valid while `Funcdata` stable | No throws | Read-only | `optional` |
| `Funcdata::beginDef()` / `endDef()` | Iterate Varnodes by definition point | `VarnodeDefSet::const_iterator` range | Overloads: `()`, `(uint4 fl)`, `(uint4 fl, Address)` | As above | No throws | Read-only | `optional` |
| `Varnode::getAddr()` / `getSize()` / `getSpace()` / `getOffset()` | Varnode storage location | `const Address&`, `int4`, `AddrSpace*`, `uintb` | Inline accessors | Stable refs/values | No throws | Read-only | `optional` |
| `Varnode::getDef()` / `beginDescend()` / `endDescend()` | Def-use chain navigation | `PcodeOp*` (def), `list<PcodeOp*>::const_iterator` (uses) | `PcodeOp* getDef()`, iterator accessors | Pointers owned by `Funcdata` | `getDef()` null for inputs/free varnodes | Read-only | `optional` |
| `Varnode::getHigh()` / `getType()` / `getSymbolEntry()` | High-level variable link, type, symbol | `HighVariable*`, `Datatype*`, `SymbolEntry*` | Inline accessors | Pointers owned by `Funcdata` / `TypeFactory` | `getHigh()` may trigger lazy update | Read-only (may trigger mutable internal update) | `optional` |
| `Varnode` flag queries | Classification flags | `bool` | `isConstant()`, `isInput()`, `isFree()`, `isImplied()`, `isExplicit()`, `isReadOnly()`, `isPersist()`, `isAddrTied()` | Value copies | No throws | Read-only | `optional` |

- `BlockGraph::getList()` returns `const vector<FlowBlock*>&`. `getSize()` / `getBlock(i)` for indexed access.
- `FlowBlock` base: `getType()` returns `block_type` enum (`t_plain`, `t_basic`, `t_graph`, `t_copy`, `t_goto`, `t_multigoto`, `t_ls`, `t_condition`, `t_if`, `t_whiledo`, `t_dowhile`, `t_switch`, `t_infloop`). Also: `getStart()`, `getStop()`, `sizeIn()`, `sizeOut()`, `getIn(i)`, `getOut(i)`.
- Structured block types: `BlockIf`, `BlockWhileDo` (with `getInitializeOp()`, `getIterateOp()`), `BlockDoWhile`, `BlockSwitch`, `BlockInfLoop`, `BlockGoto` (with `getGotoTarget()`). Access sub-blocks via `BlockGraph::getBlock(i)`.
- `BlockBasic` has `beginOp()` / `endOp()` for iterating its `PcodeOp` list, plus `getEntryAddr()`, `contains(Address)`.
- `OpCode` enum is defined in `opcodes.hh`: `CPUI_COPY`, `CPUI_LOAD`, `CPUI_STORE`, `CPUI_BRANCH`, `CPUI_CBRANCH`, `CPUI_CALL`, `CPUI_RETURN`, `CPUI_INT_ADD`, `CPUI_MULTIEQUAL`, `CPUI_INDIRECT`, etc.

### 4) Symbols & Variables

| Class::method(s) | Semantic role | Extractable data | Extraction signature | Ownership / lifetime | Errors / diagnostics | Thread-safety | MVP |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Funcdata::getScopeLocal()` | Local scope containing function-local symbols | `ScopeLocal*` | `ScopeLocal* getScopeLocal()` | Owned by `Funcdata` | No throws | Default | `required` |
| `Scope::begin()` / `end()` | Iterate all mapped SymbolEntrys in scope | `MapIterator` range | `virtual MapIterator begin() const = 0` | Iterators valid while scope stable | No throws | Read-only | `required` |
| `Scope::beginDynamic()` / `endDynamic()` | Iterate dynamically-mapped SymbolEntrys | `list<SymbolEntry>::const_iterator` range | `virtual list<SymbolEntry>::const_iterator beginDynamic() const = 0` | As above | No throws | Read-only | `optional` |
| `Scope::findFunction(const Address&)` | Look up function by entry address | `Funcdata*` | `virtual Funcdata* findFunction(const Address& addr) const = 0` | Pointer owned by scope | Null if not found | Read-only | `required` |
| `Scope::findByName(const string&, vector<Symbol*>&)` | Look up symbols by name | `vector<Symbol*>` output param | `virtual void findByName(const string& nm, vector<Symbol*>& res) const = 0` | Pointers owned by scope | Empty result if not found | Read-only | `optional` |
| `Scope::getCategorySize(int4)` / `getCategorySymbol(int4, int4)` | Access symbols by category (params, equates, etc.) | `int4` count, `Symbol*` | `virtual int4 getCategorySize(int4 cat) const = 0` | Pointer owned by scope | Null if index out of range | Read-only | `required` |
| `Symbol::getName()` / `getDisplayName()` | Symbol name | `const string&` | `const string& getName() const` | Reference to internal string | No throws | Read-only | `required` |
| `Symbol::getType()` | Symbol datatype | `Datatype*` | `Datatype* getType() const` | Pointer owned by `TypeFactory` | No throws | Read-only | `required` |
| `Symbol::getId()` / `getFlags()` / `getCategory()` | Symbol metadata | `uint8`, `uint4`, `int2` | Various inline accessors | Value copies | No throws | Read-only | `required` |
| `Symbol::getFirstWholeMap()` / `getMapEntry(i)` / `numEntries()` | Symbol storage mappings | `SymbolEntry*`, `int4` | `SymbolEntry* getFirstWholeMap() const` | Pointer owned by scope | No throws | Read-only | `required` |
| `SymbolEntry::getAddr()` / `getSize()` / `isDynamic()` / `getOffset()` | Storage details for a symbol mapping | `const Address&`, `int4`, `bool`, `int4` | Various inline accessors | Values stable while scope stable | No throws | Read-only | `required` |
| `HighVariable::getType()` / `getSymbol()` / `numInstances()` / `getInstance(i)` | Merged high-level variable | `Datatype*`, `Symbol*`, `int4`, `Varnode*` | Various accessors | Owned by `Funcdata`; lazy update on access | `getType()` may trigger mutable internal recalc | Read-only (may trigger mutable update) | `optional` |

- `Symbol::category` values: `-1` = no_category, `0` = function_parameter, `1` = equate, `2` = union_facet, `3` = fake_input (temporary placeholder for input symbols). Use `getCategorySize(0)` to count function parameters.
- `Funcdata::findHigh(const string& nm)` looks up a `HighVariable` by name directly.
- `Scope` has child scopes: `childrenBegin()` / `childrenEnd()` for sub-scope traversal (relevant for namespace scopes).
- `Database::getGlobalScope()` returns the root scope; hierarchical lookup uses `Scope::queryByName()`, `queryFunction()`, `queryByAddr()`.

### 5) Types (Datatype Model)

| Class::method(s) | Semantic role | Extractable data | Extraction signature | Ownership / lifetime | Errors / diagnostics | Thread-safety | MVP |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Architecture::types` | Pointer to the type factory | `TypeFactory*` | Public field | Owned by Architecture; valid after `init()` | No throws | Default | `required` |
| `TypeFactory::findByName(const string&)` | Look up type by name | `Datatype*` | `Datatype* findByName(const string& n)` | Pointer owned by factory | Returns null if not found | Read-only | `optional` |
| `TypeFactory::getBase(int4, type_metatype)` | Get atomic type by size and metatype | `Datatype*` | `Datatype* getBase(int4 s, type_metatype m)` | Pointer owned by factory | No throws | Read-only | `optional` |
| `TypeFactory::getTypeVoid()` | Get the void type | `TypeVoid*` | `TypeVoid* getTypeVoid()` | Pointer owned by factory | No throws | Read-only | `optional` |
| `TypeFactory::getTypePointer(...)` / `getTypeArray(...)` / `getTypeStruct(...)` | Construct or retrieve composite types | `TypePointer*`, `TypeArray*`, `TypeStruct*` | Various factory methods | Created type owned by factory | No throws | Mutates factory (inserts type) | `optional` |
| `Datatype::getName()` / `getSize()` / `getMetatype()` / `getId()` | Core type properties | `const string&`, `int4`, `type_metatype`, `uint8` | Inline accessors | Stable while factory lives | No throws | Read-only | `required` |
| `Datatype::numDepend()` / `getDepend(i)` | Sub-type components | `int4`, `Datatype*` | `virtual int4 numDepend() const`, `virtual Datatype* getDepend(int4 index) const` | Pointers owned by factory | No throws | Read-only | `optional` |
| `Datatype::getSubType(int8, int8*)` | Navigate into composite types at offset | `Datatype*` (component at offset) | `virtual Datatype* getSubType(int8 off, int8* newoff) const` | Pointer owned by factory | Returns null if no sub-type | Read-only | `optional` |
| `TypeStruct` / `TypeUnion` field iteration | Access struct/union fields | `TypeField` entries (offset, name, type) | `beginField()` / `endField()` on `TypeStruct`/`TypeUnion` | Refs stable while type lives | No throws | Read-only | `optional` |
| `TypeEnum` value iteration | Access enum named values | name-value pairs (`map<uintb,string>`) | `beginEnum()` / `endEnum()` on `TypeEnum` | Stable while type lives | No throws | Read-only | `optional` |
| `TypeCode::getPrototype()` | Function pointer type's prototype | `const FuncProto*` | `const FuncProto* getPrototype() const` | Pointer embedded in type | No throws | Read-only | `optional` |
| `TypePointer::getPtrTo()` / `getWordSize()` / `getSpace()` | Pointer target type and space | `Datatype*`, `uint4`, `AddrSpace*` | Inline accessors | Pointer owned by factory | No throws | Read-only | `optional` |
| `TypeArray::getBase()` / `numElements()` | Array element type and count | `Datatype*`, `int4` | Inline accessors | Pointer owned by factory | No throws | Read-only | `optional` |

- 18 metatypes exist: `TYPE_VOID`, `TYPE_UNKNOWN`, `TYPE_BOOL`, `TYPE_INT`, `TYPE_UINT`, `TYPE_FLOAT`, `TYPE_PTR`, `TYPE_PTRREL`, `TYPE_ARRAY`, `TYPE_STRUCT`, `TYPE_UNION`, `TYPE_CODE`, `TYPE_SPACEBASE`, `TYPE_ENUM_INT`, `TYPE_ENUM_UINT`, `TYPE_PARTIALSTRUCT`, `TYPE_PARTIALUNION`, `TYPE_PARTIALENUM`.
- All `Datatype` objects are owned by `TypeFactory`. Callers must never `delete` them.
- `TypeField` has fields: `offset` (byte offset), `name` (string), `type` (Datatype*), `ident` (identifier).

### 6) Address / Range Mapping

| Class::method(s) | Semantic role | Extractable data | Extraction signature | Ownership / lifetime | Errors / diagnostics | Thread-safety | MVP |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Address` | Compound address: (AddrSpace*, offset) | Space pointer and byte offset | `AddrSpace* getSpace() const`, `uintb getOffset() const` | Value type (copyable) | No throws | Read-only | `required` |
| `AddrSpace` | Address space descriptor | Name, type, size, wordsize, endianness | `const string& getName()`, `spacetype getType()`, `int4 getAddrSize()`, `uint4 getWordSize()`, `bool isBigEndian()` | Pointer owned by `AddrSpaceManager` (via Architecture) | No throws | Read-only | `required` |
| `SeqNum` | Unique PcodeOp identifier | Instruction address + time field | `const Address& getAddr()`, `uintm getTime()`, `uintm getOrder()` | Value type (copyable); embedded in PcodeOp | No throws | Read-only | `optional` |
| `FlowBlock::getStart()` / `getStop()` | Basic block address range | `Address` (start and stop) | `virtual Address getStart() const`, `virtual Address getStop() const` | Value copies | No throws | Read-only | `optional` |
| `Funcdata::numCalls()` / `getCallSpecs(i)` / `getCallSpecs(op)` | Call sites within the function | `int4` count, `FuncCallSpecs*` | `int4 numCalls() const`, `FuncCallSpecs* getCallSpecs(int4 i) const`, `FuncCallSpecs* getCallSpecs(const PcodeOp* op) const` | Pointers owned by `Funcdata` | No throws | Read-only | `optional` |
| `FuncCallSpecs::getOp()` / `getEntryAddress()` | Call site details | `PcodeOp*` (the CALL op), `const Address&` (callee address) | Inline accessors | Pointers owned by `Funcdata` | No throws | Read-only | `optional` |
| `Funcdata::numJumpTables()` / `getJumpTable(i)` / `findJumpTable(op)` | Jump table recovery data | `int4` count, `JumpTable*` | `int4 numJumpTables() const`, `JumpTable* getJumpTable(int4 i)` | Pointers owned by `Funcdata` | `findJumpTable` returns null if no table for op | Read-only | `optional` |
| `Range` / `RangeList` | Contiguous address range / disjoint set | First/last address; containment test | `Range::getFirstAddr()`, `Range::getLastAddr()`, `RangeList::inRange(Address, int4)` | `Range` value type; `RangeList` owned by containing scope/architecture | No throws | Read-only | `optional` |

- `AddrSpace` types: `IPTR_CONSTANT` (constants), `IPTR_PROCESSOR` (RAM/registers), `IPTR_SPACEBASE` (stack-relative), `IPTR_INTERNAL` (unique/temporaries), `IPTR_JOIN` (joined variables), `IPTR_FSPEC`, `IPTR_IOP`.
- `AddrSpaceManager::getDefaultCodeSpace()` (inherited by Architecture) returns the default code space for building function `Address` objects.
- `FuncCallSpecs` extends `FuncProto`, adding `getOp()` and `getEntryAddress()` — useful for building call-graph data.

### 7) Diagnostics (Warnings / Errors / Status)

| Class::method(s) | Semantic role | Extractable data | Extraction signature | Ownership / lifetime | Errors / diagnostics | Thread-safety | MVP |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Funcdata::isProcComplete()` | Decompilation completed fully | `bool` | `bool isProcComplete() const` | Value copy | N/A | Read-only | `required` |
| `Funcdata::hasUnreachableBlocks()` | Unreachable code detected | `bool` | `bool hasUnreachableBlocks() const` | Value copy | N/A | Read-only | `required` |
| `Funcdata::hasUnimplemented()` | Unimplemented instructions present | `bool` | `bool hasUnimplemented() const` | Value copy | N/A | Read-only | `required` |
| `Funcdata::hasBadData()` | Flow into bad data detected | `bool` | `bool hasBadData() const` | Value copy | N/A | Read-only | `required` |
| `Funcdata::isTypeRecoveryOn()` / `hasTypeRecoveryStarted()` | Type analysis status | `bool` | `bool isTypeRecoveryOn() const` | Value copy | N/A | Read-only | `ignore` |
| `Funcdata::hasNoCode()` | No code available for the function body | `bool` | `bool hasNoCode() const` (flag `0x80`) | Value copy | N/A | Read-only | `required` |
| `Funcdata::hasRestartPending()` | Analysis needs restart (e.g., prototype change during decompile) | `bool` | `bool hasRestartPending() const` (flag `0x400`) | Value copy | N/A | Read-only | `optional` |
| `Funcdata::isDoublePrecisOn()` | Double precision recovery enabled | `bool` | `bool isDoublePrecisOn() const` (flag `0x2000`) | Value copy | N/A | Read-only | `ignore` |
| `Funcdata::warning(const string&, const Address&)` | Add body-inline warning comment | Written to `CommentDatabase` as `Comment::warning` | `void warning(const string& txt, const Address& ad) const` | Comment owned by CommentDatabase | No throws on normal path | Mutates commentdb | `optional` |
| `Funcdata::warningHeader(const string&)` | Add header warning comment | Written to `CommentDatabase` as `Comment::warningheader` | `void warningHeader(const string& txt) const` | Comment owned by CommentDatabase | No throws on normal path | Mutates commentdb | `optional` |
| `CommentDatabase::beginComment(faddr)` / `endComment(faddr)` | Iterate all comments (including warnings) for a function | `CommentSet::const_iterator` range, each yielding `Comment*` | `virtual CommentSet::const_iterator beginComment(const Address& fad) const = 0` | Comments owned by database (via `Architecture::commentdb`) | No throws | Read-only | `required` |
| `Comment::getType()` / `getText()` / `getAddr()` / `getFuncAddr()` | Individual comment/warning data | `uint4` type flags, `const string&` text, `const Address&` instruction addr, `const Address&` function addr | Inline accessors (comment.hh:65-69) | Stable while database lives | No throws | Read-only | `required` |
| `LowlevelError` / `RecovError` / `ParseError` | Exception hierarchy thrown by decompile path (`error.hh`) | `string explain` (error message) | Caught by value or reference at call boundary | Stack-based; catch at boundary | `RecovError` and `ParseError` derive from `LowlevelError` | N/A | `required` |
| `DecoderError` | Independent XML/decode exception (`xml.hh:297`) — NOT in `LowlevelError` hierarchy | `string explain` (error message) | Caught separately at call boundary | Stack-based; catch at boundary | Thrown during XML spec parsing / decoder operations | N/A | `required` |
| `Action::perform()` return value | Decompilation completion status | `int4`: >= 0 means complete, < 0 means partial/break | `int4 perform(Funcdata& data)` | Value copy | Partial means breakpoint hit | N/A | `required` |

- `Comment::comment_type` flags: `user1`=1, `user2`=2, `user3`=4, `header`=8, `warning`=16, `warningheader`=32. Filter warnings with `type & (Comment::warning | Comment::warningheader)`.
- `FuncProto::hasInputErrors()` and `hasOutputErrors()` indicate parameter/return-value recovery failures — should be checked after decompile.
- **Budget/limit mechanism**: `Architecture::max_instructions` (`uint4`, architecture.hh:185, default `100000`) caps the instruction count the flow-following engine will process per function. Exceeding it sets the `FlowInfo::error_toomanyinstructions` flag and halts further flow analysis for that function. Additional limits: `max_jumptable_size` (max jump-table entries), `max_basetype_size`, `max_term_duplication`, `max_implied_ref`. There is no wall-clock timeout; external cancellation (signal/thread) is required for time-based limits.
- `Architecture::commentdb` provides access to the `CommentDatabase*` for iterating warnings.

## Extension-Only APIs (Not Direct Driver Calls)

| Symbol name | File path | Status | Why extension-only |
| --- | --- | --- | --- |
| `SleighArchitecture::collectSpecFiles(ostream&)` | `sleigh_arch.hh` / `sleigh_arch.cc` | `extension` | `protected static`; intended for subclasses during loader setup. |
| `SleighArchitecture::resolveArchitecture(void)` | `sleigh_arch.hh` / `sleigh_arch.cc` | `extension` | Called internally from `Architecture::init()`. |
| `SleighArchitecture::buildSpecFile(DocumentStorage&)` | `sleigh_arch.hh` / `sleigh_arch.cc` | `extension` | Called internally from `Architecture::init()` after architecture resolution. |
| `ActionDatabase::universalAction(Architecture*)` | `action.hh` / `coreaction.cc` | `extension` | Used by `Architecture::buildAction()` or custom overrides, not by caller-side decompile loop. |
| `TypeFactory::setCoreType(...)` + `cacheCoreTypes()` | `type.hh` / `type.cc` | `extension` | Used by `buildCoreTypes()` during initialization, not by caller-side decompile loop. |
| `Architecture::clearAnalysis(Funcdata*)` | `architecture.hh` / `architecture.cc` | `internal` | Called by restart/actions and console helpers internally; not required as an external driver call. |

## Excluded From Minimal Contract (for this invocation path)

| Symbol name | Status | Why excluded |
| --- | --- | --- |
| `ArchitectureCapability::findCapability(...)` | `extra` | Not required when the caller directly instantiates its selected `Architecture` subtype. |
| `SleighArchitecture::getLanguageDescriptions()` | `mismatch` | Not present in upstream pinned API; use `getDescriptions(void)`. |
| `SleighArchitecture::shutdown(void)` + direct `specpaths` reassignment | `extra` | Not required for the strict decompile invocation path; in pinned upstream, `shutdown()` is a no-op and does not clear cached `description` entries. |
| `IfaceDecompData::followFlow` | `extra` | Console command helper; flow is driven through `Action::perform` in this contract. |
| `RawLoadImage` | `extra` | Optional concrete `LoadImage`; the contract requires the abstract `LoadImage` interface only. |
| `ParserContext` | `extra` | Internal decode state object; not part of the minimal externally-called bridge surface for decompilation. |
| `Emit` / `EmitMarkup` / `EmitPrettyPrint` | `extra` | Indirect implementation detail under `PrintLanguage`; bridge only requires `PrintLanguage` methods above. |
