"""Component pricing. Prices live in the database and are edited by the platform super admin.

DEFAULTS are the launch prices: they seed the tables and act as a read-only fallback if a row
is missing, so a quote or Apex AI answer never has a hole in it.
"""
from decimal import Decimal, InvalidOperation

BILLING_UNITS = {
    "per_school_term": "per school per term",
    "per_admission": "per admission",
    "per_transfer": "per transfer",
    "per_student_year": "per student per academic year",
    "per_plan": "per plan",
}
CURRENCY_LABEL = {"KES": "KSh", "USD": "USD"}
MAX_AMOUNT = Decimal("10000000")
MAX_TIERS = 6

# up_to_students is inclusive: a school with exactly 1,000 students gets the first tier.
_ANALYTICS_TIERS = [{"up_to_students": 1000, "amount": Decimal("10000")},
                    {"up_to_students": None, "amount": Decimal("15000")}]

DEFAULTS = [
    {"key": "academic_analytics", "name": "Academic Analytics", "billing_unit": "per_school_term",
     "currency": "KES", "tiers": _ANALYTICS_TIERS},
    {"key": "financial_analytics", "name": "Financial Analytics", "billing_unit": "per_school_term",
     "currency": "KES", "tiers": _ANALYTICS_TIERS},
    {"key": "zeroq_admissions", "name": "ZeroQ Admissions", "billing_unit": "per_admission",
     "currency": "KES", "amount": Decimal("450")},
    {"key": "zeroq_transfers", "name": "ZeroQ Transfers", "billing_unit": "per_transfer",
     "currency": "KES", "amount": Decimal("400")},
    {"key": "careergps", "name": "CareerGPS", "billing_unit": "per_student_year",
     "currency": "KES", "amount": Decimal("1000")},
    {"key": "apex_ai_pro", "name": "Apex AI Pro", "billing_unit": "per_plan",
     "currency": "USD", "amount": Decimal("5")},
]


def _from_default(d):
    return {"id": None, "key": d["key"], "name": d["name"], "description": None,
            "billing_unit": d["billing_unit"], "currency": d["currency"], "is_active": True,
            "amount": d.get("amount"), "tiers": [dict(t) for t in d.get("tiers", [])],
            "updated_at": None, "updated_by": None}


def _from_row(c):
    return {"id": c.id, "key": c.key, "name": c.name, "description": c.description,
            "billing_unit": c.billing_unit, "currency": c.currency, "is_active": c.is_active,
            "amount": c.amount, "tiers": [{"up_to_students": t.up_to_students, "amount": t.amount} for t in c.tiers],
            "updated_at": c.updated_at, "updated_by": c.updated_by}


def default_for(key):
    return next((d for d in DEFAULTS if d["key"] == key), None)


def get_components():
    """Every component, database rows first, defaults filling any gap. Never writes."""
    from ..models import PriceComponent
    rows = {c.key: c for c in PriceComponent.query.all()}
    return [_from_row(rows[d["key"]]) if d["key"] in rows else _from_default(d) for d in DEFAULTS]


def get_component(key):
    return next((c for c in get_components() if c["key"] == key), None)


def price_for(component, students):
    """Unit price for a school with `students` students; None if the component is not on sale."""
    if not component["is_active"]:
        return None
    if not component["tiers"]:
        return component["amount"]
    for tier in component["tiers"]:
        if tier["up_to_students"] is None or students <= tier["up_to_students"]:
            return tier["amount"]
    return None


def money_text(amount, currency="KES"):
    amount = Decimal(amount)
    text = f"{amount:,.0f}" if amount == amount.to_integral_value() else f"{amount:,.2f}"
    return f"{CURRENCY_LABEL.get(currency, currency)} {text}"


def describe(component):
    """Plain-English price line(s), used in Apex AI's prompt so it quotes the live price."""
    if not component["is_active"]:
        return (f"{component['name']} is not currently on sale. Ask the school to contact the ElimuPro team "
                "for availability and pricing.")
    unit = BILLING_UNITS[component["billing_unit"]]
    cur = component["currency"]
    if not component["tiers"]:
        return f"{component['name']}: {money_text(component['amount'], cur)} {unit}."
    lines, floor = [], 0
    for t in component["tiers"]:
        if t["up_to_students"] is None:
            who = f"more than {floor:,} students"
        else:
            who = f"up to {t['up_to_students']:,} students (including exactly {t['up_to_students']:,})"
            floor = t["up_to_students"]
        lines.append(f"- Schools with {who}: {money_text(t['amount'], cur)} {unit}.")
    return f"{component['name']} is priced by school size.\n" + "\n".join(lines)


def _amount(value):
    if isinstance(value, bool) or value is None:
        return None, "Enter an amount"
    try:
        d = Decimal(str(value).strip())
    except InvalidOperation:
        return None, "Enter a valid number"
    if not d.is_finite():
        return None, "Enter a valid number"
    if d < 0 or d > MAX_AMOUNT:
        return None, f"Amount must be between 0 and {MAX_AMOUNT:,.0f}"
    if d != d.quantize(Decimal("0.01")):
        return None, "Use at most 2 decimal places"
    return d.quantize(Decimal("0.01")), None


def validate_update(payload, current):
    """Returns (changes, errors). Only a tiered component takes `tiers`; only a flat one takes `amount`."""
    changes, errors = {}, {}
    if "name" in payload:
        name = payload["name"].strip() if isinstance(payload["name"], str) else ""
        if not name or len(name) > 120:
            errors["name"] = "Name is required (120 characters at most)"
        else:
            changes["name"] = name
    if "description" in payload:
        desc = payload["description"]
        if desc is not None and (not isinstance(desc, str) or len(desc) > 500):
            errors["description"] = "Description must be 500 characters or fewer"
        else:
            changes["description"] = (desc or "").strip() or None
    if "is_active" in payload:
        if not isinstance(payload["is_active"], bool):
            errors["is_active"] = "Must be true or false"
        else:
            changes["is_active"] = payload["is_active"]
    tiered = bool(current["tiers"])
    if "amount" in payload:
        if tiered:
            errors["amount"] = "This component is priced in tiers; edit the tiers instead"
        else:
            changes["amount"], msg = _amount(payload["amount"])
            if msg:
                errors["amount"] = msg
    if "tiers" in payload:
        if not tiered:
            errors["tiers"] = "This component has one flat price; edit the amount instead"
        else:
            changes["tiers"], msg = _tiers(payload["tiers"])
            if msg:
                errors["tiers"] = msg
    if not changes and not errors:
        errors["_"] = "Nothing to update"
    return changes, errors


def _tiers(raw):
    if not isinstance(raw, list) or not 2 <= len(raw) <= MAX_TIERS:
        return None, f"Provide between 2 and {MAX_TIERS} tiers"
    tiers, previous = [], 0
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            return None, "Each tier needs a student limit and an amount"
        amount, msg = _amount(item.get("amount"))
        if msg:
            return None, f"Tier {i + 1}: {msg}"
        limit, last = item.get("up_to_students"), i == len(raw) - 1
        if last:
            if limit is not None:
                return None, "The last tier must have no student limit (it covers every larger school)"
            limit = None
        else:
            if isinstance(limit, bool) or not isinstance(limit, int) or limit <= previous:
                return None, f"Tier {i + 1}: the student limit must be a whole number above {previous:,}"
            previous = limit
        tiers.append({"up_to_students": limit, "amount": amount})
    return tiers, None
