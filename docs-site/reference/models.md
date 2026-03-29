# Data Models

All data models are frozen dataclasses.  Fields are populated on successful
decompilation; see [`DecompileResult`][flatline.DecompileResult] for how
`None` values are used on error.

## Function Structure

::: flatline.FunctionInfo

::: flatline.FunctionPrototype

::: flatline.DiagnosticFlags

## Leaf Types

::: flatline.TypeInfo

::: flatline.ParameterInfo

::: flatline.VariableInfo

::: flatline.CallSiteInfo

::: flatline.JumpTableInfo

::: flatline.StorageInfo
