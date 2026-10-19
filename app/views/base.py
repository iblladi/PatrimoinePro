"""Base commune des écrans et petits composants de mise en page."""
from __future__ import annotations

import tkinter as tk

from .. import theme, utils, widgets
from ..theme import BG, BORDER, FAINT, F_H2, F_SMALL, F_TITLE, MUTED, SURFACE, SURFACE_2, TEXT
from ..utils import S


class BaseView(tk.Frame):
    def __init__(self, master, app):
        super().__init__(master, bg=BG)
        self.app = app
        self.db = app.db
        self.params = {}

    def on_show(self, **params):
        self.params = dict(params or {})
        self.rebuild()

    def rebuild(self):
        for child in self.winfo_children():
            child.destroy()
        self.build()

    def build(self):
        raise NotImplementedError


class ScrollView(BaseView):
    def __init__(self, master, app):
        super().__init__(master, app)
        self.scroll = widgets.ScrollFrame(self, bg=BG)
        self.scroll.pack(fill="both", expand=True)
        self.body = tk.Frame(self.scroll.body, bg=BG)
        self.body.pack(fill="both", expand=True, padx=S(26), pady=(S(20), S(28)))

    def rebuild(self):
        for child in self.body.winfo_children():
            child.destroy()
        self.build()
        self.after(10, self.scroll.scroll_top)


# --------------------------------------------------------------------------
# Mise en page
# --------------------------------------------------------------------------
def page_header(parent, title, subtitle="", actions=None):
    head = tk.Frame(parent, bg=BG)
    head.pack(fill="x", pady=(0, S(18)))
    left = tk.Frame(head, bg=BG)
    left.pack(side="left", fill="x", expand=True)
    widgets.lbl(left, title, F_TITLE, TEXT, BG).pack(anchor="w")
    if subtitle:
        widgets.lbl(left, subtitle, F_SMALL, MUTED, BG).pack(anchor="w", pady=(S(4), 0))
    right = tk.Frame(head, bg=BG)
    right.pack(side="right", anchor="n")
    if actions:
        actions(right)
    return head


def section_title(parent, text, hint=""):
    row = tk.Frame(parent, bg=BG)
    row.pack(fill="x", pady=(S(22), S(10)))
    widgets.lbl(row, text, F_H2, TEXT, BG).pack(side="left")
    if hint:
        widgets.lbl(row, hint, F_SMALL, MUTED, BG).pack(side="left", padx=(S(10), 0), pady=(S(3), 0))
    return row


def gap(parent, height=16):
    return tk.Frame(parent, bg=BG, height=S(height))


def legend_row(parent, color, label, value_text="", pct_text="", bg=SURFACE):
    row = tk.Frame(parent, bg=bg)
    row.pack(fill="x", pady=S(4))
    widgets.Dot(row, color, 9, bg).pack(side="left", padx=(0, S(8)))
    widgets.lbl(row, label, F_SMALL, TEXT, bg).pack(side="left")
    if pct_text:
        widgets.lbl(row, pct_text, F_SMALL, MUTED, bg).pack(side="right", padx=(S(6), 0))
    if value_text:
        widgets.lbl(row, value_text, (theme.FONT, 9, "bold"), TEXT, bg).pack(side="right")
    return row


def empty_state(parent, title, text, action_label=None, command=None, icon="◇"):
    card = widgets.Card(parent, padding=26)
    card.pack(fill="x")
    box = tk.Frame(card.content, bg=SURFACE)
    box.pack(expand=True, pady=S(10))
    tk.Label(box, text=icon, font=(theme.FONT, 26), fg=FAINT, bg=SURFACE).pack()
    widgets.lbl(box, title, (theme.FONT, 12, "bold"), TEXT, SURFACE).pack(pady=(S(6), S(4)))
    widgets.lbl(box, text, F_SMALL, MUTED, SURFACE, wraplength=S(420),
                justify="center").pack()
    if action_label and command:
        btn = widgets.Button(box, action_label, command, variant="primary")
        btn.pack(pady=(S(14), 0))
    return card


def money_label(parent, value, font=(theme.FONT, 15, "bold"), fg=TEXT, bg=SURFACE,
                positive=None):
    """Montant coloré : vert si positif (optionnel), rouge si négatif."""
    text = utils.fmt_money(value)
    if positive is None:
        color = RED_LIKE if float(value or 0) < 0 else fg
    else:
        color = GREEN_LIKE if float(value or 0) > 0 else RED_LIKE
        if float(value or 0) == 0:
            color = fg
    return widgets.lbl(parent, text, font, color, bg)


GREEN_LIKE = theme.GREEN_DARK
RED_LIKE = "#DC2626"


def delta_chip(parent, value, suffix="", bg=SURFACE, decimals=0):
    up = float(value or 0) >= 0
    fg = theme.GREEN_DARK if up else theme.RED_DARK
    soft = theme.GREEN_SOFT if up else theme.RED_SOFT
    text = f"{'+' if up else '−'}{utils.fmt_money(abs(float(value or 0)), decimals)}{suffix}"
    return widgets.Chip(parent, text, fg, soft, bg=bg)
