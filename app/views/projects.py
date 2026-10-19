"""Écran Projets d'épargne : objectifs, progression et versements."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .. import analytics, dialogs, theme, utils, widgets
from ..db import PRIORITIES
from ..theme import (
    AMBER, BORDER, FAINT, F_SMALL, F_SMALL_B, GREEN, GREEN_DARK, MUTED, PRIMARY,
    PRIMARY_DARK, PRIMARY_SOFT, RED, RED_DARK, SURFACE, SURFACE_2, TEXT, TEXT_SOFT,
    VIOLET,
)
from ..utils import S
from .accounts import avatar
from .base import ScrollView, empty_state, page_header


class ProjectsView(ScrollView):
    def build(self):
        db = self.db
        projects = db.list_projects(include_archived=True)
        active = [p for p in projects if p["status"] != "archive"]
        metrics = {p["id"]: analytics.project_metrics(p, db.project_contributions(p["id"]))
                   for p in active}

        saved_total = sum(m["saved"] for m in metrics.values())
        target_total = sum(float(p["target_amount"]) for p in active)
        pct_total = saved_total / target_total if target_total else 0

        def actions(parent):
            widgets.Button(parent, "Nouveau projet", self.app.new_project,
                           variant="primary", icon="+").pack(side="right")

        page_header(self.body, "Projets d'épargne",
                    "Suivez vos objectifs, votre rythme et vos échéances.", actions)

        if not active:
            empty_state(self.body, "Aucun projet d'épargne",
                        "Créez un objectif (voyage, apport immobilier, fonds d'urgence…) "
                        "et suivez sa progression mois après mois.",
                        "Créer un projet", self.app.new_project, icon="◎")
            return

        # ------------------------------------------------------- synthèse
        summary = tk.Frame(self.body, bg=theme.BG)
        summary.pack(fill="x", pady=(0, S(16)))
        for i in range(3):
            summary.columnconfigure(i, weight=1, uniform="ps")

        def stat(col, label, value, hint, color):
            card = widgets.Card(summary, padding=16)
            card.grid(row=0, column=col, sticky="nsew",
                      padx=(0, S(14)) if col < 2 else 0)
            widgets.lbl(card.content, label.upper(), (theme.FONT, 8, "bold"), MUTED,
                        SURFACE).pack(anchor="w")
            widgets.lbl(card.content, value, (theme.FONT, 18, "bold"), TEXT,
                        SURFACE).pack(anchor="w", pady=(S(4), S(2)))
            widgets.lbl(card.content, hint, (theme.FONT, 8), FAINT, SURFACE).pack(anchor="w")
            bar = tk.Frame(card.content, bg=color, height=S(3))
            bar.pack(fill="x", pady=(S(8), 0))

        stat(0, "Épargne cumulée", utils.fmt_money(saved_total, 0),
             f"sur {len(active)} projets", PRIMARY)
        stat(1, "Objectifs visés", utils.fmt_money(target_total, 0),
             f"reste {utils.fmt_money(max(target_total - saved_total, 0), 0)}", VIOLET)
        stat(2, "Progression globale", utils.fmt_pct(pct_total * 100, 0),
             "tous projets confondus", GREEN)

        up = analytics.upcomings(db, 1)
        if up:
            date_, p, m = up[0]
            widgets.lbl(self.body,
                        f"Prochaine échéance : {p['name']} le {utils.fmt_date_long(date_)}"
                        f" — reste {utils.fmt_money(m['remaining'], 0)} à épargner.",
                        F_SMALL, MUTED, theme.BG).pack(anchor="w", pady=(0, S(14)))

        # ------------------------------------------------------- cartes
        grid = tk.Frame(self.body, bg=theme.BG)
        grid.pack(fill="x")
        grid.columnconfigure(0, weight=1, uniform="proj")
        grid.columnconfigure(1, weight=1, uniform="proj")
        for i, p in enumerate(active):
            card = self._project_card(grid, p, metrics[p["id"]])
            card.grid(row=i // 2, column=i % 2, sticky="nsew",
                      padx=(0, S(14)) if i % 2 == 0 else 0, pady=(0, S(14)))

    # ------------------------------------------------------------------
    def _project_card(self, parent, p, m):
        card = widgets.Card(parent, padding=16)
        head = tk.Frame(card.content, bg=SURFACE)
        head.pack(fill="x")
        avatar(head, p["color"], "◎", 38).pack(side="left", padx=(0, S(10)))
        info = tk.Frame(head, bg=SURFACE)
        info.pack(side="left", fill="x", expand=True)
        widgets.lbl(info, utils.elide(p["name"], 30), (theme.FONT, 11, "bold"), TEXT,
                    SURFACE).pack(anchor="w")
        prio = PRIORITIES.get(int(p["priority"]), "Moyenne")
        detail = f"Priorité {prio.lower()}"
        if p["account_name"]:
            detail += f"  ·  {p['account_name']}"
        widgets.lbl(info, utils.elide(detail, 40), (theme.FONT, 8), FAINT,
                    SURFACE).pack(anchor="w")

        fg, soft = theme.tone(m["tone"])
        chip = widgets.Chip(head, m["status"], fg, soft, SURFACE)
        chip.pack(side="right", anchor="n", padx=(0, S(4)))
        menu_btn = widgets.MenuButton(head, bg=SURFACE, size=26)
        menu_btn.pack(side="right", anchor="n")
        menu_btn.set_command(lambda b=menu_btn, pr=p: self._menu(b, pr))

        body = tk.Frame(card.content, bg=SURFACE)
        body.pack(fill="x", pady=(S(12), 0))
        top = tk.Frame(body, bg=SURFACE)
        top.pack(fill="x")
        widgets.lbl(top, utils.fmt_money(m["saved"], 0), (theme.FONT, 18, "bold"), TEXT,
                    SURFACE).pack(side="left")
        widgets.lbl(top, f" / {utils.fmt_money(m['target'], 0)}", F_SMALL, MUTED,
                    SURFACE).pack(side="left", pady=(S(6), 0))
        widgets.lbl(top, utils.fmt_pct(m["pct"] * 100, 0), (theme.FONT, 10, "bold"),
                    p["color"], SURFACE).pack(side="right", pady=(S(4), 0))

        pb = widgets.ProgressBar(body, height=8, color=p["color"])
        pb.pack(fill="x", pady=(S(6), S(10)))
        pb.set(m["pct"])

        facts = tk.Frame(body, bg=SURFACE)
        facts.pack(fill="x")
        facts.columnconfigure(0, weight=1, uniform="f")
        facts.columnconfigure(1, weight=1, uniform="f")
        facts.columnconfigure(2, weight=1, uniform="f")
        self._fact(facts, 0, "Reste à épargner", utils.fmt_money(m["remaining"], 0))
        self._fact(facts, 1, "Échéance",
                   utils.fmt_month(m["target_date"], True) if m["target_date"] else "—")
        effort = m["required_monthly"]
        self._fact(facts, 2, "Effort mensuel",
                   utils.fmt_money(effort, 0) if effort else "—",
                   color=AMBER if effort and m["monthly_planned"]
                   and effort > m["monthly_planned"] * 1.2 else TEXT)

        foot = tk.Frame(body, bg=SURFACE)
        foot.pack(fill="x", pady=(S(12), 0))
        widgets.Button(foot, "Verser", lambda pr=p: self._add_contribution(pr),
                       variant="primary", height=28, font=F_SMALL_B, padx=12,
                       icon="+").pack(side="left")
        widgets.Button(foot, "Détails", lambda pr=p: self._details(pr),
                       variant="secondary", height=28, font=F_SMALL_B, padx=12).pack(
            side="left", padx=(S(8), 0))
        widgets.lbl(foot, self._pace_text(m), (theme.FONT, 8), MUTED, SURFACE).pack(
            side="right")
        return card

    def _fact(self, parent, col, label, value, color=TEXT):
        cell = tk.Frame(parent, bg=SURFACE)
        cell.grid(row=0, column=col, sticky="w", padx=(0, S(6)))
        widgets.lbl(cell, label.upper(), (theme.FONT, 7, "bold"), FAINT, SURFACE).pack(anchor="w")
        widgets.lbl(cell, value, (theme.FONT, 9, "bold"), color, SURFACE).pack(anchor="w",
                                                                              pady=(S(2), 0))

    @staticmethod
    def _pace_text(m):
        if m["done"]:
            return "Objectif atteint"
        if m["projected"]:
            return f"Projection : {utils.fmt_month(m['projected'], True)}"
        return "Aucune projection"

    # ------------------------------------------------------------------
    def _menu(self, anchor, p):
        menu = tk.Menu(self, tearoff=0, font=theme.F_BODY, bg=SURFACE, fg=TEXT,
                       activebackground=PRIMARY_SOFT, activeforeground=PRIMARY_DARK,
                       bd=0, relief="flat")
        menu.add_command(label="Ajouter un versement", command=lambda: self._add_contribution(p))
        menu.add_command(label="Détails et historique", command=lambda: self._details(p))
        menu.add_command(label="Modifier", command=lambda: self.app.edit_project(p))
        menu.add_separator()
        menu.add_command(label="Archiver", command=lambda: self._archive(p))
        menu.add_command(label="Supprimer", command=lambda: self._delete(p))
        try:
            menu.tk_popup(anchor.winfo_rootx(), anchor.winfo_rooty() + anchor.winfo_height())
        finally:
            menu.grab_release()

    def _add_contribution(self, p):
        dlg = dialogs.ContributionDialog(self, self.db, p)
        if dlg.show():
            self.app.notify(dlg.payload)
            self.rebuild()

    def _details(self, p):
        dlg = ProjectDetailDialog(self, self.app, p["id"])
        dlg.show()
        self.rebuild()

    def _archive(self, p):
        self.db.update_project(p["id"], status="archive")
        self.app.notify(f"« {p['name']} » archivé")
        self.rebuild()

    def _delete(self, p):
        if widgets.ask_confirm(
            self, "Supprimer le projet",
            f"Supprimer « {p['name']} » et son historique de versements ?\n\n"
            "Les opérations bancaires liées ne sont pas supprimées.",
        ):
            self.db.delete_project(p["id"])
            self.app.notify("Projet supprimé")
            self.rebuild()


# --------------------------------------------------------------------------
# Fiche détaillée d'un projet
# --------------------------------------------------------------------------
class ProjectDetailDialog(widgets.Modal):
    def __init__(self, master, app, project_id):
        self.app = app
        self.db = app.db
        self.project_id = project_id
        p = self.db.get_project(project_id)
        super().__init__(master, p["name"] if p else "Projet",
                         "Historique des versements et trajectoire d'épargne.",
                         width=720, icon_text="◎", tone_name="green",
                         ok_label="Fermer")
        self.cancel_btn.pack_forget()
        self.body.configure(padx=0)
        self._build_content()

    def _build_content(self):
        for w in self.body.winfo_children():
            w.destroy()
        p = self.db.get_project(self.project_id)
        if not p:
            widgets.lbl(self.body, "Projet introuvable.", F_SMALL, RED_DARK, theme.BG).pack()
            return
        contributions = self.db.project_contributions(self.project_id)
        m = analytics.project_metrics(p, contributions)
        fg, soft = theme.tone(m["tone"])

        # bandeau
        banner = tk.Frame(self.body, bg=SURFACE_2, highlightbackground=BORDER,
                          highlightthickness=1)
        banner.pack(fill="x")
        inner = tk.Frame(banner, bg=SURFACE_2)
        inner.pack(fill="x", padx=S(16), pady=S(14))
        left = tk.Frame(inner, bg=SURFACE_2)
        left.pack(side="left")
        widgets.lbl(left, utils.fmt_money(m["saved"]), (theme.FONT, 20, "bold"), TEXT,
                    SURFACE_2).pack(anchor="w")
        widgets.lbl(left, f"sur un objectif de {utils.fmt_money(m['target'])}",
                    F_SMALL, MUTED, SURFACE_2).pack(anchor="w")
        right = tk.Frame(inner, bg=SURFACE_2)
        right.pack(side="right")
        widgets.Chip(right, m["status"], fg, soft, SURFACE_2).pack(anchor="e")
        if m["target_date"]:
            widgets.lbl(right, f"Échéance {utils.fmt_date_long(m['target_date'])}",
                        (theme.FONT, 8), MUTED, SURFACE_2).pack(anchor="e", pady=(S(4), 0))

        pb = widgets.ProgressBar(self.body, height=9, color=p["color"], bg=theme.BG)
        pb.pack(fill="x", pady=(S(12), S(4)))
        pb.set(m["pct"])
        widgets.lbl(self.body,
                    f"{utils.fmt_pct(m['pct'] * 100, 1)} de l'objectif — reste "
                    f"{utils.fmt_money(m['remaining'])}"
                    + (f" · effort mensuel nécessaire : {utils.fmt_money(m['required_monthly'], 0)}"
                       if m["required_monthly"] else ""),
                    (theme.FONT, 8), MUTED, theme.BG).pack(anchor="w")

        # graphique
        chart_card = widgets.Card(self.body, padding=12)
        chart_card.pack(fill="x", pady=(S(14), 0))
        points = analytics.contributions_cumulative(p, contributions)
        chart = widgets.LineChart(chart_card.content, height=150, color=p["color"],
                                  target=float(p["target_amount"]),
                                  target_label="Objectif")
        chart.pack(fill="x")
        chart.set_data([(utils.fmt_month(d, True) if i else utils.fmt_date(d, True), v)
                        for i, (d, v) in enumerate(points)])
        widgets.lbl(chart_card.content,
                    f"Rythme observé : {utils.fmt_money(m['observed'], 0)} / mois · "
                    f"versement prévu : {utils.fmt_money(m['monthly_planned'], 0)} / mois · "
                    f"projection : "
                    f"{utils.fmt_month(m['projected'], True) if m['projected'] else '—'}",
                    (theme.FONT, 8), MUTED, SURFACE).pack(anchor="w", pady=(S(6), 0))

        # historique
        head = tk.Frame(self.body, bg=theme.BG)
        head.pack(fill="x", pady=(S(16), S(6)))
        widgets.lbl(head, f"Versements ({len(contributions)})", theme.F_H3, TEXT,
                    theme.BG).pack(side="left")
        widgets.Button(head, "Ajouter un versement", self._add, variant="primary",
                       height=28, font=F_SMALL_B, icon="+").pack(side="right")

        box = tk.Frame(self.body, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1)
        box.pack(fill="both", expand=True)
        tree = ttk.Treeview(box, columns=("date", "amount", "note"), show="headings",
                            height=6, selectmode="browse")
        for key, text, width, anchor in (("date", "Date", 110, "w"),
                                        ("amount", "Montant", 130, "e"),
                                        ("note", "Note", 380, "w")):
            tree.heading(key, text=text, anchor=anchor)
            tree.column(key, width=S(width), anchor=anchor, stretch=(key == "note"))
        for i, c in enumerate(reversed(contributions)):
            tree.insert("", "end", iid=str(c["id"]), values=(
                utils.fmt_date(c["date"], True),
                utils.fmt_money(float(c["amount"])),
                c["notes"] or ("Virement associé" if c["transfer_id"] else ""),
            ), tags=("odd",) if i % 2 else ())
        tree.tag_configure("odd", background="#FCFDFE")
        sb = ttk.Scrollbar(box, orient="vertical", style="Slim.Vertical.TScrollbar",
                          command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        foot = tk.Frame(self.body, bg=theme.BG)
        foot.pack(fill="x", pady=(S(8), 0))
        widgets.Button(foot, "Supprimer le versement sélectionné", self._delete,
                       variant="ghost", height=28, font=F_SMALL_B).pack(side="left")
        self._tree = tree

    def _add(self):
        p = self.db.get_project(self.project_id)
        dlg = dialogs.ContributionDialog(self, self.db, p)
        if dlg.show():
            self.app.notify(dlg.payload)
            self._build_content()
            self.center()

    def _delete(self):
        sel = self._tree.selection() if hasattr(self, "_tree") else ()
        if not sel:
            return
        if widgets.ask_confirm(self, "Supprimer le versement",
                               "Supprimer ce versement ? Le virement bancaire associé, "
                               "s'il existe, sera également supprimé."):
            self.db.delete_contribution(int(sel[0]))
            self.app.notify("Versement supprimé")
            self._build_content()
            self.center()
