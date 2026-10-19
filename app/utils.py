"""Utilitaires : dates, montants, pourcentages, mise à l'échelle de l'interface.

Toutes les données sont stockées en euros (float) et en dates ISO (AAAA-MM-JJ).
L'affichage est en français : « 1 234,56 € ».
"""
from __future__ import annotations

import datetime as dt
import math
import unicodedata

# --------------------------------------------------------------------------
# Échelle de l'interface (DPI)
# --------------------------------------------------------------------------
UI_SCALE = 1.0


def set_ui_scale(scale: float) -> None:
    global UI_SCALE
    try:
        scale = float(scale)
    except (TypeError, ValueError):
        scale = 1.0
    UI_SCALE = max(1.0, min(2.0, scale))


def S(px: float) -> int:
    """Dimension en pixels logiques -> pixels écran."""
    return int(round(float(px) * UI_SCALE))


# --------------------------------------------------------------------------
# Devise (modifiable dans les paramètres)
# --------------------------------------------------------------------------
CURRENCY = "€"


def set_currency(symbol: str) -> None:
    global CURRENCY
    CURRENCY = symbol or "€"


# --------------------------------------------------------------------------
# Dates
# --------------------------------------------------------------------------
MONTHS = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
]
MONTHS_SHORT = [
    "janv.", "févr.", "mars", "avr.", "mai", "juin",
    "juil.", "août", "sept.", "oct.", "nov.", "déc.",
]
DAYS_SHORT = ["lun", "mar", "mer", "jeu", "ven", "sam", "dim"]


def today() -> dt.date:
    return dt.date.today()


def parse_date(value) -> dt.date | None:
    if value is None or value == "":
        return None
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    s = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d.%m.%Y", "%d %B %Y"):
        try:
            return dt.datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def iso(d) -> str:
    d = parse_date(d)
    return d.strftime("%Y-%m-%d") if d else ""


def fmt_date(value, short: bool = False) -> str:
    d = parse_date(value)
    if not d:
        return "—"
    if short:
        return f"{d.day:02d}/{d.month:02d}/{d.year % 100:02d}"
    return f"{d.day:02d}/{d.month:02d}/{d.year}"


def fmt_date_long(value) -> str:
    d = parse_date(value)
    if not d:
        return "—"
    return f"{d.day} {MONTHS[d.month - 1]} {d.year}"


def fmt_month(d, short: bool = False) -> str:
    d = parse_date(d)
    if not d:
        return "—"
    name = MONTHS_SHORT[d.month - 1] if short else MONTHS[d.month - 1]
    return f"{name} {d.year}"


def month_bounds(value=None) -> tuple[dt.date, dt.date]:
    """Premier et dernier jour du mois contenant `value`."""
    d = parse_date(value) or today()
    first = d.replace(day=1)
    return first, add_months(first, 1) - dt.timedelta(days=1)


def month_key(value=None) -> str:
    d = parse_date(value) or today()
    return d.strftime("%Y-%m")


def parse_month_key(key: str) -> dt.date:
    try:
        y, m = str(key).split("-")[:2]
        return dt.date(int(y), int(m), 1)
    except (ValueError, AttributeError):
        return today().replace(day=1)


def add_months(d: dt.date, n: int) -> dt.date:
    m = d.month - 1 + n
    y = d.year + m // 12
    m = m % 12
    day = min(d.day, _days_in_month(y, m + 1))
    return dt.date(y, m + 1, day)


def _days_in_month(year: int, month: int) -> int:
    if month == 12:
        return 31
    return (dt.date(year, month + 1, 1) - dt.timedelta(days=1)).day


def days_between(a, b) -> int:
    da, db = parse_date(a), parse_date(b)
    if not da or not db:
        return 0
    return (db - da).days


def months_between(a, b) -> float:
    """Nombre de mois (fractionnaire) entre deux dates, b - a."""
    da, db = parse_date(a), parse_date(b)
    if not da or not db:
        return 0.0
    return (db.year - da.year) * 12 + (db.month - da.month) + (db.day - da.day) / 30.44


def month_end(value=None) -> dt.date:
    return month_bounds(value)[1]


