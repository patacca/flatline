# Ghidra Decompiler Action Pipeline

How the decompiler's analysis actions are built, selected, and executed.

## Entry point (flatline side)

`src/flatline/native/session.cpp:256-269` calls three methods:

```cpp
Action* action = architecture.allacts.getCurrent();  // get root Action
action->reset(*function);                             // reset state for new function
int status = action->perform(*function);              // run the entire pipeline
architecture.print->docFunction(function);            // emit C output
```

## Action class hierarchy

Defined in `third_party/ghidra/.../action.hh`.

- **Action** (base): has `apply(Funcdata&)` pure virtual, tracks change count, supports breakpoints and repeat-until-fixpoint behavior via flags.
- **ActionGroup**: runs children sequentially; with `rule_repeatapply`, re-runs the sequence until no child makes changes (fixpoint).
- **ActionRestartGroup**: like ActionGroup but can restart from the beginning if a child requests it.
- **ActionPool**: holds Rules (peephole transforms). Applies all rules to every pcode op; repeats until no rule fires.
- **Rule**: a single peephole transform on the varnode/op graph (e.g. `x * 1 -> x`, constant folding, copy propagation).

## How perform() drives actions

`Action::perform()` (`action.cc:298`) is a loop:

1. Calls `apply(data)` on the action.
2. If the action made changes (`count` increased) **and** `rule_repeatapply` is set, loops back and calls `apply()` again.
3. Stops when no more changes are made (fixpoint) or `rule_onceperfunc` is set.

## Initialization: allacts

`allacts` is an `ActionDatabase` member of `Architecture` (`architecture.hh:212`).

Initialized in `Architecture::restoreFromSpec()` (`architecture.cc:624`):

```
Architecture::restoreFromSpec()
  +-- buildTranslator()           -- create SLEIGH translator
  +-- translate->initialize()     -- load .sla/.pspec
  +-- copySpaces()                -- set up address spaces
  +-- parseProcessorConfig()      -- processor-specific config
  +-- parseCompilerConfig()       -- compiler-specific config (.cspec)
  +-- buildAction(store)          -- architecture.cc:585
        +-- parseExtraRules()     -- load any extra rules from config
        +-- allacts.universalAction(this)  -- build the full action tree
        +-- allacts.resetDefaults()        -- set "decompile" as the current root
```

Populated once during architecture construction, before any function is decompiled. The action tree is reused across all decompile calls; `reset()` clears per-function state before each run.

## The "universal" action and root derivation

`universalAction()` (`coreaction.cc:5462`) builds a master tree registered under the name `"universal"`. Every leaf action/rule is tagged with a **group** string (e.g. `"base"`, `"deadcode"`, `"typerecovery"`, `"merge"`).

`buildDefaultGroups()` (`coreaction.cc:5419`) defines named **grouplists** -- sets of group names. Each grouplist defines a named root action.

`resetDefaults()` (`action.cc:986`) clears derived actions, rebuilds the default groups, and calls `setCurrent("decompile")`.

`setCurrent(name)` (`action.cc:1021`) calls `deriveAction("universal", name)`, which **clones** the universal tree keeping only actions/rules whose group appears in the named grouplist.

### How clone filtering works

The filtering happens at the **leaf** level, not at container level:

- **Leaf actions** check `grouplist.contains(getGroup())` in their `clone()`. If their group is in the list, they return a copy; otherwise `NULL`.
- **Containers** (`ActionGroup`, `ActionPool`, `ActionRestartGroup`) recursively `clone()` each child. If any child survives, the container reconstructs itself with the surviving children. If no child survives, the container returns `NULL`.

Container names like `"fullloop"` and `"mainloop"` are **not** group tags and don't appear in grouplists. They are preserved as long as at least one of their leaf descendants has a matching group.

### Default grouplists

