"""Formulaires modaux : comptes, opérations, projets, versements, budgets."""
from __future__ import annotations

import tkinter as tk

from . import theme, utils, widgets
from .db import (
    ACCOUNT_FAMILIES, ACCOUNT_TYPES, PRIORITIES, account_color, account_family,
    account_label, family_key_of_label, family_label, type_of_label, types_of_family,
)
from .theme import BG, BORDER, FAINT, MUTED, PRIMARY, SURFACE, TEXT, TEXT_SOFT
from .utils import S


class Form:
    """Grille de formulaire à deux colonnes."""

    def __init__(self, parent, columns: int = 2):
        self.frame = tk.Frame(parent, bg=BG)
        self.frame.pack(fill="x")
        self.columns = columns
        for c in range(columns):
            self.frame.columnconfigure(c, weight=1, uniform="f")

    def cell(self, label, row, col=0, span=1, required=False):
        box = tk.Frame(self.frame, bg=BG)
        box.grid(row=row, column=col, columnspan=span, sticky="ew",
                 pady=(S(11), 0), padx=(0, S(12) if col + span < self.columns else 0))
        widgets.lbl(box, label + (" *" if required else ""), theme.F_SMALL_B,
                    TEXT_SOFT, BG).pack(anchor="w", pady=(0, S(4)))
        holder = tk.Frame(box, bg=BG)
        holder.pack(fill="x")
        return holder

    def text_entry(self, label, var, row, col=0, span=1, required=False, width=None):
        holder = self.cell(label, row, col, span, required)
        e = widgets.entry(holder, var, width=width, bg=SURFACE)
        e.pack(fill="x", ipady=S(6))
        return e

    def money_entry(self, label, var, row, col=0, span=1, required=False, suffix=None):
        suffix = utils.CURRENCY if suffix is None else suffix
        holder = self.cell(label, row, col, span, required)
        box = tk.Frame(holder, bg=SURFACE, highlightbackground=BORDER,
                       highlightcolor=PRIMARY, highlightthickness=1)
        box.pack(fill="x")
        e = tk.Entry(box, textvariable=var, font=(theme.FONT, 12, "bold"), fg=TEXT,
                     bg=SURFACE, relief="flat", bd=0, justify="right",
                     insertbackground=TEXT, highlightthickness=0)
        e.pack(side="left", fill="x", expand=True, ipady=S(6), padx=(S(8), S(4)))
        tk.Label(box, text=suffix, font=theme.F_SMALL, fg=MUTED, bg=SURFACE).pack(
            side="right", padx=(0, S(10)))
        return e

    def combo(self, label, var, values, row, col=1, span=1, width=None):
        holder = self.cell(label, row, col, span)
        c = widgets.combo(holder, values, var, width=width)
        c.pack(fill="x", ipady=S(2))
        return c

    def date(self, label, value, row, col=0, span=1):
        holder = self.cell(label, row, col, span)
        d = widgets.DateField(holder, value=value, bg=BG)
        d.pack(anchor="w")
        return d

    def color(self, label, value, row, col=0, span=1):
        holder = self.cell(label, row, col, span)
        field = widgets.ColorField(holder, value=value, bg=BG)
        field.pack(anchor="w")
        return field

    @staticmethod
    def hide(widget):
        """Masque le champ (et son libellé) : widget = champ créé par ce formulaire."""
        try:
            widget.master.master.grid_remove()
        except Exception:
            pass

    @staticmethod
    def show(widget):
        try:
            widget.master.master.grid()
        except Exception:
            pass

    def note(self, label, row, col=0, span=2):
        holder = self.cell(label, row, col, span)
        text = tk.Text(holder, height=2, font=theme.F_BODY, fg=TEXT, bg=SURFACE,
                       relief="flat", bd=0, highlightthickness=1,
                       highlightbackground=BORDER, highlightcolor=PRIMARY,
                       insertbackground=TEXT, wrap="word", padx=S(8), pady=S(6))
        text.pack(fill="x")
        return text


def money_text(value) -> str:
    if value is None:
        return ""
    return f"{float(value):,.2f}".replace(",", " ").replace(".", ",").replace("\u202f", " ")


