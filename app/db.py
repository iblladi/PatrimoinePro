"""Couche de persistance : SQLite, schéma, requêtes et jeu de démonstration."""
from __future__ import annotations

import datetime as dt
import os
import random
import shutil
import sqlite3
import uuid

from . import utils

APP_DIR_NAME = "PatrimoinePro"
DB_FILENAME = "patrimoine.db"

# Familles de comptes : clé -> (libellé, couleur)
ACCOUNT_FAMILIES = {
    "courant": ("Comptes courants", "#3B82F6"),
    "epargne": ("Épargne", "#10B981"),
    "placement": ("Placements", "#8B5CF6"),
    "retraite": ("Retraite", "#0D9488"),
    "especes": ("Espèces & autres", "#F59E0B"),
}

# Types de comptes : clé -> (libellé, couleur, famille)
ACCOUNT_TYPES = {
    # --- Comptes courants -------------------------------------------------
    "courant": ("Compte courant", "#3B82F6", "courant"),
    "joint": ("Compte joint", "#0EA5E9", "courant"),
    "individuel": ("Compte individuel", "#38BDF8", "courant"),
    "ccp": ("Compte chèque postal (CCP)", "#2563EB", "courant"),
    "neobanque": ("Compte néobanque", "#8B5CF6", "courant"),
    "depot": ("Compte de dépôt", "#60A5FA", "courant"),
    "pro": ("Compte professionnel", "#6366F1", "courant"),
    "association": ("Compte d'association", "#818CF8", "courant"),
    "multidevise": ("Compte multi-devises", "#14B8A6", "courant"),
    "etranger": ("Compte à l'étranger", "#0891B2", "courant"),
    "prepaye": ("Compte / carte prépayée", "#7DD3FC", "courant"),
    # --- Épargne ----------------------------------------------------------
    "livret_a": ("Livret A", "#10B981", "epargne"),
    "ldds": ("LDDS", "#34D399", "epargne"),
    "lep": ("Livret d'épargne populaire (LEP)", "#059669", "epargne"),
    "livret_jeune": ("Livret jeune", "#6EE7B7", "epargne"),
    "livret_bancaire": ("Livret bancaire", "#22C55E", "epargne"),
    "cel": ("Compte épargne logement (CEL)", "#16A34A", "epargne"),
    "pel": ("Plan épargne logement (PEL)", "#15803D", "epargne"),
    "compte_terme": ("Compte à terme", "#84CC16", "epargne"),
    "epargne": ("Épargne (générique)", "#4ADE80", "epargne"),
    "epargne_salariale": ("Épargne salariale (PEE)", "#65A30D", "epargne"),
    # --- Placements -------------------------------------------------------
    "pea": ("PEA", "#8B5CF6", "placement"),
    "pea_pme": ("PEA-PME", "#A78BFA", "placement"),
    "cto": ("Compte-titres ordinaire (CTO)", "#7C3AED", "placement"),
    "assurance_vie": ("Assurance-vie", "#C084FC", "placement"),
    "investissement": ("Compte d'investissement", "#9333EA", "placement"),
    "scpi": ("SCPI / immobilier papier", "#D97706", "placement"),
    "crowdfunding": ("Crowdfunding", "#EA580C", "placement"),
    "crypto": ("Crypto-actifs", "#F59E0B", "placement"),
    "or": ("Or / métaux précieux", "#CA8A04", "placement"),
    # --- Retraite ---------------------------------------------------------
    "per": ("PER (plan d'épargne retraite)", "#0D9488", "retraite"),
    "perp": ("PERP", "#14B8A6", "retraite"),
    "art83": ("PER entreprise (art. 83)", "#2DD4BF", "retraite"),
    "madelin": ("PER Madelin", "#5EEAD4", "retraite"),
    # --- Espèces & autres -------------------------------------------------
    "especes": ("Espèces", "#F59E0B", "especes"),
    "caisse": ("Caisse / fonds de roulement", "#FBBF24", "especes"),
    "autre": ("Autre", "#64748B", "especes"),
}

