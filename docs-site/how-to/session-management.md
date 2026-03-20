# Session Management

A `DecompilerSession` owns one native Ghidra `Architecture` instance. Constructing
that instance involves loading processor specification files, setting up the sleigh
engine, and allocating native memory. These costs are real, so reusing a session
across many decompilation calls is significantly more efficient than creating a new
one per call.

This guide covers the two main usage patterns.

## Why sessions matter

Each `DecompilerSession` maps directly to one native `Architecture` object. Creating
and destroying that object on every call adds measurable overhead, especially in
batch workflows processing hundreds or thousands of functions. A long-lived session
pays the construction cost once and amortizes it across every subsequent call.

Sessions also provide deterministic resource cleanup. The native `Architecture`
instance holds file handles and allocated memory. Closing a session explicitly, or
via a context manager, releases those resources immediately rather than waiting for
the garbage collector.

## Recommended pattern: context manager

For most use cases, the `with` statement is the right tool. It guarantees the session
is closed even if an exception is raised inside the block.

```python
from flatline import DecompilerSession, DecompileRequest

request = DecompileRequest(
    memory_image=b"\x55\x48\x89\xe5\xb8\x01\x00\x00\x00\x5d\xc3",
    base_address=0x1000,
    function_address=0x1000,
    language_id="x86:LE:64:default",
    compiler_spec="gcc",
)

with DecompilerSession() as session:
    result = session.decompile_function(request)

print(result.c_code)
# The session is closed here, native resources released.
```

## Batch work: one session, many calls

When decompiling multiple functions, open the session once and call
`decompile_function` repeatedly. All calls share the same native `Architecture`
instance.

```python
from flatline import DecompilerSession, DecompileRequest

# Suppose you have a list of (base_address, function_address, code_bytes) tuples.
targets = [
    (0x1000, 0x1000, b"\x55\x48\x89\xe5\xb8\x2a\x00\x00\x00\x5d\xc3"),
    (0x2000, 0x2000, b"\x55\x48\x89\xe5\x31\xc0\x5d\xc3"),
    (0x3000, 0x3000, b"\x55\x48\x89\xe5\xb8\x00\x00\x00\x00\x5d\xc3"),
]

with DecompilerSession() as session:
    for base, entry, code in targets:
        request = DecompileRequest(
            memory_image=code,
            base_address=base,
            function_address=entry,
            language_id="x86:LE:64:default",
            compiler_spec="gcc",
        )
        result = session.decompile_function(request)
        if result.error is None:
            print(f"0x{entry:x}: {result.c_code}")
        else:
            print(f"0x{entry:x}: error — {result.error.message}")
```

## Manual lifecycle: open, use, close

If a context manager is not practical (for example, in a class that holds a session
as an attribute), manage the lifecycle explicitly with `try`/`finally` to ensure
`close()` is always called.

```python
from flatline import DecompilerSession

session = DecompilerSession()
try:
    pairs = session.list_language_compilers()
    result = session.decompile_function(request)
finally:
    session.close()
```

## Checking session state

The `is_closed` property reports whether `close()` has been called. This is useful
for defensive checks in long-lived objects.

```python
session = DecompilerSession()
print(session.is_closed)  # False

session.close()
print(session.is_closed)  # True
```

Calling `close()` on an already-closed session is safe — it is a no-op.
Calling `decompile_function()` or `list_language_compilers()` on a closed session
raises `InvalidArgumentError`.

!!! note "One session per architecture"
    A single session is bound to the runtime data directory it was opened with.
    There is no per-call architecture switching. If you need to decompile functions
    from different architectures in the same process, use separate sessions (or the
    one-shot `flatline.decompile_function()` wrapper, which creates a fresh session
    per call).