# --------------------------------------------------------------------------
# Compte
# --------------------------------------------------------------------------
class AccountDialog(widgets.Modal):
    def __init__(self, master, account=None):
        self.account = account
        title = "Modifier le compte" if account else "Nouveau compte"
        super().__init__(master, title, "Renseignez les informations du compte.",
                         width=600, icon_text="▤", tone_name="blue",
                         ok_label="Enregistrer")
        self.var_name = tk.StringVar(value=account["name"] if account else "")
        self.var_bank = tk.StringVar(value=account["institution"] if account else "")
        current_type = account["type"] if account else "courant"
        self.var_family = tk.StringVar(value=family_label(account_family(current_type)))
        self.var_type = tk.StringVar(value=account_label(current_type))
        self.var_balance = tk.StringVar(
            value=money_text(account["initial_balance"]) if account else ""
        )

        f = Form(self.body)
        self.e_name = f.text_entry("Nom du compte", self.var_name, 0, 0, span=2, required=True)
        self.e_bank = f.text_entry("Banque / établissement", self.var_bank, 1, 0)
        self.c_family = f.combo("Famille", self.var_family,
                                [ACCOUNT_FAMILIES[k][0] for k in ACCOUNT_FAMILIES], 1, 1)
        self.c_type = f.combo("Type de compte", self.var_type, [], 2, 0)
        self.e_balance = f.money_entry("Solde initial", self.var_balance, 2, 1)
        self.c_family.bind("<<ComboboxSelected>>", lambda e: self._on_family_changed())
        self._fill_types()
        self.c_type.bind("<<ComboboxSelected>>", lambda e: self._sync_color())

        hint = ("Le solde initial correspond au montant présent sur le compte avant la "
                "première opération enregistrée. Laissez vide pour démarrer à zéro.")
        widgets.lbl(self.body, hint, theme.F_SMALL, FAINT, BG, wraplength=S(540),
                    justify="left").pack(anchor="w", pady=(S(4), S(6)))
        self.color_field = f.color("Couleur", account["color"] if account else PRIMARY, 3, 0, 2)
        self.note = f.note("Notes", 4, 0, 2)
        if account and account["notes"]:
            self.note.insert("1.0", account["notes"])
        self.e_name.focus_set()

    def _on_family_changed(self):
        self._fill_types()
        self._sync_color()

    def _fill_types(self):
        family = family_key_of_label(self.var_family.get())
        labels = [ACCOUNT_TYPES[k][0] for k in types_of_family(family)]
        self.c_type.configure(values=labels)
        if self.var_type.get() not in labels:
            self.var_type.set(labels[0] if labels else "")

    def _sync_color(self):
        """Adopte la couleur par défaut du type choisi."""
        self.color_field.set(account_color(type_of_label(self.var_type.get())))

    def validate(self):
        if not self.var_name.get().strip():
            self.show_error("Le nom du compte est obligatoire.")
            return False
        bal = utils.parse_amount(self.var_balance.get() or 0)
        if bal is None:
            self.show_error("Le solde initial n'est pas un montant valide (ex. 1 250,00).")
            return False
        return True

    def values(self):
        return {
            "name": self.var_name.get().strip(),
            "institution": self.var_bank.get().strip(),
            "type": type_of_label(self.var_type.get()),
            "initial_balance": utils.parse_amount(self.var_balance.get() or 0) or 0.0,
            "color": self.color_field.get(),
            "notes": self.note.get("1.0", "end").strip(),
        }