# --------------------------------------------------------------------------
# Nombres et montants
# --------------------------------------------------------------------------
NNBSP = "\u202f"  # espace fine insécable


def _group(value: float, decimals: int) -> str:
    s = f"{abs(value):,.{decimals}f}"  # 1,234.56
    return s.replace(",", NNBSP).replace(".", ",")


def fmt_money(value, decimals: int = 2, sign: bool = False, symbol: str | None = None) -> str:
    """« 1 234,56 € » — None -> « — »."""
    if value is None:
        return "—"
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "—"
    sym = CURRENCY if symbol is None else symbol
    body = _group(v, decimals)
    if v < 0:
        prefix = "−"
    elif sign and v > 0:
        prefix = "+"
    else:
        prefix = ""
    if not sym:
        return f"{prefix}{body}"
    return f"{prefix}{body}{NNBSP}{sym}"


def fmt_money_short(value) -> str:
    """Format compact pour les axes : 12,4 k€ / 1,2 M€."""
    if value is None:
        return "—"
    v = float(value)
    a = abs(v)
    sign = "−" if v < 0 else ""
    if a >= 1_000_000:
        body = _group(a / 1_000_000, 1) + " M"
    elif a >= 1_000:
        body = _group(a / 1_000, 1) + " k"
    else:
        body = _group(a, 0)
    return f"{sign}{body}{NNBSP}{CURRENCY}" if CURRENCY else f"{sign}{body}"


def fmt_number(value, decimals: int = 2) -> str:
    if value is None:
        return "—"
    return _group(float(value), decimals)


def fmt_pct(value, decimals: int = 0) -> str:
    if value is None:
        return "—"
    return f"{_group(float(value), decimals)}{NNBSP}%"


def parse_amount(text) -> float | None:
    """Accepte « 1 234,56 », « 1234.56 », « -50 € », « (12,5) »."""
    if text is None:
        return None
    if isinstance(text, (int, float)):
        return float(text)
    t = str(text).strip()
    if not t:
        return None
    neg = False
    if t.startswith("(") and t.endswith(")"):
        neg, t = True, t[1:-1]
    for junk in ("€", "$", "£", "CHF", "MAD", "DZD", "TND", "USD", "EUR", NNBSP, "\u00a0", " ", "\t", "'"):
        t = t.replace(junk, "")
    t = t.replace(",", ".")
    if t.startswith("−"):
        neg, t = True, t[1:]
    if t.startswith("-"):
        neg, t = True, t[1:]
    try:
        v = float(t)
    except ValueError:
        return None
    return -v if neg else v


def clamp(value, lo, hi):
    return max(lo, min(hi, value))


def nice_bounds(lo: float, hi: float, ticks: int = 4):
    """Bornes « rondes » et pas pour un axe de graphique."""
    if lo is None or hi is None or not math.isfinite(lo) or not math.isfinite(hi):
        return 0.0, 1.0, 0.25
    if hi <= lo:
        hi = lo + 1.0
    span = hi - lo
    raw = span / max(1, ticks)
    mag = 10 ** math.floor(math.log10(raw)) if raw > 0 else 1
    step = mag * 10
    for m in (1, 2, 2.5, 5, 10):
        if m * mag >= raw:
            step = m * mag
            break
    lo2 = math.floor(lo / step) * step
    hi2 = math.ceil(hi / step) * step
    if hi2 <= lo2:
        hi2 = lo2 + step
    return lo2, hi2, step


def initials(name: str) -> str:
    parts = [p for p in str(name or "").replace("-", " ").split() if p]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[1][0]).upper()


def normalize(text: str) -> str:
    """Minuscule sans accents, pour la recherche."""
    s = unicodedata.normalize("NFKD", str(text or "").lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def plural(n: float, singular: str, plural_form: str | None = None) -> str:
    if abs(float(n)) >= 2:
        return plural_form or (singular + "s")
    return singular


def elide(text: str, max_chars: int) -> str:
    text = str(text or "")
    if len(text) <= max_chars:
        return text
    return text[: max(1, max_chars - 1)].rstrip() + "…"
