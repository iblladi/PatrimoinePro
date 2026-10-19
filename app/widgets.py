"""Widgets sur mesure : cartes, boutons, graphiques, calendrier, dialogues."""
from __future__ import annotations

import datetime as dt
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

from . import theme, utils
from .theme import (
    AMBER, AMBER_SOFT, BG, BORDER, BORDER_DARK, CHART_FILL, CHART_GRID, FAINT,
    F_BODY, F_BODY_B, F_H2, F_H3, F_KPI, F_NUM, F_NUM_SM, F_SMALL, F_SMALL_B,
    F_TINY, F_TITLE, GREEN, GREEN_DARK, GREEN_SOFT, MUTED, PRIMARY, PRIMARY_DARK,
    PRIMARY_SOFT, RED, RED_DARK, RED_SOFT, SIDEBAR_TEXT, SURFACE, SURFACE_2,
    SURFACE_3, TEXT, TEXT_SOFT, VIOLET, tone,
)
from .utils import S


# --------------------------------------------------------------------------
# Primitives
# --------------------------------------------------------------------------
def bg_of(widget, default=SURFACE):
    try:
        return widget.cget("bg")
    except Exception:
        return default


def lbl(parent, text="", font=F_BODY, fg=TEXT, bg=None, **kw):
    kw.setdefault("anchor", "w")
    kw.setdefault("justify", "left")
    return tk.Label(parent, text=text, font=font, fg=fg, bg=bg or bg_of(parent), **kw)


def entry(parent, textvariable=None, width=None, justify="left", bg=None, font=F_BODY):
    bg = bg or SURFACE
    e = tk.Entry(
        parent, textvariable=textvariable, font=font, bg=bg, fg=TEXT,
        insertbackground=TEXT, relief="flat", bd=0, highlightthickness=1,
        highlightbackground=BORDER, highlightcolor=PRIMARY, justify=justify,
        disabledbackground=SURFACE_2, disabledforeground=FAINT,
    )
    if width:
        e.configure(width=width)
    e.configure(insertwidth=1)
    return e


def combo(parent, values, textvariable=None, width=None, state="readonly"):
    c = ttk.Combobox(parent, values=list(values), textvariable=textvariable,
                     state=state, width=width, font=F_BODY)
    return c


def hline(parent, color=BORDER, pady=0):
    f = tk.Frame(parent, bg=color, height=1)
    return f


def vspace(parent, height):
    return tk.Frame(parent, bg=bg_of(parent), height=S(height))


def round_rect(canvas, x1, y1, x2, y2, r, **kw):
    r = max(0, min(r, (x2 - x1) / 2, (y2 - y1) / 2))
    pts = [
        x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
        x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
        x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
    ]
    return canvas.create_polygon(pts, smooth=True, **kw)


