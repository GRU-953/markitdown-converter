"""
MarkItDown Converter — GRU-953
Drag-drop batch conversion · OCR (EN+BN) · Bijoy→Unicode · Dark mode
"""

import os
import sys
import threading
from pathlib import Path
from tkinter import filedialog, messagebox
import tkinter as tk

# In PyInstaller --onefile bundled exe, hide the console window immediately.
# We use --console (not --windowed) to avoid a bootloader bug on Python 3.14,
# then suppress the console programmatically so users never see it.
if hasattr(sys, "_MEIPASS"):
    try:
        import ctypes as _ctypes
        _hwnd = _ctypes.windll.kernel32.GetConsoleWindow()
        if _hwnd:
            _ctypes.windll.user32.ShowWindow(_hwnd, 0)   # SW_HIDE = 0
    except Exception:
        pass

import customtkinter as ctk
from PIL import Image as PILImage
from tkinterdnd2 import DND_FILES, TkinterDnD

import brand
from bijoy_unicode import convert_bijoy_to_unicode, detect_script, is_bijoy
from ocr_engine import LANG_CODES, ocr_image, tesseract_available
from utils import parse_dnd_paths

_mid = None

def _init_markitdown():
    global _mid
    try:
        from markitdown import MarkItDown
        _mid = MarkItDown()
    except Exception:
        pass

try:
    import markdown as _md_lib
    _HAS_MD = True
except ImportError:
    _HAS_MD = False

try:
    from tkhtmlview import HTMLScrolledText as _HTMLText
    _HAS_HTML = True
except ImportError:
    _HAS_HTML = False

brand.load_brand_fonts()
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("green")

P = brand.ctk_pair   # P("primary") -> [light_hex, dark_hex]

_STATUS_ICON  = {"pending": "◉", "done": "✓", "error": "✗"}
_STATUS_COLOR = {
    "pending": P("text_muted"),
    "done":    P("success"),
    "error":   P("error"),
}


# ─────────────────────────────────────────────────────────── FileRow widget ──

class FileRow(ctk.CTkFrame):
    """One row in the file list."""

    def __init__(self, parent, filename, idx, on_select, on_remove, **kw):
        super().__init__(parent, height=36, fg_color=P("surface"),
                         corner_radius=6, **kw)
        self.grid_columnconfigure(1, weight=1)
        self._idx = idx

        self._status_lbl = ctk.CTkLabel(
            self, text="◉", width=22,
            font=(brand.FONT_UI_EN, 14),
            text_color=P("text_muted"),
        )
        self._status_lbl.grid(row=0, column=0, padx=(6, 2), pady=4)

        short = (filename[:34] + "…") if len(filename) > 35 else filename
        name_lbl = ctk.CTkLabel(
            self, text=short, anchor="w",
            font=(brand.FONT_UI_EN, 12),
            text_color=P("text"),
        )
        name_lbl.grid(row=0, column=1, sticky="ew", padx=(2, 4), pady=4)
        name_lbl.bind("<Button-1>", lambda _e: on_select(idx))
        self._status_lbl.bind("<Button-1>", lambda _e: on_select(idx))

        ctk.CTkButton(
            self, text="✕", width=26, height=24,
            fg_color="transparent", hover_color=P("surface_high"),
            text_color=P("text_muted"),
            font=(brand.FONT_UI_EN, 12),
            command=lambda: on_remove(idx),
        ).grid(row=0, column=2, padx=(0, 4), pady=4)

    def set_status(self, status: str, selected: bool = False):
        self._status_lbl.configure(
            text=_STATUS_ICON.get(status, "◉"),
            text_color=_STATUS_COLOR.get(status, P("text_muted")),
        )
        self.configure(fg_color=P("surface_high") if selected else P("surface"))


# ─────────────────────────────────────────────────────────────── Main App ────

