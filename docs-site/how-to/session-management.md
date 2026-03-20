# Session Management

A `DecompilerSession` owns one native bridge session. Creating a session
initializes the decompiler library, resolves the runtime data directory, and
enumerates available language/compiler pairs. Reusing a session across many
decompilation calls avoids repeating that startup work on every call.

This guide covers the two main usage patterns.

## Why sessions matter

Each `DecompilerSession` performs one-time decompiler library initialization,
runtime data directory resolution, and language/compiler pair enumeration. Without
a session, each one-shot call repeats that work. A long-lived session pays the
cost once and reuses it across every subsequent call.

Sessions also provide deterministic resource cleanup. Closing a session
explicitly, or via a context manager, releases bridge resources immediately
rather than waiting for the garbage collector.

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
`decompile_function` repeatedly. All calls share the same bridge session and
skip redundant startup work.

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

!!! note "Session and runtime data"
    A single session is bound to the runtime data directory it was opened with.
    You can decompile functions targeting different ISAs within the same session
    as long as they use the same runtime data. If you need a different runtime
    data directory, create a separate session.