# --------------------------------------------------------------------------
# Cadres défilants
# --------------------------------------------------------------------------
class ScrollFrame(tk.Frame):
    """Zone défilante verticale, sans bordure, avec barre fine escamotable."""

    def __init__(self, master, bg=BG, **kw):
        super().__init__(master, bg=bg, **kw)
        self._bg = bg
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0, takefocus=0)
        self.vsb = ttk.Scrollbar(self, orient="vertical", style="Slim.Vertical.TScrollbar",
                                 command=self.canvas.yview)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.body = tk.Frame(self.canvas, bg=bg)
        self._window = self.canvas.create_window((0, 0), window=self.body, anchor="nw")
        self.canvas.configure(yscrollcommand=self._on_scroll)
        self.body.bind("<Configure>", self._on_body)
        self.canvas.bind("<Configure>", self._on_canvas)
        self._visible = False

    # La molette est gérée au niveau de la fenêtre principale (main.App), car les
    # widgets enfants du canvas intercepteraient les événements <Enter>/<Leave>.
    def scroll_by(self, delta: int, factor: int = 3):
        if self.canvas.winfo_height() >= self.body.winfo_reqheight():
            return False
        self.canvas.yview_scroll(-1 * factor if delta > 0 else factor, "units")
        return True

    def _on_body(self, _=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self._toggle_bar()

    def _on_canvas(self, event):
        self.canvas.itemconfigure(self._window, width=event.width)
        self._toggle_bar()

    def _on_scroll(self, lo, hi):
        # Position de la barre : toujours synchronisée
        self.vsb.set(lo, hi)

    def _toggle_bar(self):
        needs = self.body.winfo_reqheight() > self.canvas.winfo_height() + 2
        if needs and not self._visible:
            self.vsb.pack(side="right", fill="y", padx=(S(6), 0))
            self._visible = True
        elif not needs and self._visible:
            self.vsb.pack_forget()
            self._visible = False

    def scroll_top(self):
        self.canvas.yview_moveto(0)


# --------------------------------------------------------------------------
# Cartes
# --------------------------------------------------------------------------
class Card(tk.Frame):
    def __init__(self, master, title=None, subtitle=None, padding=18,
                 bg=SURFACE, border=BORDER, **kw):
        super().__init__(master, bg=bg, highlightbackground=border,
                         highlightcolor=border, highlightthickness=1, bd=0, **kw)
        self.bg = bg
        self.padding = padding
        self.content = tk.Frame(self, bg=bg)
        self.content.pack(fill="both", expand=True, padx=S(padding), pady=S(padding))
        self.header = None
        self.header_right = None
        if title:
            self.header = tk.Frame(self.content, bg=bg)
            self.header.pack(fill="x", pady=(0, S(6)))
            lbl(self.header, title, F_H3, TEXT, bg).pack(side="left")
            self.header_right = tk.Frame(self.header, bg=bg)
            self.header_right.pack(side="right")
            if subtitle:
                lbl(self.content, subtitle, F_SMALL, MUTED, bg).pack(anchor="w", pady=(0, S(10)))


class KpiCard(tk.Frame):
    """Carte d'indicateur : titre, valeur, variation, petit graphique optionnel."""

    def __init__(self, master, title, value, hint="", tone_name="blue", icon=None, bg=SURFACE):
        super().__init__(master, bg=bg, highlightbackground=BORDER, highlightcolor=BORDER,
                         highlightthickness=1, bd=0)
        self.bg = bg
        inner = tk.Frame(self, bg=bg)
        inner.pack(fill="both", expand=True, padx=S(16), pady=S(14))
        top = tk.Frame(inner, bg=bg)
        top.pack(fill="x")
        lbl(top, title.upper(), (theme.FONT, 8, "bold"), MUTED, bg).pack(side="left")
        fg, soft = tone(tone_name)
        if icon:
            chip = tk.Frame(top, bg=soft)
            chip.pack(side="right")
            tk.Label(chip, text=icon, font=F_SMALL_B, fg=fg, bg=soft, padx=S(6), pady=S(1)).pack()
        self.value_label = lbl(inner, value, F_KPI, TEXT, bg)
        self.value_label.pack(anchor="w", pady=(S(6), S(2)))
        self.hint_label = lbl(inner, hint, F_SMALL, MUTED, bg)
        self.hint_label.pack(anchor="w")


# --------------------------------------------------------------------------
# Boutons
# --------------------------------------------------------------------------
BUTTON_VARIANTS = {
    # variant: (fond, fond survol, texte, bordure)
    "primary": (PRIMARY, PRIMARY_DARK, "#FFFFFF", PRIMARY),
    "secondary": (SURFACE, SURFACE_3, TEXT, BORDER),
    "ghost": (None, SURFACE_3, TEXT_SOFT, None),
    "subtle": (PRIMARY_SOFT, "#DFEBFE", PRIMARY_DARK, None),
    "danger": (RED_SOFT, "#FDE2E1", RED_DARK, None),
    "success": (GREEN_SOFT, "#D8F7EB", GREEN_DARK, None),
    "dark": ("#1E293B", "#0F172A", "#FFFFFF", None),
}


class Button(tk.Canvas):
    def __init__(self, master, text, command=None, variant="primary", width=None,
                 height=34, font=F_BODY_B, icon=None, padx=15, radius=8, bg=None,
                 anchor="center"):
        self._parent_bg = bg or bg_of(master, BG)
        self._font_spec = font
        self._font = tkfont.Font(font=font)
        self._text = text
        self._icon = icon
        self._variant = variant
        self._radius = radius
        self._padx = padx
        self._enabled = True
        self._hover = False
        self._pressed = False
        self._anchor = anchor
        self._command = command

        label = f"{icon}  {text}" if icon else text
        w = width or (self._font.measure(label) + 2 * S(padx))
        super().__init__(master, width=w, height=S(height), bg=self._parent_bg,
                         highlightthickness=0, bd=0, cursor="hand2")
        self._cw, self._ch = w, S(height)
        self._draw()
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)

    # ------------------------------------------------------------------
    def _colors(self):
        fill, hover, fg, border = BUTTON_VARIANTS.get(self._variant, BUTTON_VARIANTS["primary"])
        if fill is None:
            fill = self._parent_bg
            hover = SURFACE_3 if self._parent_bg != SURFACE_3 else "#E8EDF4"
        if not self._enabled:
            return SURFACE_3, SURFACE_3, FAINT, SURFACE_3
        return fill, hover, fg, border

    def _draw(self):
        self.delete("all")
        fill, hover, fg, border = self._colors()
        if self._pressed and self._enabled:
            fill = hover
        elif self._hover and self._enabled:
            fill = hover
        x1, y1 = 1, 1
        x2, y2 = self._cw - 1, self._ch - 1
        round_rect(self, x1, y1, x2, y2, S(self._radius), fill=fill,
                   outline=border or fill, width=1)
        label = f"{self._icon}  {self._text}" if self._icon else self._text
        self.create_text(self._cw / 2, self._ch / 2, text=label, fill=fg,
                         font=self._font_spec, anchor="center")

    def _on_enter(self, _):
        self._hover = True
        self._draw()

    def _on_leave(self, _):
        self._hover = False
        self._pressed = False
        self._draw()

    def _on_press(self, _):
        if not self._enabled:
            return
        self._pressed = True
        self._draw()

    def _on_release(self, event):
        was = self._pressed
        self._pressed = False
        self._draw()
        if was and self._enabled and 0 <= event.x <= self._cw and 0 <= event.y <= self._ch:
            if self._command:
                self._command()

    # ------------------------------------------------------------------
    def set_variant(self, variant):
        self._variant = variant
        self._draw()

    def set_text(self, text, icon=None):
        self._text = text
        if icon is not None:
            self._icon = icon
        label = f"{self._icon}  {self._text}" if self._icon else self._text
        w = self._font.measure(label) + 2 * S(self._padx)
        if w != self._cw:
            self._cw = w
            self.configure(width=w)
        self._draw()

    def set_enabled(self, enabled: bool):
        self._enabled = bool(enabled)
        self.configure(cursor="hand2" if enabled else "arrow")
        self._draw()

    def set_command(self, command):
        self._command = command