class App(TkinterDnD.Tk):

    def __init__(self):
        try:
            super().__init__()
            self._dnd_active = True
        except Exception:
            # TkinterDnD native lib failed in bundle; tkinter.Tk.__init__
            # already ran so the window exists — continue without DnD
            self._dnd_active = False
        self._files   = []    # list of {"path", "name", "status", "output"}
        self._selected = -1
        self._rows: list = []
        self._ocr_path = None
        self._build_ui()

    # ──────────────────────────────────────────────────────── window setup ──

    def _build_ui(self):
        self.title("MarkItDown Converter")
        self.minsize(960, 640)
        self.geometry("1100x720")
        try:
            from PIL import Image as _I
            _ico = _I.open(brand.app_icon_path())
            _ph  = ctk.CTkImage(_ico, size=(32, 32))
            # Store reference so GC doesn't collect it
            self._icon_img = _ph
            self.iconphoto(True, tk.PhotoImage(file=brand.app_icon_path()))
        except Exception:
            pass

        root = ctk.CTkFrame(self, fg_color=P("bg"), corner_radius=0)
        root.pack(fill="both", expand=True)
        self._build_header(root)
        self._build_status_bar(root)   # must be packed before tabs (side="bottom")
        self._build_tabs(root)
        self.bind("<Control-o>", lambda _e: self._add_files())
        self.bind("<Control-O>", lambda _e: self._add_files())
        self.bind("<Control-Return>", lambda _e: self._convert_all())

    # ──────────────────────────────────────────────────────────── header ────

    def _build_header(self, parent):
        hdr = ctk.CTkFrame(parent, height=58, fg_color=P("surface"), corner_radius=0)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        # Logo mark
        try:
            img = PILImage.open(brand.mark_path()).resize((34, 34), PILImage.LANCZOS)
            logo = ctk.CTkImage(img, size=(34, 34))
            ctk.CTkLabel(hdr, image=logo, text="").pack(side="left", padx=(14, 6))
            self._logo = logo   # keep ref
        except Exception:
            ctk.CTkLabel(hdr, text="◈", font=(brand.FONT_UI_EN, 22),
                         text_color=P("primary")).pack(side="left", padx=(14, 6))

        ctk.CTkLabel(hdr, text="MarkItDown Converter",
                     font=(brand.FONT_UI_EN, 17, "bold"),
                     text_color=P("text")).pack(side="left")
        ctk.CTkLabel(hdr, text="  by GRU-953",
                     font=(brand.FONT_UI_EN, 11),
                     text_color=P("text_muted")).pack(side="left")

        # Mode toggle (right-aligned)
        self._mode_seg = ctk.CTkSegmentedButton(
            hdr, values=["Light", "System", "Dark"],
            command=lambda v: ctk.set_appearance_mode(v),
            height=30, font=(brand.FONT_UI_EN, 12),
            fg_color=P("surface_high"),
            selected_color=P("primary"),
            selected_hover_color=P("primary_hover"),
            unselected_color=P("surface_high"),
            unselected_hover_color=P("border"),
            text_color=P("text"),
        )
        self._mode_seg.set("System")
        self._mode_seg.pack(side="right", padx=(0, 14))
        ctk.CTkLabel(hdr, text="Mode  ",
                     font=(brand.FONT_UI_EN, 12),
                     text_color=P("text_muted")).pack(side="right")

    # ──────────────────────────────────────────────────────── status bar ────

    def _build_status_bar(self, parent):
        bar = ctk.CTkFrame(parent, height=24, fg_color=P("surface"), corner_radius=0)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)
        self._status_lbl = ctk.CTkLabel(
            bar, text="", anchor="w",
            font=(brand.FONT_UI_EN, 11),
            text_color=P("text_muted"),
        )
        self._status_lbl.pack(side="left", padx=12)

    def _set_status(self, msg: str, token: str = "text_muted"):
        self._status_lbl.configure(text=msg, text_color=P(token))

    # ──────────────────────────────────────────────────────────── tabs ──────

    def _build_tabs(self, parent):
        self._tabview = ctk.CTkTabview(
            parent,
            fg_color=P("bg"),
            segmented_button_fg_color=P("surface"),
            segmented_button_selected_color=P("primary"),
            segmented_button_selected_hover_color=P("primary_hover"),
            segmented_button_unselected_color=P("surface"),
            segmented_button_unselected_hover_color=P("surface_high"),
            text_color=P("text"),
            text_color_disabled=P("text_muted"),
            border_color=P("border"),
        )
        self._tabview.pack(fill="both", expand=True, padx=12, pady=(4, 12))
        for name in ("Convert Files", "OCR", "Bijoy → Unicode"):
            self._tabview.add(name)
        self._build_tab_convert(self._tabview.tab("Convert Files"))
        self._build_tab_ocr(self._tabview.tab("OCR"))
        self._build_tab_bijoy(self._tabview.tab("Bijoy → Unicode"))

    # ──────────────────────────────────────────── Tab 1: Convert Files ──────

    def _build_tab_convert(self, tab):
        tab.grid_columnconfigure(0, weight=2, minsize=270)
        tab.grid_columnconfigure(1, weight=3)
        tab.grid_rowconfigure(0, weight=1)

        # ── Left panel ──────────────────────────────────────────────────────
        left = ctk.CTkFrame(tab, fg_color=P("surface"), corner_radius=8)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        left.grid_rowconfigure(1, weight=1)
        left.grid_columnconfigure(0, weight=1)

        # Drop zone
        dz = ctk.CTkFrame(left, height=78, fg_color=P("surface_high"),
                          corner_radius=8, border_width=2, border_color=P("border"))
        dz.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 6))
        dz.grid_propagate(False)
        dz.grid_columnconfigure(0, weight=1)
        dz.grid_rowconfigure(0, weight=1)
        _dz_lbl = ctk.CTkLabel(
            dz,
            text="⊕   Drop files here, or click to add" if self._dnd_active else "⊕   Click to add files",
            font=(brand.FONT_UI_EN, 13), text_color=P("text_muted"),
        )
        _dz_lbl.grid(row=0)
        for w in (dz, _dz_lbl):
            w.bind("<Button-1>", lambda _e: self._add_files())
        if self._dnd_active:
            dz.drop_target_register(DND_FILES)
            dz.dnd_bind("<<Drop>>", self._on_drop)

        # File list
        self._file_list = ctk.CTkScrollableFrame(
            left, fg_color=P("surface"), corner_radius=0,
        )
        self._file_list.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 6))
        self._file_list.grid_columnconfigure(0, weight=1)

        self._empty_lbl = ctk.CTkLabel(
            self._file_list,
            text="No files yet.\nDrop files above or click  ⊕",
            font=(brand.FONT_UI_EN, 12), text_color=P("text_muted"),
        )
        self._empty_lbl.grid(row=0, column=0, pady=28)

        # Buttons
        br = ctk.CTkFrame(left, fg_color="transparent")
        br.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))
        br.grid_columnconfigure((0, 1, 2, 3), weight=1)
        for col, (txt, cmd, fg) in enumerate([
            ("+ Add Files",  self._add_files,   P("primary")),
            ("Convert All",  self._convert_all, P("primary")),
            ("Save All",     self._save_all_md, P("surface_high")),
            ("Clear",        self._clear_files, P("surface_high")),
        ]):
            btn = ctk.CTkButton(
                br, text=txt, height=34,
                fg_color=fg,
                hover_color=P("primary_hover") if fg == P("primary") else P("border"),
                text_color=P("primary_text") if fg == P("primary") else P("text"),
                font=(brand.FONT_UI_EN, 12),
                command=cmd,
            )
            btn.grid(row=0, column=col,
                     padx=(0 if col == 0 else 3, 3 if col < 3 else 0),
                     sticky="ew")
            if txt == "Save All":
                self._save_all_btn = btn
                btn.configure(state="disabled")

        # ── Right panel (output) ─────────────────────────────────────────────
        right = ctk.CTkFrame(tab, fg_color=P("surface"), corner_radius=8)
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        right.grid_rowconfigure(0, weight=1)
        right.grid_columnconfigure(0, weight=1)

        out_tv = ctk.CTkTabview(
            right,
            fg_color=P("bg"),
            segmented_button_fg_color=P("surface_high"),
            segmented_button_selected_color=P("primary"),
            segmented_button_selected_hover_color=P("primary_hover"),
            segmented_button_unselected_color=P("surface_high"),
            border_color=P("border"),
        )
        out_tv.grid(row=0, column=0, sticky="nsew", padx=8, pady=(8, 0))
        out_tv.add("Raw MD")
        out_tv.add("Preview")
        self._out_tv = out_tv

        self._raw_text = ctk.CTkTextbox(
            out_tv.tab("Raw MD"), wrap="word",
            font=(brand.FONT_MONO, 12),
            fg_color=P("bg"), text_color=P("text"),
            border_color=P("border"), border_width=1,
        )
        self._raw_text.pack(fill="both", expand=True, padx=4, pady=4)

        prev_tab = out_tv.tab("Preview")
        self._html_preview = False
        if _HAS_HTML:
            try:
                self._preview = _HTMLText(
                    prev_tab, html="<p></p>",
                    background="#FFFFFF", padx=8, pady=8,
                )
                self._preview.pack(fill="both", expand=True, padx=4, pady=4)
                self._html_preview = True
            except Exception:
                pass
        if not self._html_preview:
            self._preview = ctk.CTkTextbox(
                prev_tab, wrap="word",
                font=(brand.FONT_UI_EN, 12),
                fg_color=P("bg"), text_color=P("text"),
            )
            self._preview.pack(fill="both", expand=True, padx=4, pady=4)
        out_tv.configure(command=self._on_out_tab_switch)

        bot = ctk.CTkFrame(right, fg_color="transparent")
        bot.grid(row=1, column=0, sticky="ew", padx=8, pady=(4, 8))
        bot.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(
            bot, text="Copy", height=30,
            fg_color=P("surface_high"), hover_color=P("border"),
            text_color=P("text"), font=(brand.FONT_UI_EN, 12),
            command=lambda: self._copy(self._raw_text.get("1.0", "end")),
        ).grid(row=0, column=0, padx=(0, 4), sticky="ew")
        ctk.CTkButton(
            bot, text="Save .md", height=30,
            fg_color=P("primary"), hover_color=P("primary_hover"),
            text_color=P("primary_text"), font=(brand.FONT_UI_EN, 12),
            command=self._save_md,
        ).grid(row=0, column=1, padx=(4, 0), sticky="ew")

    def _on_out_tab_switch(self):
        if self._out_tv.get() == "Preview":
            self._refresh_preview()

    def _refresh_preview(self):
        md = self._raw_text.get("1.0", "end").strip()
        if not md:
            return
        if _HAS_MD and self._html_preview:
            html = _md_lib.markdown(md, extensions=["tables", "fenced_code"])
            self._preview.set_html(
                f"<html><body style='font-family:sans-serif;padding:8px'>"
                f"{html}</body></html>"
            )
        else:
            self._preview.configure(state="normal")
            self._preview.delete("1.0", "end")
            self._preview.insert("1.0", md)
            self._preview.configure(state="disabled")

    # ──────────────────────────────────────────────── Tab 2: OCR ─────────────

    def _build_tab_ocr(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(2, weight=1)

        # Image drop zone
        dz = ctk.CTkFrame(tab, height=86, fg_color=P("surface_high"),
                          corner_radius=8, border_width=2, border_color=P("border"))
        dz.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        dz.grid_propagate(False)
        dz.grid_columnconfigure(0, weight=1)
        dz.grid_rowconfigure(0, weight=1)
        self._ocr_dz_lbl = ctk.CTkLabel(
            dz,
            text=("⊕   Drop an image here  (PNG · JPG · TIFF · BMP)\nor click to browse"
                  if self._dnd_active else
                  "⊕   Click to browse for an image  (PNG · JPG · TIFF · BMP)"),
            font=(brand.FONT_UI_EN, 13), text_color=P("text_muted"),
        )
        self._ocr_dz_lbl.grid(row=0)
        for w in (dz, self._ocr_dz_lbl):
            w.bind("<Button-1>", lambda _e: self._ocr_pick())
        if self._dnd_active:
            dz.drop_target_register(DND_FILES)
            dz.dnd_bind("<<Drop>>", self._ocr_drop)

        # Options row
        opts = ctk.CTkFrame(tab, fg_color="transparent")
        opts.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        opts.grid_columnconfigure(2, weight=1)

        ctk.CTkLabel(opts, text="Language:",
                     font=(brand.FONT_UI_EN, 13),
                     text_color=P("text")).grid(row=0, column=0, padx=(0, 8))

        self._ocr_lang = ctk.CTkSegmentedButton(
            opts, values=["English", "বাংলা", "Both"],
            font=(brand.FONT_UI_BN, 13),
            fg_color=P("surface_high"),
            selected_color=P("primary"),
            selected_hover_color=P("primary_hover"),
            unselected_color=P("surface_high"),
            text_color=P("text"),
        )
        self._ocr_lang.set("English")
        self._ocr_lang.grid(row=0, column=1, padx=(0, 16))

        self._bijoy_auto = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            opts, text="Auto-convert Bijoy → Unicode",
            variable=self._bijoy_auto,
            font=(brand.FONT_UI_EN, 12),
            fg_color=P("primary"), hover_color=P("primary_hover"),
            text_color=P("text"),
        ).grid(row=0, column=2)

        ctk.CTkButton(
            opts, text="Extract Text", height=34, width=130,
            fg_color=P("primary"), hover_color=P("primary_hover"),
            text_color=P("primary_text"), font=(brand.FONT_UI_EN, 12),
            command=self._ocr_run,
        ).grid(row=0, column=3, padx=(12, 0))

        # Output
        self._ocr_out = ctk.CTkTextbox(
            tab, wrap="word",
            font=(brand.FONT_UI_BN, 13),
            fg_color=P("bg"), text_color=P("text"),
            border_color=P("border"), border_width=1,
        )
        self._ocr_out.grid(row=2, column=0, sticky="nsew")

        bot = ctk.CTkFrame(tab, fg_color="transparent")
        bot.grid(row=3, column=0, sticky="ew", pady=(6, 0))
        bot.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(
            bot, text="Copy", height=30,
            fg_color=P("surface_high"), hover_color=P("border"),
            text_color=P("text"), font=(brand.FONT_UI_EN, 12),
            command=lambda: self._copy(self._ocr_out.get("1.0", "end")),
        ).grid(row=0, column=0, padx=(0, 4), sticky="ew")
        ctk.CTkButton(
            bot, text="Save .txt", height=30,
            fg_color=P("primary"), hover_color=P("primary_hover"),
            text_color=P("primary_text"), font=(brand.FONT_UI_EN, 12),
            command=lambda: self._save_txt(self._ocr_out.get("1.0", "end")),
        ).grid(row=0, column=1, padx=(4, 0), sticky="ew")

    # ──────────────────────────────────────── Tab 3: Bijoy → Unicode ─────────

    def _build_tab_bijoy(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=2)
        tab.grid_rowconfigure(4, weight=2)

        ctk.CTkLabel(tab, text="Input — paste Bijoy / SutonnyMJ text below:",
                     font=(brand.FONT_UI_EN, 13), text_color=P("text"),
                     anchor="w").grid(row=0, column=0, sticky="ew", pady=(0, 4))

        self._bj_in = ctk.CTkTextbox(
            tab, wrap="word",
            font=(brand.FONT_UI_BN, 13),
            fg_color=P("surface"), text_color=P("text"),
            border_color=P("border"), border_width=1,
        )
        self._bj_in.grid(row=1, column=0, sticky="nsew", pady=(0, 6))
        self._bj_in.bind("<KeyRelease>", self._bj_detect)

        mid = ctk.CTkFrame(tab, fg_color="transparent")
        mid.grid(row=2, column=0, sticky="ew", pady=(0, 6))
        mid.grid_columnconfigure(0, weight=1)

        self._bj_detect_lbl = ctk.CTkLabel(
            mid, text="Type or paste text above to auto-detect script.",
            font=(brand.FONT_UI_EN, 12), text_color=P("text_muted"), anchor="w",
        )
        self._bj_detect_lbl.grid(row=0, column=0, sticky="ew")

        ctk.CTkButton(
            mid, text="Convert  ↓", height=36, width=130,
            fg_color=P("primary"), hover_color=P("primary_hover"),
            text_color=P("primary_text"), font=(brand.FONT_UI_EN, 13),
            command=self._bj_convert,
        ).grid(row=0, column=1, padx=(8, 0))

        ctk.CTkLabel(tab, text="Output — Unicode Bengali:",
                     font=(brand.FONT_UI_EN, 13), text_color=P("text"),
                     anchor="w").grid(row=3, column=0, sticky="ew", pady=(0, 4))

        self._bj_out = ctk.CTkTextbox(
            tab, wrap="word",
            font=(brand.FONT_UI_BN, 13),
            fg_color=P("surface"), text_color=P("text"),
            border_color=P("border"), border_width=1,
        )
        self._bj_out.grid(row=4, column=0, sticky="nsew")

        bot = ctk.CTkFrame(tab, fg_color="transparent")
        bot.grid(row=5, column=0, sticky="ew", pady=(6, 0))
        bot.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(
            bot, text="Copy", height=30,
            fg_color=P("surface_high"), hover_color=P("border"),
            text_color=P("text"), font=(brand.FONT_UI_EN, 12),
            command=lambda: self._copy(self._bj_out.get("1.0", "end")),
        ).grid(row=0, column=0, padx=(0, 4), sticky="ew")
        ctk.CTkButton(
            bot, text="Save .txt", height=30,
            fg_color=P("primary"), hover_color=P("primary_hover"),
            text_color=P("primary_text"), font=(brand.FONT_UI_EN, 12),
            command=lambda: self._save_txt(self._bj_out.get("1.0", "end")),
        ).grid(row=0, column=1, padx=(4, 0), sticky="ew")

    # ──────────────────────────────────────────── File list logic ─────────────

    def _on_drop(self, event):
        for p in parse_dnd_paths(event.data):
            self._add_path(p)

    def _add_files(self):
        paths = filedialog.askopenfilenames(
            title="Select files to convert",
            filetypes=[
                ("Supported files",
                 "*.pdf *.docx *.xlsx *.pptx *.html *.htm *.csv "
                 "*.json *.xml *.zip *.png *.jpg *.jpeg *.gif "
                 "*.bmp *.tiff *.wav *.mp3"),
                ("All files", "*.*"),
            ],
        )
        for p in paths:
            self._add_path(p)

    def _add_path(self, path: str):
        p = Path(path)
        if not p.exists():
            return
        if any(f["path"] == str(p) for f in self._files):
            return
        self._files.append({
            "path": str(p), "name": p.name,
            "status": "pending", "output": "",
        })
        self._refresh_list()

    def _refresh_list(self):
        for row in self._rows:
            row.destroy()
        self._rows.clear()

        if not self._files:
            self._empty_lbl.grid(row=0, column=0, pady=28)
            return

        self._empty_lbl.grid_forget()
        for i, f in enumerate(self._files):
            row = FileRow(
                self._file_list, f["name"], i,
                on_select=self._on_select,
                on_remove=self._remove_file,
            )
            row.grid(row=i, column=0, sticky="ew", padx=0, pady=(0, 2))
            row.set_status(f["status"], selected=(i == self._selected))
            self._rows.append(row)

    def _on_select(self, idx: int):
        self._selected = idx
        for i, row in enumerate(self._rows):
            row.set_status(self._files[i]["status"], selected=(i == idx))
        self._set_raw(self._files[idx]["output"])

    def _remove_file(self, idx: int):
        self._files.pop(idx)
        if self._selected >= len(self._files):
            self._selected = len(self._files) - 1
        self._refresh_list()
        if self._selected >= 0:
            self._set_raw(self._files[self._selected]["output"])
        else:
            self._set_raw("")

    def _clear_files(self):
        self._files.clear()
        self._selected = -1
        self._rows.clear()
        self._refresh_list()
        self._set_raw("")
        self._save_all_btn.configure(state="disabled")
        if _mid is not None:
            self._set_status("Ready")

    def _set_raw(self, text: str):
        self._raw_text.configure(state="normal")
        self._raw_text.delete("1.0", "end")
        if text:
            self._raw_text.insert("1.0", text)

    def _convert_all(self):
        if not self._files:
            messagebox.showinfo("No Files", "Add files first.")
            return
        if _mid is None:
            messagebox.showinfo(
                "Please wait",
                "MarkItDown is still initializing.\nPlease try again in a moment.",
            )
            return
        total = len(self._files)
        self._set_status(f"Converting… (0 / {total} done)")
        self._save_all_btn.configure(state="disabled")
        for f in self._files:
            f["status"] = "pending"
        self._refresh_list()
        for i in range(total):
            threading.Thread(
                target=self._convert_one, args=(i,), daemon=True
            ).start()

    def _convert_one(self, idx: int):
        f = self._files[idx]
        try:
            result  = _mid.convert(f["path"])
            f["output"] = result.text_content or ""
            f["status"]  = "done"
        except Exception as exc:
            f["output"] = f"Conversion error:\n{exc}"
            f["status"]  = "error"
        self.after(0, self._refresh_list)
        self.after(0, self._update_convert_status)
        if self._selected in (-1, idx):
            self.after(0, lambda: self._on_select(idx))

    def _update_convert_status(self):
        done    = sum(1 for f in self._files if f["status"] == "done")
        errors  = sum(1 for f in self._files if f["status"] == "error")
        pending = sum(1 for f in self._files if f["status"] == "pending")
        total   = len(self._files)
        if pending > 0:
            self._set_status(f"Converting… ({done + errors} / {total} done)")
        else:
            if errors and done == 0:
                self._set_status(f"All {errors} file{'s' if errors > 1 else ''} failed", "error")
            elif errors:
                self._set_status(
                    f"Done — {done} converted, {errors} error{'s' if errors > 1 else ''}",
                    "warning",
                )
            else:
                self._set_status(f"Done — {done} file{'s' if done > 1 else ''} converted", "success")
        self._save_all_btn.configure(state="normal" if done > 0 else "disabled")

    def _save_all_md(self):
        done_files = [f for f in self._files if f["status"] == "done"]
        if not done_files:
            messagebox.showinfo("Nothing to save", "Convert files first.")
            return
        folder = filedialog.askdirectory(title="Choose output folder")
        if not folder:
            return
        out_dir = Path(folder)
        saved = 0
        for f in done_files:
            stem = Path(f["name"]).stem
            dest = out_dir / (stem + ".md")
            counter = 1
            while dest.exists():
                dest = out_dir / f"{stem}_{counter}.md"
                counter += 1
            dest.write_text(f["output"], encoding="utf-8")
            saved += 1
        self._set_status(
            f"Saved {saved} file{'s' if saved > 1 else ''} → {out_dir.name}/",
            "success",
        )

    # ──────────────────────────────────────────────────── OCR logic ──────────

    def _ocr_drop(self, event):
        paths = parse_dnd_paths(event.data)
        if paths:
            self._ocr_set(paths[0])

    def _ocr_pick(self):
        path = filedialog.askopenfilename(
            title="Select image for OCR",
            filetypes=[
                ("Images", "*.png *.jpg *.jpeg *.bmp *.tiff *.gif *.webp"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self._ocr_set(path)

    def _ocr_set(self, path: str):
        self._ocr_path = path
        self._ocr_dz_lbl.configure(
            text=f"✓   {Path(path).name}",
            text_color=P("success"),
        )

    def _ocr_run(self):
        if not self._ocr_path:
            messagebox.showinfo("No Image", "Drop or select an image first.")
            return
        if not tesseract_available():
            messagebox.showerror(
                "Tesseract not found",
                "Tesseract OCR is not installed or not on PATH.\n"
                "Download: github.com/UB-Mannheim/tesseract/wiki",
            )
            return
        lang = self._ocr_lang.get()
        auto = self._bijoy_auto.get()
        self._ocr_out.configure(state="normal")
        self._ocr_out.delete("1.0", "end")
        self._ocr_out.insert("1.0", "Running OCR…")
        self._ocr_out.configure(state="disabled")
        threading.Thread(
            target=self._ocr_thread, args=(self._ocr_path, lang, auto), daemon=True
        ).start()

    def _ocr_thread(self, path: str, lang: str, auto_bijoy: bool):
        try:
            text = ocr_image(path, lang)
            if auto_bijoy and is_bijoy(text):
                text = convert_bijoy_to_unicode(text)
            self.after(0, lambda: self._ocr_show(text))
        except Exception as exc:
            self.after(0, lambda: self._ocr_show(f"OCR error:\n{exc}"))

    def _ocr_show(self, text: str):
        self._ocr_out.configure(state="normal")
        self._ocr_out.delete("1.0", "end")
        self._ocr_out.insert("1.0", text)

    # ──────────────────────────────────────────── Bijoy tab logic ────────────

    def _bj_detect(self, _event=None):
        text = self._bj_in.get("1.0", "end").strip()
        if not text:
            self._bj_detect_lbl.configure(
                text="Type or paste text above to auto-detect script.",
                text_color=P("text_muted"),
            )
            return
        script = detect_script(text[:300])
        _info = {
            "bijoy":      ("Bijoy / SutonnyMJ detected  ✓  —  ready to convert", P("success")),
            "unicode_bn": ("Unicode Bengali detected  —  no conversion needed", P("warning")),
            "latin":      ("Latin / English text detected", P("text_muted")),
            "other":      ("Script unrecognised", P("text_muted")),
        }
        lbl, col = _info.get(script, ("Script unrecognised", P("text_muted")))
        self._bj_detect_lbl.configure(text=lbl, text_color=col)

    def _bj_convert(self):
        text = self._bj_in.get("1.0", "end").strip()
        if not text:
            return
        result = convert_bijoy_to_unicode(text)
        self._bj_out.configure(state="normal")
        self._bj_out.delete("1.0", "end")
        self._bj_out.insert("1.0", result)

    # ──────────────────────────────────────────────── Shared helpers ──────────

    def _copy(self, text: str):
        text = text.strip()
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)
            self._set_status("Copied to clipboard")

    def _save_md(self):
        text = self._raw_text.get("1.0", "end").strip()
        if not text:
            messagebox.showinfo("Nothing to save", "Convert a file first.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".md",
            filetypes=[("Markdown", "*.md"), ("All files", "*.*")],
        )
        if path:
            Path(path).write_text(text, encoding="utf-8")
            self._set_status(f"Saved → {Path(path).name}")

    def _save_txt(self, text: str):
        text = text.strip()
        if not text:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text file", "*.txt"), ("All files", "*.*")],
        )
        if path:
            Path(path).write_text(text, encoding="utf-8")


# ─────────────────────────────────────────────────────────────────── entry ──

def main():
    app = App()
    app._set_status("Initializing MarkItDown…")

    def _bg():
        _init_markitdown()
        app.after(0, lambda: app._set_status("Ready"))

    # Defer until after the window is drawn to avoid GIL/import-lock deadlock.
    app.after(500, lambda: threading.Thread(target=_bg, daemon=True).start())
    app.mainloop()


if __name__ == "__main__":
    main()
