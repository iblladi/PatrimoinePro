"""Fenêtre principale, navigation et actions globales."""
from __future__ import annotations

import os
import sys
import traceback
import tkinter as tk
from tkinter import messagebox

from . import __app_name__, __version__, analytics, dialogs, theme, utils, widgets
from .db import Database
from .theme import (
    BG, BORDER, FAINT, F_SMALL, F_SMALL_B, GREEN_DARK, MUTED, PRIMARY, RED,
    SIDEBAR, SIDEBAR_2, SIDEBAR_ACTIVE, SIDEBAR_HOVER, SIDEBAR_MUTED, SIDEBAR_TEXT,
    SURFACE, TEXT, VIOLET,
)
from .utils import S
from .views.accounts import AccountsView
from .views.budgets import BudgetsView
from .views.dashboard import DashboardView
from .views.projects import ProjectsView
from .views.settings import SettingsView
from .views.transactions import TransactionsView

NAV_ITEMS = [
    ("dashboard", "Tableau de bord", "grid"),
    ("accounts", "Portefeuille", "wallet"),
    ("transactions", "Transactions", "arrows"),
    ("projects", "Projets d'épargne", "target"),
    ("budgets", "Budgets", "pie"),
    ("settings", "Paramètres", "gear"),
]

VIEW_CLASSES = {
    "dashboard": DashboardView,
    "accounts": AccountsView,
    "transactions": TransactionsView,
    "projects": ProjectsView,
    "budgets": BudgetsView,
    "settings": SettingsView,
}


def enable_dpi_awareness():
    if sys.platform != "win32":
        return
    try:
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def resource_path(relative: str) -> str:
    base = getattr(sys, "_MEIPASS", None)
    if not base:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative)


# --------------------------------------------------------------------------
# Icônes vectorielles de navigation
# --------------------------------------------------------------------------
class NavIcon(tk.Canvas):
    def __init__(self, master, kind, color=SIDEBAR_TEXT, size=18, bg=SIDEBAR):
        super().__init__(master, width=S(size), height=S(size), bg=bg,
                         highlightthickness=0, bd=0)
        self._kind = kind
        self._color = color
        self._size = S(size)
        self.draw()

    def set_color(self, color):
        self._color = color
        self.draw()

    def draw(self):
        self.delete("all")
        c = self._color
        s = self._size
        u = s / 18.0
        w = max(1, int(round(1.4 * u)))
        k = self._kind
        if k == "grid":
            for x, y in ((1, 1), (10, 1), (1, 10), (10, 10)):
                self.create_rectangle(x * u, y * u, (x + 7) * u, (y + 7) * u,
                                      outline=c, width=w)
        elif k == "wallet":
            self.create_rectangle(1 * u, 4 * u, 17 * u, 15 * u, outline=c, width=w)
            self.create_line(1 * u, 7 * u, 17 * u, 7 * u, fill=c, width=w)
            self.create_oval(12 * u, 9.5 * u, 14 * u, 11.5 * u, outline=c, width=w)
        elif k == "arrows":
            self.create_line(2 * u, 6 * u, 15 * u, 6 * u, fill=c, width=w,
                             arrow="last", arrowshape=(4 * u, 4 * u, 2 * u))
            self.create_line(16 * u, 12 * u, 3 * u, 12 * u, fill=c, width=w,
                             arrow="last", arrowshape=(4 * u, 4 * u, 2 * u))
        elif k == "target":
            self.create_oval(1 * u, 1 * u, 17 * u, 17 * u, outline=c, width=w)
            self.create_oval(6 * u, 6 * u, 12 * u, 12 * u, outline=c, width=w)
            self.create_oval(8.2 * u, 8.2 * u, 9.8 * u, 9.8 * u, fill=c, outline=c)
        elif k == "pie":
            self.create_oval(2 * u, 2 * u, 16 * u, 16 * u, outline=c, width=w)
            self.create_line(9 * u, 9 * u, 9 * u, 2 * u, fill=c, width=w)
            self.create_line(9 * u, 9 * u, 16 * u, 12 * u, fill=c, width=w)
        elif k == "gear":
            import math
            self.create_oval(6 * u, 6 * u, 12 * u, 12 * u, outline=c, width=w)
            for i in range(8):
                a = math.pi / 4 * i
                x1 = 9 * u + math.cos(a) * 5.2 * u
                y1 = 9 * u + math.sin(a) * 5.2 * u
                x2 = 9 * u + math.cos(a) * 7.6 * u
                y2 = 9 * u + math.sin(a) * 7.6 * u
                self.create_line(x1, y1, x2, y2, fill=c, width=w)