class MenuButton(tk.Canvas):
    """Bouton « … » dessiné (évite les glyphes d'ellipse peu lisibles)."""

    def __init__(self, master, command=None, bg=None, size=28, color=MUTED):
        self._mb_bg = bg or bg_of(master, SURFACE)
        super().__init__(master, width=S(size), height=S(size), bg=self._mb_bg,
                         highlightthickness=0, bd=0, cursor="hand2")
        self._size = S(size)
        self._color = color
        self._command = command
        self._hover = False
        self.bind("<Enter>", self._enter)
        self.bind("<Leave>", self._leave)
        self.bind("<ButtonRelease-1>", self._click)
        self._draw()

    def _draw(self):
        self.delete("all")
        s = self._size
        if self._hover:
            round_rect(self, 2, 2, s - 2, s - 2, S(6), fill=SURFACE_3, outline=SURFACE_3)
        cx, cy = s / 2, s / 2
        r = max(1.4, S(1.6))
        for dx in (-S(5), 0, S(5)):
            self.create_oval(cx + dx - r, cy - r, cx + dx + r, cy + r,
                             fill=self._color, outline=self._color)

    def _enter(self, _):
        self._hover = True
        self._draw()

    def _leave(self, _):
        self._hover = False
        self._draw()

    def _click(self, _):
        if self._command:
            self._command()

    def set_command(self, command):
        self._command = command


class Chip(tk.Frame):
    def __init__(self, master, text, fg=MUTED, soft=SURFACE_3, font=F_SMALL_B, bg=None):
        super().__init__(master, bg=bg or bg_of(master))
        self._label = tk.Label(self, text=text, font=font, fg=fg, bg=soft,
                               padx=S(8), pady=S(2))
        self._label.pack()

    def configure_text(self, text, fg=None, soft=None):
        self._label.configure(text=text)
        if fg:
            self._label.configure(fg=fg)
        if soft:
            self._label.configure(bg=soft)


class Dot(tk.Canvas):
    def __init__(self, master, color=PRIMARY, size=9, bg=None):
        super().__init__(master, width=S(size), height=S(size), bg=bg or bg_of(master),
                         highlightthickness=0, bd=0)
        self._size = S(size)
        self.create_oval(1, 1, self._size - 1, self._size - 1, fill=color, outline="")

    def set_color(self, color):
        self.delete("all")
        self.create_oval(1, 1, self._size - 1, self._size - 1, fill=color, outline="")


class Segmented(tk.Canvas):
    """Sélecteur de période compact."""

    def __init__(self, master, options, value=None, command=None, height=32, bg=None):
        self._segments = list(options)
        self._value = value or self._segments[0]
        self._command = command
        self._bg = bg or bg_of(master, SURFACE)
        self._font = tkfont.Font(font=F_SMALL_B)
        widths = [self._font.measure(o) + S(22) for o in self._segments]
        total = sum(widths)
        super().__init__(master, width=total + 4, height=S(height), bg=self._bg,
                         highlightthickness=0, bd=0, cursor="hand2")
        self._widths = widths
        self._h = S(height)
        self._draw()
        self.bind("<Button-1>", self._on_click)
        self.bind("<ButtonRelease-1>", self._on_click)

    def _draw(self):
        self.delete("all")
        round_rect(self, 1, 1, sum(self._widths) + 3, self._h - 1, S(self._h / 2),
                   fill=SURFACE_3, outline=SURFACE_3)
        x = 2
        for opt, w in zip(self._segments, self._widths):
            active = opt == self._value
            if active:
                round_rect(self, x, 2, x + w, self._h - 2, S((self._h - 4) / 2),
                           fill=SURFACE, outline=BORDER)
            self.create_text(x + w / 2, self._h / 2, text=opt,
                             fill=TEXT if active else MUTED,
                             font=F_SMALL_B if active else F_SMALL)
            x += w

    def _on_click(self, event):
        x = 2
        for opt, w in zip(self._segments, self._widths):
            if x <= event.x <= x + w:
                if opt != self._value:
                    self._value = opt
                    self._draw()
                    if self._command:
                        self._command(opt)
                return
            x += w

    def get(self):
        return self._value

    def set(self, value):
        if value in self._segments:
            self._value = value
            self._draw()


# --------------------------------------------------------------------------
# Barre de progression
# --------------------------------------------------------------------------
class ProgressBar(tk.Canvas):
    def __init__(self, master, height=8, color=PRIMARY, track=SURFACE_3, bg=None):
        self._h = S(height)
        super().__init__(master, height=self._h, bg=bg or bg_of(master, SURFACE),
                         highlightthickness=0, bd=0)
        self._color = color
        self._track = track
        self._value = 0.0
        self.bind("<Configure>", lambda e: self._draw())

    def set(self, value, color=None):
        self._value = utils.clamp(float(value or 0), 0.0, 1.0)
        if color:
            self._color = color
        self._draw()

    def _draw(self):
        self.delete("all")
        w = self.winfo_width()
        if w <= 1:
            w = self.winfo_reqwidth()
        if w <= 1:
            return
        r = self._h / 2
        round_rect(self, 0, 0, w, self._h, r, fill=self._track, outline=self._track)
        if self._value > 0:
            fw = max(self._h, w * self._value)
            round_rect(self, 0, 0, fw, self._h, r, fill=self._color, outline=self._color)