# --------------------------------------------------------------------------
# Opération
# --------------------------------------------------------------------------
class TransactionDialog(widgets.Modal):
    """Dépense, revenu ou virement interne."""

    def __init__(self, master, db, transaction=None, preset_account=None, preset_type="Dépense"):
        editing = transaction is not None
        super().__init__(master, "Modifier l'opération" if editing else "Nouvelle opération",
                         "Saisissez une dépense, un revenu ou un virement entre comptes.",
                         width=640, icon_text="±", tone_name="blue",
                         ok_label="Enregistrer")
        self.db = db
        self.transaction = transaction
        accounts = db.list_accounts()
        self.accounts = accounts
        self.acc_names = [a["name"] for a in accounts]
        self.acc_by_name = {a["name"]: a for a in accounts}

        self.categories = {k: db.list_categories(k) for k in ("depense", "revenu")}
        self.cat_by_name = {}
        for kind, rows in self.categories.items():
            for r in rows:
                self.cat_by_name[(kind, r["name"])] = r

        # type initial
        initial_type = preset_type
        from_name = self.acc_names[0] if self.acc_names else ""
        to_name = self.acc_names[1] if len(self.acc_names) > 1 else ""
        if editing:
            if transaction["transfer_id"]:
                initial_type = "Virement"
                if float(transaction["amount"]) < 0:
                    from_name = transaction["account_name"]
                    to_name = transaction["counterpart_account"] or to_name
                else:
                    from_name = transaction["counterpart_account"] or from_name
                    to_name = transaction["account_name"]
            else:
                initial_type = "Dépense" if float(transaction["amount"]) < 0 else "Revenu"
                from_name = transaction["account_name"]
        elif preset_account:
            acc = db.get_account(preset_account)
            if acc:
                from_name = acc["name"]

        self.var_amount = tk.StringVar(
            value=money_text(abs(float(transaction["amount"]))) if editing else ""
        )
        self.var_payee = tk.StringVar(value=transaction["payee"] if editing else "")
        self.var_account = tk.StringVar(value=from_name)
        self.var_to = tk.StringVar(value=to_name)
        self.var_cat = tk.StringVar(value="")

        head = tk.Frame(self.body, bg=BG)
        head.pack(fill="x")
        self.type_sel = widgets.Segmented(head, ["Dépense", "Revenu", "Virement"],
                                          initial_type, self._on_type_change, height=34)
        self.type_sel.pack(side="left")

        f = Form(self.body)
        self.e_amount = f.money_entry("Montant", self.var_amount, 0, 0, required=True)
        self.date_field = f.date("Date", transaction["date"] if editing else utils.today(), 0, 1)
        self.e_payee = f.text_entry("Libellé", self.var_payee, 1, 0, span=2)
        self.c_account = f.combo("Compte", self.var_account, self.acc_names, 2, 0)
        self.c_to = f.combo("Compte de destination", self.var_to, self.acc_names, 2, 1)
        self.c_cat = f.combo("Catégorie", self.var_cat, [], 3, 0)
        self.c_account.bind("<<ComboboxSelected>>", lambda e: None)

        self.hint_label = widgets.lbl(self.body, "", theme.F_SMALL, FAINT, BG,
                                      wraplength=S(580), justify="left")
        self.hint_label.pack(anchor="w", pady=(S(8), 0))

        if editing and transaction["category_name"] and initial_type != "Virement":
            self.var_cat.set(transaction["category_name"])

        self._on_type_change(initial_type, initial=True)
        if not accounts:
            self.show_error("Ajoutez d'abord un compte dans le portefeuille.")
        self.e_amount.focus_set()

    def _on_type_change(self, value, initial=False):
        is_transfer = value == "Virement"
        # catégories
        kind = "depense" if value == "Dépense" else "revenu"
        names = ["Sans catégorie"] + [c["name"] for c in self.categories.get(kind, [])]
        self.c_cat.configure(values=names)
        if not initial or not self.var_cat.get():
            self.var_cat.set("Sans catégorie")
        # champs : on masque ce qui ne sert pas
        if is_transfer:
            Form.hide(self.c_cat)
            Form.show(self.c_to)
            self.c_to.configure(state="readonly")
        else:
            Form.show(self.c_cat)
            Form.hide(self.c_to)
            self.var_to.set("")
            self.var_cat.set(self.var_cat.get() or "Sans catégorie")
        if not is_transfer:
            self.hint_label.configure(
                text="Le montant est saisi en positif : il sera déduit pour une dépense, "
                     "ajouté pour un revenu."
            )
        else:
            if not self.var_to.get():
                others = [n for n in self.acc_names if n != self.var_account.get()]
                self.var_to.set(others[0] if others else "")
            self.hint_label.configure(
                text="Le virement déplace de l'argent entre deux comptes : le patrimoine "
                     "total reste inchangé."
            )

    def validate(self):
        amount = utils.parse_amount(self.var_amount.get())
        if amount is None or amount <= 0:
            self.show_error("Saisissez un montant positif, par exemple 42,50.")
            return False
        if not self.date_field.is_valid():
            self.show_error("La date n'est pas valide (format JJ/MM/AAAA).")
            return False
        acc = self.acc_by_name.get(self.var_account.get())
        if not acc:
            self.show_error("Sélectionnez un compte.")
            return False
        if self.type_sel.get() == "Virement":
            to = self.acc_by_name.get(self.var_to.get())
            if not to:
                self.show_error("Sélectionnez le compte de destination.")
                return False
            if to["id"] == acc["id"]:
                self.show_error("Les deux comptes du virement doivent être différents.")
                return False
        return True

    def apply(self):
        """Écrit dans la base. Retourne un message de confirmation."""
        db = self.db
        amount = utils.parse_amount(self.var_amount.get()) or 0.0
        date = self.date_field.get()
        acc = self.acc_by_name[self.var_account.get()]
        kind = self.type_sel.get()
        payee = self.var_payee.get().strip()

        old_transfer = self.transaction["transfer_id"] if self.transaction else None
        if old_transfer:
            db.delete_transfer(old_transfer)

        if kind == "Virement":
            to = self.acc_by_name[self.var_to.get()]
            db.add_transfer(date, acc["id"], to["id"], amount,
                            notes=self.transaction["notes"] if self.transaction else "")
            return f"Virement de {utils.fmt_money(amount)} enregistré"

        category_id = None
        cat_name = self.var_cat.get()
        if cat_name and cat_name != "Sans catégorie":
            cat = self.cat_by_name.get(("depense" if kind == "Dépense" else "revenu", cat_name))
            category_id = cat["id"] if cat else None
        signed = -amount if kind == "Dépense" else amount
        if self.transaction:
            db.update_transaction(self.transaction["id"], date, acc["id"], signed,
                                  category_id, payee, self.transaction["notes"] or "")
        else:
            db.add_transaction(date, acc["id"], signed, category_id, payee)
        return f"{kind} de {utils.fmt_money(amount)} enregistrée"


