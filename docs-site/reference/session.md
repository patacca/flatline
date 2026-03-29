# Session

A [`DecompilerSession`][flatline.DecompilerSession] owns one native bridge
session and amortizes library initialization, runtime data resolution, and
language/compiler enumeration across multiple calls.  Use it as a context
manager for deterministic cleanup, or manage the lifecycle manually with
[`close()`][flatline.DecompilerSession.close].

For one-off operations, the module-level convenience functions create a
short-lived session, run one operation, and tear it down immediately.

## Session API

::: flatline.DecompilerSession
    options:
      group_by_category: true
      show_category_heading: true
      members:
        - decompile_function
        - list_language_compilers
        - close
        - is_closed

## One-Shot Functions

::: flatline.decompile_function

::: flatline.list_language_compilers

::: flatline.get_version_info

## Return Types

::: flatline.LanguageCompilerPair

::: flatline.VersionInfo
