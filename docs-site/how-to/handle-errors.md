# Handle Errors

flatline reports problems through two distinct mechanisms depending on when and where
the error occurs. Understanding the difference helps you write robust error handling.

## Two error channels

**Exceptions** (`FlatlineError` subclasses) are raised for hard errors detected
before or during decompilation setup — invalid arguments, unrecognized targets,
addresses outside the memory image, and decompiler engine failures.

**`DecompileResult.error`** is a structured `ErrorItem` value (not an exception)
returned inside the result object for non-fatal or partial failures that still
produce a result object. If `result.error` is not `None`, inspect its `category`
and `message` fields.

In the normal success case, no exception is raised and `result.error` is `None`.

## The error hierarchy

All flatline exceptions inherit from `FlatlineError`. There are six concrete
subclasses, each with a stable `category` string:

```
FlatlineError
    InvalidArgumentError       category = "invalid_argument"
    UnsupportedTargetError     category = "unsupported_target"
    InvalidAddressError        category = "invalid_address"
    DecompileFailedError       category = "decompile_failed"
    ConfigurationError         category = "configuration_error"
    InternalError              category = "internal_error"
```

## Catching specific errors

Import the exceptions you need and catch them individually for precise handling.

```python
from flatline import (
    DecompilerSession,
    DecompileRequest,
    InvalidArgumentError,
    UnsupportedTargetError,
    InvalidAddressError,
    DecompileFailedError,
    ConfigurationError,
    InternalError,
    FlatlineError,
)

request = DecompileRequest(
    memory_image=b"\x55\x48\x89\xe5\xb8\x01\x00\x00\x00\x5d\xc3",
    base_address=0x1000,
    function_address=0x1000,
    language_id="x86:LE:64:default",
    compiler_spec="gcc",
)

try:
    with DecompilerSession() as session:
        result = session.decompile_function(request)
except InvalidArgumentError as e:
    # Bad request construction: empty memory_image, wrong type, etc.
    print(f"Bad argument: {e.message}")
except UnsupportedTargetError as e:
    # language_id or compiler_spec not recognized.
    # Call list_language_compilers() to find valid values.
    print(f"Unknown target: {e.message}")
except InvalidAddressError as e:
    # function_address is outside the supplied memory_image.
    print(f"Address out of range: {e.message}")
except DecompileFailedError as e:
    # The decompiler engine failed internally.
    print(f"Decompilation failed: {e.message}")
except ConfigurationError as e:
    # Installation or runtime data problem — see below.
    print(f"Configuration problem: {e.message}")
except InternalError as e:
    # flatline bug — see below.
    raise
```

## Catching all flatline errors

When you want a single fallback handler for any flatline problem, catch the base
class. The `category` attribute identifies which kind of error occurred.

```python
from flatline import FlatlineError

try:
    result = flatline.decompile_function(request)
except FlatlineError as e:
    print(f"[{e.category}] {e.message}")
```

## Per-category handling patterns

### `invalid_argument`

Raised when the `DecompileRequest` or session arguments are malformed: empty
`memory_image`, non-string `language_id`, invalid `analysis_budget` fields, or
calling methods on a closed session.

```python
from flatline import DecompileRequest, InvalidArgumentError

try:
    # Empty memory_image — caught at construction time.
    request = DecompileRequest(
        memory_image=b"",
        base_address=0x1000,
        function_address=0x1000,
        language_id="x86:LE:64:default",
    )
except InvalidArgumentError as e:
    print(e.message)  # "memory_image must not be empty"
```

### `unsupported_target`

Raised when `language_id` or `compiler_spec` is not found in the runtime data.
Enumerate available targets first.

```python
import flatline
from flatline import UnsupportedTargetError

pairs = flatline.list_language_compilers()
valid_ids = {p.language_id for p in pairs}

if "x86:LE:64:default" not in valid_ids:
    print("Target not available in this runtime data directory.")
```

### `invalid_address`

Raised when `function_address` does not fall within the range
`[base_address, base_address + len(memory_image))`.

```python
from flatline import DecompilerSession, DecompileRequest, InvalidAddressError

request = DecompileRequest(
    memory_image=b"\x55\x48\x89\xe5\xc3",
    base_address=0x1000,
    function_address=0x9000,  # Outside the image.
    language_id="x86:LE:64:default",
)

try:
    with DecompilerSession() as session:
        result = session.decompile_function(request)
except InvalidAddressError as e:
    print(f"Address 0x9000 is not mapped: {e.message}")
```

### `decompile_failed`

Raised when the Ghidra decompiler engine itself encounters an unrecoverable
internal failure. This is distinct from partial or degraded output (which is
reported via `result.error` or `result.warnings` instead).

### `configuration_error` and `internal_error`

!!! important "configuration_error vs internal_error"
    These two categories have different remediation paths:

    - **`configuration_error`** means the problem is user-fixable. Common causes
      include a missing or corrupt runtime data directory, an incompatible
      `ghidra-sleigh` installation, or a misconfigured `runtime_data_dir` path.
      Check your installation and the path you passed to `DecompilerSession`.

    - **`internal_error`** means flatline itself has a bug. You should not need
      to handle this in normal operation. If you encounter one, please
      [report it as a bug](https://github.com/patacca/flatline/issues).

```python
from flatline import ConfigurationError, InternalError

try:
    with DecompilerSession(runtime_data_dir="/bad/path") as session:
        result = session.decompile_function(request)
except ConfigurationError as e:
    # Guide the user to fix their setup.
    print(f"Setup problem (user-fixable): {e.message}")
    print("Check that ghidra-sleigh is installed and runtime_data_dir is correct.")
except InternalError as e:
    # Re-raise so it surfaces as an unhandled exception.
    # Do not silently swallow internal errors.
    raise
```

## `DecompileResult.error` — inline error reporting

Some failures produce a result object rather than raising an exception. In these
cases `result.error` is an `ErrorItem` with three fields:

- `category` — one of the six error category strings
- `message` — human-readable description
- `retryable` — `True` if the operation might succeed on a subsequent attempt

Check `result.error` after every call if you need to distinguish success from
degraded or failed output.

```python
import flatline

result = flatline.decompile_function(request)

if result.error is not None:
    print(f"Error [{result.error.category}]: {result.error.message}")
    if result.error.retryable:
        print("This error may be transient — retrying could help.")
else:
    print(result.c_code)

# Warnings are separate from errors and can accompany a successful result.
for warning in result.warnings:
    print(f"Warning [{warning.phase}]: {warning.message}")
```

!!! note "Exceptions vs result errors"
    Exceptions are raised for problems detected before decompilation begins
    (bad arguments, unknown targets, unmapped addresses) or for catastrophic
    engine failures. `DecompileResult.error` is used when the decompiler
    produces a result object but that result reflects a failure or partial
    output. Always check both when robustness matters.
