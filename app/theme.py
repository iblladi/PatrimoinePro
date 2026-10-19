"""Thème visuel : palette, typographie et styles ttk de l'application."""
from __future__ import annotations

from tkinter import ttk

from .utils import S

# ---------------------------------------------------------------- palette
BG = "#F2F5F9"
SURFACE = "#FFFFFF"
SURFACE_2 = "#F8FAFC"
SURFACE_3 = "#F1F5F9"
BORDER = "#E3E8EF"
BORDER_DARK = "#CBD5E1"

TEXT = "#0F172A"
TEXT_SOFT = "#334155"
MUTED = "#64748B"
FAINT = "#94A3B8"

PRIMARY = "#2563EB"
PRIMARY_DARK = "#1D4ED8"
PRIMARY_SOFT = "#EFF6FF"
PRIMARY_TINT = "#DBEAFE"

GREEN = "#10B981"
GREEN_DARK = "#047857"
GREEN_SOFT = "#ECFDF5"

AMBER = "#F59E0B"
AMBER_DARK = "#B45309"
AMBER_SOFT = "#FFFBEB"

RED = "#EF4444"
RED_DARK = "#B91C1C"
RED_SOFT = "#FEF2F2"

VIOLET = "#8B5CF6"
VIOLET_SOFT = "#F5F3FF"
CYAN = "#0891B2"

SIDEBAR = "#0B1220"
SIDEBAR_2 = "#111C2E"
SIDEBAR_HOVER = "#16233A"
SIDEBAR_ACTIVE = "#1C2C47"
SIDEBAR_TEXT = "#93A4BC"
SIDEBAR_MUTED = "#5B6B84"

CHART_GRID = "#EDF1F6"
CHART_FILL = "#E8F0FE"

TONES = {
    "green": (GREEN_DARK, GREEN_SOFT),
    "amber": (AMBER_DARK, AMBER_SOFT),
    "red": (RED_DARK, RED_SOFT),
    "blue": (PRIMARY_DARK, PRIMARY_SOFT),
    "violet": (VIOLET, VIOLET_SOFT),
    "muted": (MUTED, SURFACE_3),
}

CATEGORY_COLORS = [
    "#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#06B6D4",
    "#EC4899", "#14B8A6", "#F97316", "#6366F1", "#84CC16", "#64748B",
]

# ---------------------------------------------------------------- typographie
FONT = "Segoe UI"
F_TITLE = (FONT, 19, "bold")
F_SUBTITLE = (FONT, 10)
F_H2 = (FONT, 13, "bold")
F_H3 = (FONT, 11, "bold")
F_BODY = (FONT, 10)
F_BODY_B = (FONT, 10, "bold")
F_SMALL = (FONT, 9)
F_SMALL_B = (FONT, 9, "bold")
F_TINY = (FONT, 8)
F_KPI = (FONT, 23, "bold")
F_NUM = (FONT, 15, "bold")
F_NUM_SM = (FONT, 12, "bold")


def tone(name: str):
    return TONES.get(name, TONES["muted"])


def setup(root):
    """Applique les styles globaux (thème clam, tableaux, listes déroulantes)."""
    root.configure(bg=BG)
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass

    style.configure(".", background=BG, foreground=TEXT, font=F_BODY, borderwidth=0,
                    focuscolor=BG)

    # --- tableaux ---------------------------------------------------------
    style.configure(
        "Treeview",
        background=SURFACE,
        fieldbackground=SURFACE,
        foreground=TEXT,
        borderwidth=0,
        relief="flat",
        rowheight=S(36),
        font=F_BODY,
    )
    style.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
    style.configure(
        "Treeview.Heading",
        background=SURFACE_2,
        foreground=MUTED,
        relief="flat",
        borderwidth=0,
        font=F_SMALL_B,
        padding=(S(10), S(9)),
    )
    style.map("Treeview.Heading", background=[("active", SURFACE_3)])
    style.map(
        "Treeview",
        background=[("selected", PRIMARY_SOFT)],
        foreground=[("selected", PRIMARY_DARK)],
    )

    # --- listes déroulantes ----------------------------------------------
    style.configure(
        "TCombobox",
        fieldbackground=SURFACE,
        background=SURFACE,
        foreground=TEXT,
        arrowcolor=MUTED,
        bordercolor=BORDER,
        lightcolor=SURFACE,
        darkcolor=SURFACE,
        padding=(S(8), S(6)),
        arrowsize=S(11),
        relief="flat",
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", SURFACE), ("disabled", SURFACE_2)],
        selectbackground=[("readonly", SURFACE)],
        selectforeground=[("readonly", TEXT)],
        bordercolor=[("focus", PRIMARY), ("hover", BORDER_DARK)],
        arrowcolor=[("active", TEXT)],
        background=[("readonly", SURFACE)],
    )
    style.configure(
        "TCombobox.Listbox",
        background=SURFACE,
        foreground=TEXT,
        selectbackground=PRIMARY_SOFT,
        selectforeground=PRIMARY_DARK,
        borderwidth=0,
        font=F_BODY,
    )
    root.option_add("*TCombobox*Listbox.background", SURFACE)
    root.option_add("*TCombobox*Listbox.foreground", TEXT)
    root.option_add("*TCombobox*Listbox.selectBackground", PRIMARY_SOFT)
    root.option_add("*TCombobox*Listbox.selectForeground", PRIMARY_DARK)
    # Important : la famille de police doit être entre accolades, sinon Tk échoue à
    # analyser "Segoe UI 10" et la liste déroulante ne peut plus s'ouvrir.
    root.option_add("*TCombobox*Listbox.font", "{Segoe UI} 10")
    root.option_add("*TCombobox*Listbox.borderWidth", 0)

    # --- barres de défilement --------------------------------------------
    for orient in ("Vertical", "Horizontal"):
        name = f"Slim.{orient}.TScrollbar"
        style.configure(
            name,
            background=BORDER_DARK,
            troughcolor=BG,
            bordercolor=BG,
            arrowcolor=BG,
            relief="flat",
            borderwidth=0,
            arrowsize=S(10),
            width=S(8),
        )
        style.map(name, background=[("active", FAINT)])
    style.layout(
        "Slim.Vertical.TScrollbar",
        [("Vertical.Scrollbar.trough",
          {"sticky": "ns", "children": [("Vertical.Scrollbar.thumb",
                                        {"expand": "1", "sticky": "nswe"})]})],
    )
    style.layout(
        "Slim.Horizontal.TScrollbar",
        [("Horizontal.Scrollbar.trough",
          {"sticky": "ew", "children": [("Horizontal.Scrollbar.thumb",
                                        {"expand": "1", "sticky": "nswe"})]})],
    )

    # --- divers -----------------------------------------------------------
    style.configure("TCheckbutton", background=SURFACE, foreground=TEXT, font=F_BODY,
                    indicatorcolor=SURFACE, focuscolor=SURFACE)
    style.map("TCheckbutton", indicatorcolor=[("selected", PRIMARY)],
              foreground=[("active", TEXT)])
    style.configure("TSeparator", background=BORDER)
    style.configure("TNotebook", background=BG, borderwidth=0)
