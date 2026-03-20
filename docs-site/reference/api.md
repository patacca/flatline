# API Reference

## Session API

A `DecompilerSession` owns one native architecture instance and amortizes
startup cost across multiple decompile calls. Use it as a context manager for
deterministic cleanup, or manage the lifecycle manually with `close()`.

::: flatline.DecompilerSession
    options:
      members:
        - decompile_function
        - list_language_compilers
        - close
        - is_closed

## One-Shot Functions

These module-level convenience functions each create a short-lived session,
run one operation, and close the session immediately. They are the simplest
entry point when you only need a single call.

::: flatline.decompile_function

::: flatline.list_language_compilers

::: flatline.get_version_info

## Request and Result

::: flatline.DecompileRequest

::: flatline.DecompileResult

## Data Models

All data models are frozen dataclasses. Fields are populated on successful
decompilation; see `DecompileResult` for how `None` values are used on error.

::: flatline.FunctionInfo

::: flatline.FunctionPrototype

::: flatline.TypeInfo

::: flatline.ParameterInfo

::: flatline.VariableInfo

::: flatline.CallSiteInfo

::: flatline.JumpTableInfo

::: flatline.DiagnosticFlags

::: flatline.StorageInfo

::: flatline.AnalysisBudget

## Diagnostics

::: flatline.WarningItem

::: flatline.ErrorItem

## Enumeration Types

::: flatline.LanguageCompilerPair

::: flatline.VersionInfo

## Constants

::: flatline.VALID_METATYPES

::: flatline.VALID_WARNING_PHASES

::: flatline.ERROR_CATEGORIES

::: flatline.CATEGORY_TO_EXCEPTION

::: flatline.DECOMPILER_VERSION

::: flatline.__version__
