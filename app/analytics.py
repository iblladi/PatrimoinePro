"""Calculs : patrimoine, flux, catégories, budgets et trajectoires des projets."""
from __future__ import annotations

import bisect
import datetime as dt
import math

from . import utils


# --------------------------------------------------------------------------
# Patrimoine
# --------------------------------------------------------------------------
def total_net_worth(db) -> float:
    return sum(float(a["balance"] or 0) for a in db.list_accounts())


def net_worth_series(db, months: int = 12, end=None):
    """Valeur du patrimoine à la fin de chacun des `months` derniers mois."""
    end_date = utils.parse_date(end) or utils.today()
    last_month = end_date.replace(day=1)

    rows = db.conn.execute("SELECT date, amount FROM transactions").fetchall()
    pairs = sorted((r["date"], float(r["amount"])) for r in rows)
    dates = [p[0] for p in pairs]
    prefix = [0.0]
    for _, amount in pairs:
        prefix.append(prefix[-1] + amount)

    accounts = db.list_accounts(include_archived=True)
    base = sum(float(a["initial_balance"] or 0) for a in accounts)
    points = []
    for i in range(months - 1, -1, -1):
        m = utils.add_months(last_month, -i)
        m_end = utils.month_bounds(m)[1]
        key = utils.iso(m_end)
        idx = bisect.bisect_right(dates, key)
        points.append((m_end, base + prefix[idx]))
    return points


def net_worth_change(db, days: int = 30):
    """Variation du patrimoine sur les `days` derniers jours."""
    today = utils.today()
    start = today - dt.timedelta(days=days)
    current = total_net_worth(db)
    row = db.conn.execute(
        "SELECT SUM(amount) s FROM transactions WHERE date > ?", (utils.iso(start),)
    ).fetchone()
    past = current - float(row["s"] or 0)
    return current, current - past


# --------------------------------------------------------------------------
# Flux
# --------------------------------------------------------------------------
def totals(db, start=None, end=None, include_transfers: bool = False):
    where, params = ["1=1"], []
    if start:
        where.append("date >= ?")
        params.append(utils.iso(start))
    if end:
        where.append("date <= ?")
        params.append(utils.iso(end))
    if not include_transfers:
        where.append("transfer_id IS NULL")
    row = db.conn.execute(
        f"""SELECT
              COALESCE(SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END), 0) AS income,
              COALESCE(SUM(CASE WHEN amount < 0 THEN -amount ELSE 0 END), 0) AS expense,
              COUNT(*) AS count
            FROM transactions WHERE {' AND '.join(where)}""",
        params,
    ).fetchone()
    return {
        "income": float(row["income"]),
        "expense": float(row["expense"]),
        "count": int(row["count"]),
        "balance": float(row["income"]) - float(row["expense"]),
    }


def flows_series(db, months: int = 6, end=None):
    """Revenus / dépenses par mois (hors virements internes)."""
    end_date = utils.parse_date(end) or utils.today()
    last_month = end_date.replace(day=1)
    rows = db.conn.execute(
        """SELECT substr(date, 1, 7) AS mk,
                  SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) AS inc,
                  SUM(CASE WHEN amount < 0 THEN -amount ELSE 0 END) AS exp
           FROM transactions WHERE transfer_id IS NULL GROUP BY mk"""
    ).fetchall()
    by_month = {r["mk"]: (float(r["inc"] or 0), float(r["exp"] or 0)) for r in rows}
    series = []
    for i in range(months - 1, -1, -1):
        m = utils.add_months(last_month, -i)
        key = utils.month_key(m)
        inc, exp = by_month.get(key, (0.0, 0.0))
        series.append({
            "date": m,
            "label": utils.MONTHS_SHORT[m.month - 1],
            "income": inc,
            "expense": exp,
            "net": inc - exp,
        })
    return series


def expenses_by_category(db, start=None, end=None, limit=None):
    where = ["amount < 0", "transfer_id IS NULL"]
    params = []
    if start:
        where.append("t.date >= ?")
        params.append(utils.iso(start))
    if end:
        where.append("t.date <= ?")
        params.append(utils.iso(end))
    rows = db.conn.execute(
        f"""SELECT COALESCE(c.name, 'Non classé') AS name,
                   COALESCE(c.color, '#94A3B8') AS color,
                   -SUM(t.amount) AS amount
            FROM transactions t LEFT JOIN categories c ON c.id = t.category_id
            WHERE {' AND '.join(where)}
            GROUP BY COALESCE(c.id, 0)
            ORDER BY amount DESC""",
        params,
    ).fetchall()
    items = [{"name": r["name"], "color": r["color"], "amount": float(r["amount"])} for r in rows]
    if limit:
        items = items[:limit]
    total = sum(i["amount"] for i in items) or 1.0
    for i in items:
        i["pct"] = i["amount"] / total
    return items, total


def savings_rate(income: float, expense: float) -> float | None:
    if not income:
        return None
    return (income - expense) / income


# --------------------------------------------------------------------------
# Projets d'épargne
# --------------------------------------------------------------------------
def monthly_savings_rate(db, months: int = 6) -> float:
    """Moyenne des versements projets des derniers mois (tous projets)."""
    start = utils.add_months(utils.today().replace(day=1), -months)
    row = db.conn.execute(
        "SELECT COALESCE(SUM(amount), 0) s FROM project_contributions WHERE date >= ? AND amount > 0",
        (utils.iso(start),),
    ).fetchone()
    return float(row["s"]) / max(1, months)