# --------------------------------------------------------------------------
# Projet d'épargne
# --------------------------------------------------------------------------
class ProjectDialog(widgets.Modal):
    def __init__(self, master, db, project=None):
        editing = project is not None
        super().__init__(master, "Modifier le projet" if editing else "Nouveau projet d'épargne",
                         "Définissez un objectif, une échéance et un rythme d'épargne.",
                         width=640, icon_text="◎", tone_name="green",
                         ok_label="Enregistrer")
        self.db = db
        self.project = project
        accounts = db.list_accounts()
        self.acc_names = ["Aucun compte"] + [a["name"] for a in accounts]
        self.acc_by_name = {a["name"]: a for a in accounts}

        self.var_name = tk.StringVar(value=project["name"] if editing else "")
        self.var_target = tk.StringVar(
            value=money_text(project["target_amount"]) if editing else "")
        self.var_monthly = tk.StringVar(
            value=money_text(project["monthly_contribution"]) if editing else "")
        self.var_priority = tk.StringVar(
            value=PRIORITIES.get(int(project["priority"]), "Moyenne") if editing else "Moyenne")
        acc_value = "Aucun compte"
        if editing and project["account_id"]:
            acc_value = project["account_name"] or "Aucun compte"
        self.var_account = tk.StringVar(value=acc_value)
        self.var_initial = tk.StringVar(value="")

        f = Form(self.body)
        self.e_name = f.text_entry("Nom du projet", self.var_name, 0, 0, span=2, required=True)
        self.e_target = f.money_entry("Montant de l'objectif", self.var_target, 1, 0, required=True)
        self.date_field = f.date("Échéance", project["target_date"] if editing else
                                 utils.add_months(utils.today(), 12), 1, 1)
        self.c_account = f.combo("Compte dédié", self.var_account, self.acc_names, 2, 0)
        self.e_monthly = f.money_entry("Versement mensuel prévu", self.var_monthly, 2, 1)
        self.c_priority = f.combo("Priorité", self.var_priority,
                                  [PRIORITIES[k] for k in sorted(PRIORITIES)], 3, 0)
        self.color_field = f.color("Couleur", project["color"] if editing else "#2563EB", 3, 1)
        if not editing:
            holder = f.cell("Déjà épargné (facultatif)", 4, 0)
            box = tk.Frame(holder, bg=SURFACE, highlightbackground=BORDER,
                           highlightcolor=PRIMARY, highlightthickness=1)
            box.pack(fill="x")
            tk.Label(box, text=utils.CURRENCY, font=theme.F_SMALL, fg=MUTED,
                     bg=SURFACE).pack(side="right", padx=(0, S(10)))
            self.e_initial = tk.Entry(box, textvariable=self.var_initial,
                                      font=(theme.FONT, 12, "bold"), fg=TEXT, bg=SURFACE,
                                      relief="flat", bd=0, justify="right",
                                      insertbackground=TEXT, highlightthickness=0)
            self.e_initial.pack(side="left", fill="x", expand=True, ipady=S(6),
                                padx=(S(8), S(4)))
        self.note = f.note("Notes", 4 if editing else 5, 0, 2)
        if editing and project["notes"]:
            self.note.insert("1.0", project["notes"])
        self.e_name.focus_set()

    def validate(self):
        if not self.var_name.get().strip():
            self.show_error("Le nom du projet est obligatoire.")
            return False
        target = utils.parse_amount(self.var_target.get())
        if target is None or target <= 0:
            self.show_error("Le montant de l'objectif doit être supérieur à zéro.")
            return False
        if not self.date_field.is_valid():
            self.show_error("L'échéance n'est pas une date valide.")
            return False
        monthly = utils.parse_amount(self.var_monthly.get() or 0)
        if monthly is None or monthly < 0:
            self.show_error("Le versement mensuel doit être un montant positif.")
            return False
        return True

    def data(self):
        acc = self.acc_by_name.get(self.var_account.get())
        return {
            "name": self.var_name.get().strip(),
            "target_amount": utils.parse_amount(self.var_target.get()),
            "target_date": utils.iso(self.date_field.get()),
            "account_id": acc["id"] if acc else None,
            "monthly_contribution": utils.parse_amount(self.var_monthly.get() or 0) or 0.0,
            "priority": next((k for k, v in PRIORITIES.items() if v == self.var_priority.get()), 2),
            "color": self.color_field.get(),
            "notes": self.note.get("1.0", "end").strip(),
        }


