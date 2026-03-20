# Error Taxonomy

flatline uses a structured exception hierarchy. Every exception raised by the
library is a subclass of `FlatlineError`, and every subclass maps to exactly
one entry in `ERROR_CATEGORIES`.

## Exception Hierarchy

```
FlatlineError
├── InvalidArgumentError        (invalid_argument)
├── UnsupportedTargetError      (unsupported_target)
├── InvalidAddressError         (invalid_address)
├── DecompileFailedError        (decompile_failed)
├── ConfigurationError          (configuration_error)
└── InternalError               (internal_error)
```

Each class carries a `category` class attribute that matches the corresponding
`ERROR_CATEGORIES` string. The same category strings appear in
`DecompileResult.error.category` when errors are surfaced as structured data
rather than raised exceptions.

## Error Category Reference

| Category | Exception Class | User-Fixable? | Description |
|---|---|:---:|---|
| `invalid_argument` | `InvalidArgumentError` | Yes | A request field is missing, the wrong type, or has an invalid value. For example: empty `memory_image`, non-string `language_id`, or a non-positive `max_instructions`. |
| `unsupported_target` | `UnsupportedTargetError` | Yes | The `language_id` or `compiler_spec` in the request is not recognized by the runtime data. Call `list_language_compilers()` to see valid values. |
| `invalid_address` | `InvalidAddressError` | Yes | The `function_address` does not fall within the provided `memory_image`. Check that the address lies in the range `[base_address, base_address + len(memory_image))`. |
| `decompile_failed` | `DecompileFailedError` | Sometimes | The decompiler engine could not produce output for the given input. May indicate corrupt data, an unsupported instruction sequence, or a budget exceeded condition. |
| `configuration_error` | `ConfigurationError` | Yes | A problem with the installation or runtime environment that the caller can resolve: missing `ghidra-sleigh` package, invalid `runtime_data_dir`, or corrupted runtime data files. |
| `internal_error` | `InternalError` | No | An unexpected error inside flatline — this is a bug. Please report it with a reproduction case. |

## `ERROR_CATEGORIES` and `CATEGORY_TO_EXCEPTION`

`ERROR_CATEGORIES` is a `frozenset[str]` containing all valid category strings:

```python
import flatline

print(flatline.ERROR_CATEGORIES)
# frozenset({'invalid_argument', 'unsupported_target', 'invalid_address',
#            'decompile_failed', 'configuration_error', 'internal_error'})
```

`CATEGORY_TO_EXCEPTION` is a `dict[str, type[FlatlineError]]` that maps each
category string to its exception class. This is useful when you receive a
`DecompileResult.error` and want to raise or inspect the corresponding
exception:

```python
import flatline

result = flatline.decompile_function(request)
if result.error:
    exc_class = flatline.CATEGORY_TO_EXCEPTION[result.error.category]
    raise exc_class(result.error.message)
```

Both collections are stable across minor and patch releases. New categories
will only be introduced in major releases.

## When Each Error Is Raised

**`InvalidArgumentError`** is raised during request construction or before the
decompiler is invoked:

```python
# Empty memory image
flatline.DecompileRequest(memory_image=b"", ...)  # raises InvalidArgumentError

# Non-positive budget
flatline.AnalysisBudget(max_instructions=0)  # raises InvalidArgumentError

# Closed session
session.close()
session.decompile_function(request)  # raises InvalidArgumentError
```

**`UnsupportedTargetError`** is raised when the language or compiler is not
available in the current runtime data:

```python
# Unknown language
request = flatline.DecompileRequest(language_id="notreal:LE:64:default", ...)
flatline.decompile_function(request)  # raises UnsupportedTargetError
```

**`InvalidAddressError`** is raised when the function address is out of range:

```python
request = flatline.DecompileRequest(
    memory_image=b"\x90" * 16,
    base_address=0x1000,
    function_address=0x9000,  # outside image
    ...
)
flatline.decompile_function(request)  # raises InvalidAddressError
```

**`DecompileFailedError`** is raised when the engine runs but cannot produce
decompiled output. This is distinct from a budget exceeded condition, which
currently results in partial output with diagnostic flags set.

**`ConfigurationError`** is raised at session startup when the runtime
environment is not usable:

```python
# Missing ghidra-sleigh package
flatline.DecompilerSession()  # raises ConfigurationError if ghidra-sleigh absent

# Bad runtime_data_dir
flatline.DecompilerSession(runtime_data_dir="/nonexistent")  # raises ConfigurationError
```

**`InternalError`** is raised when flatline encounters an unexpected condition.
If you see this error in normal use, it is a bug. The error message includes
context to help with reporting.

## `FlatlineError.message`

All `FlatlineError` subclasses expose a `message` property that returns the
human-readable error string from the first argument:

```python
try:
    flatline.decompile_function(request)
except flatline.FlatlineError as exc:
    print(exc.category)  # e.g. "unsupported_target"
    print(exc.message)   # human-readable description
```
