"""tkinter window for flatline.xray.
The flatline.xray API is alpha. XrayWindow subclasses ``tk.Tk``, so only one
instance should exist per process.
"""

from __future__ import annotations

try:
    import tkinter as tk
except ImportError as exc:  # pragma: no cover - platform dependent
    raise ImportError(
        "flatline-xray requires tkinter, which is missing from this Python "
        "installation.\n"
        "  Debian/Ubuntu:  sudo apt install python3-tk\n"
        "  Fedora:         sudo dnf install python3-tkinter\n"
        "  macOS Homebrew: brew install python-tk"
    ) from exc
import flatline.xray._theme as _theme
from flatline.xray._canvas import (
    draw_cross_edge,
    draw_depth_bands,
    draw_edges,
    draw_nodes,
)
from flatline.xray._inputs import disassemble_instruction_addresses
from flatline.xray._inspector import op_text, summary_text, varnode_text
from flatline.xray._layout import (
    VisualNode,
    assign_forest_positions,
    build_visual_forest,
    collect_visual_nodes,
    compute_canvas_size,
    measure_forest,
    node_size,
    sorted_ops,
)


class XrayWindow(tk.Tk):
    """Interactive pcode graph viewer for one decompiled function."""

    _root_gap = 100.0
    _child_gap = 26.0
    _level_gap = 122.0
    _top_margin = 90.0
    _bottom_margin = 120.0
    _side_margin = 100.0

    def __init__(
        self,
        title: str,
        result,
        *,
        request=None,
        source_label: str | None = None,
    ) -> None:
        super().__init__()
        self.window_title = title
        self.result = result
        self.request = request
        self.source_label = source_label
        self.pcode = self._require_pcode(result)
        self.op_by_id = {op.id: op for op in self.pcode.pcode_ops}
        self.varnode_by_id = {varnode.id: varnode for varnode in self.pcode.varnodes}
        self.sorted_ops = sorted_ops(self.pcode.pcode_ops)
        self.visual_roots, self._cross_edges = build_visual_forest(
            self.op_by_id,
            self.varnode_by_id,
            self.sorted_ops,
        )
        self.visual_nodes = collect_visual_nodes(self.visual_roots)
        self.max_depth = measure_forest(
            self.visual_roots,
            lambda node: node_size(node, self.op_by_id, self.varnode_by_id),
            child_gap=self._child_gap,
        )
        self.virtual_width, self.virtual_height = compute_canvas_size(
            self.visual_roots,
            self.max_depth,
            root_gap=self._root_gap,
            top_margin=self._top_margin,
            bottom_margin=self._bottom_margin,
            side_margin=self._side_margin,
            level_gap=self._level_gap,
        )
        assign_forest_positions(
            self.visual_roots,
            self.virtual_height,
            side_margin=self._side_margin,
            bottom_margin=self._bottom_margin,
            root_gap=self._root_gap,
            child_gap=self._child_gap,
            level_gap=self._level_gap,
        )
        self.result_label = self._result_label()
        self._node_by_key: dict[str, VisualNode] = {node.key: node for node in self.visual_nodes}
        self._disasm = self._disassemble()
        self._highlighted_keys: set[str] = set()
        title_suffix = f" - {self.result_label}" if self.result_label else ""
        self.title(f"{title}{title_suffix}")
        self.geometry("1500x980")
        self.configure(bg=_theme.BACKGROUND)
        header = tk.Frame(self, bg=_theme.BACKGROUND)
        header.pack(fill="x", padx=18, pady=(18, 10))
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
        body = tk.Frame(self, bg=_theme.BACKGROUND)
        body.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        sidebar = tk.Frame(body, bg=_theme.PANEL_BG, width=360)
        sidebar.pack(side="right", fill="y", padx=(16, 0))
        sidebar.pack_propagate(False)
        tk.Label(
            sidebar,
            text="Inspector",
            bg=_theme.PANEL_BG,
            fg=_theme.TEXT,
            font=_theme.PANEL_TITLE_FONT,
        ).pack(anchor="w", padx=14, pady=(14, 8))
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
        asm_frame = tk.Frame(body, bg=_theme.PANEL_BG, width=300)
        asm_frame.pack(side="left", fill="y", padx=(0, 16))
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
            font=_theme.BODY_FONT,
            selectmode=tk.EXTENDED,
            activestyle="none",
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
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
        canvas_frame.pack(side="left", fill="both", expand=True)
        self.canvas = tk.Canvas(canvas_frame, bg=_theme.CANVAS_BG, highlightthickness=0)
        x_scroll = tk.Scrollbar(canvas_frame, orient="horizontal", command=self.canvas.xview)
        y_scroll = tk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=x_scroll.set, yscrollcommand=y_scroll.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")
        canvas_frame.grid_rowconfigure(0, weight=1)
        canvas_frame.grid_columnconfigure(0, weight=1)
        self._zoom = 1.0
        draw_depth_bands(
            self.canvas,
            self.max_depth,
            self.virtual_width,
            self.virtual_height,
            self._bottom_margin,
            self._level_gap,
        )
        for root in self.visual_roots:
            draw_edges(self.canvas, root, self.op_by_id, self.varnode_by_id)
        for parent, child in self._cross_edges:
            draw_cross_edge(self.canvas, child, parent, self.op_by_id, self.varnode_by_id)
        for root in self.visual_roots:
            draw_nodes(self.canvas, root, self.op_by_id, self.varnode_by_id, self._show_node)
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
        self.canvas.xview_moveto(0.0)
        self.canvas.yview_moveto(0.0)
        self.canvas.bind("<MouseWheel>", self._on_mouse_wheel)
        self.canvas.bind(
            "<Button-4>",
            lambda event: (
                self._do_zoom(self._zoom * 1.15, event)
                if event.state & 0x4
                else self.canvas.xview_scroll(-3, "units")
                if event.state & 0x1
                else self.canvas.yview_scroll(-3, "units")
            ),
        )
        self.canvas.bind(
            "<Button-5>",
            lambda event: (
                self._do_zoom(self._zoom / 1.15, event)
                if event.state & 0x4
                else self.canvas.xview_scroll(3, "units")
                if event.state & 0x1
                else self.canvas.yview_scroll(3, "units")
            ),
        )
        try:
            self.canvas.bind("<Button-6>", lambda _event: self.canvas.xview_scroll(-3, "units"))
            self.canvas.bind("<Button-7>", lambda _event: self.canvas.xview_scroll(3, "units"))
        except tk.TclError:
            pass
        self.bind("<Control-equal>", lambda event: self._do_zoom(self._zoom * 1.15, event))
        self.bind(
            "<Control-minus>",
            lambda event: self._do_zoom(self._zoom / 1.15, event),
        )
        self.bind("<Control-0>", lambda _event: self._do_zoom(1.0))

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

    def _show_node(self, node: VisualNode) -> None:
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
        if address is not None:
            self._select_asm_address(address)

    def _disassemble(self) -> list[tuple[int, str]]:
        return disassemble_instruction_addresses(
            self.result.enriched.instructions if self.result.enriched is not None else None
        )

    def _on_asm_select(self, _event) -> None:
        sel = self.asm_listbox.curselection()
        addresses = {self._disasm[i][0] for i in sel}
        self._highlight_addresses(addresses)

    def _highlight_addresses(self, addresses: set[int]) -> None:
        for key in self._highlighted_keys:
            node = self._node_by_key[key]
            default = _theme.NODE_OUTLINE if node.actual[0] == "op" else _theme.NODE_OUTLINE_ALT
            self.canvas.itemconfigure(f"shape-{key}", outline=default, width=2)
        self._highlighted_keys.clear()
        if not addresses:
            return
        related_varnode_ids: set[int] = set()
        for node in self.visual_nodes:
            if node.actual[0] != "op":
                continue
            op = self.op_by_id[node.actual[1]]
            if op.instruction_address in addresses:
                self._highlighted_keys.add(node.key)
                related_varnode_ids.update(op.input_varnode_ids)
                if op.output_varnode_id is not None:
                    related_varnode_ids.add(op.output_varnode_id)
        for node in self.visual_nodes:
            if node.actual[0] == "varnode" and node.actual[1] in related_varnode_ids:
                self._highlighted_keys.add(node.key)
        for key in self._highlighted_keys:
            self.canvas.itemconfigure(f"shape-{key}", outline=_theme.SELECTION_OUTLINE, width=3)

    def _select_asm_address(self, address: int) -> None:
        self.asm_listbox.selection_clear(0, tk.END)
        for index, (addr, _) in enumerate(self._disasm):
            if addr == address:
                self.asm_listbox.selection_set(index)
                self.asm_listbox.see(index)
                break
        self._highlight_addresses({address})

    def _on_mouse_wheel(self, event) -> None:
        if event.state & 0x4:
            factor = 1.15 if event.delta > 0 else 1 / 1.15
            self._do_zoom(self._zoom * factor, event)
        elif event.state & 0x1:
            self.canvas.xview_scroll(int(-event.delta / 120), "units")
        else:
            self.canvas.yview_scroll(int(-event.delta / 120), "units")

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
        new_w = self.virtual_width * new_zoom
        new_h = self.virtual_height * new_zoom
        self.canvas.configure(scrollregion=(0, 0, new_w, new_h))
        if new_w > 0:
            self.canvas.xview_moveto((cx * ratio - widget_x) / new_w)
        if new_h > 0:
            self.canvas.yview_moveto((cy * ratio - widget_y) / new_h)
        self._zoom = new_zoom


__all__ = ["XrayWindow"]
