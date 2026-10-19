"""Écran Transactions : journal filtrable des opérations."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .. import analytics, theme, utils, widgets
from ..theme import (
    BORDER, FAINT, F_SMALL, F_SMALL_B, GREEN_DARK, MUTED, PRIMARY, PRIMARY_DARK,
    PRIMARY_SOFT, RED_DARK, SURFACE, SURFACE_2, TEXT, TEXT_SOFT,
)
from ..utils import S
from .base import BaseView, page_header


class TransactionsView(BaseView):
    def __init__(self, master, app):
        super().__init__(master, app)
        self.period = "Mois"
        self.account_id = None
        self.category_id = None
        self.search = ""
        self._after_id = None

    # ------------------------------------------------------------------
    def on_show(self, **params):
        if params.get("account_id"):
            self.account_id = int(params["account_id"])
        self.params = dict(params or {})
        self.rebuild()

    def build(self):
        db = self.db
        self.accounts = db.list_accounts(include_archived=True)
        self.categories = db.list_categories()

        outer = tk.Frame(self, bg=theme.BG)
        outer.pack(fill="both", expand=True, padx=S(26), pady=(S(20), S(18)))

        def actions(parent):
            widgets.Button(parent, "Nouvelle opération", self.app.new_transaction,
                           variant="primary", icon="+").pack(side="right")

        page_header(outer, "Transactions",
                    "Toutes vos dépenses, revenus et virements internes.", actions)

        # ------------------------------------------------------ filtres
        bar = widgets.Card(outer, padding=12)
        bar.pack(fill="x")
        line = tk.Frame(bar.content, bg=SURFACE)
        line.pack(fill="x")

        # la recherche est placée en premier à droite pour ne jamais être rognée
        self.var_search = tk.StringVar(value=self.search)
        search_box = tk.Frame(line, bg=SURFACE, highlightbackground=BORDER,
                              highlightcolor=PRIMARY, highlightthickness=1)
        search_box.pack(side="right")
        icon = tk.Canvas(search_box, width=S(16), height=S(16), bg=SURFACE,
                         highlightthickness=0, bd=0)
        icon.pack(side="left", padx=(S(8), S(2)))
        icon.create_oval(2, 2, 11, 11, outline=FAINT, width=1)
        icon.create_line(11, 11, 15, 15, fill=FAINT, width=1)
        e_search = tk.Entry(search_box, textvariable=self.var_search, width=20,
                            font=F_SMALL, bg=SURFACE, fg=TEXT, relief="flat", bd=0,
                            insertbackground=TEXT, highlightthickness=0)
        e_search.pack(side="left", padx=(0, S(8)), ipady=S(5))
        self.var_search.trace_add("write", lambda *a: self._debounce_search())

        self.seg = widgets.Segmented(line, ["Mois", "3 mois", "12 mois", "Tout"],
                                     self.period, self._on_period, height=32)
        self.seg.pack(side="left")

        names = ["Tous les comptes"] + [a["name"] for a in self.accounts]
        self.acc_by_name = {a["name"]: a for a in self.accounts}
        self.var_acc = tk.StringVar(
            value=next((a["name"] for a in self.accounts if a["id"] == self.account_id),
                       "Tous les comptes"))
        c_acc = widgets.combo(line, names, self.var_acc, width=17)
        c_acc.pack(side="left", padx=(S(10), 0), ipady=S(2))
        c_acc.bind("<<ComboboxSelected>>", lambda e: self._on_account())

        cat_names = ["Toutes les catégories"] + [c["name"] for c in self.categories]
        self.cat_by_name = {c["name"]: c for c in self.categories}
        self.var_cat = tk.StringVar(value="Toutes les catégories")
        c_cat = widgets.combo(line, cat_names, self.var_cat, width=18)
        c_cat.pack(side="left", padx=(S(8), 0), ipady=S(2))
        c_cat.bind("<<ComboboxSelected>>", lambda e: self._on_category())

        # ------------------------------------------------------ résumé
        self.summary = tk.Frame(outer, bg=theme.BG)
        self.summary.pack(fill="x", pady=(S(12), S(10)))
        self.lbl_count = widgets.lbl(self.summary, "", F_SMALL, MUTED, theme.BG)
        self.lbl_count.pack(side="left")
        self.lbl_flow = widgets.lbl(self.summary, "", F_SMALL, MUTED, theme.BG)
        self.lbl_flow.pack(side="right")

        # ------------------------------------------------------ tableau
        box = tk.Frame(outer, bg=SURFACE, highlightbackground=BORDER,
                       highlightthickness=1)
        box.pack(fill="both", expand=True)

        columns = ("date", "label", "category", "account", "amount")
        self.tree = ttk.Treeview(box, columns=columns, show="headings",
                                 selectmode="browse")
        headings = {
            "date": ("Date", 92, "w"),
            "label": ("Libellé", 300, "w"),
            "category": ("Catégorie", 150, "w"),
            "account": ("Compte", 150, "w"),
            "amount": ("Montant", 130, "e"),
        }
        for key, (text, width, anchor) in headings.items():
            self.tree.heading(key, text=text, anchor=anchor)
            self.tree.column(key, width=S(width), minwidth=S(70), anchor=anchor,
                             stretch=(key == "label"))
        self.tree.tag_configure("income", foreground=GREEN_DARK)
        self.tree.tag_configure("expense", foreground=TEXT)
        self.tree.tag_configure("transfer", foreground=MUTED)
        self.tree.tag_configure("odd", background="#FCFDFE")

        sb = ttk.Scrollbar(box, orient="vertical", style="Slim.Vertical.TScrollbar",
                           command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        self.empty_label = tk.Label(box, text="Aucune opération pour ces critères.",
                                    font=F_SMALL, fg=FAINT, bg=SURFACE)

        self.tree.bind("<Double-1>", lambda e: self._edit_selected())
        self.tree.bind("<Return>", lambda e: self._edit_selected())
        self.tree.bind("<Button-3>", self._context_menu)
        self.tree.bind("<<TreeviewSelect>>", lambda e: self._selection_changed())

        # ------------------------------------------------------ pied
        foot = tk.Frame(outer, bg=theme.BG)
        foot.pack(fill="x", pady=(S(8), 0))
        self.lbl_sel = widgets.lbl(foot, "", F_SMALL, MUTED, theme.BG)
        self.lbl_sel.pack(side="left")
        self.btn_delete = widgets.Button(foot, "Supprimer", self._delete_selected,
                                         variant="danger", height=30, font=F_SMALL_B)
        self.btn_delete.pack(side="right")
        self.btn_edit = widgets.Button(foot, "Modifier", self._edit_selected,
                                       variant="secondary", height=30, font=F_SMALL_B)
        self.btn_edit.pack(side="right", padx=(0, S(8)))
        self.btn_edit.set_enabled(False)
        self.btn_delete.set_enabled(False)

        self._reload()

    # ------------------------------------------------------------------
    def _period_range(self):
        today = utils.today()
        if self.period == "Mois":
            return utils.month_bounds(today)
        if self.period == "3 mois":
            return utils.add_months(today.replace(day=1), -2), utils.month_bounds(today)[1]
        if self.period == "12 mois":
            return utils.add_months(today.replace(day=1), -11), utils.month_bounds(today)[1]
        return None, None

    def _on_period(self, value):
        self.period = value
        self._reload()

    def _on_account(self):
        acc = self.acc_by_name.get(self.var_acc.get())
        self.account_id = acc["id"] if acc else None
        self._reload()

    def _on_category(self):
        cat = self.cat_by_name.get(self.var_cat.get())
        self.category_id = cat["id"] if cat else None
        self._reload()

    def _debounce_search(self):
        if self._after_id:
            try:
                self.after_cancel(self._after_id)
            except Exception:
                pass
        self._after_id = self.after(220, self._apply_search)

    def _apply_search(self):
        self._after_id = None
        self.search = self.var_search.get().strip()
        self._reload()

    def _reload(self):
        start, end = self._period_range()
        rows = self.db.list_transactions(
            start=start, end=end, account_id=self.account_id,
            category_id=self.category_id, search=self.search or None, limit=600,
        )
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._rows = {}
        for i, r in enumerate(rows):
            amount = float(r["amount"])
            if r["transfer_id"]:
                category = "Virement interne"
                tag = "transfer"
            else:
                category = r["category_name"] or "Sans catégorie"
                tag = "income" if amount >= 0 else "expense"
            label = self.db._tx_label(r)
            if amount < 0 and r["transfer_id"]:
                label = f"→ {r['counterpart_account'] or 'Virement'}"
            elif amount > 0 and r["transfer_id"]:
                label = f"← {r['counterpart_account'] or 'Virement'}"
            iid = str(r["id"])
            self._rows[iid] = r
            tags = (tag,) if i % 2 == 0 else (tag, "odd")
            self.tree.insert("", "end", iid=iid, tags=tags, values=(
                utils.fmt_date(r["date"]),
                label,
                category,
                r["account_name"],
                utils.fmt_money(amount),
            ))

        if rows:
            self.empty_label.place_forget()
        else:
            self.empty_label.place(relx=0.5, rely=0.5, anchor="center")

        # résumé
        flows = [r for r in rows if not r["transfer_id"]]
        income = sum(float(r["amount"]) for r in flows if float(r["amount"]) > 0)
        expense = -sum(float(r["amount"]) for r in flows if float(r["amount"]) < 0)
        self.lbl_count.configure(
            text=f"{len(rows)} opération{'s' if len(rows) > 1 else ''}"
        )
        self.lbl_flow.configure(
            text=f"Entrées {utils.fmt_money(income)}      "
                 f"Sorties {utils.fmt_money(expense)}      "
                 f"Solde {utils.fmt_money(income - expense)}"
        )
        self._selection_changed()

    def _selection_changed(self):
        selected = self.tree.selection()
        has = bool(selected)
        self.btn_edit.set_enabled(has)
        self.btn_delete.set_enabled(has)
        if has and selected[0] in self._rows:
            r = self._rows[selected[0]]
            self.lbl_sel.configure(
                text=f"{utils.fmt_date_long(r['date'])} · {self.db._tx_label(r)} · "
                     f"{r['account_name']}")
        else:
            self.lbl_sel.configure(text="Sélectionnez une opération pour la modifier.")

    # ------------------------------------------------------------------
    def _edit_selected(self):
        selected = self.tree.selection()
        if not selected:
            return
        r = self._rows.get(selected[0])
        if r:
            self.app.edit_transaction(r)

    def _delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            return
        r = self._rows.get(selected[0])
        if not r:
            return
        message = f"Supprimer « {self.db._tx_label(r)} » du {utils.fmt_date_long(r['date'])} ?"
        if r["transfer_id"]:
            message += "\n\nLes deux écritures du virement seront supprimées."
        if widgets.ask_confirm(self, "Supprimer l'opération", message):
            self.db.delete_transaction(r["id"])
            self.app.notify("Opération supprimée")
            self._reload()

    def _context_menu(self, event):
        iid = self.tree.identify_row(event.y)
        if not iid:
            return
        self.tree.selection_set(iid)
        menu = tk.Menu(self, tearoff=0, font=theme.F_BODY, bg=SURFACE, fg=TEXT,
                       activebackground=PRIMARY_SOFT, activeforeground=PRIMARY_DARK,
                       bd=0, relief="flat")
        menu.add_command(label="Modifier", command=self._edit_selected)
        menu.add_command(label="Dupliquer", command=self._duplicate_selected)
        menu.add_separator()
        menu.add_command(label="Supprimer", command=self._delete_selected)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _duplicate_selected(self):
        selected = self.tree.selection()
        if not selected:
            return
        r = self._rows.get(selected[0])
        if not r:
            return
        self.db.add_transaction(r["date"], r["account_id"], float(r["amount"]),
                                r["category_id"], (r["payee"] or "") + " (copie)",
                                r["notes"] or "")
        self.app.notify("Opération dupliquée")
        self._reload()