class NavItem(tk.Frame):
    def __init__(self, master, key, label, icon, command, active=False):
        super().__init__(master, bg=SIDEBAR, cursor="hand2")
        self.key = key
        self._command = command
        self._active = active
        self.accent = tk.Frame(self, bg=SIDEBAR, width=S(3))
        self.accent.pack(side="left", fill="y")
        self.inner = tk.Frame(self, bg=SIDEBAR)
        self.inner.pack(side="left", fill="both", expand=True, padx=(S(14), S(10)),
                        pady=S(9))
        self.icon = NavIcon(self.inner, icon, SIDEBAR_TEXT, 18, SIDEBAR)
        self.icon.pack(side="left", padx=(0, S(11)))
        self.label = tk.Label(self.inner, text=label, font=F_SMALL_B, fg=SIDEBAR_TEXT,
                              bg=SIDEBAR, anchor="w")
        self.label.pack(side="left")
        for w in (self, self.inner, self.icon, self.label):
            w.bind("<Button-1>", self._click)
            w.bind("<Enter>", self._enter)
            w.bind("<Leave>", self._leave)

    def _click(self, _):
        self._command(self.key)

    def _enter(self, _):
        if not self._active:
            for w in (self, self.inner, self.label):
                w.configure(bg=SIDEBAR_HOVER)
            self.icon.configure(bg=SIDEBAR_HOVER)
            self.icon.set_color("#C7D3E4")
            self.label.configure(fg="#C7D3E4")

    def _leave(self, _):
        if not self._active:
            for w in (self, self.inner, self.label):
                w.configure(bg=SIDEBAR)
            self.icon.configure(bg=SIDEBAR)
            self.icon.set_color(SIDEBAR_TEXT)
            self.label.configure(fg=SIDEBAR_TEXT)

    def set_active(self, active: bool):
        self._active = active
        bg = SIDEBAR_ACTIVE if active else SIDEBAR
        for w in (self, self.inner, self.label):
            w.configure(bg=bg)
        self.icon.configure(bg=bg)
        self.accent.configure(bg=PRIMARY if active else SIDEBAR)
        self.icon.set_color("#FFFFFF" if active else SIDEBAR_TEXT)
        self.label.configure(fg="#FFFFFF" if active else SIDEBAR_TEXT,
                            font=(theme.FONT, 9, "bold" if active else "normal"))