# --------------------------------------------------------------------------
# Versement sur un projet
# --------------------------------------------------------------------------
class ContributionDialog(widgets.Modal):
    def __init__(self, master, db, project):
        super().__init__(master, "Nouveau versement",
                         f"{project['name']} — objectif {utils.fmt_money(project['target_amount'])}",
                         width=540, icon_text="+", tone_name="green",
                         ok_label="Enregistrer le versement")
        self.db = db
        self.project = project
        accounts = [a for a in db.list_accounts()
                    if project["account_id"] is None or a["id"] != project["account_id"]]
        self.acc_names = ["Aucun (simple affectation)"] + [a["name"] for a in accounts]
        self.acc_by_name = {a["name"]: a for a in accounts}

        self.var_amount = tk.StringVar(value=money_text(project["monthly_contribution"]
                                                        if project["monthly_contribution"] else ""))
        self.var_source = tk.StringVar(value="Aucun (simple affectation)")

        f = Form(self.body)
        self.e_amount = f.money_entry("Montant du versement", self.var_amount, 0, 0, required=True)
        self.date_field = f.date("Date", utils.today(), 0, 1)
        self.c_source = f.combo("Depuis le compte", self.var_source, self.acc_names, 1, 0, span=2)
        self.note = f.note("Note", 2, 0, 2)

        hint = ("Le versement est affecté au projet. Si vous choisissez un compte source, "
                "un virement réel est créé vers le compte dédié au projet."
                if project["account_id"] else
                "Ce projet n'est pas rattaché à un compte : le versement est une simple "
                "affectation d'épargne.")
        widgets.lbl(self.body, hint, theme.F_SMALL, FAINT, BG, wraplength=S(480),
                    justify="left").pack(anchor="w", pady=(S(8), 0))
        self.e_amount.focus_set()

    def validate(self):
        amount = utils.parse_amount(self.var_amount.get())
        if amount is None or amount == 0:
            self.show_error("Saisissez un montant (négatif pour un retrait).")
            return False
        if not self.date_field.is_valid():
            self.show_error("La date n'est pas valide.")
            return False
        return True

    def apply(self):
        amount = utils.parse_amount(self.var_amount.get()) or 0.0
        source = self.acc_by_name.get(self.var_source.get())
        self.db.add_contribution(
            self.project["id"], self.date_field.get(), amount,
            self.note.get("1.0", "end").strip(),
            source_account_id=source["id"] if source else None,
        )
        return f"Versement de {utils.fmt_money(amount)} enregistré"


