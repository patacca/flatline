"""Graph extraction adapter for the xray-layout benchmark.

Loads a binary via flatline's public API, runs the decompiler with
``enriched=True``, and projects the resulting pcode IR into a
``networkx.MultiDiGraph`` whose nodes/edges carry the metadata required
by the benchmark layout pipeline.

Node metadata (every node has all three keys):
    kind:              "pcode_op" | "varnode" | "cfg_block"
    instruction_addr:  int address of the source assembly instruction
                       this node belongs to, or ``None`` for synthetic
                       nodes (e.g. constants without a defining op).
    label:             short human-readable string used by renderers.

Edge metadata (every edge has both keys):
    edge_type:         "pcode_dataflow" | "cfg" | "iop"
    port_constraint:   "vertical_only"      (pcode_dataflow)
                     | "vertical_preferred" (cfg)
                     | "horizontal_only"    (iop)

The base ``Pcode.to_graph()`` projection emits only bipartite
varnode<->op data-flow edges. To exercise layout backends on a
realistic CFG-shaped graph (and to make the resulting graph connected),
we synthesise two additional edge families on top of the base graph
without touching flatline's public API:

* ``iop`` edges: pcode ops in execution order. We sort all ops by
  ``(sequence_time, sequence_order)`` and add one edge from each op to
  the immediately following op. This produces a single op-spine that
  threads the entire function, irrespective of basic-block boundaries.

* ``cfg`` edges: every branch op (BRANCH, CBRANCH and similar) whose
  ``true_target_address`` / ``false_target_address`` is set fans out to
  every op whose ``instruction_address`` matches that target. We do not
  attempt to identify "the first op" of the target instruction because
  the public API exposes per-op fields only; emitting an edge to every
  matching op is correct under set semantics and keeps this extractor
  free of basic-block reconstruction logic.

``cfg_block`` nodes remain reserved for a future projection that
exposes basic blocks; this extractor never emits them.

CLI:
    python -m benchmarks.xray_layout.bench.graph_extract \\
        <binary.elf> <meta.json> -o <out.gpickle>
"""

from __future__ import annotations

import argparse
import json
import pickle
import sys
from typing import TYPE_CHECKING

import networkx as nx

from flatline import DecompileRequest, decompile_function

if TYPE_CHECKING:
    from pathlib import Path

# Edge-type vocabulary -- kept in one place so the classification scheme
# is easy to extend when CFG/IOP projections become available upstream.
EDGE_TYPE_PCODE_DATAFLOW = "pcode_dataflow"
EDGE_TYPE_CFG = "cfg"
EDGE_TYPE_IOP = "iop"

# Port-constraint hints describe how the layout engine should attach
# the edge to its endpoints. They are intentionally library-agnostic
# strings; concrete layout backends translate them into native options.
_PORT_CONSTRAINT_BY_EDGE_TYPE = {
    EDGE_TYPE_PCODE_DATAFLOW: "vertical_only",
    EDGE_TYPE_CFG: "vertical_preferred",
    EDGE_TYPE_IOP: "horizontal_only",
}

# Node-kind vocabulary mirrors the bipartite ("pcode_op", "varnode")
# split produced by ``Pcode.to_graph()``, plus a forward-looking
# "cfg_block" kind for when the public API exposes basic blocks.
NODE_KIND_PCODE_OP = "pcode_op"
NODE_KIND_VARNODE = "varnode"
NODE_KIND_CFG_BLOCK = "cfg_block"


