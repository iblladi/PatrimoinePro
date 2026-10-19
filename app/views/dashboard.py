"""Écran Tableau de bord : indicateurs, graphiques et aperçus."""
from __future__ import annotations

import datetime as dt
import tkinter as tk

from .. import analytics, theme, utils, widgets
from ..db import account_family
from ..theme import (
    AMBER, BG, BORDER, FAINT, F_SMALL, GREEN, GREEN_DARK, MUTED, PRIMARY,
    RED, RED_DARK, SURFACE, SURFACE_2, TEXT, TEXT_SOFT, VIOLET,
)
from ..utils import S
from .base import ScrollView, delta_chip, empty_state, page_header

DAY_NAMES = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]


class DashboardView(ScrollView):
    def build(self):
        db = self.db
        now = dt.datetime.now()
        today = now.date()
        subtitle = (f"{DAY_NAMES[today.weekday()].capitalize()} "
                    f"{today.day} {utils.MONTHS[today.month - 1]} {today.year}"
                    f"  ·  dernière actualisation à {now.strftime('%H:%M')}")

        def actions(parent):
            widgets.Button(parent, "Actualiser", self.rebuild, variant="secondary").pack(
                side="right", padx=(S(8), 0))
            widgets.Button(parent, "Nouvelle opération", self.app.new_transaction,
                           variant="primary", icon="+").pack(side="right")

        page_header(self.body, "Tableau de bord", subtitle, actions)

        accounts = db.list_accounts()
        if not accounts:
            empty_state(
                self.body, "Votre portefeuille est vide",
                "Ajoutez votre premier compte pour suivre votre patrimoine, vos dépenses "
                "et vos projets d'épargne.",
                "Ajouter un compte", self.app.new_account, icon="◈",
            )
            return

        total = analytics.total_net_worth(db)
        _, change = analytics.net_worth_change(db, 30)
        cur, prev = analytics.month_compare(db, today)
        projects = db.list_projects()
        metrics = {p["id"]: analytics.project_metrics(p, db.project_contributions(p["id"]))
                   for p in projects}
        saved_total = sum(m["saved"] for m in metrics.values())
        target_total = sum(float(p["target_amount"]) for p in projects) or 1.0
        budget = analytics.budget_overview(db, utils.month_key(today))

        # ---------------------------------------------------------- KPI
        kpi_row = tk.Frame(self.body, bg=BG)
        kpi_row.pack(fill="x")
        for i in range(4):
            kpi_row.columnconfigure(i, weight=1, uniform="kpi")

        k1 = widgets.KpiCard(kpi_row, "Patrimoine net", utils.fmt_money(total, 0),
                             "", "blue", icon="◈")
        k1.grid(row=0, column=0, sticky="nsew", padx=(0, S(14)))
        up = change >= 0
        k1.hint_label.configure(
            text=f"{'+' if up else '−'}{utils.fmt_money(abs(change), 0)} sur 30 jours",
            fg=GREEN_DARK if up else RED_DARK,
        )

        def variation(cur_v, prev_v):
            if prev_v <= 0:
                return "—", MUTED
            pct = (cur_v - prev_v) / prev_v * 100
            if abs(pct) < 0.5:
                return "Stable vs mois dernier", MUTED
            arrow = "▲" if pct > 0 else "▼"
            color = GREEN_DARK if pct > 0 else RED_DARK
            return f"{arrow} {utils.fmt_pct(abs(pct))} vs mois dernier", color

        k2 = widgets.KpiCard(kpi_row, "Revenus du mois", utils.fmt_money(cur["income"], 0),
                             "", "green", icon="↑")
        k2.grid(row=0, column=1, sticky="nsew", padx=(0, S(14)))
        txt, col = variation(cur["income"], prev["income"])
        k2.hint_label.configure(text=txt, fg=col)

        k3 = widgets.KpiCard(kpi_row, "Dépenses du mois", utils.fmt_money(cur["expense"], 0),
                             "", "amber", icon="↓")
        k3.grid(row=0, column=2, sticky="nsew", padx=(0, S(14)))
        if budget["total_budget"] > 0:
            k3.hint_label.configure(
                text=f"{utils.fmt_pct(budget['pct'] * 100)} du budget mensuel",
                fg=RED_DARK if budget["pct"] > 1 else MUTED,
            )
        else:
            txt, col = variation(cur["expense"], prev["expense"])
            k3.hint_label.configure(text=txt, fg=col)

        k4 = widgets.KpiCard(kpi_row, "Épargne des projets",
                             utils.fmt_money(saved_total, 0), "", "violet", icon="◎")
        k4.grid(row=0, column=3, sticky="nsew")
        k4.hint_label.configure(
            text=f"{len(projects)} projets · {utils.fmt_pct(saved_total / target_total * 100)} "
                 f"des objectifs",
            fg=MUTED,
        )

        # -------------------------------------------------- évolution + répartition
        grid = tk.Frame(self.body, bg=BG)
        grid.pack(fill="x", pady=(S(16), 0))
        grid.columnconfigure(0, weight=3, uniform="main")
        grid.columnconfigure(1, weight=2, uniform="main")

        series = analytics.net_worth_series(db, 12)
        evolution = widgets.Card(grid, title="Évolution du patrimoine", padding=18)
        evolution.grid(row=0, column=0, sticky="nsew", padx=(0, S(16)))
        chart = widgets.LineChart(evolution.content, height=212)
        chart.pack(fill="x", pady=(S(10), 0))
        chart.set_data([(utils.MONTHS_SHORT[d.month - 1], v) for d, v in series])
        if len(series) > 1:
            gain = series[-1][1] - series[0][1]
            chip = delta_chip(evolution.header_right, gain, " sur 12 mois", SURFACE)
            chip.pack(side="right")

        # répartition par famille de comptes (courant, épargne, placements…)
        by_family = {}
        for a in accounts:
            key = account_family(a["type"])
            by_family.setdefault(key, 0.0)
            by_family[key] += float(a["balance"] or 0)
        repart = widgets.Card(grid, title="Répartition", padding=18)
        repart.grid(row=0, column=1, sticky="nsew")
        rep_body = tk.Frame(repart.content, bg=SURFACE)
        rep_body.pack(fill="both", expand=True, pady=(S(8), 0))
        donut = widgets.DonutChart(rep_body, size=170, thickness=20)
        donut.pack(side="left")
        legend = tk.Frame(rep_body, bg=SURFACE)
        legend.pack(side="left", fill="both", expand=True, padx=(S(16), 0))
        types_sorted = sorted(by_family.items(), key=lambda kv: -kv[1])
        donut.set_data([(v, _family_color(k)) for k, v in types_sorted], total, "Patrimoine")
        for key, value in types_sorted:
            label = _family_label(key)
            pct = value / total * 100 if total else 0
            row = tk.Frame(legend, bg=SURFACE)
            row.pack(fill="x", pady=(0, S(8)))
            widgets.Dot(row, _family_color(key), 9, SURFACE).pack(
                side="left", padx=(0, S(8)), anchor="n", pady=(S(3), 0))
            texts = tk.Frame(row, bg=SURFACE)
            texts.pack(side="left", fill="x", expand=True)
            widgets.lbl(texts, label, F_SMALL, TEXT, SURFACE).pack(anchor="w")
            widgets.lbl(texts, f"{utils.fmt_money(value, 0)}  ·  {utils.fmt_pct(pct, 0)}",
                        (theme.FONT, 8), MUTED, SURFACE).pack(anchor="w")

        # -------------------------------------------------- flux + dépenses
        grid2 = tk.Frame(self.body, bg=BG)
        grid2.pack(fill="x", pady=(S(16), 0))
        grid2.columnconfigure(0, weight=3, uniform="m2")
        grid2.columnconfigure(1, weight=2, uniform="m2")

        flows = widgets.Card(grid2, title="Revenus et dépenses", padding=18)
        flows.grid(row=0, column=0, sticky="nsew", padx=(0, S(16)))
        legend_bar = tk.Frame(flows.content, bg=SURFACE)
        legend_bar.pack(fill="x")
        for label, color in (("Revenus", GREEN), ("Dépenses", RED)):
            box = tk.Frame(legend_bar, bg=SURFACE)
            box.pack(side="left", padx=(0, S(14)))
            widgets.Dot(box, color, 8, SURFACE).pack(side="left", padx=(0, S(5)))
            widgets.lbl(box, label, F_SMALL, MUTED, SURFACE).pack(side="left")
        flows.content.pack_configure(pady=(S(10), 0))
        bars = widgets.BarsChart(flows.content, height=186)
        bars.pack(fill="x", pady=(S(6), 0))
        series_flows = analytics.flows_series(db, 6)
        bars.set_data([(f["label"], [(f["income"], GREEN), (f["expense"], RED)])
                       for f in series_flows])

        cats, cat_total = analytics.expenses_by_category(db, *utils.month_bounds(today))
        spend = widgets.Card(grid2, title="Dépenses du mois", padding=18)
        spend.grid(row=0, column=1, sticky="nsew")
        if cats:
            chip = widgets.Chip(spend.header_right, utils.fmt_money(cat_total, 0),
                                RED_DARK, theme.RED_SOFT, SURFACE)
            chip.pack(side="right")
        else:
            widgets.lbl(spend.content, "Aucune dépense ce mois-ci.", F_SMALL, FAINT, SURFACE).pack(
                anchor="w", pady=S(10))
        spend.content.pack_configure(pady=(S(6), 0))
        top = cats[:5]
        max_amount = max((c["amount"] for c in top), default=1)
        for item in top:
            row = tk.Frame(spend.content, bg=SURFACE)
            row.pack(fill="x", pady=(S(6), 0))
            head = tk.Frame(row, bg=SURFACE)
            head.pack(fill="x")
            widgets.Dot(head, item["color"], 8, SURFACE).pack(side="left", padx=(0, S(6)))
            widgets.lbl(head, item["name"], F_SMALL, TEXT, SURFACE).pack(side="left")
            widgets.lbl(head, utils.fmt_money(item["amount"], 0), (theme.FONT, 9, "bold"),
                        TEXT, SURFACE).pack(side="right")
            pb = widgets.ProgressBar(row, height=5, color=item["color"])
            pb.pack(fill="x", pady=(S(4), 0))
            pb.set(item["amount"] / max_amount if max_amount else 0)

        # -------------------------------------------------- projets + opérations
        grid3 = tk.Frame(self.body, bg=BG)
        grid3.pack(fill="x", pady=(S(16), 0))
        grid3.columnconfigure(0, weight=3, uniform="m3")
        grid3.columnconfigure(1, weight=2, uniform="m3")

        proj_card = widgets.Card(grid3, title="Projets d'épargne", padding=18)
        proj_card.grid(row=0, column=0, sticky="nsew", padx=(0, S(16)))
        link = widgets.Button(proj_card.header_right, "Tout voir", lambda: self.app.navigate("projects"),
                              variant="ghost", height=26, padx=8, font=theme.F_SMALL_B)
        link.pack(side="right")
        proj_card.content.pack_configure(pady=(S(8), 0))
        if not projects:
            widgets.lbl(proj_card.content, "Aucun projet pour l'instant.", F_SMALL, FAINT,
                        SURFACE).pack(anchor="w", pady=S(8))
        for p in projects[:4]:
            m = metrics[p["id"]]
            row = tk.Frame(proj_card.content, bg=SURFACE)
            row.pack(fill="x", pady=(S(7), 0))
            top_row = tk.Frame(row, bg=SURFACE)
            top_row.pack(fill="x")
            widgets.Dot(top_row, p["color"], 8, SURFACE).pack(side="left", padx=(0, S(6)))
            widgets.lbl(top_row, p["name"], F_SMALL, TEXT, SURFACE).pack(side="left")
            widgets.lbl(top_row, utils.fmt_money(m["saved"], 0) + " / " +
                        utils.fmt_money(m["target"], 0),
                        (theme.FONT, 8, "bold"), MUTED, SURFACE).pack(side="right")
            pb = widgets.ProgressBar(row, height=6, color=p["color"])
            pb.pack(fill="x", pady=(S(4), 0))
            pb.set(m["pct"])

        recent_card = widgets.Card(grid3, title="Dernières opérations", padding=18)
        recent_card.grid(row=0, column=1, sticky="nsew")
        go = widgets.Button(recent_card.header_right, "Tout voir",
                            lambda: self.app.navigate("transactions"),
                            variant="ghost", height=26, padx=8, font=theme.F_SMALL_B)
        go.pack(side="right")
        recent_card.content.pack_configure(pady=(S(6), 0))
        rows = db.recent_transactions(6)
        if not rows:
            widgets.lbl(recent_card.content, "Aucune opération.", F_SMALL, FAINT,
                        SURFACE).pack(anchor="w", pady=S(8))
        for r in rows:
            amount = float(r["amount"])
            row = tk.Frame(recent_card.content, bg=SURFACE)
            row.pack(fill="x", pady=S(4))
            left = tk.Frame(row, bg=SURFACE)
            left.pack(side="left", fill="x", expand=True)
            color = r["category_color"] if r["transfer_id"] is None and r["category_color"] else FAINT
            widgets.Dot(left, color, 7, SURFACE).pack(side="left", padx=(0, S(6)))
            txt = tk.Frame(left, bg=SURFACE)
            txt.pack(side="left")
            widgets.lbl(txt, utils.elide(db._tx_label(r), 26), F_SMALL, TEXT, SURFACE).pack(anchor="w")
            widgets.lbl(txt, utils.fmt_date(r["date"], True) + " · " + r["account_name"],
                        (theme.FONT, 8), FAINT, SURFACE).pack(anchor="w")
            widgets.lbl(row, utils.fmt_money(amount), (theme.FONT, 9, "bold"),
                        GREEN_DARK if amount >= 0 else TEXT, SURFACE).pack(side="right")


def _family_color(key: str) -> str:
    from ..db import ACCOUNT_FAMILIES
    return ACCOUNT_FAMILIES.get(key, ("", PRIMARY))[1]


def _family_label(key: str) -> str:
    from ..db import ACCOUNT_FAMILIES
    return ACCOUNT_FAMILIES.get(key, ("Autre", PRIMARY))[0]
