# How-to Guides

How-to guides are problem-oriented recipes. Each guide walks through solving a specific task with flatline, assuming you have already completed the [Getting Started](../getting-started.md) guide.

## Guides

| Guide | What it covers |
|-------|---------------|
| [Load from a Binary File](load-from-binary.md) | Extracting `memory_image` from ELF, PE, and Mach-O files using common Python libraries. |
| [Enumerate Languages](enumerate-languages.md) | Listing and filtering the language/compiler pairs available in your runtime data directory. |
| [Session Management](session-management.md) | Using context managers and long-lived sessions for efficient batch decompilation. |
| [Handle Errors](handle-errors.md) | Catching specific error categories, interpreting `DecompileResult.error`, and distinguishing user-fixable from internal errors. |
| [Analysis Budget](analysis-budget.md) | Tuning `max_instructions` to handle complex or large functions within resource bounds. |
| [Enriched Output](enriched-output.md) | Accessing p-code IR, resolving fspec/IOP varnodes, and inspecting CBRANCH branch targets. |
