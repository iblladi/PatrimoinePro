"""Tests des formulaires (sans affichage) : validation et écriture en base."""
from __future__ import annotations

import os
import sys
import traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import tkinter as tk  # noqa: E402

from app import dialogs, theme, utils  # noqa: E402
from app.db import Database  # noqa: E402

FAILED = []


def check(label, condition, detail=""):
    if condition:
        print(f"  OK   {label}")
    else:
        print(f"  FAIL {label} {detail}")
        FAILED.append(label)


def main():
    workdir = os.path.join(ROOT, ".tmp")
    os.makedirs(workdir, exist_ok=True)
    path = os.path.join(workdir, "dialogs.db")
    for suffix in ("", "-wal", "-shm"):
        try:
            os.remove(path + suffix)
        except OSError:
            pass

    db = Database(path)
    db.seed_demo()
    accounts = db.list_accounts()

    root = tk.Tk()
    root.withdraw()
    theme.setup(root)

    try:
        print("· compte")
        dlg = dialogs.AccountDialog(root)
        dlg.var_name.set("Compte test")
        dlg.var_balance.set("1 500,50")
        check("validation compte", dlg.validate())
        db.add_account(**dlg.values())
        created = [a for a in db.list_accounts() if a["name"] == "Compte test"]
        check("compte créé", len(created) == 1)
        check("solde initial", created and abs(created[0]["initial_balance"] - 1500.5) < 0.01,
              str(created[0]["initial_balance"] if created else None))
        check("type par défaut", created and created[0]["type"] == "courant",
              str(created[0]["type"] if created else None))
        dlg.destroy()

        print("· montant initial : formats acceptés")
        for text, expected in (("1.500,50", 1500.5), ("1500,50", 1500.5),
                               ("1 500,50", 1500.5), ("1500.50", 1500.5),
                               ("2 000", 2000.0)):
            dlg = dialogs.AccountDialog(root)
            dlg.var_name.set("Test format")
            dlg.var_balance.set(text)
            ok = dlg.validate()
            value = dlg.values()["initial_balance"]
            check(f"solde « {text} »", ok and abs(value - expected) < 0.01,
                  f"ok={ok} value={value}")
            dlg.destroy()

        print("· message d'erreur visible")
        dlg = dialogs.AccountDialog(root)
        dlg.center()
        dlg.deiconify()
        for _ in range(4):
            root.update()
        required_before = dlg.winfo_reqheight()
        dlg.show_error("Message d'erreur de test")
        for _ in range(4):
            root.update()
        check("la fenêtre s'agrandit", dlg.winfo_reqheight() > required_before,
              f"{required_before} -> {dlg.winfo_reqheight()}")
        check("message affiché", dlg._error_var.get() == "Message d'erreur de test")
        dlg.destroy()

        print("· catalogue des types de comptes")
        dlg = dialogs.AccountDialog(root)
        check("famille initiale", dlg.var_family.get() == "Comptes courants",
              dlg.var_family.get())
        dlg.var_family.set("Épargne")
        dlg._on_family_changed()
        check("type après famille Épargne", dlg.var_type.get() == "Livret A",
              dlg.var_type.get())
        dlg.var_type.set("Livret d'épargne populaire (LEP)")
        dlg._sync_color()
        check("couleur du type", dlg.color_field.get() == "#059669", dlg.color_field.get())
        dlg.var_name.set("LEP test")
        check("clé de type enregistrée", dlg.values()["type"] == "lep",
              dlg.values()["type"])
        dlg.var_family.set("Retraite")
        dlg._on_family_changed()
        check("types de retraite", dlg.var_type.get() in
              ("PER (plan d'épargne retraite)", "PERP", "PER entreprise (art. 83)",
               "PER Madelin"), dlg.var_type.get())
        dlg.destroy()

        print("· opération (dépense)")
        dlg = dialogs.TransactionDialog(root, db)
        dlg.var_amount.set("42,50")
        dlg.var_payee.set("Boulangerie")
        dlg.var_cat.set("Alimentation")
        check("validation dépense", dlg.validate())
        n_before = db.transaction_count()
        dlg.apply()
        dlg.destroy()
        check("opération ajoutée", db.transaction_count() == n_before + 1)
        created = db.list_transactions(search="Boulangerie")
        check("opération retrouvée", len(created) == 1, str(len(created)))
        last = created[0] if created else db.list_transactions(limit=1)[0]
        check("montant négatif", abs(float(last["amount"]) + 42.5) < 0.01, str(last["amount"]))
        check("libellé", last["payee"] == "Boulangerie", last["payee"])
        check("catégorie", last["category_name"] == "Alimentation", str(last["category_name"]))

        print("· virement")
        dlg = dialogs.TransactionDialog(root, db)
        dlg.type_sel.set("Virement")
        dlg._on_type_change("Virement")
        dlg.var_amount.set("100")
        dlg.var_account.set("Compte courant")
        dlg.var_to.set("Livret A")
        check("validation virement", dlg.validate())
        src = next(a for a in db.list_accounts() if a["name"] == "Compte courant")
        dst = next(a for a in db.list_accounts() if a["name"] == "Livret A")
        b_src, b_dst = float(src["balance"]), float(dst["balance"])
        dlg.apply()
        dlg.destroy()
        src2 = db.get_account(src["id"])
        dst2 = db.get_account(dst["id"])
        check("virement débité", abs(db.account_balance(src["id"]) - (b_src - 100)) < 0.01)
        check("virement crédité", abs(db.account_balance(dst["id"]) - (b_dst + 100)) < 0.01)

        print("· modification d'un virement")
        transfer = None
        for row in db.list_transactions(limit=60):
            if row["transfer_id"]:
                transfer = row
                break
        check("virement trouvé", transfer is not None)
        if transfer:
            old_id = transfer["transfer_id"]
            dlg = dialogs.TransactionDialog(root, db, transaction=transfer)
            dlg.var_amount.set("250")
            check("validation édition", dlg.validate())
            dlg.apply()
            dlg.destroy()
            legs = db.conn.execute(
                "SELECT amount FROM transactions WHERE transfer_id=?",
                (old_id,)).fetchall()
            check("ancien virement supprimé", len(legs) == 0, str(len(legs)))
            new_transfer = None
            for row in db.list_transactions(limit=60):
                if row["transfer_id"] and row["transfer_id"] != old_id:
                    new_transfer = row
                    break
            check("nouveau virement créé", new_transfer is not None)
            if new_transfer:
                legs = db.conn.execute(
                    "SELECT amount FROM transactions WHERE transfer_id=?",
                    (new_transfer["transfer_id"],)).fetchall()
                check("deux écritures", len(legs) == 2, str(len(legs)))
                check("montants mis à jour",
                      sorted(abs(float(x["amount"])) for x in legs) == [250.0, 250.0],
                      str([x["amount"] for x in legs]))

        print("· projet")
        dlg = dialogs.ProjectDialog(root, db)
        dlg.var_name.set("Projet test")
        dlg.var_target.set("10 000")
        dlg.var_monthly.set("250")
        dlg.var_initial.set("1 000")
        dlg.var_account.set("Livret A")
        check("validation projet", dlg.validate())
        data = dlg.data()
        pid = db.add_project(initial_amount=1000, **data)
        dlg.destroy()
        project = db.get_project(pid)
        check("projet créé", project is not None)
        check("projet rattaché au compte", project["account_name"] == "Livret A",
              str(project["account_name"]))
        check("épargne initiale", abs(float(project["saved"]) - 1000) < 0.01,
              str(project["saved"]))

        print("· versement")
        dlg = dialogs.ContributionDialog(root, db, project)
        dlg.var_amount.set("300")
        dlg.var_source.set("Compte courant")
        check("validation versement", dlg.validate())
        src_bal = db.account_balance(src["id"])
        dlg.apply()
        dlg.destroy()
        project = db.get_project(pid)
        check("épargne mise à jour", abs(float(project["saved"]) - 1300) < 0.01,
              str(project["saved"]))
        check("compte source débité", abs(db.account_balance(src["id"]) - (src_bal - 300)) < 0.01)

        print("· budget")
        dlg = dialogs.BudgetDialog(root, db, utils.month_key(), current=0)
        dlg.var_cat.set("Alimentation")
        dlg.var_amount.set("500")
        check("validation budget", dlg.validate())
        dlg.apply()
        dlg.destroy()
        rows = {r["category_name"]: float(r["amount"]) for r in db.budgets_for(utils.month_key())}
        check("budget enregistré", abs(rows.get("Alimentation", 0) - 500) < 0.01, str(rows))

        print("· catégorie")
        dlg = dialogs.CategoryDialog(root, kind="depense")
        dlg.var_name.set("Animaux")
        check("validation catégorie", dlg.validate())
        data = dlg.values()
        cid = db.add_category(data["name"], data["kind"], data["color"])
        dlg.destroy()
        check("catégorie créée", db.get_category(cid)["name"] == "Animaux")

        print("· devise")
        symbol_before = utils.CURRENCY
        utils.set_currency("CHF")
        check("format CHF", utils.fmt_money(1234.5).endswith("CHF"), utils.fmt_money(1234.5))
        utils.set_currency(symbol_before)
        check("format restauré", utils.fmt_money(1).endswith("€"), utils.fmt_money(1))

        print("· validations négatives")
        dlg = dialogs.TransactionDialog(root, db)
        dlg.var_amount.set("abc")
        check("montant invalide refusé", not dlg.validate())
        dlg.var_amount.set("-5")
        check("montant négatif refusé", not dlg.validate())
        dlg.var_amount.set("20")
        dlg.date_field.var.set("32/13/2026")
        check("date invalide refusée", not dlg.validate())
        dlg.destroy()

        dlg = dialogs.ProjectDialog(root, db)
        dlg.var_name.set("")
        check("projet sans nom refusé", not dlg.validate())
        dlg.destroy()

    finally:
        try:
            root.destroy()
        except Exception:
            pass

    print()
    if FAILED:
        print(f"ÉCHECS : {len(FAILED)} -> {FAILED}")
        return 1
    print("Tous les formulaires fonctionnent.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        sys.exit(2)
