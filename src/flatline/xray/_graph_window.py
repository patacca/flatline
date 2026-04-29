"""tkinter window for flatline.xray.
The flatline.xray API is alpha. XrayWindow subclasses ``tk.Tk``, so only one
instance should exist per process.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

try:
    import tkinter as tk
except ImportError as exc:
    raise ImportError(
        "tkinter is required for flatline.xray - install a Python build "
        "that includes tkinter (e.g. python3-tk on Debian/Ubuntu).",
    ) from exc

if TYPE_CHECKING:
    from typing import ClassVar

    from ..models.types import FunctionInfo

from . import _theme
from ._arrowhead_scale import _clamp_arrowshape
from ._canvas import (
    hide_all_glows,
    show_node_glow,
)
from ._cpg_overlay import (
    build_checkbox_panel,
)
from ._inputs import disassemble_instruction_addresses
from ._inspector import op_text, summary_text, varnode_text
from ._layout import (
    HORIZONTAL_NODE_GAP,
    VERTICAL_LEVEL_GAP,
    LayoutResult,
    Position,
    VisualNode,
    compute_layout,
    sorted_ops,
)
from ._overlay_pipeline import render_graph_with_overlays


class XrayWindow(tk.Tk):
    """Interactive pcode graph viewer for one decompiled function."""

    _root_gap = 100.0
    _child_gap = HORIZONTAL_NODE_GAP
    _level_gap = VERTICAL_LEVEL_GAP
    _top_margin = 90.0
    _bottom_margin = 120.0
    _side_margin = 100.0

    _asm_default_width = 220
    _inspector_default_width = 280
    _asm_min_width = 180
    _inspector_min_width = 180

    _INITIAL_ZOOM = 1.0

    _ARROWSHAPE_MIN: ClassVar[tuple[float, float, float]] = (5.0, 6.0, 2.0)
    _ARROWSHAPE_MAX: ClassVar[tuple[float, float, float]] = (19.0, 22.0, 10.0)

    _ARROW_LARGE = (10, 11, 5)
    _ARROW_SMALL = (8, 10, 4)
    _ARROW_SHAPES: ClassVar[dict[str, tuple[int, int, int]]] = {
        "tree_edge": _ARROW_LARGE,
        "cbranch_edge": _ARROW_LARGE,
        "cross_edge": _ARROW_SMALL,
        "iop_edge": _ARROW_SMALL,
        "fspec_edge": _ARROW_SMALL,
    }

    def __init__(
        self,
        title: str,
        result,
        *,
        request=None,
        source_label: str | None = None,
        cpg: bool = False,
        function_info: FunctionInfo | None = None,
    ) -> None:
        super().__init__()
        self.window_title = title
        self.result = result
        self.request = request
        self.source_label = source_label
        self._cpg_enabled = cpg
        self._function_info = function_info
        self.pcode = self._require_pcode(result)
        self.op_by_id = {op.id: op for op in self.pcode.pcode_ops}
        self.varnode_by_id = {varnode.id: varnode for varnode in self.pcode.varnodes}
        self.sorted_ops = sorted_ops(self.pcode.pcode_ops)
        self.pcode_graph = self.pcode.to_graph()
        self._layout_cache: dict[int, LayoutResult] = {}
        self.layout = self._get_layout(self.pcode_graph)
        self.visual_nodes = self._build_visual_nodes(self.layout)
        self.visual_roots = self.visual_nodes
        self.max_depth = self._layout_depth(self.layout)
        self.virtual_width, self.virtual_height = self._canvas_size(self.layout)
        self.result_label = self._result_label()
        self._node_by_key: dict[str, VisualNode] = {node.key: node for node in self.visual_nodes}
        self._disasm = self._disassemble()
        self._selected_key: str | None = None
        self._highlighted_keys: set[str] = set()
        self._related_keys: set[str] = set()
        self._muted_keys: set[str] = set()
        title_suffix = f" - {self.result_label}" if self.result_label else ""
        self.title(f"{title}{title_suffix}")
        self.geometry("1500x980")
        self.configure(bg=_theme.BACKGROUND)
        header = tk.Frame(self, bg=_theme.BACKGROUND)
        header.pack(fill="x", padx=14, pady=(10, 6))
        tk.Label(
            header,
            text=title,
            bg=_theme.BACKGROUND,
            fg=_theme.SELECTION_OUTLINE,
            font=_theme.TITLE_FONT,
        ).pack(anchor="w")
        subtitle = (
            f"{self.result_label} | tree view | "
            f"{len(self.pcode.pcode_ops)} ops | {len(self.pcode.varnodes)} varnodes"
        )
        tk.Label(
            header,
            text=subtitle,
            bg=_theme.BACKGROUND,
            fg=_theme.TEXT_MUTED,
            font=_theme.SUBTITLE_FONT,
        ).pack(anchor="w", pady=(4, 0))
        body = tk.PanedWindow(
            self,
            orient="horizontal",
            bg=_theme.BACKGROUND,
            sashrelief="flat",
            sashwidth=6,
            handlesize=0,
        )
        body.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        asm_frame = tk.Frame(body, bg=_theme.PANEL_BG, width=self._asm_default_width)
        asm_frame.pack_propagate(False)
        tk.Label(
            asm_frame,
            text="Assembly",
            bg=_theme.PANEL_BG,
            fg=_theme.TEXT,
            font=_theme.PANEL_TITLE_FONT,
        ).pack(anchor="w", padx=14, pady=(14, 8))
        asm_inner = tk.Frame(asm_frame, bg=_theme.PANEL_BG)
        asm_inner.pack(fill="both", expand=True, padx=(14, 0))
        self.asm_listbox = tk.Listbox(
            asm_inner,
            bg=_theme.PANEL_BG,
            fg=_theme.TEXT,
            selectbackground=_theme.SELECTION_BACKGROUND,
            selectforeground=_theme.SELECTION_TEXT,
            selectborderwidth=0,
            font=_theme.BODY_FONT,
            selectmode=tk.EXTENDED,
            activestyle="none",
            exportselection=False,
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            width=48,
        )
        asm_vscroll = tk.Scrollbar(asm_inner, orient="vertical", command=self.asm_listbox.yview)
        asm_hscroll = tk.Scrollbar(asm_inner, orient="horizontal", command=self.asm_listbox.xview)
        self.asm_listbox.configure(yscrollcommand=asm_vscroll.set, xscrollcommand=asm_hscroll.set)
        self.asm_listbox.grid(row=0, column=0, sticky="nsew")
        asm_vscroll.grid(row=0, column=1, sticky="ns")
        asm_hscroll.grid(row=1, column=0, sticky="ew")
        asm_inner.grid_rowconfigure(0, weight=1)
        asm_inner.grid_columnconfigure(0, weight=1)
        for _, line_text in self._disasm:
            self.asm_listbox.insert(tk.END, line_text)
        self.asm_listbox.bind("<<ListboxSelect>>", self._on_asm_select)
        canvas_frame = tk.Frame(body, bg=_theme.BACKGROUND)
        self.canvas = tk.Canvas(canvas_frame, bg=_theme.CANVAS_BG, highlightthickness=0)
        x_scroll = tk.Scrollbar(canvas_frame, orient="horizontal", command=self.canvas.xview)
        y_scroll = tk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=x_scroll.set, yscrollcommand=y_scroll.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")
        canvas_frame.grid_rowconfigure(0, weight=1)
        canvas_frame.grid_columnconfigure(0, weight=1)
        sidebar = tk.Frame(body, bg=_theme.PANEL_BG, width=self._inspector_default_width)
        sidebar.pack_propagate(False)
        tk.Label(
            sidebar,
            text="Inspector",
            bg=_theme.PANEL_BG,
            fg=_theme.TEXT,
            font=_theme.PANEL_TITLE_FONT,
        ).pack(anchor="w", padx=14, pady=(14, 8))
        panel = build_checkbox_panel(sidebar, self.canvas, self._cpg_enabled)
        panel.pack(fill="x", padx=0, pady=0)
        self.inspector = tk.Text(
            sidebar,
            bg=_theme.PANEL_BG,
            fg=_theme.TEXT,
            insertbackground=_theme.TEXT,
            relief="flat",
            wrap="word",
            padx=14,
            pady=4,
            font=_theme.BODY_FONT,
        )
        self.inspector.pack(fill="both", expand=True)
        self.inspector.configure(state="disabled")
        body.add(
            asm_frame,
            minsize=self._asm_min_width,
            width=self._asm_default_width,
            stretch="never",
        )
        body.add(canvas_frame, stretch="always")
        body.add(
            sidebar,
            minsize=self._inspector_min_width,
            width=self._inspector_default_width,
            stretch="never",
        )
        self._zoom = self._INITIAL_ZOOM
        render_graph_with_overlays(
            self.canvas,
            layout=self.layout,
            pcode_graph=self.pcode_graph,
            pcode=self.pcode,
            visual_roots=self.visual_roots,
            visual_nodes=self.visual_nodes,
            op_by_id=self.op_by_id,
            varnode_by_id=self.varnode_by_id,
            function_info=self._function_info,
            show_node=self._show_node,
            cpg_enabled=self._cpg_enabled,
        )
        self._set_inspector_text(
            summary_text(
                title,
                result=result,
                pcode=self.pcode,
                target_label=self.result_label,
                source_label=self.source_label,
                fallback_address=self._fallback_address(),
            )
        )
        self.canvas.configure(scrollregion=(0, 0, self.virtual_width, self.virtual_height))
        # Center the graph horizontally; start at the top so the first ops are visible.
        x_center = max(0.0, (self.virtual_width / 2.0 - 750) / max(self.virtual_width, 1))
        self.canvas.xview_moveto(x_center)
        self.canvas.yview_moveto(0.0)
        self.canvas.bind("<MouseWheel>", self._on_mouse_wheel)
        self.canvas.bind("<Button-4>", lambda e: self._handle_button_scroll(e, zoom_in=True))
        self.canvas.bind("<Button-5>", lambda e: self._handle_button_scroll(e, zoom_in=False))
        try:
            self.canvas.bind("<Button-6>", lambda _e: self.canvas.xview_scroll(-3, "units"))
            self.canvas.bind("<Button-7>", lambda _e: self.canvas.xview_scroll(3, "units"))
        except tk.TclError:
            pass
        self.bind("<Control-equal>", lambda e: self._do_zoom(self._zoom * 1.15, e))
        self.bind("<Control-minus>", lambda e: self._do_zoom(self._zoom / 1.15, e))
        self.bind("<Control-0>", lambda _event: self.reset_view())
        self.canvas.bind("<Button-1>", self._on_canvas_click)

    def _get_layout(self, pcode_graph) -> LayoutResult:
        key = id(pcode_graph)
        cached = self._layout_cache.get(key)
        if cached is not None:
            return cached
        raw_layout = compute_layout(pcode_graph)
        layout = self._shift_layout_into_view(raw_layout)
        self._layout_cache[key] = layout
        return layout

    def _shift_layout_into_view(self, layout: LayoutResult) -> LayoutResult:
        if not layout.nodes:
            return layout
        min_left = min(pos.x - pos.w / 2.0 for pos in layout.nodes.values())
        min_top = min(pos.y - pos.h / 2.0 for pos in layout.nodes.values())
        dx = self._side_margin - min_left
        dy = self._top_margin - min_top
        shifted = {
            key: Position(pos.x + dx, pos.y + dy, pos.w, pos.h)
            for key, pos in layout.nodes.items()
        }
        return LayoutResult(nodes=shifted, meta=layout.meta)

    def _build_visual_nodes(self, layout: LayoutResult) -> list[VisualNode]:
        depths = self._depth_by_node_key(layout)
        visual_nodes: list[VisualNode] = []
        for node_id in sorted(self.pcode_graph.nodes, key=repr):
            key = repr(node_id)
            pos = layout.nodes[key]
            visual_nodes.append(
                VisualNode(key=key, actual=node_id, depth=depths[key], x=pos.x, y=pos.y)
            )
        return visual_nodes

    def _depth_by_node_key(self, layout: LayoutResult) -> dict[str, int]:
        ys = sorted({round(pos.y, 3) for pos in layout.nodes.values()})
        y_to_depth = {y: index for index, y in enumerate(ys)}
        return {key: y_to_depth[round(pos.y, 3)] for key, pos in layout.nodes.items()}

    def _layout_depth(self, layout: LayoutResult) -> int:
        return max(self._depth_by_node_key(layout).values(), default=0)

    def _canvas_size(self, layout: LayoutResult) -> tuple[int, int]:
        if not layout.nodes:
            return (1400, 940)
        width = max(pos.x + pos.w / 2.0 for pos in layout.nodes.values()) + self._side_margin
        height = max(pos.y + pos.h / 2.0 for pos in layout.nodes.values()) + self._bottom_margin
        return (max(1400, int(width)), max(940, int(height)))

    def show(self) -> None:
        self.mainloop()

    def _require_pcode(self, result):
        if result.error is not None:
            raise ValueError("XrayWindow requires a successful decompilation result")
        if result.enriched is None or result.enriched.pcode is None:
            raise ValueError("XrayWindow requires a result produced with enriched=True")
        return result.enriched.pcode

    def _result_label(self) -> str:
        if self.request is not None:
            compiler = self.request.compiler_spec or "default"
            return f"{self.request.language_id} / {compiler}"
        metadata = self.result.metadata or {}
        language = metadata.get("language_id", "?")
        compiler = metadata.get("compiler_spec", "?")
        return f"{language} / {compiler}"

    def _fallback_address(self) -> int | None:
        if self.request is not None:
            return self.request.function_address
        info = self.result.function_info
        return info.entry_address if info is not None else None

    def _set_inspector_text(self, text: str) -> None:
        self.inspector.configure(state="normal")
        self.inspector.delete("1.0", tk.END)
        self.inspector.insert("1.0", text)
        self.inspector.configure(state="disabled")

    def _default_outline(self, node: VisualNode) -> str:
        return _theme.NODE_OUTLINE if node.actual[0] == "op" else _theme.NODE_OUTLINE_ALT

    def _set_node_style(self, key: str, *, outline: str, width: int) -> None:
        self.canvas.itemconfigure(f"shape-{key}", outline=outline, width=width)

    def _on_canvas_click(self, _event) -> None:
        if not self.canvas.find_withtag("current"):
            self.asm_listbox.selection_clear(0, tk.END)
            self._clear_selection_state()
            self._show_default_summary()

    def _clear_selection_state(self) -> None:
        hide_all_glows(self.canvas)
        for node in self.visual_nodes:
            self._set_node_style(node.key, outline=self._default_outline(node), width=2)
        self._selected_key = None
        self._highlighted_keys.clear()
        self._related_keys.clear()
        self._muted_keys.clear()

    def _apply_selection_state(
        self,
        *,
        selected_keys: set[str],
        related_keys: set[str],
    ) -> None:
        self._clear_selection_state()
        if not selected_keys and not related_keys:
            return
        self._selected_key = next(iter(selected_keys)) if len(selected_keys) == 1 else None
        self._related_keys = set(related_keys)
        self._highlighted_keys = set(selected_keys | related_keys)
        self._muted_keys = {
            node.key for node in self.visual_nodes if node.key not in self._highlighted_keys
        }
        for key in self._muted_keys:
            self._set_node_style(key, outline=_theme.TEXT_MUTED, width=1)
        for key in related_keys:
            self._set_node_style(key, outline=_theme.EDGE_RELATED, width=3)
            show_node_glow(self.canvas, key, _theme.RELATED_GLOW)
        for key in selected_keys:
            self._set_node_style(key, outline=_theme.SELECTION_OUTLINE, width=4)
            show_node_glow(self.canvas, key, _theme.SELECTION_GLOW)

    def _related_keys_for_node(self, node: VisualNode) -> set[str]:
        related_actuals: set[tuple[str, int]] = set()
        if node.actual[0] == "op":
            op = self.op_by_id[node.actual[1]]
            related_actuals.update(("varnode", varnode_id) for varnode_id in op.input_varnode_ids)
            if op.output_varnode_id is not None:
                related_actuals.add(("varnode", op.output_varnode_id))
        else:
            varnode = self.varnode_by_id[node.actual[1]]
            if varnode.defining_op_id is not None:
                related_actuals.add(("op", varnode.defining_op_id))
            related_actuals.update(("op", op_id) for op_id in varnode.use_op_ids)
        return {
            visual_node.key
            for visual_node in self.visual_nodes
            if visual_node.actual in related_actuals and visual_node.key != node.key
        }

    def _show_default_summary(self) -> None:
        self._set_inspector_text(
            summary_text(
                self.window_title,
                result=self.result,
                pcode=self.pcode,
                target_label=self.result_label,
                source_label=self.source_label,
                fallback_address=self._fallback_address(),
            )
        )

    def _assembly_selection_text(
        self,
        *,
        addresses: set[int],
        selected_op_ids: set[int],
        related_varnode_ids: set[int],
    ) -> str:
        addr = "\n".join(f"  - 0x{a:x}" for a in sorted(addresses))
        ops = "\n".join(
            f"  - op#{op.id}: {op.opcode}" for op in self.sorted_ops if op.id in selected_op_ids
        )
        vns = "\n".join(
            f"  - v{v.id}: {v.space}@0x{v.offset:x}"
            for v in self.pcode.varnodes
            if v.id in related_varnode_ids
        )
        return (
            f"Assembly selection\n\nAddresses:\n{addr or '  - none'}\n\n"
            f"Ops at selection:\n{ops or '  - none'}\n\n"
            f"Related varnodes:\n{vns or '  - none'}"
        )

    def _show_node(self, node: VisualNode) -> None:
        related_keys = self._related_keys_for_node(node)
        if node.actual[0] == "op":
            op = self.op_by_id[node.actual[1]]
            text = op_text(op, self.varnode_by_id, depth=node.depth)
            address = op.instruction_address
        else:
            varnode = self.varnode_by_id[node.actual[1]]
            text = varnode_text(varnode, self.op_by_id, depth=node.depth)
            address = (
                self.op_by_id[varnode.defining_op_id].instruction_address
                if varnode.defining_op_id is not None and varnode.defining_op_id in self.op_by_id
                else None
            )
        self._set_inspector_text(text)
        self._apply_selection_state(selected_keys={node.key}, related_keys=related_keys)
        if address is not None:
            self._select_asm_address(address, sync_graph=False)

    def _disassemble(self) -> list[tuple[int, str]]:
        return disassemble_instruction_addresses(
            self.result.enriched.instructions if self.result.enriched is not None else None
        )

    def _on_asm_select(self, _event) -> None:
        sel = self.asm_listbox.curselection()
        addresses = {self._disasm[i][0] for i in sel}
        selected_op_ids, related_varnode_ids = self._highlight_addresses(addresses)
        if not addresses:
            self._show_default_summary()
            return
        self._set_inspector_text(
            self._assembly_selection_text(
                addresses=addresses,
                selected_op_ids=selected_op_ids,
                related_varnode_ids=related_varnode_ids,
            )
        )

    def _highlight_addresses(self, addresses: set[int]) -> tuple[set[int], set[int]]:
        if not addresses:
            self._clear_selection_state()
            return set(), set()
        selected_op_ids: set[int] = set()
        selected_keys: set[str] = set()
        related_varnode_ids: set[int] = set()
        for node in self.visual_nodes:
            if node.actual[0] != "op":
                continue
            op = self.op_by_id[node.actual[1]]
            if op.instruction_address in addresses:
                selected_op_ids.add(op.id)
                selected_keys.add(node.key)
                related_varnode_ids.update(op.input_varnode_ids)
                if op.output_varnode_id is not None:
                    related_varnode_ids.add(op.output_varnode_id)
        related_keys: set[str] = set()
        for node in self.visual_nodes:
            if node.actual[0] == "varnode" and node.actual[1] in related_varnode_ids:
                related_keys.add(node.key)
        self._apply_selection_state(selected_keys=selected_keys, related_keys=related_keys)
        return selected_op_ids, related_varnode_ids

    def _select_asm_address(self, address: int, *, sync_graph: bool = True) -> None:
        self.asm_listbox.selection_clear(0, tk.END)
        for index, (addr, _) in enumerate(self._disasm):
            if addr == address:
                self.asm_listbox.selection_set(index)
                self.asm_listbox.see(index)
                break
        if sync_graph:
            _ = self._highlight_addresses({address})

    def _on_mouse_wheel(self, event) -> None:
        state = int(getattr(event, "state", 0))
        if state & 0x4:
            factor = 1.15 if event.delta > 0 else 1 / 1.15
            self._do_zoom(self._zoom * factor, event)
        elif state & 0x1:
            self.canvas.xview_scroll(int(-event.delta / 120), "units")
        else:
            self.canvas.yview_scroll(int(-event.delta / 120), "units")

    def _handle_button_scroll(self, event, *, zoom_in: bool) -> None:
        state = int(getattr(event, "state", 0))
        if state & 0x4:
            self._do_zoom(self._zoom * (1.15 if zoom_in else 1 / 1.15), event)
        elif state & 0x1:
            self.canvas.xview_scroll(-3 if zoom_in else 3, "units")
        else:
            self.canvas.yview_scroll(-3 if zoom_in else 3, "units")

    def _do_zoom(self, new_zoom: float, event=None) -> None:
        new_zoom = max(0.15, min(5.0, new_zoom))
        if abs(new_zoom - self._zoom) < 0.001:
            return
        ratio = new_zoom / self._zoom
        if event is not None and hasattr(event, "x"):
            widget_x, widget_y = event.x, event.y
        else:
            widget_x = self.canvas.winfo_width() / 2
            widget_y = self.canvas.winfo_height() / 2
        cx = self.canvas.canvasx(widget_x)
        cy = self.canvas.canvasy(widget_y)
        self.canvas.scale("all", 0, 0, ratio, ratio)
        self._rescale_arrowheads(new_zoom)
        new_w = self.virtual_width * new_zoom
        new_h = self.virtual_height * new_zoom
        self.canvas.configure(scrollregion=(0, 0, new_w, new_h))
        if new_w > 0:
            self.canvas.xview_moveto((cx * ratio - widget_x) / new_w)
        if new_h > 0:
            self.canvas.yview_moveto((cy * ratio - widget_y) / new_h)
        self._zoom = new_zoom

    def reset_view(self) -> None:
        """Reset zoom to the initial level and re-center the viewport."""
        self._do_zoom(self._INITIAL_ZOOM)
        w = self.virtual_width * self._zoom
        x_center = max(0.0, (w / 2.0 - self.canvas.winfo_width() / 2.0) / max(w, 1))
        self.canvas.xview_moveto(x_center)
        self.canvas.yview_moveto(0.0)

    def _rescale_arrowheads(self, zoom: float) -> None:
        """Rescale arrowheads for all edge tags; clamps to readable MIN/MAX range."""
        for tag, base in self._ARROW_SHAPES.items():
            clamped = _clamp_arrowshape(base, zoom, self._ARROWSHAPE_MIN, self._ARROWSHAPE_MAX)
            self.canvas.itemconfigure(tag, arrowshape=clamped)


__all__ = ["XrayWindow"]
