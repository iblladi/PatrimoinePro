"""Écran Budgets : enveloppes mensuelles par catégorie."""
from __future__ import annotations

import tkinter as tk

from .. import analytics, dialogs, theme, utils, widgets
from ..theme import (
    AMBER, AMBER_DARK, AMBER_SOFT, BORDER, FAINT, F_SMALL, F_SMALL_B, GREEN,
    GREEN_DARK, MUTED, PRIMARY, RED, RED_DARK, SURFACE, SURFACE_2, TEXT, TEXT_SOFT,
    VIOLET,
)
from ..utils import S
from .base import ScrollView, empty_state, page_header


class BudgetsView(ScrollView):
    def __init__(self, master, app):
        super().__init__(master, app)
        self.month = utils.today().replace(day=1)

    def build(self):
        db = self.db
        month_key = self.month.strftime("%Y-%m")
        overview = analytics.budget_overview(db, month_key)

        def actions(parent):
            widgets.Button(parent, "Ajouter un budget", self._add, variant="primary",
                           icon="+").pack(side="right")

        page_header(self.body, "Budgets",
                    "Comparez vos dépenses réelles à vos enveloppes mensuelles.", actions)

        # navigation de mois
        nav = tk.Frame(self.body, bg=theme.BG)
        nav.pack(fill="x", pady=(0, S(16)))
        widgets.Button(nav, "‹", lambda: self._shift(-1), variant="secondary",
                       width=S(34), height=32).pack(side="left")
        month_lbl = widgets.lbl(nav, utils.fmt_month(self.month).capitalize(),
                                (theme.FONT, 13, "bold"), TEXT, theme.BG)
        month_lbl.pack(side="left", padx=S(14))
        widgets.Button(nav, "›", lambda: self._shift(1), variant="secondary",
                       width=S(34), height=32).pack(side="left")
        if self.month.replace(day=1) != utils.today().replace(day=1):
            widgets.Button(nav, "Mois courant", self._today, variant="ghost",
                           height=30, font=theme.F_SMALL_B).pack(side="left", padx=(S(10), 0))
        widgets.Button(nav, "Copier le mois précédent", self._copy_previous,
                       variant="secondary", height=30, font=theme.F_SMALL_B).pack(side="right")

        if not overview["items"]:
            empty_state(self.body, "Aucun budget pour ce mois",
                        "Définissez un plafond de dépenses par catégorie pour suivre "
                        "vos enveloppes et anticiper les dépassements.",
                        "Définir un premier budget", self._add, icon="◔")
            self._unbudgeted_section(overview)
            return

        # ------------------------------------------------------ synthèse
        card = widgets.Card(self.body, padding=20)
        card.pack(fill="x")
        kpis = tk.Frame(card.content, bg=SURFACE)
        kpis.pack(fill="x")
        for i in range(3):
            kpis.columnconfigure(i, weight=1, uniform="b")
        fg, bgc = (RED_DARK, theme.RED_SOFT) if overview["pct"] > 1 else (
            (AMBER_DARK, AMBER_SOFT) if overview["pct"] > 0.85 else (GREEN_DARK, theme.GREEN_SOFT))

        self._kpi(kpis, 0, "Budget total", utils.fmt_money(overview["total_budget"], 0), TEXT)
        self._kpi(kpis, 1, "Dépensé", utils.fmt_money(overview["total_spent"], 0), TEXT)
        self._kpi(kpis, 2, "Reste disponible", utils.fmt_money(overview["remaining"], 0), fg)

        pb = widgets.ProgressBar(card.content, height=10,
                                 color=RED if overview["pct"] > 1 else
                                 (AMBER if overview["pct"] > 0.85 else GREEN))
        pb.pack(fill="x", pady=(S(14), S(4)))
        pb.set(min(overview["pct"], 1.0))
        widgets.lbl(card.content,
                    f"{utils.fmt_pct(overview['pct'] * 100)} du budget consommé"
                    + (f"  ·  dépassement de {utils.fmt_money(overview['total_spent'] - overview['total_budget'])}"
                       if overview["pct"] > 1 else ""),
                    F_SMALL, MUTED, SURFACE).pack(anchor="w")

        # ------------------------------------------------------ lignes
        list_card = widgets.Card(self.body, padding=0)
        list_card.pack(fill="x", pady=(S(14), 0))
        inner = tk.Frame(list_card.content, bg=SURFACE)
        inner.pack(fill="x", padx=S(18), pady=S(6))
        for i, item in enumerate(overview["items"]):
            self._budget_row(inner, item, month_key, i == 0)
            if i < len(overview["items"]) - 1:
                tk.Frame(inner, bg=theme.SURFACE_3, height=1).pack(fill="x")

        self._unbudgeted_section(overview)

    # ------------------------------------------------------------------
    def _kpi(self, parent, col, label, value, color):
        cell = tk.Frame(parent, bg=SURFACE)
        cell.grid(row=0, column=col, sticky="w")
        widgets.lbl(cell, label.upper(), (theme.FONT, 8, "bold"), MUTED, SURFACE).pack(anchor="w")
        widgets.lbl(cell, value, (theme.FONT, 17, "bold"), color, SURFACE).pack(
            anchor="w", pady=(S(3), 0))

    def _budget_row(self, parent, item, month_key, first=False):
        row = tk.Frame(parent, bg=SURFACE)
        row.pack(fill="x", pady=(S(10), S(10)))
        head = tk.Frame(row, bg=SURFACE)
        head.pack(fill="x")
        widgets.Dot(head, item["color"], 9, SURFACE).pack(side="left", padx=(0, S(7)))
        widgets.lbl(head, item["name"], F_SMALL_B, TEXT, SURFACE).pack(side="left")
        over = item["spent"] > item["budget"]
        widgets.Button(head, "Modifier", lambda it=item: self._edit(it), variant="ghost",
                       height=24, font=(theme.FONT, 8), padx=6).pack(side="right",
                                                                    padx=(S(6), 0))
        widgets.lbl(head, f"{utils.fmt_money(item['spent'])} / {utils.fmt_money(item['budget'])}",
                    (theme.FONT, 9, "bold"), RED_DARK if over else TEXT,
                    SURFACE).pack(side="right")

        line = tk.Frame(row, bg=SURFACE)
        line.pack(fill="x", pady=(S(6), 0))
        line.columnconfigure(0, weight=1)
        pct = item["pct"]
        color = RED if pct > 1 else (AMBER if pct > 0.85 else item["color"])
        pb = widgets.ProgressBar(line, height=7, color=color)
        pb.grid(row=0, column=0, sticky="ew")
        pb.set(min(pct, 1.0))
        widgets.lbl(line, utils.fmt_pct(pct * 100), (theme.FONT, 8, "bold"),
                    RED_DARK if pct > 1 else MUTED, SURFACE).grid(row=0, column=1,
                                                                 padx=(S(10), 0))
        rest_txt = (f"reste {utils.fmt_money(item['remaining'])}" if not over
                    else f"dépassement {utils.fmt_money(-item['remaining'])}")
        widgets.lbl(line, rest_txt, (theme.FONT, 8), RED_DARK if over else FAINT,
                    SURFACE).grid(row=0, column=2, padx=(S(10), 0), sticky="e")
        line.columnconfigure(2, minsize=S(120))

    def _unbudgeted_section(self, overview):
        db = self.db
        month_key = self.month.strftime("%Y-%m")
        budgeted = {i["category_id"] for i in overview["items"]}
        cats = [c for c in db.list_categories("depense") if c["id"] not in budgeted]
        if not cats:
            return
        start, end = utils.month_bounds(self.month)
        expenses, _ = analytics.expenses_by_category(db, start, end)
        by_name = {e["name"]: e["amount"] for e in expenses}
        spent_without = sum(by_name.get(c["name"], 0) for c in cats)

        widgets.lbl(self.body, "Catégories sans budget", theme.F_H2, TEXT,
                    theme.BG).pack(anchor="w", pady=(S(24), S(2)))
        widgets.lbl(self.body,
                    f"{utils.fmt_money(spent_without, 0)} de dépenses ce mois-ci dans "
                    f"{len(cats)} catégories non budgétées.",
                    F_SMALL, MUTED, theme.BG).pack(anchor="w", pady=(0, S(10)))

        card = widgets.Card(self.body, padding=0)
        card.pack(fill="x")
        inner = tk.Frame(card.content, bg=SURFACE)
        inner.pack(fill="x", padx=S(18), pady=S(6))
        for i, c in enumerate(cats):
            row = tk.Frame(inner, bg=SURFACE)
            row.pack(fill="x", pady=S(7))
            widgets.Dot(row, c["color"], 8, SURFACE).pack(side="left", padx=(0, S(7)))
            widgets.lbl(row, c["name"], F_SMALL, TEXT, SURFACE).pack(side="left")
            spent = by_name.get(c["name"], 0)
            if spent:
                widgets.lbl(row, utils.fmt_money(spent), (theme.FONT, 8), MUTED,
                            SURFACE).pack(side="left", padx=(S(10), 0))
            widgets.Button(row, "Définir", lambda cc=c: self._add(cc), variant="ghost",
                           height=24, font=(theme.FONT, 8), padx=6).pack(side="right")
            if i < len(cats) - 1:
                tk.Frame(inner, bg=theme.SURFACE_3, height=1).pack(fill="x")

    # ------------------------------------------------------------------
    def _shift(self, delta):
        self.month = utils.add_months(self.month.replace(day=1), delta)
        self.rebuild()

    def _today(self):
        self.month = utils.today().replace(day=1)
        self.rebuild()

    def _add(self, category=None):
        month_key = self.month.strftime("%Y-%m")
        current = 0
        if category:
            for r in self.db.budgets_for(month_key):
                if r["category_id"] == category["id"]:
                    current = float(r["amount"])
        dlg = dialogs.BudgetDialog(self, self.db, month_key, category=category, current=current)
        if dlg.show():
            message = dlg.apply()
            self.app.notify(message)
            self.rebuild()

    def _edit(self, item):
        cat = self.db.get_category(item["category_id"])
        self._add(cat)

    def _copy_previous(self):
        db = self.db
        prev = utils.add_months(self.month, -1)
        prev_key = prev.strftime("%Y-%m")
        month_key = self.month.strftime("%Y-%m")
        rows = db.budgets_for(prev_key)
        if not rows:
            self.app.notify("Aucun budget à copier depuis le mois précédent", "amber")
            return
        for r in rows:
            db.set_budget(r["category_id"], month_key, float(r["amount"]))
        self.app.notify(f"{len(rows)} budgets copiés depuis {utils.fmt_month(prev)}")
        self.rebuild()
