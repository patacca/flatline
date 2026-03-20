# Architecture

flatline is organized as a three-layer adapter. Each layer has a clear
responsibility, and the boundaries between them are intentional: the public
API is stable, the bridge is internal, and the native layer is the upstream
Ghidra decompiler engine with no modifications.

## The Three Layers

```
┌─────────────────────────────────────────────────────────┐
│  Public API                                             │
│  DecompilerSession  ·  decompile_function()             │
│  DecompileRequest   ·  DecompileResult                  │
│  models  ·  errors  ·  constants                        │
│  (_session.py  ·  _models.py  ·  _errors.py)            │
├─────────────────────────────────────────────────────────┤
│  Bridge                                                 │
│  _flatline_native (nanobind C++ extension)              │
│  _bridge.py (Python fallback + coercion layer)          │
├─────────────────────────────────────────────────────────┤
│  Native                                                 │
│  82 upstream Ghidra C++ sources                         │
│  static library: ghidra_decompiler                      │
│  SleighArchitecture  ·  LoadImage  ·  Action pipeline   │
└─────────────────────────────────────────────────────────┘
```

### Public layer

This is the only stable surface. `DecompilerSession`, `DecompileRequest`,
`DecompileResult`, and all the data models are pure Python frozen dataclasses.
They carry no native pointers — everything is copied into ordinary Python
values at the bridge boundary, so the caller never has to think about native
memory lifetimes.

The public layer validates inputs eagerly. If `memory_image` is empty or
`language_id` is the wrong type, `InvalidArgumentError` is raised during
`DecompileRequest` construction, before anything touches the decompiler. This
keeps errors close to their cause.

`DecompilerSession` manages the lifecycle of one native bridge session.
Creating a session is not free — it initializes the decompiler library,
resolves the runtime data directory, and enumerates available
language/compiler pairs. Reusing a session avoids repeating that startup
work on every call. The one-shot `decompile_function()` and
`list_language_compilers()` module-level functions create and close a session
automatically for single-call use.

### Bridge layer

The bridge sits between the Python public API and the native code. It has two
implementations:

- **`_flatline_native`** — a compiled nanobind C++ extension that drives the
  native decompiler directly. This is what runs in distributed wheels.
- **`_FallbackBridgeSession`** — a pure-Python skeleton that returns
  structured `configuration_error` results for decompile calls. It exists so
  the Python package is importable and `list_language_compilers()` works even
  in environments where the native extension could not be compiled.

At session startup, `create_bridge_session()` tries to import
`flatline._flatline_native`. If the import succeeds, a `_NativeBridgeSession`
wraps it. If not, a `_FallbackBridgeSession` is used instead. This selection
is transparent to callers.

The bridge is intentionally unstable. Its internal shapes — how native results
are coerced, what the native session protocol looks like, how the fallback
behaves — can change between versions without notice. Only the public layer
contracts are stable.

### Native layer

The native layer is 82 upstream Ghidra C++ source files compiled into a static
library (`ghidra_decompiler`). flatline does not modify this code; the goal is
to stay as close to upstream as possible so future Ghidra updates are easier
to absorb.

The decompilation path through the native layer looks like this:

1. **`SleighArchitecture` initialization** — loads the processor `.sla` file
   for the requested `language_id`, sets up the address model and compiler
   spec, and configures the action pipeline.
2. **`LoadImage` setup** — installs the caller's `memory_image` bytes as the
   backing store for the decompiler's virtual address space.
3. **Action pipeline execution** — runs the full Ghidra decompile action
   sequence: lifting to p-code, simplification, type recovery, and variable
   recovery.
4. **`docFunction` output** — extracts the rendered C code and structured
   function data from the decompiler's internal representation and marshals
   it across the ABI boundary as plain C++ value types. No native pointers
   leave the native layer.

The `zlib` library is a build-time dependency of the native layer (Ghidra uses
it for `.sla` file decompression). It is either statically linked or
discovered from the system at build time; callers do not need to install or
configure it.

## Why This Design

The core motivation is **stability over instability**. Ghidra's C++ internals
change between releases. By isolating the public API in pure Python and
keeping the bridge as a narrow coercion boundary, the upstream can update
without breaking callers' code. A version bump to Ghidra means updating
`third_party/ghidra`, adjusting the native binding, and testing — not
rewriting the public API.

Frozen dataclasses for all result types reinforce this: once a `DecompileResult`
is returned, it cannot be mutated. There are no cached native references that
could become dangling. The caller owns their data completely.

The Python fallback in the bridge serves a different kind of stability:
`import flatline` always works, `list_language_compilers()` always works, and
the error you get when the native extension is missing is a structured
`ConfigurationError` rather than a cryptic import failure.

## Runtime Data and `ghidra-sleigh`

Ghidra's decompiler needs processor definition files (`.sla` files and compiler
spec files) to know how to decode and lift instructions for a given ISA. These
files are not bundled inside flatline itself — they are provided by the
companion `ghidra-sleigh` package.

When you create a `DecompilerSession` without specifying `runtime_data_dir`,
flatline calls `ghidra_sleigh.get_runtime_data_dir()` to locate the data
automatically. This means:

- Installing `flatline` also installs `ghidra-sleigh` as a dependency.
- The processor definitions are kept separate from the decompiler binary,
  making the flatline wheel smaller and allowing the data to be updated
  independently.
- You can point flatline at a custom runtime data directory by passing
  `runtime_data_dir` to `DecompilerSession` or `DecompileRequest` if you need
  a different set of processor definitions.

The `.ldefs` files inside the runtime data directory declare which
`language_id` / `compiler_spec` combinations are available. flatline parses
these at session startup to populate `list_language_compilers()` and to
validate `language_id` and `compiler_spec` before passing them to the native
layer.
