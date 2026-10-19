"""Écran Paramètres : devise, données, catégories et informations."""
from __future__ import annotations

import csv
import os
import sys
import tkinter as tk
from tkinter import filedialog

from .. import __version__, dialogs, theme, utils, widgets
from ..theme import (
    AMBER, BORDER, FAINT, F_SMALL, F_SMALL_B, GREEN, GREEN_DARK, MUTED, PRIMARY,
    RED_DARK, SURFACE, SURFACE_2, TEXT, TEXT_SOFT,
)
from ..utils import S
from .base import ScrollView, page_header


class SettingsView(ScrollView):
    def build(self):
        db = self.db
        page_header(self.body, "Paramètres",
                    "Personnalisez l'application, sauvegardez et gérez vos catégories.")

        # ------------------------------------------------------ devise
        card = widgets.Card(self.body, title="Préférences", padding=18)
        card.pack(fill="x")
        row = tk.Frame(card.content, bg=SURFACE)
        row.pack(fill="x")
        left = tk.Frame(row, bg=SURFACE)
        left.pack(side="left")
        widgets.lbl(left, "Devise d'affichage", F_SMALL_B, TEXT, SURFACE).pack(anchor="w")
        widgets.lbl(left, "Utilisée pour tous les montants de l'application.",
                    (theme.FONT, 8), FAINT, SURFACE).pack(anchor="w", pady=(S(2), 0))
        self.var_currency = tk.StringVar(value=db.get_setting("currency", "€"))
        c = widgets.combo(row, ["€", "$", "£", "CHF", "MAD", "DZD", "TND", "CAD"], self.var_currency,
                          width=10)
        c.pack(side="right", ipady=S(2))
        c.bind("<<ComboboxSelected>>", lambda e: self._set_currency())

        # ------------------------------------------------------ données
        stats = db.stats()
        card2 = widgets.Card(self.body, title="Vos données", padding=18)
        card2.pack(fill="x", pady=(S(14), 0))
        path_row = tk.Frame(card2.content, bg=SURFACE_2, highlightbackground=BORDER,
                            highlightthickness=1)
        path_row.pack(fill="x")
        tk.Label(path_row, text=db.path, font=(theme.FONT, 8), fg=TEXT_SOFT, bg=SURFACE_2,
                 anchor="w", padx=S(10), pady=S(8)).pack(side="left", fill="x", expand=True)

        info = tk.Frame(card2.content, bg=SURFACE)
        info.pack(fill="x", pady=(S(10), 0))
        widgets.lbl(info,
                    f"{stats['accounts']} comptes · {stats['transactions']} opérations · "
                    f"{stats['projects']} projets · {stats['categories']} catégories",
                    F_SMALL, MUTED, SURFACE).pack(side="left")

        btns = tk.Frame(card2.content, bg=SURFACE)
        btns.pack(fill="x", pady=(S(12), 0))
        widgets.Button(btns, "Sauvegarder une copie", self._backup, variant="secondary",
                       height=32, font=F_SMALL_B).pack(side="left", padx=(0, S(8)))
        widgets.Button(btns, "Exporter en CSV", self._export_csv, variant="secondary",
                       height=32, font=F_SMALL_B).pack(side="left", padx=(0, S(8)))
        widgets.Button(btns, "Ouvrir le dossier", self._open_folder, variant="ghost",
                       height=32, font=F_SMALL_B).pack(side="left")

        # ------------------------------------------------------ démo / réinit
        card3 = widgets.Card(self.body, title="Données de démonstration", padding=18)
        card3.pack(fill="x", pady=(S(14), 0))
        widgets.lbl(card3.content,
                    "Explorez l'application avec un portefeuille d'exemple (4 comptes, "
                    "15 mois d'opérations, 4 projets). Cette action remplace toutes les "
                    "données existantes.",
                    F_SMALL, MUTED, SURFACE, wraplength=S(760), justify="left").pack(anchor="w")
        btns3 = tk.Frame(card3.content, bg=SURFACE)
        btns3.pack(fill="x", pady=(S(12), 0))
        widgets.Button(btns3, "Charger la démonstration", self._load_demo,
                       variant="secondary", height=32, font=F_SMALL_B).pack(side="left",
                                                                           padx=(0, S(8)))
        widgets.Button(btns3, "Tout effacer", self._wipe, variant="danger", height=32,
                       font=F_SMALL_B).pack(side="left")

        # ------------------------------------------------------ catégories
        head = tk.Frame(self.body, bg=theme.BG)
        head.pack(fill="x", pady=(S(24), S(10)))
        widgets.lbl(head, "Catégories", theme.F_H2, TEXT, theme.BG).pack(side="left")
        widgets.Button(head, "Nouvelle catégorie", self._add_category, variant="primary",
                       height=30, font=F_SMALL_B, icon="+").pack(side="right")

        card4 = widgets.Card(self.body, padding=0)
        card4.pack(fill="x")
        inner = tk.Frame(card4.content, bg=SURFACE)
        inner.pack(fill="x", padx=S(18), pady=S(6))
        categories = db.list_categories()
        for i, cat in enumerate(categories):
            row = tk.Frame(inner, bg=SURFACE)
            row.pack(fill="x", pady=S(7))
            widgets.Dot(row, cat["color"], 9, SURFACE).pack(side="left", padx=(0, S(8)))
            widgets.lbl(row, cat["name"], F_SMALL, TEXT, SURFACE).pack(side="left")
            kind = "Dépense" if cat["kind"] == "depense" else "Revenu"
            widgets.Chip(row, kind, MUTED, theme.SURFACE_3, SURFACE).pack(side="left",
                                                                        padx=(S(10), 0))
            usage = db.category_usage(cat["id"])
            if usage:
                widgets.lbl(row, f"{usage} opération{'s' if usage > 1 else ''}",
                            (theme.FONT, 8), FAINT, SURFACE).pack(side="left", padx=(S(10), 0))
            widgets.Button(row, "Supprimer", lambda c=cat: self._delete_category(c),
                           variant="ghost", height=24, font=(theme.FONT, 8),
                           padx=6).pack(side="right")
            widgets.Button(row, "Modifier", lambda c=cat: self._edit_category(c),
                           variant="ghost", height=24, font=(theme.FONT, 8),
                           padx=6).pack(side="right", padx=(0, S(4)))
            if i < len(categories) - 1:
                tk.Frame(inner, bg=theme.SURFACE_3, height=1).pack(fill="x")

        # ------------------------------------------------------ à propos
        card5 = widgets.Card(self.body, title="À propos", padding=18)
        card5.pack(fill="x", pady=(S(14), S(4)))
        widgets.lbl(card5.content, f"PatrimoinePro {__version__}", F_SMALL_B, TEXT,
                    SURFACE).pack(anchor="w")
        widgets.lbl(card5.content,
                    "Application locale de gestion de portefeuille et de projets d'épargne. "
                    "Vos données restent sur votre ordinateur, dans une base SQLite.",
                    (theme.FONT, 8), MUTED, SURFACE, wraplength=S(760),
                    justify="left").pack(anchor="w", pady=(S(3), S(8)))
        widgets.lbl(card5.content,
                    f"Python {sys.version.split()[0]} · Tk {tk.TkVersion} · "
                    f"base de données locale",
                    (theme.FONT, 8), FAINT, SURFACE).pack(anchor="w")
        widgets.lbl(card5.content,
                    "Raccourcis : Ctrl+N nouvelle opération · Ctrl+1…6 navigation · "
                    "F5 actualiser",
                    (theme.FONT, 8), FAINT, SURFACE).pack(anchor="w", pady=(S(4), 0))

    # ------------------------------------------------------------------
    def _set_currency(self):
        symbol = self.var_currency.get()
        self.db.set_setting("currency", symbol)
        utils.set_currency(symbol)
        self.app.notify(f"Devise : {symbol}")
        self.rebuild()

    def _backup(self):
        default = f"patrimoine-{utils.today().strftime('%Y-%m-%d')}.db"
        path = filedialog.asksaveasfilename(
            parent=self, title="Sauvegarder une copie de la base",
            defaultextension=".db", initialfile=default,
            filetypes=[("Base SQLite", "*.db"), ("Tous les fichiers", "*.*")],
        )
        if not path:
            return
        try:
            self.db.backup_to(path)
            self.app.notify("Sauvegarde créée")
        except Exception as exc:  # pragma: no cover - dépend du système
            widgets.ask_confirm(self, "Échec de la sauvegarde", str(exc),
                                confirm_label="Fermer", tone_name="red")

    def _export_csv(self):
        path = filedialog.asksaveasfilename(
            parent=self, title="Exporter les opérations",
            defaultextension=".csv", initialfile="operations.csv",
            filetypes=[("Fichier CSV", "*.csv")],
        )
        if not path:
            return
        rows = self.db.list_transactions()
        with open(path, "w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle, delimiter=";")
            writer.writerow(["Date", "Libellé", "Catégorie", "Compte", "Montant",
                             "Notes", "Virement"])
            for r in rows:
                writer.writerow([
                    utils.fmt_date(r["date"]),
                    self.db._tx_label(r),
                    r["category_name"] or "",
                    r["account_name"],
                    f"{float(r['amount']):.2f}".replace(".", ","),
                    r["notes"] or "",
                    "oui" if r["transfer_id"] else "non",
                ])
        self.app.notify(f"{len(rows)} opérations exportées")

    def _open_folder(self):
        folder = os.path.dirname(self.db.path)
        try:
            os.startfile(folder)  # type: ignore[attr-defined]
        except Exception:
            self.app.notify("Impossible d'ouvrir le dossier", "amber")

    def _load_demo(self):
        if not widgets.ask_confirm(
            self, "Charger la démonstration",
            "Toutes vos données actuelles seront remplacées par un jeu de démonstration "
            "(4 comptes, 15 mois d'opérations, 4 projets). Continuer ?",
            confirm_label="Charger la démonstration", tone_name="amber", icon_text="!",
        ):
            return
        try:
            self.db.seed_demo()
            utils.set_currency(self.db.get_setting("currency", "€"))
            self.app.notify("Données de démonstration chargées")
            self.app.navigate("dashboard")
        except Exception as exc:  # pragma: no cover
            self.app.notify(f"Erreur : {exc}", "red")

    def _wipe(self):
        if not widgets.ask_confirm(
            self, "Tout effacer",
            "Supprimer définitivement tous les comptes, opérations, projets et budgets ? "
            "Cette action est irréversible.",
            confirm_label="Tout supprimer",
        ):
            return
        self.db.wipe()
        self.app.notify("Toutes les données ont été effacées")
        self.app.navigate("dashboard")

    def _add_category(self):
        dlg = dialogs.CategoryDialog(self)
        if dlg.show():
            data = dlg.values()
            try:
                self.db.add_category(data["name"], data["kind"], data["color"])
                self.app.notify("Catégorie ajoutée")
                self.rebuild()
            except Exception:
                self.app.notify("Cette catégorie existe déjà", "amber")

    def _edit_category(self, cat):
        dlg = dialogs.CategoryDialog(self, category=cat)
        if dlg.show():
            data = dlg.values()
            try:
                self.db.update_category(cat["id"], data["name"], data["color"])
                self.app.notify("Catégorie modifiée")
                self.rebuild()
            except Exception:
                self.app.notify("Cette catégorie existe déjà", "amber")

    def _delete_category(self, cat):
        usage = self.db.category_usage(cat["id"])
        message = f"Supprimer la catégorie « {cat['name']} » ?"
        if usage:
            message += (f"\n\n{usage} opération{'s' if usage > 1 else ''} "
                        f"seront reclassée{'s' if usage > 1 else ''} sans catégorie.")
        if widgets.ask_confirm(self, "Supprimer la catégorie", message):
            self.db.delete_category(cat["id"])
            self.app.notify("Catégorie supprimée")
            self.rebuild()