def extract(binary_path: Path, meta_path: Path) -> nx.MultiDiGraph[object]:
    """Decompile ``binary_path`` and return its enriched pcode graph.

    Args:
        binary_path: Path to the raw binary memory image.
        meta_path: Path to the corpus meta JSON describing the target
            language, compiler spec, base address, and target function
            entry point.

    Returns:
        A ``networkx.MultiDiGraph`` with the node/edge metadata schema
        documented at module level.

    Raises:
        RuntimeError: If decompilation does not succeed or no enriched
            pcode payload is produced. We hard-error rather than return
            partial graphs so downstream benchmark stages do not silently
            measure broken inputs.
    """

    meta = _load_meta(meta_path)
    raw_bytes = binary_path.read_bytes()

    # The corpus stores ``base_address=0x0`` for every entry while
    # ``target_func_addr`` is the symbol's virtual address inside the
    # ELF. Passing the raw file with base=0x0 puts ``target_func_addr``
    # outside the memory image. When the input is an ELF we therefore
    # extract the LOAD segment containing the function and feed flatline
    # the segment bytes plus its true VA. Non-ELF inputs are passed
    # straight through (caller controls the slicing).
    memory_image, base_address = _slice_for_function(
        raw_bytes,
        declared_base=meta["base_address"],
        function_address=meta["target_func_addr"],
    )

    request = DecompileRequest(
        memory_image=memory_image,
        base_address=base_address,
        function_address=meta["target_func_addr"],
        language_id=meta["language_id"],
        compiler_spec=meta["compiler_spec"],
        enriched=True,
    )
    result = decompile_function(request)

    # Hard-fail surfaces broken corpus entries immediately. The
    # benchmark must never silently degrade to an empty graph.
    if result.error is not None:
        raise RuntimeError(
            f"decompilation failed for {binary_path}: {result.error.category}: {result.error.message}"
        )
    if result.enriched is None or result.enriched.pcode is None:
        raise RuntimeError(
            f"decompilation succeeded but no enriched pcode payload for {binary_path}"
        )

    pcode = result.enriched.pcode
    base_graph = pcode.to_graph()

    # Build a lookup so varnode nodes can adopt the instruction address
    # of their defining op (when available). This makes nodes that share
    # an instruction cluster trivially groupable downstream by equality
    # on the ``instruction_addr`` attribute.
    op_by_id = {op.id: op for op in pcode.pcode_ops}
    varnode_by_id = {vn.id: vn for vn in pcode.varnodes}

    augmented = _augment_graph(base_graph, op_by_id, varnode_by_id)
    _add_iop_edges(augmented, pcode.pcode_ops)
    _add_cfg_edges(augmented, pcode.pcode_ops)
    return augmented


def _load_meta(meta_path: Path) -> dict[str, int | str]:
    """Parse the corpus meta JSON and normalise hex address fields.

    The corpus meta files store addresses as hex strings (with or
    without ``0x`` prefix). We normalise to ``int`` here so the public
    ``DecompileRequest`` receives the type it expects.
    """

    raw = json.loads(meta_path.read_text())
    return {
        "target_func_addr": _parse_hex(raw["target_func_addr"]),
        "base_address": _parse_hex(raw["base_address"]),
        "language_id": raw["language_id"],
        "compiler_spec": raw["compiler_spec"],
    }


def _parse_hex(value: str) -> int:
    """Parse a hex address string, tolerating an optional ``0x`` prefix."""

    text = value.strip().lower()
    if text.startswith("0x"):
        return int(text, 16)
    # Bare hex form (e.g. "0000000000401000") is also accepted.
    return int(text, 16)


# ELF64 ``PT_LOAD`` program-header type.
_ELF_PT_LOAD = 1


def _slice_for_function(
    raw_bytes: bytes,
    *,
    declared_base: int,
    function_address: int,
) -> tuple[bytes, int]:
    """Return (memory_image, base_address) suitable for flatline.

    For ELF64 inputs we locate the ``PT_LOAD`` segment that contains
    ``function_address`` and return that segment's bytes paired with its
    runtime VA. For everything else we honour the meta-declared base
    verbatim (caller is responsible for producing a compatible slice).
    """

    if not raw_bytes.startswith(b"\x7fELF") or raw_bytes[4] != 2:
        # Not an ELF64; trust caller-provided slicing.
        return raw_bytes, declared_base

    # Minimal ELF64 program-header parse (little-endian, class=64).
    # We deliberately avoid ``elftools`` so the benchmark has zero
    # extra dependencies beyond flatline + networkx.
    import struct

    e_phoff = struct.unpack_from("<Q", raw_bytes, 0x20)[0]
    e_phentsize = struct.unpack_from("<H", raw_bytes, 0x36)[0]
    e_phnum = struct.unpack_from("<H", raw_bytes, 0x38)[0]

    for i in range(e_phnum):
        ph_off = e_phoff + i * e_phentsize
        p_type = struct.unpack_from("<I", raw_bytes, ph_off)[0]
        if p_type != _ELF_PT_LOAD:
            continue
        p_offset = struct.unpack_from("<Q", raw_bytes, ph_off + 8)[0]
        p_vaddr = struct.unpack_from("<Q", raw_bytes, ph_off + 16)[0]
        p_filesz = struct.unpack_from("<Q", raw_bytes, ph_off + 32)[0]
        if p_vaddr <= function_address < p_vaddr + p_filesz:
            segment = raw_bytes[p_offset : p_offset + p_filesz]
            return segment, p_vaddr

    # No LOAD segment covers the function -- hard-error so a broken
    # corpus entry never produces a silently empty graph.
    raise RuntimeError(
        f"no PT_LOAD segment in ELF covers function_address={hex(function_address)}"
    )