# --------------------------------------------------------------------------
# Application
# --------------------------------------------------------------------------
class App(tk.Tk):
    def __init__(self, db: Database | None = None):
        enable_dpi_awareness()
        super().__init__()
        self._apply_scale()
        self.db = db or Database()
        utils.set_currency(self.db.get_setting("currency", "€"))
        theme.setup(self)

        self.title("PatrimoinePro — Gestion de portefeuille et projets d'épargne")
        self.configure(bg=BG)
        width, height = S(1300), S(860)
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        width, height = min(width, sw - S(60)), min(height, sh - S(80))
        x = (sw - width) // 2
        y = max(0, (sh - height) // 2 - S(20))
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.minsize(S(1080), S(720))
        self._set_icon()
        self.report_callback_exception = self._on_tk_error

        self.current = None
        self.current_key = None
        self._build_shell()
        self._bind_shortcuts()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(120, self._on_ready)

    # ------------------------------------------------------------------
    def _apply_scale(self):
        try:
            dpi = self.winfo_fpixels("1i")
            utils.set_ui_scale(dpi / 96.0)
            self.tk.call("tk", "scaling", dpi / 72.0)
        except Exception:
            utils.set_ui_scale(1.0)

    def _set_icon(self):
        for name in ("assets/icon.ico", "icon.ico"):
            path = resource_path(name)
            if os.path.exists(path):
                try:
                    self.iconbitmap(path)
                    return
                except Exception:
                    pass

    def _on_tk_error(self, exc, value, tb):
        traceback.print_exception(exc, value, tb)
        try:
            messagebox.showerror(
                "Erreur inattendue",
                f"Une erreur est survenue :\n\n{value}\n\nL'application reste utilisable.",
                parent=self,
            )
        except Exception:
            pass

    # ------------------------------------------------------------------
    def _build_shell(self):
        sidebar = tk.Frame(self, bg=SIDEBAR, width=S(238))
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        self.sidebar = sidebar

        brand = tk.Frame(sidebar, bg=SIDEBAR)
        brand.pack(fill="x", padx=S(18), pady=(S(22), S(18)))
        logo = tk.Canvas(brand, width=S(36), height=S(36), bg=SIDEBAR,
                         highlightthickness=0, bd=0)
        logo.pack(side="left")
        widgets.round_rect(logo, 0, 0, S(36), S(36), S(10), fill=PRIMARY, outline=PRIMARY)
        logo.create_text(S(18), S(18) + 1, text="P", fill="#FFFFFF",
                         font=(theme.FONT, 15, "bold"))
        btxt = tk.Frame(brand, bg=SIDEBAR)
        btxt.pack(side="left", padx=(S(10), 0))
        tk.Label(btxt, text="PatrimoinePro", font=(theme.FONT, 12, "bold"),
                 fg="#FFFFFF", bg=SIDEBAR, anchor="w").pack(anchor="w")
        tk.Label(btxt, text="Portefeuille & épargne", font=(theme.FONT, 8),
                 fg=SIDEBAR_MUTED, bg=SIDEBAR, anchor="w").pack(anchor="w")

        tk.Label(sidebar, text="NAVIGATION", font=(theme.FONT, 7, "bold"),
                 fg=SIDEBAR_MUTED, bg=SIDEBAR, anchor="w").pack(
            fill="x", padx=S(22), pady=(0, S(6)))

        self.nav_items = {}
        for key, label, icon in NAV_ITEMS:
            item = NavItem(sidebar, key, label, icon, self.navigate)
            item.pack(fill="x", pady=(0, S(2)))
            self.nav_items[key] = item

        # bloc patrimoine en bas
        bottom = tk.Frame(sidebar, bg=SIDEBAR)
        bottom.pack(side="bottom", fill="x", padx=S(16), pady=(S(10), S(14)))
        box = tk.Frame(bottom, bg=SIDEBAR_2)
        box.pack(fill="x")
        tk.Label(box, text="PATRIMOINE NET", font=(theme.FONT, 7, "bold"),
                 fg=SIDEBAR_MUTED, bg=SIDEBAR_2, anchor="w").pack(
            anchor="w", padx=S(12), pady=(S(10), 0))
        self.sidebar_total = tk.Label(box, text="—", font=(theme.FONT, 14, "bold"),
                                      fg="#FFFFFF", bg=SIDEBAR_2, anchor="w")
        self.sidebar_total.pack(anchor="w", padx=S(12))
        self.sidebar_hint = tk.Label(box, text="", font=(theme.FONT, 7),
                                     fg=SIDEBAR_MUTED, bg=SIDEBAR_2, anchor="w")
        self.sidebar_hint.pack(anchor="w", padx=S(12), pady=(0, S(10)))
        tk.Label(bottom, text=f"Version {__version__}", font=(theme.FONT, 7),
                 fg=SIDEBAR_MUTED, bg=SIDEBAR).pack(anchor="w", padx=S(2), pady=(S(10), 0))

        self.content = tk.Frame(self, bg=BG)
        self.content.pack(side="left", fill="both", expand=True)

        self.views = {key: cls(self.content, self) for key, cls in VIEW_CLASSES.items()}

    def _update_sidebar(self):
        total = analytics.total_net_worth(self.db)
        self.sidebar_total.configure(text=utils.fmt_money(total, 0))
        _, change = analytics.net_worth_change(self.db, 30)
        sign = "+" if change >= 0 else "−"
        color = "#6EE7B7" if change >= 0 else "#FCA5A5"
        self.sidebar_hint.configure(text=f"{sign}{utils.fmt_money(abs(change), 0)} sur 30 jours",
                                    fg=color)

    # ------------------------------------------------------------------
    def navigate(self, key, **params):
        if key not in self.views:
            return
        view = self.views[key]
        if self.current is not None and self.current is not view:
            self.current.pack_forget()
        if self.current is not view:
            view.pack(fill="both", expand=True)
        self.current = view
        self.current_key = key
        for k, item in self.nav_items.items():
            item.set_active(k == key)
        view.on_show(**params)
        self._update_sidebar()

    def refresh(self):
        if self.current is not None:
            self.current.rebuild()
        self._update_sidebar()

    def notify(self, message, tone_name="green"):
        try:
            widgets.Toast.show(self, message, tone_name)
        except Exception:
            pass
        self.refresh()

    # ------------------------------------------------------------------
    def new_transaction(self, preset_account=None):
        dlg = dialogs.TransactionDialog(self, self.db, preset_account=preset_account)
        if dlg.show():
            self.notify(dlg.payload)

    def edit_transaction(self, row):
        dlg = dialogs.TransactionDialog(self, self.db, transaction=row)
        if dlg.show():
            self.notify(dlg.payload)

    def new_account(self):
        dlg = dialogs.AccountDialog(self)
        if dlg.show() and dlg.payload:
            self.db.add_account(**dlg.payload)
            self.notify("Compte ajouté")
            self.navigate("accounts")

    def edit_account(self, account):
        dlg = dialogs.AccountDialog(self, account=account)
        if dlg.show() and dlg.payload:
            self.db.update_account(account["id"], **dlg.payload)
            self.notify("Compte mis à jour")
            self.refresh()

    def new_project(self):
        dlg = dialogs.ProjectDialog(self, self.db)
        if dlg.show() and dlg.payload:
            self.db.add_project(**dlg.payload)
            self.notify("Projet créé")
            self.navigate("projects")

    def edit_project(self, project):
        dlg = dialogs.ProjectDialog(self, self.db, project=project)
        if dlg.show() and dlg.payload:
            self.db.update_project(project["id"], **dlg.payload)
            self.notify("Projet mis à jour")
            self.refresh()

    # ------------------------------------------------------------------
    def _bind_shortcuts(self):
        self.bind("<Control-n>", lambda e: self.new_transaction())
        self.bind("<Control-N>", lambda e: self.new_transaction())
        self.bind("<F5>", lambda e: self.refresh())
        self.bind("<MouseWheel>", self._on_mousewheel)
        for index, (key, _label, _icon) in enumerate(NAV_ITEMS, start=1):
            self.bind(f"<Control-Key-{index}>", lambda e, k=key: self.navigate(k))

    def _on_mousewheel(self, event):
        """Fait défiler l'écran courant : la molette est captée au niveau de la fenêtre
        car les widgets enfants du canvas ne propagent pas <Enter>/<Leave>."""
        view = self.current
        scroller = getattr(view, "scroll", None) if view is not None else None
        if scroller is None:
            return None
        try:
            scroller.scroll_by(event.delta)
        except Exception:
            pass
        return "break"

    def _on_ready(self):
        self.navigate("dashboard")
        self._maybe_welcome()

    def _maybe_welcome(self):
        if not self.db.is_empty() or self.db.get_setting("first_run_done") == "1":
            return
        dlg = widgets.Modal(
            self, "Bienvenue dans PatrimoinePro",
            "Gérez votre portefeuille et vos projets d'épargne, hors ligne.",
            width=560, icon_text="✶", tone_name="blue",
            ok_label="Découvrir avec un exemple",
        )
        widgets.lbl(dlg.body,
                    "Cette application enregistre vos comptes, vos opérations, vos budgets "
                    "et vos objectifs d'épargne dans une base de données locale.",
                    theme.F_BODY, theme.TEXT_SOFT, BG, wraplength=S(490),
                    justify="left").pack(fill="x")
        widgets.lbl(dlg.body,
                    "Souhaitez-vous commencer avec un portefeuille de démonstration "
                    "(4 comptes, 15 mois d'opérations, 4 projets) ou partir d'une base vide ?",
                    theme.F_SMALL, MUTED, BG, wraplength=S(490),
                    justify="left").pack(fill="x", pady=(S(12), 0))
        dlg.cancel_btn.set_text("Partir de zéro")
        result = dlg.show()
        self.db.set_setting("first_run_done", "1")
        if result:
            self.db.seed_demo()
            self.notify("Données de démonstration chargées")
            self.navigate("dashboard")
        else:
            self.navigate("dashboard")
            self.new_account()

    def _on_close(self):
        try:
            self.db.close()
        finally:
            self.destroy()


def main():
    db = Database()
    app = App(db=db)
    app.mainloop()


if __name__ == "__main__":
    main()