ACCOUNT_TYPE_FALLBACK = ("Autre", "#64748B", "especes")


def account_type(key: str):
    """(libellé, couleur, famille) pour une clé de type, avec repli sûr."""
    return ACCOUNT_TYPES.get(key or "", ACCOUNT_TYPE_FALLBACK)


def account_label(key: str) -> str:
    return account_type(key)[0]


def account_color(key: str) -> str:
    return account_type(key)[1]


def account_family(key: str) -> str:
    return account_type(key)[2]


def family_label(key: str) -> str:
    return ACCOUNT_FAMILIES.get(key, ("Autre", "#64748B"))[0]


def types_of_family(family: str):
    """Liste des clés de types appartenant à une famille (ordre du catalogue)."""
    return [k for k, v in ACCOUNT_TYPES.items() if v[2] == family]


def family_of_label(label: str) -> str:
    """Retrouve la famille à partir du libellé d'un type."""
    for key, value in ACCOUNT_TYPES.items():
        if value[0] == label:
            return value[2]
    return "courant"


def family_key_of_label(label: str) -> str:
    """Retrouve la clé de famille à partir de son libellé (« Épargne » -> « epargne »)."""
    for key, value in ACCOUNT_FAMILIES.items():
        if value[0] == label:
            return key
    return "courant"


def type_of_label(label: str) -> str:
    for key, value in ACCOUNT_TYPES.items():
        if value[0] == label:
            return key
    return "autre"

PRIORITIES = {1: "Haute", 2: "Moyenne", 3: "Basse"}

SEED_CATEGORIES = [
    ("Salaire", "revenu", "#10B981"),
    ("Prime", "revenu", "#34D399"),
    ("Revenus locatifs", "revenu", "#14B8A6"),
    ("Remboursement", "revenu", "#6EE7B7"),
    ("Autres revenus", "revenu", "#A7F3D0"),
    ("Logement", "depense", "#EF4444"),
    ("Alimentation", "depense", "#F97316"),
    ("Transport", "depense", "#F59E0B"),
    ("Santé", "depense", "#EC4899"),
    ("Loisirs", "depense", "#8B5CF6"),
    ("Abonnements", "depense", "#6366F1"),
    ("Shopping", "depense", "#06B6D4"),
    ("Restaurants", "depense", "#F43F5E"),
    ("Éducation", "depense", "#0EA5E9"),
    ("Voyages", "depense", "#14B8A6"),
    ("Divers", "depense", "#64748B"),
]

SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    type            TEXT NOT NULL DEFAULT 'courant',
    institution     TEXT DEFAULT '',
    initial_balance REAL NOT NULL DEFAULT 0,
    currency        TEXT NOT NULL DEFAULT 'EUR',
    color           TEXT NOT NULL DEFAULT '#3B82F6',
    archived        INTEGER NOT NULL DEFAULT 0,
    notes           TEXT DEFAULT '',
    created_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS categories (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    name  TEXT NOT NULL,
    kind  TEXT NOT NULL DEFAULT 'depense',
    color TEXT NOT NULL DEFAULT '#64748B',
    UNIQUE(name, kind)
);

