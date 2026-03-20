# Analysis Budget

flatline imposes a deterministic instruction limit on each decompilation call. This
prevents runaway analysis on pathological functions and keeps batch pipelines
predictable. This guide shows how to inspect and adjust the limit.

## The default budget

Every `DecompileRequest` applies a budget of **100,000 p-code instructions** unless
you override it. This is enough for the vast majority of real-world functions.

```python
from flatline import DecompileRequest, AnalysisBudget

# These two requests are equivalent — the default budget is applied automatically.
request_default = DecompileRequest(
    memory_image=code,
    base_address=0x1000,
    function_address=0x1000,
    language_id="x86:LE:64:default",
)

request_explicit = DecompileRequest(
    memory_image=code,
    base_address=0x1000,
    function_address=0x1000,
    language_id="x86:LE:64:default",
    analysis_budget=AnalysisBudget(max_instructions=100_000),
)
```

## Raising the limit for complex functions

Large or highly optimized functions — compiler-generated dispatch tables, inlined
library code, auto-vectorized loops — can exceed the default limit. Raise
`max_instructions` to give the decompiler more room.

```python
from flatline import DecompilerSession, DecompileRequest, AnalysisBudget

request = DecompileRequest(
    memory_image=code,
    base_address=0x1000,
    function_address=0x1000,
    language_id="x86:LE:64:default",
    compiler_spec="gcc",
    analysis_budget=AnalysisBudget(max_instructions=500_000),
)

with DecompilerSession() as session:
    result = session.decompile_function(request)
```

## Dict coercion

As a convenience, you can pass a plain `dict` instead of an `AnalysisBudget` object.
flatline coerces it automatically. Only the `"max_instructions"` key is supported;
unknown keys raise `InvalidArgumentError`.

```python
from flatline import DecompileRequest

request = DecompileRequest(
    memory_image=code,
    base_address=0x1000,
    function_address=0x1000,
    language_id="x86:LE:64:default",
    analysis_budget={"max_instructions": 250_000},
)
```

## Lowering the limit for fast screening

When you only need a quick first pass — for example, to triage a large set of
functions before doing deeper analysis — a lower limit reduces per-call latency at
the cost of potentially incomplete output.

```python
from flatline import DecompilerSession, DecompileRequest, AnalysisBudget

screening_budget = AnalysisBudget(max_instructions=10_000)

with DecompilerSession() as session:
    for base, entry, code in targets:
        request = DecompileRequest(
            memory_image=code,
            base_address=base,
            function_address=entry,
            language_id="x86:LE:64:default",
            analysis_budget=screening_budget,
        )
        result = session.decompile_function(request)
        # Check diagnostics to see if the budget was a limiting factor.
        if result.function_info and not result.function_info.is_complete:
            print(f"0x{entry:x}: incomplete — may need a higher budget")
```

## What happens when the budget is exceeded

When the decompiler hits the instruction limit, it stops analysis early and produces
whatever output it has accumulated. The result is still returned — no exception is
raised — but the output may be partial or degraded.

Look for these signals in the result:

- `result.function_info.is_complete` is `False`
- `result.function_info.diagnostics.has_unimplemented` may be `True`
- `result.warnings` may contain entries describing the truncation
- `result.error` may be set if the decompiler could not produce usable output at all

```python
import flatline

result = flatline.decompile_function(request)

if result.function_info is not None:
    info = result.function_info
    if not info.is_complete:
        print("Decompilation did not complete — consider raising max_instructions.")
    if info.diagnostics.has_unimplemented:
        print("Unimplemented instructions encountered.")

for warning in result.warnings:
    print(f"[{warning.phase}] {warning.message}")
```

!!! warning "Validity constraints"
    `max_instructions` must be a positive integer. Passing zero, a negative value,
    or a non-integer raises `InvalidArgumentError` at `DecompileRequest` construction
    time — before any decompilation work is done.

    ```python
    from flatline import DecompileRequest, InvalidArgumentError

    try:
        request = DecompileRequest(
            memory_image=code,
            base_address=0x1000,
            function_address=0x1000,
            language_id="x86:LE:64:default",
            analysis_budget={"max_instructions": 0},  # Invalid
        )
    except InvalidArgumentError as e:
        print(e.message)  # "analysis_budget.max_instructions must be positive"
    ```
