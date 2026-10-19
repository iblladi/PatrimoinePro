"""Tests hors interface de la couche métier (exécution : python tests/test_backend.py)."""
from __future__ import annotations

import os
import shutil
import sys
import traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app import analytics, utils  # noqa: E402
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
    tmp = os.path.join(workdir, "test.db")
    for suffix in ("", "-wal", "-shm"):
        try:
            os.remove(tmp + suffix)
        except OSError:
            pass
    db = Database(tmp)

    print("· base vide")
    check("aucun compte", len(db.list_accounts()) == 0)
    check("catégories initiales", len(db.list_categories()) >= 10)

    print("· jeu de démonstration")
    stats = db.seed_demo()
    print("  ", stats)
    accounts = db.list_accounts()
    check("4 comptes", len(accounts) == 4, str(len(accounts)))
    total = analytics.total_net_worth(db)
    print(f"   patrimoine net = {utils.fmt_money(total)}")
    check("patrimoine positif", total > 20000, str(total))
    check("aucun compte négatif", all(a["balance"] > 0 for a in accounts),
          str([(a["name"], a["balance"]) for a in accounts]))

    series = analytics.net_worth_series(db, 12)
    check("série 12 points", len(series) == 12)
    check("série croissante", series[-1][1] > series[0][1], f"{series[0]} -> {series[-1]}")
    print("   ", [(utils.fmt_month(d, True), round(v)) for d, v in series[-4:]])

    flows = analytics.flows_series(db, 6)
    check("flux 6 mois", len(flows) == 6)
    avg_income = sum(f["income"] for f in flows) / 6
    print(f"   revenu moyen/mois = {utils.fmt_money(avg_income)}")
    check("revenus > 2000", avg_income > 2000, str(avg_income))

    t = analytics.totals(db, *utils.month_bounds())
    print(f"   mois courant : entrées {utils.fmt_money(t['income'])}, "
          f"sorties {utils.fmt_money(t['expense'])}")

    cats, cat_total = analytics.expenses_by_category(db, *utils.month_bounds())
    check("catégories de dépenses", len(cats) > 0)
    print("   top :", [(c["name"], round(c["amount"])) for c in cats[:4]])

    print("· projets")
    projects = db.list_projects()
    check("4 projets", len(projects) == 4, str(len(projects)))
    for p in projects:
        m = analytics.project_metrics(p, db.project_contributions(p["id"]))
        print(f"   {p['name']:<24} {m['saved']:>9.0f}/{m['target']:<8.0f} "
              f"{m['pct']*100:5.1f}%  reste {m['remaining']:>8.0f}  "
              f"statut {m['status']:<20} proj {m['projected']}")
        check(f"progression {p['name']}", 0 < m["pct"] <= 1.01, str(m["pct"]))
        check(f"statut {p['name']}", m["status"] in
              ("Objectif atteint", "Sans échéance", "En avance", "Dans les temps",
               "En retard", "Effort à augmenter"), m["status"])

    print("· opérations")
    tid = db.add_transaction(utils.today(), accounts[0]["id"], -42.5, None, "Test", "")
    tx = db.get_transaction(tid)
    check("ajout transaction", tx is not None and tx["amount"] == -42.5)
    db.update_transaction(tid, utils.today(), accounts[0]["id"], -50.0, None, "Test modifié", "")
    check("modification", db.get_transaction(tid)["amount"] == -50.0)
    db.delete_transaction(tid)
    check("suppression", db.get_transaction(tid) is None)

    before = db.account_balance(accounts[0]["id"])
    db.add_transfer(utils.today(), accounts[0]["id"], accounts[1]["id"], 100.0, "Essai")
    check("virement débit", abs(db.account_balance(accounts[0]["id"]) - (before - 100)) < 0.01)
    check("virement crédit", db.account_balance(accounts[1]["id"]) > 0)

    print("· versement projet avec virement")
    p = db.get_project(projects[0]["id"])
    target_account = p["account_id"]
    src = [a["id"] for a in db.list_accounts() if a["id"] != target_account][0]
    bal_src = db.account_balance(src)
    bal_dst = db.account_balance(target_account)
    cid = db.add_contribution(p["id"], utils.today(), 250.0, "test", src)
    check("versement enregistré", len(db.project_contributions(p["id"])) > 0)
    check("transfert source", abs(db.account_balance(src) - (bal_src - 250)) < 0.01)
    check("transfert cible", abs(db.account_balance(target_account) - (bal_dst + 250)) < 0.01)
    db.delete_contribution(cid)
    check("annulation transfert", abs(db.account_balance(src) - bal_src) < 0.01)

    print("· budgets")
    overview = analytics.budget_overview(db, utils.month_key())
    check("budgets présents", len(overview["items"]) >= 5)
    print(f"   budget {utils.fmt_money(overview['total_budget'])} / "
          f"dépensé {utils.fmt_money(overview['total_spent'])} "
          f"({overview['pct']*100:.0f} %)")

    print("· formats")
    check("format montant", utils.fmt_money(1234.5) == "1\u202f234,50\u202f€", utils.fmt_money(1234.5))
    check("format négatif", utils.fmt_money(-1234.5) == "−1\u202f234,50\u202f€", utils.fmt_money(-1234.5))
    check("parse virgule", utils.parse_amount("1 234,56 €") == 1234.56)
    check("parse négatif", utils.parse_amount("-12.5") == -12.5)
    check("parse invalide", utils.parse_amount("abc") is None)
    check("parse milliers point+virgule", utils.parse_amount("1.500,50") == 1500.5)
    check("parse milliers multiples", utils.parse_amount("1.234.567,89") == 1234567.89)
    check("parse point milliers seul", utils.parse_amount("1.500") == 1500.0)
    check("parse décimal .5", utils.parse_amount(",5") == 0.5)
    check("parse virgule multiple", utils.parse_amount("1,2,3") is None)
    check("parse espaces", utils.parse_amount("   ") is None)
    check("parse négatif milliers", utils.parse_amount("-1.500,50") == -1500.5)
    check("date fr", utils.fmt_date("2026-03-09") == "09/03/2026")
    check("parse date", utils.parse_date("09/03/2026").isoformat() == "2026-03-09")
    check("mois +1", utils.add_months(utils.parse_date("2026-01-31"), 1).isoformat() == "2026-02-28")

    print("· sauvegarde")
    bak = os.path.join(os.path.dirname(tmp), "backup.db")
    db.backup_to(bak)
    check("fichier de sauvegarde", os.path.exists(bak) and os.path.getsize(bak) > 1000)

    db.close()

    print()
    if FAILED:
        print(f"ÉCHECS : {len(FAILED)} -> {FAILED}")
        return 1
    print("Tous les tests métier sont passés.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        sys.exit(2)
