"""Écran Portefeuille : liste et gestion des comptes."""
from __future__ import annotations

import tkinter as tk

from .. import theme, utils, widgets
from ..db import account_family, account_type
from ..theme import (
    BORDER, FAINT, F_SMALL, F_SMALL_B, MUTED, PRIMARY, PRIMARY_DARK, PRIMARY_SOFT,
    SURFACE, SURFACE_2, TEXT, TEXT_SOFT,
)
from ..utils import S
from .base import ScrollView, empty_state, page_header


def avatar(parent, color, text, size=42, bg=SURFACE):
    cv = tk.Canvas(parent, width=S(size), height=S(size), bg=bg,
                   highlightthickness=0, bd=0)
    widgets.round_rect(cv, 0, 0, S(size), S(size), S(10), fill=color, outline=color)
    cv.create_text(S(size) / 2, S(size) / 2, text=text, fill="#FFFFFF",
                   font=(theme.FONT, 11, "bold"))
    return cv


class AccountsView(ScrollView):
    def __init__(self, master, app):
        super().__init__(master, app)
        self.show_archived = False

    def build(self):
        db = self.db
        accounts = db.list_accounts(include_archived=True)
        active = [a for a in accounts if not a["archived"]]
        archived = [a for a in accounts if a["archived"]]
        total = sum(float(a["balance"] or 0) for a in active)

        def actions(parent):
            widgets.Button(parent, "Ajouter un compte", self.app.new_account,
                           variant="primary", icon="+").pack(side="right")

        page_header(self.body, "Portefeuille",
                    f"{len(active)} compte{'s' if len(active) > 1 else ''} actif"
                    f"{'s' if len(active) > 1 else ''}  ·  patrimoine net "
                    f"{utils.fmt_money(total, 0)}", actions)

        if not accounts:
            empty_state(self.body, "Aucun compte enregistré",
                        "Compte courant, livret, PEA, espèces… ajoutez vos comptes pour "
                        "voir votre patrimoine consolidé.",
                        "Ajouter mon premier compte", self.app.new_account, icon="▤")
            return

        # ---------------------------------------------------------- synthèse
        summary = widgets.Card(self.body, padding=18)
        summary.pack(fill="x", pady=(0, S(18)))
        row = tk.Frame(summary.content, bg=SURFACE)
        row.pack(fill="x")
        for i in range(4):
            row.columnconfigure(i, weight=1, uniform="sum")

        by_family = {}
        for a in active:
            fam = account_family(a["type"])
            by_family.setdefault(fam, 0.0)
            by_family[fam] += float(a["balance"] or 0)
        epargne_total = (by_family.get("epargne", 0.0)
                         + by_family.get("placement", 0.0)
                         + by_family.get("retraite", 0.0))
        best = max(active, key=lambda a: float(a["balance"] or 0)) if active else None
        stats = [
            ("Patrimoine net", utils.fmt_money(total, 0), "Tous comptes confondus", PRIMARY),
            ("Comptes actifs", str(len(active)), "Suivis au quotidien", theme.GREEN),
            ("Épargne", utils.fmt_money(epargne_total, 0),
             "Livrets, placements, retraite", theme.VIOLET),
            ("Compte principal", utils.fmt_money(best["balance"], 0) if best else "—",
             best["name"] if best else "", theme.AMBER),
        ]
        for i, (label, value, hint, color) in enumerate(stats):
            cell = tk.Frame(row, bg=SURFACE)
            cell.grid(row=0, column=i, sticky="nsew",
                      padx=(0, S(14)) if i < 3 else 0)
            widgets.lbl(cell, label.upper(), (theme.FONT, 8, "bold"), MUTED, SURFACE).pack(anchor="w")
            widgets.lbl(cell, value, (theme.FONT, 16, "bold"), TEXT, SURFACE).pack(
                anchor="w", pady=(S(4), S(2)))
            widgets.lbl(cell, hint, (theme.FONT, 8), FAINT, SURFACE).pack(anchor="w")
            bar = tk.Frame(cell, bg=color, height=S(3))
            bar.pack(fill="x", pady=(S(8), 0))
            if i < 3:
                tk.Frame(row, bg=BORDER, width=1).grid(row=0, column=i, sticky="nse",
                                                       padx=(0, S(0)))

        # ---------------------------------------------------------- comptes
        grid = tk.Frame(self.body, bg=theme.BG)
        grid.pack(fill="x")
        cols = 3
        for c in range(cols):
            grid.columnconfigure(c, weight=1, uniform="acc")

        for i, account in enumerate(active):
            card = self._account_card(grid, account)
            card.grid(row=i // cols, column=i % cols, sticky="nsew",
                      padx=(0, S(14)) if i % cols < cols - 1 else 0,
                      pady=(0, S(14)))

        if archived:
            bar = tk.Frame(self.body, bg=theme.BG)
            bar.pack(fill="x", pady=(S(6), 0))
            label = (f"Masquer les comptes archivés ({len(archived)})" if self.show_archived
                     else f"Afficher les comptes archivés ({len(archived)})")
            widgets.Button(bar, label, self._toggle_archived, variant="ghost",
                           height=30, font=F_SMALL_B).pack(side="left")
            if self.show_archived:
                agrid = tk.Frame(self.body, bg=theme.BG)
                agrid.pack(fill="x", pady=(S(10), 0))
                for c in range(cols):
                    agrid.columnconfigure(c, weight=1, uniform="arc")
                for i, account in enumerate(archived):
                    card = self._account_card(agrid, account, muted=True)
                    card.grid(row=i // cols, column=i % cols, sticky="nsew",
                              padx=(0, S(14)) if i % cols < cols - 1 else 0,
                              pady=(0, S(14)))

    # ------------------------------------------------------------------
    def _toggle_archived(self):
        self.show_archived = not self.show_archived
        self.rebuild()

    def _account_card(self, parent, account, muted=False):
        db = self.db
        type_label, type_color, _family = account_type(account["type"])
        balance = float(account["balance"] or 0)
        card = widgets.Card(parent, padding=16)
        card.content.configure(bg=SURFACE)

        head = tk.Frame(card.content, bg=SURFACE)
        head.pack(fill="x")
        avatar(head, type_color if not muted else theme.BORDER_DARK,
               utils.initials(account["name"]), 38).pack(side="left", padx=(0, S(10)))
        info = tk.Frame(head, bg=SURFACE)
        info.pack(side="left", fill="x", expand=True)
        widgets.lbl(info, utils.elide(account["name"], 22), (theme.FONT, 10, "bold"),
                    TEXT if not muted else MUTED, SURFACE).pack(anchor="w")
        sub = account["institution"] or type_label
        widgets.lbl(info, utils.elide(sub, 26), (theme.FONT, 8), FAINT, SURFACE).pack(anchor="w")

        menu_btn = widgets.MenuButton(head, bg=SURFACE, size=28)
        menu_btn.pack(side="right", anchor="n")
        menu_btn.set_command(lambda b=menu_btn, a=account: self._menu(b, a))

        tk.Frame(card.content, bg=SURFACE, height=S(10)).pack()
        widgets.lbl(card.content, utils.fmt_money(balance), (theme.FONT, 17, "bold"),
                    TEXT if not muted else MUTED, SURFACE).pack(anchor="w")
        foot_info = tk.Frame(card.content, bg=SURFACE)
        foot_info.pack(fill="x", pady=(S(2), 0))
        widgets.lbl(foot_info, type_label, (theme.FONT, 8), type_color, SURFACE).pack(side="left")
        widgets.lbl(foot_info, f"{account['tx_count']} opération"
                    f"{'s' if account['tx_count'] > 1 else ''}", (theme.FONT, 8), FAINT,
                    SURFACE).pack(side="left", padx=(S(8), 0))

        tk.Frame(card.content, bg=theme.SURFACE_3, height=1).pack(fill="x", pady=(S(12), 0))
        actions = tk.Frame(card.content, bg=SURFACE)
        actions.pack(fill="x", pady=(S(8), 0))
        widgets.Button(actions, "Opérations",
                       lambda a=account: self.app.navigate("transactions", account_id=a["id"]),
                       variant="ghost", height=26, padx=6, font=F_SMALL_B).pack(side="left")
        widgets.Button(actions, "Modifier", lambda a=account: self.app.edit_account(a),
                       variant="ghost", height=26, padx=6, font=F_SMALL_B).pack(side="right")
        return card

    def _menu(self, anchor, account):
        menu = tk.Menu(self, tearoff=0, font=theme.F_BODY, bg=SURFACE, fg=TEXT,
                       activebackground=PRIMARY_SOFT, activeforeground=PRIMARY_DARK,
                       bd=0, relief="flat")
        menu.add_command(label="Modifier le compte", command=lambda: self.app.edit_account(account))
        menu.add_command(label="Voir les opérations",
                         command=lambda: self.app.navigate("transactions", account_id=account["id"]))
        menu.add_separator()
        if account["archived"]:
            menu.add_command(label="Restaurer", command=lambda: self._archive(account, False))
        else:
            menu.add_command(label="Archiver", command=lambda: self._archive(account, True))
        menu.add_command(label="Supprimer", command=lambda: self._delete(account))
        try:
            menu.tk_popup(anchor.winfo_rootx(), anchor.winfo_rooty() + anchor.winfo_height())
        finally:
            menu.grab_release()

    def _archive(self, account, archived: bool):
        self.db.update_account(account["id"], archived=1 if archived else 0)
        self.app.notify("Compte archivé" if archived else "Compte restauré")
        self.rebuild()

    def _delete(self, account):
        count = int(account["tx_count"] or 0)
        message = (f"Supprimer le compte « {account['name']} » ?")
        if count:
            message += f"\n\nLes {count} opérations liées seront également supprimées. "
            message += "Cette action est définitive."
        if widgets.ask_confirm(self, "Supprimer le compte", message,
                               confirm_label="Supprimer définitivement"):
            self.db.delete_account(account["id"])
            self.app.notify("Compte supprimé")
            self.rebuild()
