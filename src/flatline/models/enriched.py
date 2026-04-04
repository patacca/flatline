"""Opt-in pcode graph payloads for enriched decompiler output."""

from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property

import networkx as nx

from flatline._errors import InvalidArgumentError
from flatline.models.types import PcodeOpInfo, VarnodeInfo


@dataclass(frozen=True)
class Pcode:
    """Opt-in pcode payload extracted from the decompiler IR."""

    pcode_ops: list[PcodeOpInfo]
    varnodes: list[VarnodeInfo]

    def get_pcode_op(self, op_id: int) -> PcodeOpInfo:
        """Return one pcode op by stable ID."""
        _validate_lookup_id(op_id, "op_id")
        try:
            return self._pcode_ops_by_id[op_id]
        except KeyError as exc:
            raise InvalidArgumentError(f"unknown pcode op id: {op_id}") from exc

    def get_varnode(self, varnode_id: int) -> VarnodeInfo:
        """Return one varnode by stable ID."""
        _validate_lookup_id(varnode_id, "varnode_id")
        try:
            return self._varnodes_by_id[varnode_id]
        except KeyError as exc:
            raise InvalidArgumentError(f"unknown varnode id: {varnode_id}") from exc

    def to_graph(self) -> nx.MultiDiGraph:
        """Return a traversable bipartite graph of pcode ops and varnodes."""
        graph = nx.MultiDiGraph()
        varnodes_by_id = self._varnodes_by_id

        for pcode_op in self.pcode_ops:
            graph.add_node(("op", pcode_op.id), kind="pcode_op", op=pcode_op)
        for varnode in self.varnodes:
            graph.add_node(("varnode", varnode.id), kind="varnode", varnode=varnode)

        for pcode_op in self.pcode_ops:
            op_node = ("op", pcode_op.id)
            for input_index, varnode_id in enumerate(pcode_op.input_varnode_ids):
                try:
                    input_varnode = varnodes_by_id[varnode_id]
                except KeyError:
                    raise InvalidArgumentError(
                        f"pcode op {pcode_op.id} references unknown input varnode {varnode_id}"
                    ) from None
                graph.add_edge(
                    ("varnode", input_varnode.id),
                    op_node,
                    key=("input", input_index),
                    kind="input",
                    input_index=input_index,
                )

            if pcode_op.output_varnode_id is not None:
                try:
                    output_varnode = varnodes_by_id[pcode_op.output_varnode_id]
                except KeyError:
                    raise InvalidArgumentError(
                        f"pcode op {pcode_op.id} references unknown output varnode "
                        f"{pcode_op.output_varnode_id}"
                    ) from None
                graph.add_edge(
                    op_node,
                    ("varnode", output_varnode.id),
                    key=("output", 0),
                    kind="output",
                    input_index=None,
                )

        return graph

    @cached_property
    def _pcode_ops_by_id(self) -> dict[int, PcodeOpInfo]:
        return _index_pcode_ops(self.pcode_ops)

    @cached_property
    def _varnodes_by_id(self) -> dict[int, VarnodeInfo]:
        return _index_varnodes(self.varnodes)


@dataclass(frozen=True)
class Enriched:
    """Optional companion payload for enriched decompiler output."""

    pcode: Pcode | None = None


def _validate_lookup_id(value: int, field_name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise InvalidArgumentError(f"{field_name} must be an int")


def _index_pcode_ops(pcode_ops: list[PcodeOpInfo]) -> dict[int, PcodeOpInfo]:
    pcode_ops_by_id: dict[int, PcodeOpInfo] = {}
    for pcode_op in pcode_ops:
        if pcode_op.id in pcode_ops_by_id:
            raise InvalidArgumentError(f"duplicate pcode op id: {pcode_op.id}")
        pcode_ops_by_id[pcode_op.id] = pcode_op
    return pcode_ops_by_id


def _index_varnodes(varnodes: list[VarnodeInfo]) -> dict[int, VarnodeInfo]:
    varnodes_by_id: dict[int, VarnodeInfo] = {}
    for varnode in varnodes:
        if varnode.id in varnodes_by_id:
            raise InvalidArgumentError(f"duplicate varnode id: {varnode.id}")
        varnodes_by_id[varnode.id] = varnode
    return varnodes_by_id


__all__ = [
    "Enriched",
    "Pcode",
]