```
"decompile" (the default -- full pipeline):
    base, protorecovery, protorecovery_a, deindirect, localrecovery,
    deadcode, typerecovery, stackptrflow, blockrecovery, stackvars,
    deadcontrolflow, switchnorm, cleanup, splitcopy, splitpointer,
    merge, dynamic, casts, analysis, fixateglobals, fixateproto,
    constsequence, segment, returnsplit, nodejoin, doubleload,
    doubleprecis, unreachable, subvar, floatprecision, conditionalexe

"jumptable" (lightweight, used during switch recovery):
    base, noproto, localrecovery, deadcode, stackptrflow,
    stackvars, analysis, segment, subvar, normalizebranches, conditionalexe

"normalize":
    base, protorecovery, protorecovery_b, deindirect, localrecovery,
    deadcode, stackptrflow, normalanalysis, stackvars, deadcontrolflow,
    analysis, fixateproto, nodejoin, unreachable, subvar, floatprecision,
    normalizebranches, conditionalexe

"paramid":
    base, protorecovery, protorecovery_b, deindirect, localrecovery,
    deadcode, typerecovery, stackptrflow, siganalysis, stackvars,
    deadcontrolflow, analysis, fixateproto, unreachable, subvar,
    floatprecision, conditionalexe

"register":   base, analysis, subvar
"firstpass":  base
```

Groups unique to specific roots (not in "decompile"):
- `noproto` -- jumptable only
- `normalanalysis` -- normalize only
- `normalizebranches` -- jumptable, normalize
- `siganalysis` -- paramid only
- `protorecovery_b` -- normalize, paramid (decompile uses `protorecovery_a`)

The `"jumptable"` root is used internally during switch table recovery (`funcdata_block.cc:501`) where a partial function gets a lightweight analysis pass.

## The "universal" action tree (full structure)

