from flask import Blueprint, g, request

from ..extensions import db
from ..models import PriceComponent, PriceTier
from ..services import pricing
from ..utils.responses import err, ok
from ..utils.security import audit, roles_required

bp = Blueprint("pricing", __name__, url_prefix="/api/pricing")


def _public(c):
    return {"key": c["key"], "name": c["name"], "description": c["description"],
            "billing_unit": c["billing_unit"], "billing_label": pricing.BILLING_UNITS[c["billing_unit"]],
            "currency": c["currency"], "is_active": c["is_active"],
            "amount": float(c["amount"]) if c["amount"] is not None else None,
            "tiers": [{"up_to_students": t["up_to_students"], "amount": float(t["amount"])} for t in c["tiers"]],
            "updated_at": c["updated_at"].isoformat() if c["updated_at"] else None}


def _snapshot(c):
    return {k: v for k, v in _public(c).items() if k in ("name", "is_active", "amount", "tiers")}


@bp.get("")
@roles_required("super_admin")
def list_prices():
    return ok([_public(c) for c in pricing.get_components()])


@bp.put("/<key>")
@roles_required("super_admin")
def update_price(key):
    default = pricing.default_for(key)
    if not default:
        return err("Unknown component", 404)
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return err("Send a JSON object", 400)
    before = pricing.get_component(key)
    changes, errors = pricing.validate_update(payload, before)
    if errors:
        return err("Please fix the highlighted fields", 422, errors)

    row = PriceComponent.query.filter_by(key=key).first()
    if not row:  # first edit of a component that has only ever used its default
        row = PriceComponent(key=key, name=default["name"], billing_unit=default["billing_unit"],
                             currency=default["currency"], amount=default.get("amount"))
        row.tiers = [PriceTier(up_to_students=t["up_to_students"], amount=t["amount"])
                     for t in default.get("tiers", [])]
        db.session.add(row)
    for field in ("name", "description", "is_active", "amount"):
        if field in changes:
            setattr(row, field, changes[field])
    if "tiers" in changes:
        row.tiers = [PriceTier(up_to_students=t["up_to_students"], amount=t["amount"]) for t in changes["tiers"]]
    row.updated_by = g.user.id
    db.session.flush()
    after = pricing.get_component(key)
    audit("pricing.updated", "price_component", row.id,
          {"key": key, "before": _snapshot(before), "after": _snapshot(after)})
    db.session.commit()
    return ok(_public(pricing.get_component(key)))