# --------------------------------------------------------------------------
# Budget
# --------------------------------------------------------------------------
class BudgetDialog(widgets.Modal):
    def __init__(self, master, db, month: str, category=None, current=0):
        super().__init__(master, "Définir un budget",
                         f"Budget mensuel — {utils.fmt_month(utils.parse_month_key(month))}",
                         width=480, icon_text="◔", tone_name="violet",
                         ok_label="Enregistrer")
        self.db = db
        self.month = month
        cats = db.list_categories("depense")
        self.cats = cats
        names = [c["name"] for c in cats]
        self.var_cat = tk.StringVar(value=category["name"] if category else (names[0] if names else ""))
        self.var_amount = tk.StringVar(value=money_text(current) if current else "")

        f = Form(self.body, columns=1)
        self.c_cat = f.combo("Catégorie de dépense", self.var_cat, names, 0, 0)
        if category:
            self.c_cat.configure(state="disabled")
        self.e_amount = f.money_entry("Montant du budget mensuel", self.var_amount, 1, 0,
                                      required=True)
        widgets.lbl(self.body, "Le budget s'applique au mois affiché. 0 supprime le budget.",
                    theme.F_SMALL, FAINT, BG).pack(anchor="w", pady=(S(8), 0))
        self.e_amount.focus_set()

    def validate(self):
        amount = utils.parse_amount(self.var_amount.get() or 0)
        if amount is None or amount < 0:
            self.show_error("Saisissez un montant positif (ou 0 pour supprimer).")
            return False
        return True

    def apply(self):
        cat = next((c for c in self.cats if c["name"] == self.var_cat.get()), None)
        if not cat:
            return "Aucune catégorie"
        amount = utils.parse_amount(self.var_amount.get() or 0) or 0
        if amount <= 0:
            self.db.delete_budget(cat["id"], self.month)
            return "Budget supprimé"
        self.db.set_budget(cat["id"], self.month, amount)
        return f"Budget {cat['name']} : {utils.fmt_money(amount)}"


# --------------------------------------------------------------------------
# Catégorie
# --------------------------------------------------------------------------
class CategoryDialog(widgets.Modal):
    def __init__(self, master, category=None, kind="depense"):
        super().__init__(master, "Modifier la catégorie" if category else "Nouvelle catégorie",
                         "Les catégories classent vos dépenses et vos revenus.",
                         width=480, icon_text="◦", tone_name="violet",
                         ok_label="Enregistrer")
        self.category = category
        self.kind = category["kind"] if category else kind
        self.var_name = tk.StringVar(value=category["name"] if category else "")
        self.var_kind = tk.StringVar(value="Dépense" if self.kind == "depense" else "Revenu")

        f = Form(self.body, columns=2)
        self.e_name = f.text_entry("Nom", self.var_name, 0, 0, span=2, required=True)
        self.c_kind = f.combo("Type", self.var_kind, ["Dépense", "Revenu"], 1, 0)
        if category:
            self.c_kind.configure(state="disabled")
        self.color_field = f.color("Couleur", category["color"] if category else "#3B82F6", 2, 0, 2)
        self.e_name.focus_set()

    def validate(self):
        if not self.var_name.get().strip():
            self.show_error("Le nom de la catégorie est obligatoire.")
            return False
        return True

    def values(self):
        return {
            "name": self.var_name.get().strip(),
            "kind": "depense" if self.var_kind.get() == "Dépense" else "revenu",
            "color": self.color_field.get(),
        }
