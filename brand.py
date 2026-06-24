"""
GRU953 brand tokens for the MarkItDown Converter UI.
Derived from GRU953-Brand-Package-v2.0 colour-tokens.json and Typography.md.
"""

import ctypes
import os
import sys
from pathlib import Path


def _resource(rel: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
    return base / rel


def load_font(rel_path: str) -> bool:
    """Load a .ttf font file into the GDI registry so tkinter can use it."""
    path = _resource(rel_path)
    if not path.exists():
        return False
    try:
        FR_PRIVATE = 0x10
        data = path.read_bytes()
        buf  = ctypes.create_string_buffer(data)
        count = ctypes.c_uint32(0)
        ctypes.windll.gdi32.AddFontMemResourceEx(
            buf, ctypes.c_uint32(len(data)), None, ctypes.byref(count)
        )
        return count.value > 0
    except Exception:
        return False


def load_brand_fonts():
    """Register all GRU953 brand fonts."""
    fonts = [
        "assets/Figtree.ttf",
        "assets/HindSiliguri-Regular.ttf",
        "assets/HindSiliguri-SemiBold.ttf",
        "assets/HindSiliguri-Bold.ttf",
        "assets/TiroBangla.ttf",
    ]
    for f in fonts:
        load_font(f)


# ── Colour tokens ─────────────────────────────────────────────────────────────
# (light_value, dark_value) pairs matching GRU953 colour-tokens.json

COLORS = {
    # Backgrounds
    "bg":            ("#FFFFFF",  "#06302B"),
    "surface":       ("#F3F7F5",  "#0A4A41"),
    "surface_high":  ("#E8F2EF",  "#0E5549"),
    # Borders
    "border":        ("#E3E9E6",  "#13564C"),
    "border_focus":  ("#0E8C7A",  "#3FBBA5"),
    # Brand / interactive
    "primary":       ("#0E8C7A",  "#3FBBA5"),
    "primary_hover": ("#0A6E60",  "#0E8C7A"),
    "primary_text":  ("#FFFFFF",  "#FFFFFF"),
    # Text
    "text":          ("#0B1A18",  "#EEF9F7"),
    "text_muted":    ("#5A6E6A",  "#869490"),
    "text_on_brand": ("#FFFFFF",  "#FFFFFF"),
    # Status
    "success":       ("#2E9E60",  "#4AC97A"),
    "error":         ("#D63A3A",  "#F08080"),
    "warning":       ("#C97A00",  "#F0B840"),
    # Tab bar
    "tab_active_bg": ("#0E8C7A",  "#3FBBA5"),
    "tab_active_fg": ("#FFFFFF",  "#06302B"),
    "tab_idle_bg":   ("#E8F2EF",  "#0A4A41"),
    "tab_idle_fg":   ("#0B1A18",  "#86B8B0"),
}


def c(name: str, mode: str = "light") -> str:
    """Return a hex colour string for a given token and appearance mode."""
    pair = COLORS.get(name, ("#000000", "#FFFFFF"))
    return pair[0] if mode == "light" else pair[1]


def ctk_pair(name: str):
    """Return a (light, dark) tuple suitable for CTk's fg_color= argument."""
    pair = COLORS.get(name, ("#000000", "#FFFFFF"))
    return list(pair)


# ── Font names (after load_brand_fonts() is called) ──────────────────────────
FONT_UI_EN = "Figtree"
FONT_UI_BN = "Hind Siliguri"
FONT_BODY   = "Tiro Bangla"
FONT_MONO   = "Consolas"


def app_icon_path() -> str:
    return str(_resource("assets/app_icon.png"))


def mark_path() -> str:
    return str(_resource("assets/mark_primary.png"))