def _augment_graph(
    base_graph: nx.MultiDiGraph[object],
    op_by_id: dict[int, object],
    varnode_by_id: dict[int, object],
) -> nx.MultiDiGraph[object]:
    """Attach benchmark-specific metadata to nodes and edges.

    The base graph from ``Pcode.to_graph()`` already carries ``kind``
    and the underlying ``op`` / ``varnode`` payloads on each node, plus
    ``kind=input|output`` on each edge. We layer the benchmark schema on
    top without dropping the original attributes; downstream code that
    wants the raw flatline objects can still reach them.
    """

    graph: nx.MultiDiGraph[object] = nx.MultiDiGraph()

    for node, data in base_graph.nodes(data=True):
        node_kind, instruction_addr, label = _node_attributes(
            node, data, op_by_id, varnode_by_id
        )
        merged = {**data, "kind": node_kind, "instruction_addr": instruction_addr, "label": label}
        graph.add_node(node, **merged)

    for src, dst, key, data in base_graph.edges(keys=True, data=True):
        # All edges produced by the public ``Pcode.to_graph()`` are
        # bipartite varnode<->op data-flow edges. CFG and IOP edges are
        # reserved here for a future projection that exposes basic
        # blocks; the classifier is centralised in
        # ``_classify_edge`` so adding new edge sources is a one-liner.
        edge_type = _classify_edge(data)
        merged_edge = {
            **data,
            "edge_type": edge_type,
            "port_constraint": _PORT_CONSTRAINT_BY_EDGE_TYPE[edge_type],
        }
        graph.add_edge(src, dst, key=key, **merged_edge)

    return graph


def _add_iop_edges(graph: nx.MultiDiGraph[object], pcode_ops: list[object]) -> None:
    """Add inter-op (IOP) execution-order edges to the graph in place.

    Sorts all ops by ``(sequence_time, sequence_order)`` (Ghidra's
    deterministic per-op key) and links each op to the immediately
    following op with a single ``edge_type="iop"`` edge. The result is a
    single op-spine that traverses the entire function regardless of
    basic-block boundaries; this is intentional and avoids reconstructing
    blocks from the public API surface.
    """

    ordered = sorted(pcode_ops, key=lambda op: (op.sequence_time, op.sequence_order))
    iop_attrs = {
        "edge_type": EDGE_TYPE_IOP,
        "port_constraint": _PORT_CONSTRAINT_BY_EDGE_TYPE[EDGE_TYPE_IOP],
        # ``kind`` mirrors the base-graph convention (string discriminator)
        # so any consumer that switches on ``kind`` keeps working.
        "kind": EDGE_TYPE_IOP,
    }
    for current, follower in zip(ordered, ordered[1:], strict=False):
        src = ("op", current.id)
        dst = ("op", follower.id)
        # Both endpoints must already exist as nodes in the augmented
        # graph (they were added from ``base_graph`` above). If not, the
        # base projection is missing an op node -- skip rather than
        # invent a node, to keep the contract one-way.
        if src in graph and dst in graph:
            graph.add_edge(src, dst, **iop_attrs)


def _add_cfg_edges(graph: nx.MultiDiGraph[object], pcode_ops: list[object]) -> None:
    """Add control-flow (CFG) edges in place from each branch op.

    For every op exposing a non-None ``true_target_address`` or
    ``false_target_address`` (covers BRANCH, CBRANCH, and any future op
    class that surfaces these fields), we emit one CFG edge from the
    branch op to *every* op whose ``instruction_address`` matches that
    target address. We deliberately fan out instead of picking a single
    "first op of the target instruction" because the public API exposes
    only per-op fields; set-fanout is correct under any later block
    reconstruction (every targeted op is reachable along the branch).
    """

    # Pre-bucket ops by instruction address so target lookup is O(1).
    ops_by_addr: dict[int, list[object]] = {}
    for op in pcode_ops:
        ops_by_addr.setdefault(int(op.instruction_address), []).append(op)

    cfg_attrs = {
        "edge_type": EDGE_TYPE_CFG,
        "port_constraint": _PORT_CONSTRAINT_BY_EDGE_TYPE[EDGE_TYPE_CFG],
        "kind": EDGE_TYPE_CFG,
    }
    for op in pcode_ops:
        # ``getattr`` + None-check works for any op class that may or may
        # not expose these fields, without coupling to the BranchOp
        # hierarchy at import time.
        for target_attr in ("true_target_address", "false_target_address"):
            target = getattr(op, target_attr, None)
            if target is None:
                continue
            target_addr = int(target)
            target_ops = ops_by_addr.get(target_addr, ())
            src = ("op", op.id)
            if src not in graph:
                continue
            for target_op in target_ops:
                dst = ("op", target_op.id)
                if dst in graph:
                    graph.add_edge(src, dst, **cfg_attrs)