```
ActionRestartGroup "universal"  (rule_onceperfunc)
|
+-- ActionStart [base]                     -- lift bytes to raw pcode
+-- ActionConstbase [base]                 -- set up constant space
+-- ActionNormalizeSetup [normalanalysis]   -- normalize analysis prep
+-- ActionDefaultParams [base]             -- default parameter setup
+-- ActionExtraPopSetup [base]             -- stack adjustment
+-- ActionPrototypeTypes [protorecovery]   -- prototype recovery
+-- ActionFuncLink [protorecovery]         -- resolve call targets
+-- ActionFuncLinkOutOnly [noproto]        -- outgoing-only links
|
+-- ActionGroup "fullloop"  (rule_repeatapply)      -- OUTER FIXPOINT
|   |
|   +-- ActionGroup "mainloop"  (rule_repeatapply)  -- INNER FIXPOINT
|   |   +-- ActionUnreachable [base]
|   |   +-- ActionVarnodeProps [base]
|   |   +-- ActionHeritage [base]               -- SSA construction
|   |   +-- ActionParamDouble [protorecovery]
|   |   +-- ActionSegmentize [base]
|   |   +-- ActionInternalStorage [base]
|   |   +-- ActionForceGoto [blockrecovery]
|   |   +-- ActionDirectWrite [protorecovery_a] (true)
|   |   +-- ActionDirectWrite [protorecovery_b] (false)
|   |   +-- ActionActiveParam [protorecovery]
|   |   +-- ActionReturnRecovery [protorecovery]
|   |   +-- // ActionParamShiftStop [paramshift]   -- commented out upstream
|   |   +-- ActionRestrictLocal [localrecovery]    -- do before dead code removed
|   |   +-- ActionDeadCode [deadcode]
|   |   +-- ActionDynamicMapping [dynamic]         -- must come before restructurevarnode and infertypes
|   |   +-- ActionRestructureVarnode [localrecovery]
|   |   +-- ActionSpacebase [base]                 -- must come before infertypes and nonzeromask
|   |   +-- ActionNonzeroMask [analysis]
|   |   +-- ActionInferTypes [typerecovery]
|   |   |
|   |   +-- ActionGroup "stackstall"  (rule_repeatapply)
|   |   |   +-- ActionPool "oppool1"  (rule_repeatapply)
|   |   |   |   ~130 Rules [analysis, deadcode, subvar, etc.]:
|   |   |   |     arithmetic simplification, boolean logic, shift/mask,
|   |   |   |     comparisons, copy propagation, subvar analysis,
|   |   |   |     conditional execution, float, type recovery, ...
|   |   |   |   Also includes CPU-specific rules via conf->extra_pool_rules
|   |   |   +-- ActionLaneDivide [base]
|   |   |   +-- ActionMultiCse [analysis]        -- CSE
|   |   |   +-- ActionShadowVar [analysis]
|   |   |   +-- ActionDeindirect [deindirect]    -- resolve indirect calls
|   |   |   +-- ActionStackPtrFlow [stackptrflow]
|   |   |
|   |   +-- ActionRedundBranch [deadcontrolflow]   -- dead code removal
|   |   +-- ActionBlockStructure [blockrecovery]
|   |   +-- ActionConstantPtr [typerecovery]
|   |   +-- ActionPool "oppool2"  (rule_repeatapply) -- type-driven rules
|   |   |   +-- RulePushPtr [typerecovery]
|   |   |   +-- RuleStructOffset0 [typerecovery]
|   |   |   +-- RulePtrArith [typerecovery]
|   |   |   +-- // RuleIndirectConcat [analysis]   -- commented out upstream
|   |   |   +-- RuleLoadVarnode [stackvars]
|   |   |   +-- RuleStoreVarnode [stackvars]
|   |   +-- ActionDeterminedBranch [unreachable]
|   |   +-- ActionUnreachable [unreachable]
|   |   +-- ActionNodeJoin [nodejoin]
|   |   +-- ActionConditionalExe [conditionalexe]
|   |   +-- ActionConditionalConst [analysis]
|   |
|   +-- ActionLikelyTrash [protorecovery]
|   +-- ActionDirectWrite [protorecovery_a] (true)
|   +-- ActionDirectWrite [protorecovery_b] (false)
|   +-- ActionDeadCode [deadcode]
|   +-- ActionDoNothing [deadcontrolflow]
|   +-- ActionSwitchNorm [switchnorm]
|   +-- ActionReturnSplit [returnsplit]
|   +-- ActionUnjustifiedParams [protorecovery]
|   +-- ActionStartTypes [typerecovery]
|   +-- ActionActiveReturn [protorecovery]
|
+-- ActionMappedLocalSync [localrecovery]
+-- ActionStartCleanUp [cleanup]
+-- ActionPool "cleanup"  (rule_repeatapply)
|   ~15 cleanup rules [cleanup, splitcopy, splitpointer, constsequence]:
|     MultNegOne, AddUnsigned, 2Comp2Sub, DumptyHumpLate, SubRight,
|     FloatSignCleanup, ExpandLoad, PtrsubCharConstant, ExtensionPush,
|     PieceStructure, SplitCopy, SplitLoad, SplitStore, StringCopy,
|     StringStore
|
+-- ActionPreferComplement [blockrecovery]
+-- ActionStructureTransform [blockrecovery]
+-- ActionNormalizeBranches [normalizebranches]
+-- ActionAssignHigh [merge]              -- MERGE PHASE begins
+-- ActionMergeRequired [merge]
+-- ActionMarkExplicit [merge]
+-- ActionMarkImplied [merge]             -- must come BEFORE general merging
+-- ActionMergeMultiEntry [merge]
+-- ActionMergeCopy [merge]
+-- ActionDominantCopy [merge]
+-- ActionDynamicSymbols [dynamic]
+-- ActionMarkIndirectOnly [merge]        -- must come after required merges but before speculative
+-- ActionMergeAdjacent [merge]
+-- ActionMergeType [merge]
+-- ActionHideShadow [merge]
+-- ActionCopyMarker [merge]
+-- ActionOutputPrototype [localrecovery]
+-- ActionInputPrototype [fixateproto]
+-- ActionMapGlobals [fixateglobals]
+-- ActionDynamicSymbols [dynamic]
+-- ActionNameVars [merge]
+-- ActionSetCasts [casts]
+-- ActionFinalStructure [blockrecovery]
+-- ActionPrototypeWarnings [protorecovery]
+-- ActionStop [base]
```

[group] = the basegroup string used for clone filtering.

## Pipeline phases in plain English

1. **Lift** -- decode bytes into raw pcode.
2. **Setup** -- constant space, parameters, call linking.
3. **Analysis loop** (fixpoint) -- SSA heritage, dead code, type inference, ~130 peephole rules applied until nothing changes, block structure recovery.
4. **Outer loop** -- switch normalization, prototype refinement, restart inner loop if needed.
5. **Cleanup** -- cosmetic simplifications.
6. **Merge** -- collapse redundant varnodes into high-level variables.
7. **Finalize** -- name variables, insert casts, emit final C structure.

## Source files

- `action.hh` / `action.cc` -- Action/ActionGroup/ActionPool/ActionDatabase classes, perform() loop, clone filtering
- `coreaction.hh` / `coreaction.cc` -- all concrete Action subclasses, Rule subclasses, universalAction(), buildDefaultGroups()
- `architecture.hh` / `architecture.cc` -- Architecture::allacts member, restoreFromSpec() init chain
- `funcdata_block.cc` -- internal use of "jumptable" root for switch recovery
