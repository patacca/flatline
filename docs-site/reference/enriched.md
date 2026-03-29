# Enriched Output

Enriched output is opt-in: set
[`DecompileRequest.enriched`][flatline.DecompileRequest] to `True` to receive
post-simplification pcode operations and varnode use-def graph data alongside
the standard decompilation result.

## Container

::: flatline.Enriched

## Pcode

::: flatline.Pcode
    options:
      group_by_category: true
      show_category_heading: true
      members:
        - pcode_ops
        - varnodes
        - get_pcode_op
        - get_varnode
        - to_graph

## Pcode Types

::: flatline.PcodeOpInfo

::: flatline.VarnodeInfo

::: flatline.VarnodeFlags