CREATE TABLE IF NOT EXISTS projects (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    name                TEXT NOT NULL,
    target_amount       REAL NOT NULL,
    target_date         TEXT,
    account_id          INTEGER REFERENCES accounts(id) ON DELETE SET NULL,
    monthly_contribution REAL NOT NULL DEFAULT 0,
    priority            INTEGER NOT NULL DEFAULT 2,
    color               TEXT NOT NULL DEFAULT '#2563EB',
    icon                TEXT NOT NULL DEFAULT '◎',
    status              TEXT NOT NULL DEFAULT 'actif',
    notes               TEXT DEFAULT '',
    start_date          TEXT,
    created_at          TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS transactions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    date        TEXT NOT NULL,
    account_id  INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    amount      REAL NOT NULL,
    category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    payee       TEXT DEFAULT '',
    notes       TEXT DEFAULT '',
    transfer_id TEXT,
    project_id  INTEGER REFERENCES projects(id) ON DELETE SET NULL,
    created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tx_date ON transactions(date);
CREATE INDEX IF NOT EXISTS idx_tx_account ON transactions(account_id);
CREATE INDEX IF NOT EXISTS idx_tx_transfer ON transactions(transfer_id);

CREATE TABLE IF NOT EXISTS project_contributions (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id     INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    date           TEXT NOT NULL,
    amount         REAL NOT NULL,
    notes          TEXT DEFAULT '',
    transfer_id    TEXT,
    created_at     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_contrib_project ON project_contributions(project_id);

CREATE TABLE IF NOT EXISTS budgets (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    month       TEXT NOT NULL,
    amount      REAL NOT NULL,
    UNIQUE(category_id, month)
);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);
"""

DEFAULT_SETTINGS = {
    "currency": "€",
    "app_version": "1.0",
    "first_run_done": "0",
    "user_name": "",
}


def default_db_path() -> str:
    """%APPDATA%\\PatrimoinePro\\patrimoine.db (surchargeable par PATRIMOINE_DB)."""
    override = os.environ.get("PATRIMOINE_DB")
    if override:
        return os.path.abspath(override)
    base = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), ".local", "share")
    return os.path.join(base, APP_DIR_NAME, DB_FILENAME)


def _now() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class Database:
    def __init__(self, path: str | None = None):
        self.path = os.path.abspath(path or default_db_path())
        folder = os.path.dirname(self.path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(SCHEMA)
        self._init_settings()
        self._seed_categories()

    # ------------------------------------------------------------------ bas
    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass

    def _init_settings(self):
        with self.conn:
            for k, v in DEFAULT_SETTINGS.items():
                self.conn.execute(
                    "INSERT OR IGNORE INTO settings(key, value) VALUES (?, ?)", (k, v)
                )

    def _seed_categories(self):
        with self.conn:
            for name, kind, color in SEED_CATEGORIES:
                self.conn.execute(
                    "INSERT OR IGNORE INTO categories(name, kind, color) VALUES (?,?,?)",
                    (name, kind, color),
                )

    # ------------------------------------------------------------- settings
    def get_setting(self, key: str, default: str = "") -> str:
        row = self.conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default

    def set_setting(self, key: str, value: str):
        with self.conn:
            self.conn.execute(
                "INSERT INTO settings(key, value) VALUES (?,?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, str(value)),
            )

    def is_empty(self) -> bool:
        return self.conn.execute("SELECT COUNT(*) c FROM accounts").fetchone()["c"] == 0

    # -------------------------------------------------------------- comptes
    def list_accounts(self, include_archived: bool = False):
        sql = """
            SELECT a.*,
                   a.initial_balance + COALESCE(SUM(t.amount), 0) AS balance,
                   COUNT(t.id) AS tx_count
            FROM accounts a
            LEFT JOIN transactions t ON t.account_id = a.id
            {where}
            GROUP BY a.id
            ORDER BY a.archived ASC, a.name COLLATE NOCASE ASC
        """
        where = "" if include_archived else "WHERE a.archived = 0"
        return self.conn.execute(sql.format(where=where)).fetchall()

    def get_account(self, account_id):
        return self.conn.execute("SELECT * FROM accounts WHERE id=?", (account_id,)).fetchone()

    def add_account(self, name, type="courant", institution="", initial_balance=0.0,
                    color=None, notes="") -> int:
        color = color or account_color(type)
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO accounts(name, type, institution, initial_balance, color, notes, created_at) "
                "VALUES (?,?,?,?,?,?,?)",
                (name.strip(), type, institution.strip(), float(initial_balance), color, notes, _now()),
            )
        return int(cur.lastrowid)

    def update_account(self, account_id, **fields):
        allowed = {"name", "type", "institution", "initial_balance", "color", "notes", "archived"}
        data = {k: v for k, v in fields.items() if k in allowed}
        if not data:
            return
        cols = ", ".join(f"{k}=?" for k in data)
        with self.conn:
            self.conn.execute(f"UPDATE accounts SET {cols} WHERE id=?", (*data.values(), account_id))

    def delete_account(self, account_id):
        with self.conn:
            self.conn.execute("DELETE FROM accounts WHERE id=?", (account_id,))

    def account_balance(self, account_id) -> float:
        row = self.conn.execute(
            "SELECT a.initial_balance + COALESCE(SUM(t.amount),0) AS b "
            "FROM accounts a LEFT JOIN transactions t ON t.account_id=a.id "
            "WHERE a.id=? GROUP BY a.id",
            (account_id,),
        ).fetchone()
        return float(row["b"]) if row else 0.0

    # ----------------------------------------------------------- catégories
    def list_categories(self, kind: str | None = None):
        if kind:
            return self.conn.execute(
                "SELECT * FROM categories WHERE kind=? ORDER BY name COLLATE NOCASE", (kind,)
            ).fetchall()
        return self.conn.execute("SELECT * FROM categories ORDER BY kind DESC, name COLLATE NOCASE").fetchall()

    def get_category(self, category_id):
        return self.conn.execute("SELECT * FROM categories WHERE id=?", (category_id,)).fetchone()

    def add_category(self, name: str, kind: str, color: str) -> int:
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO categories(name, kind, color) VALUES (?,?,?)", (name.strip(), kind, color)
            )
        return int(cur.lastrowid)

    def update_category(self, category_id, name: str, color: str):
        with self.conn:
            self.conn.execute("UPDATE categories SET name=?, color=? WHERE id=?", (name, color, category_id))

    def delete_category(self, category_id):
        with self.conn:
            self.conn.execute("UPDATE transactions SET category_id=NULL WHERE category_id=?", (category_id,))
            self.conn.execute("DELETE FROM budgets WHERE category_id=?", (category_id,))
            self.conn.execute("DELETE FROM categories WHERE id=?", (category_id,))

    def category_usage(self, category_id) -> int:
        return self.conn.execute(
            "SELECT COUNT(*) c FROM transactions WHERE category_id=?", (category_id,)
        ).fetchone()["c"]

    # ------------------------------------------------------------ opérations
    _TX_SELECT = """
        SELECT t.*,
               a.name  AS account_name,
               a.color AS account_color,
               a.archived AS account_archived,
               c.name  AS category_name,
               c.color AS category_color,
               c.kind  AS category_kind,
               p.name  AS project_name,
               a2.name AS counterpart_account,
               a2.id   AS counterpart_id
        FROM transactions t
        JOIN accounts a ON a.id = t.account_id
        LEFT JOIN categories c ON c.id = t.category_id
        LEFT JOIN projects p ON p.id = t.project_id
        LEFT JOIN transactions t2 ON t2.transfer_id = t.transfer_id AND t2.id <> t.id
        LEFT JOIN accounts a2 ON a2.id = t2.account_id
    """

    def list_transactions(self, start=None, end=None, account_id=None, category_id=None,
                          search=None, project_id=None, show_transfers=True, limit=None):
        where, params = ["1=1"], []
        if start:
            where.append("t.date >= ?")
            params.append(utils.iso(start))
        if end:
            where.append("t.date <= ?")
            params.append(utils.iso(end))
        if account_id:
            where.append("t.account_id = ?")
            params.append(int(account_id))
        if category_id:
            where.append("t.category_id = ?")
            params.append(int(category_id))
        if project_id:
            where.append("t.project_id = ?")
            params.append(int(project_id))
        if not show_transfers:
            where.append("t.transfer_id IS NULL")
        sql = self._TX_SELECT + " WHERE " + " AND ".join(where) + " ORDER BY t.date DESC, t.id DESC"
        if limit:
            sql += f" LIMIT {int(limit)}"
        rows = self.conn.execute(sql, params).fetchall()
        if search:
            needle = utils.normalize(search)
            rows = [r for r in rows if needle in utils.normalize(self._tx_label(r))]
        return rows

    @staticmethod
    def _tx_label(row) -> str:
        if row["transfer_id"]:
            other = row["counterpart_account"] or "virement"
            return ("Virement vers " + other) if float(row["amount"]) < 0 \
                else ("Virement depuis " + other)
        return row["payee"] or row["category_name"] or "Opération"

    def get_transaction(self, tx_id):
        return self.conn.execute(self._TX_SELECT + " WHERE t.id = ?", (tx_id,)).fetchone()

    def add_transaction(self, date, account_id, amount, category_id=None, payee="",
                        notes="", project_id=None) -> int:
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO transactions(date, account_id, amount, category_id, payee, notes, "
                "project_id, created_at) VALUES (?,?,?,?,?,?,?,?)",
                (utils.iso(date), int(account_id), float(amount),
                 int(category_id) if category_id else None, payee or "", notes or "",
                 int(project_id) if project_id else None, _now()),
            )
        return int(cur.lastrowid)

    def update_transaction(self, tx_id, date, account_id, amount, category_id=None,
                           payee="", notes="", project_id=None):
        row = self.conn.execute("SELECT * FROM transactions WHERE id=?", (tx_id,)).fetchone()
        if not row:
            return
        with self.conn:
            self.conn.execute(
                "UPDATE transactions SET date=?, account_id=?, amount=?, category_id=?, payee=?, "
                "notes=?, project_id=? WHERE id=?",
                (utils.iso(date), int(account_id), float(amount),
                 int(category_id) if category_id else None, payee or "", notes or "",
                 int(project_id) if project_id else None, tx_id),
            )
            if row["transfer_id"]:
                sign = 1 if row["amount"] >= 0 else -1
                self.conn.execute(
                    "UPDATE transactions SET date=? WHERE transfer_id=? AND id<>?",
                    (utils.iso(date), row["transfer_id"], tx_id),
                )
                self.conn.execute(
                    "UPDATE transactions SET amount=? WHERE transfer_id=? AND id<>?",
                    (sign * abs(float(amount)), row["transfer_id"], tx_id),
                )

    def delete_transaction(self, tx_id):
        row = self.conn.execute("SELECT * FROM transactions WHERE id=?", (tx_id,)).fetchone()
        if not row:
            return
        with self.conn:
            if row["transfer_id"]:
                self.conn.execute("DELETE FROM transactions WHERE transfer_id=?", (row["transfer_id"],))
            else:
                self.conn.execute("DELETE FROM transactions WHERE id=?", (tx_id,))

    def add_transfer(self, date, from_account_id, to_account_id, amount, notes="",
                     project_id=None) -> str:
        tid = uuid.uuid4().hex[:12]
        amount = abs(float(amount))
        with self.conn:
            self.conn.execute(
                "INSERT INTO transactions(date, account_id, amount, payee, notes, transfer_id, "
                "project_id, created_at) VALUES (?,?,?,?,?,?,?,?)",
                (utils.iso(date), int(from_account_id), -amount, "", notes or "", tid,
                 int(project_id) if project_id else None, _now()),
            )
            self.conn.execute(
                "INSERT INTO transactions(date, account_id, amount, payee, notes, transfer_id, "
                "project_id, created_at) VALUES (?,?,?,?,?,?,?,?)",
                (utils.iso(date), int(to_account_id), amount, "", notes or "", tid,
                 int(project_id) if project_id else None, _now()),
            )
        return tid

    def delete_transfer(self, transfer_id: str):
        with self.conn:
            self.conn.execute("DELETE FROM transactions WHERE transfer_id=?", (transfer_id,))

    def recent_transactions(self, limit: int = 8):
        return self.list_transactions(limit=limit)

    def transaction_count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) c FROM transactions").fetchone()["c"]

    # ------------------------------------------------------------- projets
    _PROJECT_SELECT = """
        SELECT p.*,
               a.name AS account_name,
               a.color AS account_color,
               COALESCE((SELECT SUM(c.amount) FROM project_contributions c
                         WHERE c.project_id = p.id), 0) AS saved,
               (SELECT COUNT(*) FROM project_contributions c WHERE c.project_id = p.id) AS contrib_count
        FROM projects p
        LEFT JOIN accounts a ON a.id = p.account_id
    """

    def list_projects(self, include_archived: bool = False):
        where = "" if include_archived else "WHERE p.status <> 'archive'"
        return self.conn.execute(
            self._PROJECT_SELECT + f" {where} ORDER BY p.priority ASC, p.target_date ASC, p.id ASC"
        ).fetchall()

    def get_project(self, project_id):
        return self.conn.execute(self._PROJECT_SELECT + " WHERE p.id=?", (project_id,)).fetchone()

    def add_project(self, name, target_amount, target_date=None, account_id=None,
                    monthly_contribution=0.0, priority=2, color="#2563EB", notes="",
                    initial_amount=0.0, start_date=None) -> int:
        start_date = utils.iso(start_date or utils.today())
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO projects(name, target_amount, target_date, account_id, "
                "monthly_contribution, priority, color, status, notes, start_date, created_at) "
                "VALUES (?,?,?,?,?,?,?, 'actif', ?,?,?)",
                (name.strip(), float(target_amount), utils.iso(target_date) or None,
                 int(account_id) if account_id else None, float(monthly_contribution),
                 int(priority), color, notes or "", start_date, _now()),
            )
        pid = int(cur.lastrowid)
        if initial_amount:
            self.add_contribution(pid, start_date, initial_amount, "Montant de départ")
        return pid

    def update_project(self, project_id, **fields):
        allowed = {"name", "target_amount", "target_date", "account_id", "monthly_contribution",
                   "priority", "color", "status", "notes", "start_date"}
        data = {k: v for k, v in fields.items() if k in allowed}
        if not data:
            return
        cols = ", ".join(f"{k}=?" for k in data)
        with self.conn:
            self.conn.execute(f"UPDATE projects SET {cols} WHERE id=?", (*data.values(), project_id))

    def delete_project(self, project_id):
        with self.conn:
            self.conn.execute("DELETE FROM projects WHERE id=?", (project_id,))

    def project_contributions(self, project_id):
        return self.conn.execute(
            "SELECT * FROM project_contributions WHERE project_id=? ORDER BY date ASC, id ASC",
            (project_id,),
        ).fetchall()

    def all_contributions(self):
        return self.conn.execute(
            "SELECT * FROM project_contributions ORDER BY date ASC, id ASC"
        ).fetchall()

    def add_contribution(self, project_id, date, amount, notes="", source_account_id=None,
                         transfer_id=None) -> int:
        """Enregistre un versement. Si `source_account_id` est fourni et que le projet est
        rattaché à un compte, un virement réel est créé entre les deux comptes."""
        project = self.get_project(project_id)
        amount = float(amount)
        if transfer_id is None and source_account_id and project and project["account_id"]:
            if int(source_account_id) != int(project["account_id"]):
                transfer_id = self.add_transfer(
                    date, source_account_id, project["account_id"], amount, f"Épargne — {project['name']}",
                    project_id=project_id,
                )
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO project_contributions(project_id, date, amount, notes, transfer_id, created_at) "
                "VALUES (?,?,?,?,?,?)",
                (int(project_id), utils.iso(date), amount, notes or "", transfer_id, _now()),
            )
        self._refresh_project_status(project_id)
        return int(cur.lastrowid)

    def delete_contribution(self, contribution_id, delete_transfer: bool = True):
        row = self.conn.execute(
            "SELECT * FROM project_contributions WHERE id=?", (contribution_id,)
        ).fetchone()
        if not row:
            return
        with self.conn:
            self.conn.execute("DELETE FROM project_contributions WHERE id=?", (contribution_id,))
        if delete_transfer and row["transfer_id"]:
            self.delete_transfer(row["transfer_id"])
        self._refresh_project_status(row["project_id"])

    def _refresh_project_status(self, project_id):
        project = self.get_project(project_id)
        if not project:
            return
        if project["status"] == "archive":
            return
        saved = float(project["saved"] or 0)
        status = "atteint" if saved >= float(project["target_amount"]) else "actif"
        if status != project["status"]:
            with self.conn:
                self.conn.execute("UPDATE projects SET status=? WHERE id=?", (status, project_id))

    # ------------------------------------------------------------- budgets
    def set_budget(self, category_id, month: str, amount: float):
        with self.conn:
            self.conn.execute(
                "INSERT INTO budgets(category_id, month, amount) VALUES (?,?,?) "
                "ON CONFLICT(category_id, month) DO UPDATE SET amount=excluded.amount",
                (int(category_id), month, float(amount)),
            )

    def delete_budget(self, category_id, month: str):
        with self.conn:
            self.conn.execute(
                "DELETE FROM budgets WHERE category_id=? AND month=?", (int(category_id), month)
            )

    def budgets_for(self, month: str):
        rows = self.conn.execute(
            "SELECT b.*, c.name AS category_name, c.color AS category_color, "
            "  COALESCE((SELECT -SUM(t.amount) FROM transactions t "
            "            WHERE t.category_id = b.category_id AND substr(t.date,1,7)=b.month "
            "            AND t.amount < 0), 0) AS spent "
            "FROM budgets b JOIN categories c ON c.id = b.category_id "
            "WHERE b.month=? ORDER BY c.name COLLATE NOCASE",
            (month,),
        ).fetchall()
        return rows

    def budget_months(self):
        return [r["month"] for r in self.conn.execute(
            "SELECT DISTINCT month FROM budgets ORDER BY month DESC"
        ).fetchall()]

    # ------------------------------------------------------------- maintenance
    def backup_to(self, destination: str) -> str:
        destination = os.path.abspath(destination)
        os.makedirs(os.path.dirname(destination) or ".", exist_ok=True)
        target = sqlite3.connect(destination)
        with target:
            self.conn.backup(target)
        target.close()
        return destination

    def wipe(self):
        with self.conn:
            self.conn.executescript(
                "DELETE FROM project_contributions; DELETE FROM transactions; "
                "DELETE FROM budgets; DELETE FROM projects; DELETE FROM accounts;"
            )
        with self.conn:
            self.conn.execute("UPDATE categories SET id=id")

    def stats(self) -> dict:
        return {
            "accounts": self.conn.execute("SELECT COUNT(*) c FROM accounts").fetchone()["c"],
            "transactions": self.transaction_count(),
            "projects": self.conn.execute("SELECT COUNT(*) c FROM projects").fetchone()["c"],
            "categories": self.conn.execute("SELECT COUNT(*) c FROM categories").fetchone()["c"],
        }

    # ------------------------------------------------------------- démo
    def seed_demo(self, months: int = 15):
        """Données de démonstration cohérentes (déterministes)."""
        rng = random.Random(20261020)
        self.wipe()
        cur = utils.today().replace(day=1)
        start = utils.add_months(cur, -(months - 1))

        cat = {r["name"]: r["id"] for r in self.conn.execute("SELECT id, name FROM categories")}

        a_current = self.add_account("Compte courant", "courant", "Banque Populaire",
                                     1240.0, "#3B82F6", "Compte du quotidien")
        a_livret = self.add_account("Livret A", "livret_a", "Banque Populaire",
                                    8500.0, "#10B981", "Épargne de précaution")
        a_pea = self.add_account("PEA", "pea", "Bourse Direct",
                                 14500.0, "#8B5CF6", "Fonds européens")
        a_cash = self.add_account("Espèces", "especes", "", 160.0, "#F59E0B", "")

        def day(y, m, d):
            try:
                value = dt.date(y, m, d)
            except ValueError:
                value = dt.date(y, m, 28)
            # jamais d'opération dans le futur (mois en cours)
            return min(value, utils.today())

        for i in range(months):
            m0 = utils.add_months(start, i)
            y, m = m0.year, m0.month

            self.add_transaction(day(y, m, 2), a_current, 2650.0, cat["Salaire"],
                                 "Virement salaire — Atelier Duval", "Salaire mensuel")
            self.add_transaction(day(y, m, 3), a_current, -950.0, cat["Logement"],
                                 "Loyer", "")
            self.add_transaction(day(y, m, 4), a_current, -48.9, cat["Abonnements"],
                                 "Internet + mobile", "")
            self.add_transaction(day(y, m, 6), a_current, -75.0, cat["Transport"],
                                 "Abonnement transport", "")

            weeks = [5, 12, 19, 26]
            for w_i, w in enumerate(weeks):
                amount = -round(rng.uniform(72, 108), 2)
                self.add_transaction(day(y, m, w), a_current, amount, cat["Alimentation"],
                                     rng.choice(["Supermarché", "Marché", "Épicerie", "Drive"]), "")
            for _ in range(rng.choice([1, 2, 2, 3])):
                self.add_transaction(day(y, m, rng.randint(5, 27)), a_current,
                                     -round(rng.uniform(28, 78), 2), cat["Restaurants"],
                                     rng.choice(["Restaurant", "Brasserie", "Pizzeria", "Café"]), "")
            if rng.random() < 0.8:
                self.add_transaction(day(y, m, rng.randint(4, 25)), a_current,
                                     -round(rng.uniform(35, 130), 2), cat["Loisirs"],
                                     rng.choice(["Cinéma", "Concert", "Livre", "Salle de sport"]), "")
            if rng.random() < 0.7:
                self.add_transaction(day(y, m, rng.randint(4, 25)), a_current,
                                     -round(rng.uniform(45, 160), 2), cat["Shopping"],
                                     rng.choice(["Vêtements", "Maison", "High-tech"]), "")
            if rng.random() < 0.35:
                self.add_transaction(day(y, m, rng.randint(4, 25)), a_current,
                                     -round(rng.uniform(22, 65), 2), cat["Santé"],
                                     "Pharmacie", "")

            # Investissement trimestriel
            if m0.month in (1, 4, 7, 10):
                self.add_transfer(day(y, m, 8), a_current, a_pea, 600.0, "Investissement trimestriel")

            if i == months - 3:
                self.add_transaction(day(y, m, 15), a_current, 1200.0, cat["Prime"],
                                     "Prime annuelle", "")

        # ---------------- Projets d'épargne
        p1 = self.add_project(
            "Apport immobilier", 40000, utils.add_months(utils.today(), 26),
            a_livret, 450, 1, "#2563EB",
            "Objectif : 20 % d'apport pour un appartement en 2028.", 6000,
            utils.add_months(start, -8),
        )
        p2 = self.add_project(
            "Voyage au Japon", 6000, utils.add_months(utils.today(), 12),
            a_livret, 180, 3, "#F59E0B",
            "Deux semaines au printemps.", 820,
            utils.add_months(start, -10),
        )
        p3 = self.add_project(
            "Remplacement voiture", 18000, utils.add_months(utils.today(), 34),
            a_pea, 300, 2, "#8B5CF6",
            "Véhicule d'occasion hybride.", 2500,
            utils.add_months(start, -12),
        )
        p4 = self.add_project(
            "Fonds d'urgence", 9000, utils.add_months(utils.today(), 6),
            a_livret, 150, 1, "#10B981",
            "6 mois de dépenses de précaution.", 5000,
            utils.add_months(start, -14),
        )

        # Versements mensuels pour chaque projet
        plans = [(p1, 450, a_current), (p2, 180, None), (p3, 300, None), (p4, 150, None)]
        for pid, amount, source in plans:
            for i in range(months - 1):
                d = utils.add_months(start, i)
                d = dt.date(d.year, d.month, min(12, 28))
                jitter = rng.choice([0, 0, 0, 25, 50]) if amount >= 300 else 0
                try:
                    self.add_contribution(pid, d, amount + jitter, "", source)
                except Exception:
                    pass

        # ---------------- Budgets du mois courant
        budget_plan = {
            "Logement": 1000, "Alimentation": 480, "Transport": 120, "Restaurants": 200,
            "Loisirs": 180, "Abonnements": 60, "Shopping": 160, "Santé": 90,
        }
        mk = utils.month_key(utils.today())
        for name, amount in budget_plan.items():
            self.set_budget(cat[name], mk, amount)

        self.set_setting("first_run_done", "1")
        return self.stats()