def _node_attributes(
    node: object,
    data: dict[str, object],
    op_by_id: dict[int, object],
    varnode_by_id: dict[int, object],
) -> tuple[str, int | None, str]:
    """Derive (kind, instruction_addr, label) for one graph node.

    The bipartite key shape is ``(role, id)`` where role is ``"op"`` or
    ``"varnode"``; we map that onto the public node-kind vocabulary and
    pull a stable instruction address from the op (directly) or from
    the varnode's defining op (transitively).
    """

    base_kind = data.get("kind")
    if base_kind == "pcode_op" or (isinstance(node, tuple) and node[0] == "op"):
        op = op_by_id.get(node[1]) if isinstance(node, tuple) else None
        if op is None:
            return NODE_KIND_PCODE_OP, None, "op"
        return (
            NODE_KIND_PCODE_OP,
            int(op.instruction_address),
            f"{op.opcode}#{op.id}",
        )

    if base_kind == "varnode" or (isinstance(node, tuple) and node[0] == "varnode"):
        varnode = varnode_by_id.get(node[1]) if isinstance(node, tuple) else None
        if varnode is None:
            return NODE_KIND_VARNODE, None, "varnode"
        # Prefer the defining op's instruction address so a varnode
        # clusters with the op that produced it. Constants and function
        # inputs have no defining op -> ``None`` (synthetic).
        instruction_addr: int | None = None
        defining_op_id = varnode.defining_op_id
        if defining_op_id is not None:
            defining_op = op_by_id.get(defining_op_id)
            if defining_op is not None:
                instruction_addr = int(defining_op.instruction_address)
        return NODE_KIND_VARNODE, instruction_addr, f"v{varnode.id}"

    # Forward-compat path for a future ``cfg_block`` projection.
    if base_kind == "cfg_block":
        return NODE_KIND_CFG_BLOCK, None, "block"

    # Unknown node shape -> mark synthetic; never raise so the benchmark
    # can still measure partial graphs from future projections.
    return NODE_KIND_VARNODE, None, "unknown"


def _classify_edge(data: dict[str, object]) -> str:
    """Return the benchmark ``edge_type`` for a base-graph edge.

    The current public projection only emits data-flow (input/output)
    edges, so we treat every base-graph edge as ``pcode_dataflow``.
    Future projections that tag edges with e.g. ``kind="cfg"`` or
    ``kind="iop"`` can be threaded through here without changes to
    callers.
    """

    base_kind = data.get("kind")
    if base_kind in {"input", "output"}:
        return EDGE_TYPE_PCODE_DATAFLOW
    if base_kind == "cfg":
        return EDGE_TYPE_CFG
    if base_kind == "iop":
        return EDGE_TYPE_IOP
    # Default: data-flow. Keeps the contract ``edge_type`` invariant
    # satisfied even for unanticipated edge kinds.
    return EDGE_TYPE_PCODE_DATAFLOW


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Extract a flatline enriched-pcode graph for the xray-layout benchmark.",
    )
    parser.add_argument("binary_path", help="Path to the binary memory image.")
    parser.add_argument("meta_path", help="Path to the corpus meta JSON.")
    parser.add_argument(
        "-o",
        "--output",
        required=True,
        help="Destination .gpickle path for the extracted graph.",
    )
    args = parser.parse_args(argv)

    from pathlib import Path

    graph = extract(Path(args.binary_path), Path(args.meta_path))

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("wb") as handle:
        pickle.dump(graph, handle)

    print(
        f"extracted graph: nodes={graph.number_of_nodes()} "
        f"edges={graph.number_of_edges()} -> {out_path}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(_main())