def project_metrics(project, contributions=None, today=None) -> dict:
    """Indicateurs complets d'un projet d'épargne."""
    today = utils.parse_date(today) or utils.today()
    target = float(project["target_amount"] or 0)
    saved = float(project["saved"] if "saved" in project.keys() else 0)
    if contributions is None:
        contributions = []
    if not saved and contributions:
        saved = sum(float(c["amount"]) for c in contributions)

    remaining = max(target - saved, 0.0)
    pct = (saved / target) if target > 0 else 0.0
    target_date = utils.parse_date(project["target_date"])
    start_date = utils.parse_date(project["start_date"]) or today
    monthly_planned = float(project["monthly_contribution"] or 0)

    # Rythme observé : moyenne mensuelle des versements des 6 derniers mois
    horizon = utils.add_months(today, -6)
    recent = [c for c in contributions
              if utils.parse_date(c["date"]) and utils.parse_date(c["date"]) >= horizon
              and float(c["amount"]) > 0]
    active_months = len({str(c["date"])[:7] for c in recent}) or 1
    observed = sum(float(c["amount"]) for c in recent) / active_months if recent else 0.0
    pace = observed if observed > 0 else monthly_planned

    months_left = utils.months_between(today, target_date) if target_date else None
    days_left = (target_date - today).days if target_date else None
    required_monthly = None
    if months_left is not None and months_left > 0:
        required_monthly = remaining / months_left

    projected = None
    if remaining <= 0:
        projected = today
    elif pace > 0:
        n = remaining / pace
        projected = utils.add_months(today, max(1, math.ceil(n)))

    # Avance / retard par rapport à une progression linéaire vers l'échéance
    delta = 0.0
    expected = None
    if target_date and target_date > start_date:
        elapsed = max(0.0, utils.months_between(start_date, today))
        duration = max(0.1, utils.months_between(start_date, target_date))
        ratio = utils.clamp(elapsed / duration, 0.0, 1.0)
        expected = target * ratio
        delta = saved - expected

    if remaining <= 0:
        status, tone = "Objectif atteint", "green"
    elif target_date is None:
        status, tone = "Sans échéance", "muted"
    elif projected and projected <= target_date:
        status, tone = ("En avance" if delta > 0 else "Dans les temps"), "green"
    elif required_monthly and monthly_planned and required_monthly > monthly_planned * 1.6:
        status, tone = "Effort à augmenter", "red"
    else:
        status, tone = "En retard", "amber"

    return {
        "saved": saved,
        "target": target,
        "remaining": remaining,
        "pct": utils.clamp(pct, 0.0, 1.0),
        "pct_raw": pct,
        "target_date": target_date,
        "months_left": months_left,
        "days_left": days_left,
        "monthly_planned": monthly_planned,
        "observed": observed,
        "pace": pace,
        "required_monthly": required_monthly,
        "projected": projected,
        "expected": expected,
        "delta": delta,
        "status": status,
        "tone": tone,
        "done": remaining <= 0,
    }


def contributions_cumulative(project, contributions, target: float | None = None):
    """Série cumulée des versements (pour le graphique du projet)."""
    total = 0.0
    points = []
    for c in contributions:
        total += float(c["amount"])
        points.append((utils.parse_date(c["date"]) or utils.today(), total))
    if not points:
        points.append((utils.today(), 0.0))
    return points


def upcomings(db, limit: int = 4):
    """Prochains jalons : projets triés par échéance encore ouverte."""
    items = []
    for p in db.list_projects():
        m = project_metrics(p, db.project_contributions(p["id"]))
        if m["done"] or not m["target_date"]:
            continue
        items.append((m["target_date"], p, m))
    items.sort(key=lambda x: x[0])
    return items[:limit]


# --------------------------------------------------------------------------
# Budgets
# --------------------------------------------------------------------------
def budget_overview(db, month: str):
    rows = db.budgets_for(month)
    total_budget = sum(float(r["amount"]) for r in rows)
    total_spent = sum(float(r["spent"]) for r in rows)
    items = []
    for r in rows:
        amount = float(r["amount"])
        spent = float(r["spent"])
        items.append({
            "category_id": r["category_id"],
            "name": r["category_name"],
            "color": r["category_color"],
            "budget": amount,
            "spent": spent,
            "remaining": amount - spent,
            "pct": (spent / amount) if amount > 0 else 0.0,
        })
    return {
        "items": items,
        "total_budget": total_budget,
        "total_spent": total_spent,
        "remaining": total_budget - total_spent,
        "pct": (total_spent / total_budget) if total_budget > 0 else 0.0,
    }


def month_compare(db, month: dt.date):
    """Totaux du mois et du mois précédent (hors virements)."""
    cur_start, cur_end = utils.month_bounds(month)
    prev = utils.add_months(cur_start, -1)
    prev_start, prev_end = utils.month_bounds(prev)
    return totals(db, cur_start, cur_end), totals(db, prev_start, prev_end)


def top_expenses_month(db, month: dt.date, limit: int = 5):
    start, end = utils.month_bounds(month)
    rows = db.list_transactions(start=start, end=end, show_transfers=False)
    expenses = [r for r in rows if float(r["amount"]) < 0]
    expenses.sort(key=lambda r: float(r["amount"]))
    return expenses[:limit]