# --------------------------------------------------------------------------
# Graphiques
# --------------------------------------------------------------------------
class LineChart(tk.Canvas):
    """Courbe avec aire, grille, infobulle et ligne d'objectif optionnelle."""

    def __init__(self, master, height=210, color=PRIMARY, area=CHART_FILL,
                 value_fmt=utils.fmt_money_short, bg=SURFACE, target=None,
                 target_label="Objectif", show_points=True, ylabel=None):
        super().__init__(master, height=S(height), bg=bg, highlightthickness=0, bd=0)
        self._bg = bg
        self._color = color
        self._area = area
        self._fmt = value_fmt
        self._target = target
        self._target_label = target_label
        self._show_points = show_points
        self._points = []
        self._hover = None
        self._font = tkfont.Font(font=F_TINY)
        self._font_b = tkfont.Font(font=F_SMALL_B)
        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<Motion>", self._on_motion)
        self.bind("<Leave>", self._on_leave)

    def set_data(self, points, target=None):
        self._points = list(points or [])
        if target is not None:
            self._target = target
        self._draw()

    def _geom(self):
        w, h = self.winfo_width(), self.winfo_height()
        return w, h, S(54), S(12), S(14), S(24)

    def _draw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 60 or h < 50:
            return
        pad_l, pad_r, pad_t, pad_b = S(54), S(12), S(14), S(24)
        pts = self._points
        if not pts:
            self.create_text(w / 2, h / 2, text="Aucune donnée", fill=FAINT, font=F_SMALL)
            return
        values = [float(v) for _, v in pts]
        lo, hi = min(values), max(values)
        if self._target is not None:
            hi = max(hi, float(self._target))
            lo = min(lo, float(self._target))
        span = hi - lo
        if span <= 0:
            span = abs(hi) or 1.0
        lo_b, hi_b, step = utils.nice_bounds(lo - span * 0.12, hi + span * 0.12, 4)

        def ypos(v):
            return pad_t + (hi_b - v) / (hi_b - lo_b) * (h - pad_t - pad_b)

        # grille + graduations
        v = lo_b
        while v <= hi_b + step / 2:
            y = ypos(v)
            self.create_line(pad_l, y, w - pad_r, y, fill=CHART_GRID, dash=(1, 3))
            self.create_text(pad_l - S(8), y, text=self._fmt(v), anchor="e",
                             fill=FAINT, font=self._font)
            v += step

        n = len(pts)
        x0, x1 = pad_l, w - pad_r
        step_x = (x1 - x0) / max(1, n - 1)
        coords = []
        for i, (_, value) in enumerate(pts):
            coords.extend([x0 + i * step_x, ypos(float(value))])

        # aire
        if len(coords) >= 4:
            poly = [x0, h - pad_b] + coords + [x0 + (n - 1) * step_x, h - pad_b]
            self.create_polygon(poly, fill=self._area, outline="")

        # ligne d'objectif
        if self._target is not None:
            ty = ypos(float(self._target))
            self.create_line(pad_l, ty, w - pad_r, ty, fill=GREEN, dash=(4, 3), width=1)
            self.create_text(w - pad_r - S(2), ty - S(7), text=self._target_label,
                             anchor="e", fill=GREEN_DARK, font=self._font)

        # courbe
        self.create_line(*coords, fill=self._color, width=max(2, S(2)),
                         capstyle="round", joinstyle="round", smooth=False)

        if self._show_points and n <= 30:
            for i in range(n):
                cx, cy = coords[2 * i], coords[2 * i + 1]
                self.create_oval(cx - S(3), cy - S(3), cx + S(3), cy + S(3),
                                 fill=SURFACE, outline=self._color, width=max(1, S(1)))

        # étiquettes de l'axe X
        label_step = max(1, int((n + 5) // 6))
        for i, (label, _) in enumerate(pts):
            if i % label_step == 0 or i == n - 1:
                self.create_text(x0 + i * step_x, h - S(10), text=label,
                                 fill=MUTED, font=self._font, anchor="center")

        # infobulle
        if self._hover is not None and 0 <= self._hover < n:
            i = self._hover
            cx, cy = coords[2 * i], coords[2 * i + 1]
            self.create_line(cx, pad_t, cx, h - pad_b, fill=BORDER_DARK, dash=(2, 3))
            self.create_oval(cx - S(4), cy - S(4), cx + S(4), cy + S(4),
                             fill=self._color, outline=SURFACE, width=S(2))
            label, value = pts[i]
            txt = f"{label}   {self._fmt(float(value))}"
            tw = self._font_b.measure(txt) + S(16)
            bx = min(max(cx - tw / 2, pad_l), w - pad_r - tw)
            by = max(cy - S(34), pad_t)
            round_rect(self, bx, by, bx + tw, by + S(24), S(6), fill=SIDEBAR_ISH,
                       outline=SIDEBAR_ISH)
            self.create_text(bx + tw / 2, by + S(12), text=txt, fill="#FFFFFF",
                             font=self._font_b, anchor="center")

    def _on_motion(self, event):
        if not self._points:
            return
        w, _ = self.winfo_width(), self.winfo_height()
        pad_l, pad_r = S(54), S(12)
        n = len(self._points)
        if n == 1:
            idx = 0
        else:
            step_x = (w - pad_r - pad_l) / (n - 1)
            idx = int(round((event.x - pad_l) / step_x))
            idx = max(0, min(n - 1, idx))
        if idx != self._hover:
            self._hover = idx
            self._draw()

    def _on_leave(self, _):
        if self._hover is not None:
            self._hover = None
            self._draw()


SIDEBAR_ISH = "#0F172A"


class DonutChart(tk.Canvas):
    def __init__(self, master, size=190, thickness=22, bg=SURFACE, center_fmt=utils.fmt_money_short,
                 center_label="Total"):
        super().__init__(master, width=S(size), height=S(size), bg=bg,
                         highlightthickness=0, bd=0)
        self._bg = bg
        self._thickness = thickness
        self._items = []
        self._fmt = center_fmt
        self._center_label = center_label
        self._center_value = 0.0
        self.bind("<Configure>", lambda e: self._draw())

    def set_data(self, items, center_value=None, center_label=None):
        """items : liste de (valeur, couleur) ou (valeur, couleur, libellé)."""
        norm = []
        for item in items or []:
            if len(item) >= 3:
                value, color, label = item[0], item[1], item[2]
            else:
                value, color, label = item[0], item[1], ""
            value = float(value)
            if value > 0:
                norm.append((value, color, label))
        self._items = norm
        if center_value is not None:
            self._center_value = float(center_value)
        else:
            self._center_value = sum(i[0] for i in self._items)
        if center_label:
            self._center_label = center_label
        self._draw()

    def _draw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 40 or h < 40:
            return
        size = min(w, h)
        cx, cy = w / 2, h / 2
        thick = S(self._thickness)
        r = size / 2 - S(4)
        box = (cx - r, cy - r, cx + r, cy + r)
        total = sum(float(i[0]) for i in self._items)
        if total <= 0:
            self.create_oval(cx - r + thick / 2, cy - r + thick / 2,
                             cx + r - thick / 2, cy + r - thick / 2,
                             outline=SURFACE_3, width=thick)
        else:
            # Parts dessinées en secteurs (extent toujours positif, sens horaire)
            cum = 0.0
            gaps = min(1.4, 60.0 / max(1, len(self._items))) if len(self._items) > 1 else 0.0
            for value, color, _label in self._items:
                extent = 360.0 * (float(value) / total)
                draw = max(0.4, extent - gaps)
                self.create_arc(*box, start=90.0 - cum - extent,
                                extent=draw, style="pieslice",
                                fill=color, outline=color, width=0)
                cum += extent
            hole = max(2.0, r - thick)
            self.create_oval(cx - hole, cy - hole, cx + hole, cy + hole,
                             fill=self._bg, outline=self._bg)
        self.create_text(cx, cy - S(4), text=self._fmt(self._center_value),
                         fill=TEXT, font=F_NUM, anchor="center")
        self.create_text(cx, cy + S(16), text=self._center_label,
                         fill=MUTED, font=F_TINY, anchor="center")


class BarsChart(tk.Canvas):
    """Barres groupées (revenus / dépenses) par mois."""

    def __init__(self, master, height=200, bg=SURFACE, value_fmt=utils.fmt_money_short,
                 target=None):
        super().__init__(master, height=S(height), bg=bg, highlightthickness=0, bd=0)
        self._bg = bg
        self._groups = []
        self._fmt = value_fmt
        self._font = tkfont.Font(font=F_TINY)
        self.bind("<Configure>", lambda e: self._draw())

    def set_data(self, groups):
        """groups : [(libellé, [(valeur, couleur), ...]), ...]"""
        self._groups = list(groups or [])
        self._draw()

    def _draw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 60 or h < 50:
            return
        pad_l, pad_r, pad_t, pad_b = S(50), S(8), S(14), S(24)
        groups = self._groups
        if not groups:
            self.create_text(w / 2, h / 2, text="Aucune donnée", fill=FAINT, font=F_SMALL)
            return
        vmax = max([float(v) for _, bars in groups for v, _ in bars] + [1.0])
        lo_b, hi_b, step = utils.nice_bounds(0, vmax, 4)

        def ypos(v):
            return pad_t + (hi_b - v) / (hi_b - lo_b) * (h - pad_t - pad_b)

        v = lo_b
        while v <= hi_b + step / 2:
            y = ypos(v)
            self.create_line(pad_l, y, w - pad_r, y, fill=CHART_GRID, dash=(1, 3))
            self.create_text(pad_l - S(8), y, text=self._fmt(v), anchor="e",
                             fill=FAINT, font=self._font)
            v += step

        n = len(groups)
        group_w = (w - pad_l - pad_r) / n
        for gi, (label, bars) in enumerate(groups):
            nb = max(1, len(bars))
            bar_w = min(S(15), (group_w * 0.62) / nb)
            total_w = bar_w * nb + S(3) * (nb - 1)
            bx = pad_l + gi * group_w + (group_w - total_w) / 2
            for value, color in bars:
                top = ypos(float(value))
                bottom = ypos(0)
                if bottom - top < 1:
                    top = bottom - 1
                round_rect(self, bx, top, bx + bar_w, bottom, min(S(3), bar_w / 2),
                           fill=color, outline=color)
                bx += bar_w + S(3)
            if n <= 8 or gi % 2 == 0 or gi == n - 1:
                self.create_text(pad_l + gi * group_w + group_w / 2, h - S(10),
                                 text=str(label), fill=MUTED, font=self._font)


# --------------------------------------------------------------------------
# Sélecteur de couleur
# --------------------------------------------------------------------------
class ColorPicker(tk.Frame):
    def __init__(self, master, value=PRIMARY, colors=None, bg=None, on_change=None):
        self._bg = bg or bg_of(master, SURFACE)
        super().__init__(master, bg=self._bg)
        self._value = value
        self._colors = colors or theme.CATEGORY_COLORS
        self._on_change = on_change
        self._swatches = []
        for c in self._colors:
            cv = tk.Canvas(self, width=S(18), height=S(18), bg=self._bg,
                           highlightthickness=0, bd=0, cursor="hand2")
            cv.pack(side="left", padx=(0, S(5)))
            cv.bind("<Button-1>", lambda e, col=c: self.set(col))
            self._swatches.append((c, cv))
        self._paint()

    def _paint(self):
        for color, cv in self._swatches:
            cv.delete("all")
            selected = color.lower() == (self._value or "").lower()
            outline = TEXT if selected else SURFACE
            width = 2 if selected else 1
            cv.create_oval(1, 1, S(16), S(16), fill=color, outline=outline, width=width)
            if selected:
                cv.create_oval(S(5), S(5), S(11), S(11), fill=SURFACE, outline="")

    def set(self, color):
        self._value = color
        self._paint()
        if self._on_change:
            self._on_change(color)

    def get(self):
        return self._value


# --------------------------------------------------------------------------
# Champ de date + calendrier
# --------------------------------------------------------------------------
class DateField(tk.Frame):
    def __init__(self, master, value=None, width=12, bg=None):
        self._bg = bg or SURFACE
        super().__init__(master, bg=self._bg)
        d = utils.parse_date(value) or utils.today()
        self.var = tk.StringVar(value=d.strftime("%d/%m/%Y"))
        self._entry = entry(self, textvariable=self.var, width=width, bg=self._bg)
        self._entry.pack(side="left", ipady=S(5))
        self._btn = tk.Canvas(self, width=S(30), height=S(30), bg=self._bg,
                              highlightthickness=0, bd=0, cursor="hand2")
        self._btn.pack(side="left", padx=(S(4), 0))
        self._draw_icon()
        self._btn.bind("<Button-1>", self._open_calendar)
        self._popup = None

    def _draw_icon(self):
        c = self._btn
        c.delete("all")
        c.create_rectangle(S(7), S(8), S(23), S(23), outline=MUTED, width=1)
        c.create_line(S(7), S(13), S(23), S(13), fill=MUTED)
        c.create_line(S(11), S(5), S(11), S(10), fill=MUTED)
        c.create_line(S(19), S(5), S(19), S(10), fill=MUTED)

    def get(self):
        d = utils.parse_date(self.var.get())
        return d or utils.today()

    def is_valid(self):
        return utils.parse_date(self.var.get()) is not None

    def set(self, value):
        d = utils.parse_date(value)
        if d:
            self.var.set(d.strftime("%d/%m/%Y"))

    # ------------------------------------------------------------------
    def _open_calendar(self, _event=None):
        if self._popup and self._popup.winfo_exists():
            self._popup.destroy()
            self._popup = None
            return
        self._popup = CalendarPopup(self, self.get(), self._pick)

    def _pick(self, d):
        self.set(d)
        if self._popup:
            self._popup.destroy()
            self._popup = None


class CalendarPopup(tk.Toplevel):
    def __init__(self, anchor: tk.Widget, value, on_pick):
        super().__init__(anchor)
        self.withdraw()
        self.overrideredirect(True)
        self.configure(bg=BORDER)
        self._on_pick = on_pick
        self._cursor = utils.parse_date(value) or utils.today()

        outer = tk.Frame(self, bg=SURFACE, padx=S(10), pady=S(10))
        outer.pack(fill="both", expand=True, padx=1, pady=1)

        head = tk.Frame(outer, bg=SURFACE)
        head.pack(fill="x", pady=(0, S(8)))
        self._prev = tk.Label(head, text="‹", font=(theme.FONT, 13, "bold"), fg=MUTED,
                              bg=SURFACE, cursor="hand2", padx=S(8))
        self._prev.pack(side="left")
        self._prev.bind("<Button-1>", lambda e: self._shift(-1))
        self._next = tk.Label(head, text="›", font=(theme.FONT, 13, "bold"), fg=MUTED,
                              bg=SURFACE, cursor="hand2", padx=S(8))
        self._next.pack(side="right")
        self._next.bind("<Button-1>", lambda e: self._shift(1))
        self._title = tk.Label(head, text="", font=F_SMALL_B, fg=TEXT, bg=SURFACE)
        self._title.pack(side="left", expand=True)

        self._grid = tk.Frame(outer, bg=SURFACE)
        self._grid.pack()
        for i, d in enumerate(utils.DAYS_SHORT):
            tk.Label(self._grid, text=d[:2], font=F_TINY, fg=FAINT, bg=SURFACE,
                     width=3).grid(row=0, column=i, pady=(0, S(4)))

        foot = tk.Frame(outer, bg=SURFACE)
        foot.pack(fill="x", pady=(S(8), 0))
        today_btn = tk.Label(foot, text="Aujourd'hui", font=F_TINY, fg=PRIMARY,
                             bg=SURFACE, cursor="hand2")
        today_btn.pack(side="left")
        today_btn.bind("<Button-1>", lambda e: self._pick(utils.today()))

        self.update_idletasks()
        x = anchor.winfo_rootx()
        y = anchor.winfo_rooty() + anchor.winfo_height() + S(4)
        self.geometry(f"+{x}+{y}")
        self._render()
        self.deiconify()
        self.focus_force()
        self.bind("<FocusOut>", self._maybe_close)
        self.bind("<Escape>", lambda e: self.destroy())

    def _maybe_close(self, _event):
        try:
            focus = self.focus_get()
        except Exception:
            focus = None
        if focus is None or not str(focus).startswith(str(self)):
            self.destroy()

    def _shift(self, delta):
        self._cursor = utils.add_months(self._cursor.replace(day=1), delta)
        self._render()

    def _pick(self, d):
        self._on_pick(d)
        self.destroy()

    def _render(self):
        self._title.configure(text=utils.fmt_month(self._cursor).capitalize())
        for w in self._grid.grid_slaves():
            if int(w.grid_info()["row"]) > 0:
                w.destroy()
        first = self._cursor.replace(day=1)
        start_col = first.weekday()
        days_in = utils.month_bounds(first)[1].day
        today = utils.today()
        selected = utils.parse_date(self._cursor)
        for day in range(1, days_in + 1):
            idx = start_col + day - 1
            row, col = idx // 7 + 1, idx % 7
            cur = dt.date(first.year, first.month, day)
            fg = TEXT
            bgc = SURFACE
            font = F_SMALL
            if cur == utils.today():
                fg, bgc, font = PRIMARY_DARK, PRIMARY_SOFT, F_SMALL_B
            if selected and cur == selected:
                fg, bgc = "#FFFFFF", PRIMARY
                font = F_SMALL_B
            cell = tk.Label(self._grid, text=str(day), font=font, fg=fg, bg=bgc,
                            width=3, pady=S(2), cursor="hand2")
            cell.grid(row=row, column=col, padx=1, pady=1)
            cell.bind("<Button-1>", lambda e, d=cur: self._pick(d))
            cell.bind("<Enter>", lambda e, c=cell, b=bgc, col=col: c.configure(
                bg=SURFACE_3) if b == SURFACE else None)


# --------------------------------------------------------------------------
# Notifications
# --------------------------------------------------------------------------
class Toast:
    _current = None

    @classmethod
    def show(cls, master, message, tone_name="green", duration=2800):
        try:
            if cls._current and cls._current.winfo_exists():
                cls._current.destroy()
        except Exception:
            pass
        root = master.winfo_toplevel()
        fg, soft = tone(tone_name)
        top = tk.Toplevel(root)
        cls._current = top
        top.overrideredirect(True)
        try:
            top.attributes("-topmost", True)
        except Exception:
            pass
        top.configure(bg=BORDER)
        frame = tk.Frame(top, bg=soft)
        frame.pack(fill="both", expand=True, padx=1, pady=1)
        tk.Label(frame, text="✓" if tone_name == "green" else "•", font=F_SMALL_B,
                 fg=fg, bg=soft, padx=S(4)).pack(side="left", padx=(S(12), 0),
                                                pady=S(10))
        tk.Label(frame, text=message, font=F_SMALL_B, fg=fg, bg=soft,
                 padx=S(8)).pack(side="left", padx=(0, S(14)), pady=S(10))
        top.update_idletasks()
        w = max(S(220), top.winfo_reqwidth())
        h = top.winfo_reqheight()
        x = root.winfo_rootx() + root.winfo_width() - w - S(24)
        y = root.winfo_rooty() + root.winfo_height() - h - S(24)
        top.geometry(f"{w}x{h}+{max(0, x)}+{max(0, y)}")
        top.after(duration, lambda: cls._safe_destroy(top))

    @staticmethod
    def _safe_destroy(win):
        try:
            if win.winfo_exists():
                win.destroy()
        except Exception:
            pass


# --------------------------------------------------------------------------
# Dialogues
# --------------------------------------------------------------------------
class Modal(tk.Toplevel):
    """Fenêtre modale : en-tête, corps, pied de page avec boutons."""

    def __init__(self, master, title, subtitle=None, width=560, icon_text="✦",
                 tone_name="blue", show_footer=True, ok_label="Enregistrer"):
        super().__init__(master, bg=BG)
        self.withdraw()
        self.title(f"{title} — PatrimoinePro")
        self.resizable(False, False)
        self.transient(master.winfo_toplevel())
        self.result = None
        self.payload = None
        self._ok_label = ok_label
        self._on_submit = None
        self._error_var = tk.StringVar()

        outer = tk.Frame(self, bg=BG)
        outer.pack(fill="both", expand=True)

        # en-tête
        head = tk.Frame(outer, bg=SURFACE)
        head.pack(fill="x")
        inner_head = tk.Frame(head, bg=SURFACE)
        inner_head.pack(fill="x", padx=S(24), pady=S(18))
        fg, soft = tone(tone_name)
        badge = tk.Frame(inner_head, bg=soft, width=S(36), height=S(36))
        badge.pack(side="left", padx=(0, S(12)))
        badge.pack_propagate(False)
        tk.Label(badge, text=icon_text, font=(theme.FONT, 14), fg=fg, bg=soft).pack(
            expand=True)
        txt = tk.Frame(inner_head, bg=SURFACE)
        txt.pack(side="left", fill="x", expand=True)
        lbl(txt, title, (theme.FONT, 14, "bold"), TEXT, SURFACE).pack(anchor="w")
        if subtitle:
            lbl(txt, subtitle, F_SMALL, MUTED, SURFACE).pack(anchor="w", pady=(S(2), 0))
        close = tk.Label(inner_head, text="✕", font=(theme.FONT, 11), fg=FAINT,
                         bg=SURFACE, cursor="hand2", padx=S(4))
        close.pack(side="right", anchor="n")
        close.bind("<Button-1>", lambda e: self.cancel())
        tk.Frame(outer, bg=BORDER, height=1).pack(fill="x")

        self.body = tk.Frame(outer, bg=BG)
        self.body.pack(fill="both", expand=True, padx=S(24), pady=S(20))
        self.body.columnconfigure(0, weight=1)

        self.error_label = tk.Label(self.body, textvariable=self._error_var, font=F_SMALL,
                                    fg=RED_DARK, bg=BG, anchor="w", justify="left",
                                    wraplength=S(width - 60))
        self.footer = tk.Frame(outer, bg=SURFACE)
        if show_footer:
            tk.Frame(outer, bg=BORDER, height=1).pack(fill="x")
            self.footer.pack(fill="x")
            btns = tk.Frame(self.footer, bg=SURFACE)
            btns.pack(fill="x", padx=S(24), pady=S(14))
            self.cancel_btn = Button(btns, "Annuler", self.cancel, variant="secondary")
            self.cancel_btn.pack(side="right")
            self.ok_btn = Button(btns, ok_label, self.ok, variant="primary")
            self.ok_btn.pack(side="right", padx=(0, S(8)))
        else:
            self.cancel_btn = self.ok_btn = None

        self._width = width
        self.protocol("WM_DELETE_WINDOW", self.cancel)
        self.bind("<Escape>", lambda e: self.cancel())
        self.bind("<Return>", self._on_return)

    # ------------------------------------------------------------------
    def _on_return(self, event):
        widget = event.widget
        if isinstance(widget, tk.Text):
            return
        if self.ok_btn:
            self.ok()

    def field_label(self, text, row=None, required=False):
        l = lbl(self.body, text + (" *" if required else ""), F_SMALL_B, TEXT_SOFT, BG)
        if row is not None:
            l.grid(row=row, column=0, columnspan=2, sticky="w", pady=(S(10), S(4)))
        return l

    def show_error(self, message):
        """Affiche l'erreur en bas du formulaire et agrandit la fenêtre si besoin,
        pour que le message soit toujours visible."""
        self._error_var.set(message)
        if not self.error_label.winfo_ismapped():
            self.error_label.pack(fill="x", pady=(S(10), 0))
        self.update_idletasks()
        try:
            need = self.winfo_reqheight()
            current = self.winfo_height()
            if need > current + 1:
                width = max(self.winfo_width(), max(self.winfo_reqwidth(), S(self._width)))
                x, y = self.winfo_x(), self.winfo_y()
                screen_h = self.winfo_screenheight()
                if y + need > screen_h - S(20):
                    y = max(0, screen_h - need - S(20))
                self.geometry(f"{width}x{need}+{x}+{y}")
        except Exception:
            pass

    def clear_error(self):
        self._error_var.set("")
        self.error_label.pack_forget()

    def center(self):
        self.update_idletasks()
        w = max(self.winfo_reqwidth(), S(self._width))
        h = self.winfo_reqheight()
        parent = self.master.winfo_toplevel()
        px, py = parent.winfo_rootx(), parent.winfo_rooty()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        x = max(0, px + (pw - w) // 2)
        y = max(0, py + (ph - h) // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def show(self):
        self.center()
        self.deiconify()
        self.grab_set()
        self.focus_set()
        self.wait_window()
        return self.result

    # ------------------------------------------------------------------
    def validate(self) -> bool:
        return True

    def collect(self):
        """Données à conserver après la fermeture.

        Appelée par `ok()` **avant** la destruction de la fenêtre : les champs
        (Entry, Text, combos…) sont encore vivants. Les sous-classes retournent
        ici leurs valeurs ; elles sont disponibles ensuite dans `self.payload`.
        """
        return None

    def ok(self):
        self.clear_error()
        if not self.validate():
            return
        try:
            data = self.collect()
        except Exception as exc:  # écriture en base impossible, etc.
            self.show_error(f"Enregistrement impossible : {exc}")
            return
        self.payload = data
        self.result = True
        self.destroy()

    def cancel(self):
        self.result = None
        self.destroy()


class ConfirmDialog(Modal):
    def __init__(self, master, title, message, confirm_label="Confirmer",
                 tone_name="red", icon_text="!", ok_label=None):
        super().__init__(master, title, width=470, icon_text=icon_text,
                         tone_name=tone_name, ok_label=ok_label or confirm_label)
        self.body.configure(padx=0)
        lbl(self.body, message, F_BODY, TEXT_SOFT, BG, wraplength=S(410),
            justify="left").pack(fill="x")
        self.ok_btn.set_variant("danger" if tone_name == "red" else "primary")


def ask_confirm(master, title, message, confirm_label="Supprimer", tone_name="red",
                icon_text="!") -> bool:
    dlg = ConfirmDialog(master, title, message, confirm_label, tone_name, icon_text)
    return bool(dlg.show())


def show_info(master, title, message, tone_name="blue", icon_text="i", width=500):
    dlg = Modal(master, title, width=width, icon_text=icon_text, tone_name=tone_name,
                show_footer=True, ok_label="Fermer")
    dlg.body.configure(padx=0)
    lbl(dlg.body, message, F_BODY, TEXT_SOFT, BG, wraplength=S(width - 60),
        justify="left").pack(fill="x")
    dlg.cancel_btn.pack_forget()
    dlg.show()


class ColorField(tk.Frame):
    def __init__(self, master, value=PRIMARY, bg=None):
        super().__init__(master, bg=bg or BG)
        self.picker = ColorPicker(self, value=value, bg=bg or BG)
        self.picker.pack(anchor="w")

    def get(self):
        return self.picker.get()

    def set(self, color):
        self.picker.set(color)
