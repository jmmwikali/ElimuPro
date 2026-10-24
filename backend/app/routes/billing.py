import json
import secrets
from datetime import timedelta

from flask import Blueprint, current_app, g, request

from ..config import BRAND_NAME
from ..extensions import db
from ..models import Invoice, PaymentAttempt, School
from ..models.billing import INFLIGHT
from ..models.core import now
from ..services import billing, cyzora
from ..utils.responses import err, ok
from ..utils.security import ADMIN_ROLES, audit, roles_required, scoped_get
from ..utils.validation import normalize_phone, paginate

bp = Blueprint("billing", __name__, url_prefix="/api/billing")

RETRY_AFTER_MINUTES = 2  # an STK prompt that is still pending blocks a second prompt for this long
MAX_WEBHOOK_BYTES = 1_000_000
NOT_CONFIGURED = f"Online payments are not set up yet. Please contact {BRAND_NAME} support."


def _find(invoice_id):
    return db.session.get(Invoice, invoice_id) if g.user.role == "super_admin" else scoped_get(Invoice, invoice_id)


def _provider_failure(e):
    """Turn a Cyzora error into a clear message and status for the caller."""
    if e.status in (401, 403):  # our key is wrong or not allowed: not something the school can fix
        current_app.logger.error("Cyzora rejected our credentials (HTTP %s)", e.status)
        return f"Online payments are misconfigured. Please contact {BRAND_NAME} support.", 502
    if e.status == 429:
        return "The payment provider is busy. Please try again in a minute.", 429
    if e.status and 400 <= e.status < 500:
        return f"The payment could not be started: {e}", 422
    return "We could not confirm that the payment prompt was sent. Wait a minute and check the status before retrying.", 502


@bp.get("/invoices")
@roles_required("super_admin", *ADMIN_ROLES)
def list_invoices():
    q = Invoice.query
    if g.user.role != "super_admin":
        q = q.filter_by(school_id=g.user.school_id)
    elif request.args.get("school_id", type=int):
        q = q.filter_by(school_id=request.args.get("school_id", type=int))
    if request.args.get("status") in ("unpaid", "paid", "void"):
        q = q.filter_by(status=request.args["status"])
    items, meta = paginate(q.order_by(Invoice.id.desc()))
    return ok([i.to_dict(with_school=g.user.role == "super_admin") for i in items], meta=meta)


@bp.get("/invoices/<int:invoice_id>")
@roles_required("super_admin", *ADMIN_ROLES)
def get_invoice(invoice_id):
    inv = _find(invoice_id)
    return ok(inv.to_dict(with_school=g.user.role == "super_admin")) if inv else err("Invoice not found", 404)


@bp.post("/invoices")
@roles_required("super_admin")
def create_invoice():
    d = request.get_json(silent=True) or {}
    school = db.session.get(School, d.get("school_id")) if isinstance(d.get("school_id"), int) else None
    if not school:
        return err("Please fix the highlighted fields", 422, {"school_id": "Choose a school"})
    invoice, errors = billing.issue_invoice(school, d.get("component_key"), d.get("quantity"), d.get("reference"), g.user)
    if errors:
        return err("Please fix the highlighted fields", 422, errors)
    db.session.flush()
    audit("billing.invoice_issued", "invoice", invoice.id, {"number": invoice.number, "amount": float(invoice.amount)})
    db.session.commit()
    return ok(invoice.to_dict(with_school=True), 201)


@bp.post("/invoices/<int:invoice_id>/void")
@roles_required("super_admin")
def void_invoice(invoice_id):
    inv = db.session.get(Invoice, invoice_id)
    if not inv:
        return err("Invoice not found", 404)
    if inv.status != "unpaid":
        return err(f"A {inv.status} invoice cannot be voided", 409)
    recent = now() - timedelta(minutes=15)
    if any(a.status in INFLIGHT and a.created_at > recent for a in inv.attempts):
        return err("A payment prompt for this invoice may still be in progress. Try again in a few minutes.", 409)
    inv.status = "void"
    audit("billing.invoice_voided", "invoice", inv.id)
    db.session.commit()
    return ok(inv.to_dict(with_school=True))


@bp.post("/invoices/<int:invoice_id>/pay")
@roles_required(*ADMIN_ROLES)
def pay_invoice(invoice_id):
    """Send an M-Pesa STK prompt. This only STARTS a payment; the invoice is marked paid by the webhook
    or a status check after Cyzora confirms it, never by this call."""
    inv = scoped_get(Invoice, invoice_id)
    if not inv:
        return err("Invoice not found", 404)
    if inv.status != "unpaid":
        return err(f"This invoice is already {inv.status}", 409)
    if not cyzora.configured():
        return err(NOT_CONFIGURED, 503)
    phone = normalize_phone((request.get_json(silent=True) or {}).get("phone"))
    if not phone:
        return err("Please fix the highlighted fields", 422, {"phone": "Enter a valid Safaricom number, e.g. 0712345678"})
    cutoff = now() - timedelta(minutes=RETRY_AFTER_MINUTES)
    if any(a.status in INFLIGHT and a.created_at > cutoff for a in inv.attempts):
        return err("A payment prompt was just sent. Check the phone, or wait a couple of minutes to try again.", 409)

    attempt = PaymentAttempt(
        invoice_id=inv.id, school_id=inv.school_id, phone=phone, amount_cents=int(inv.amount * 100),
        idempotency_key=f"{inv.number}-{secrets.token_hex(6)}", created_by=g.user.id)
    db.session.add(attempt)
    db.session.commit()  # recorded before we call out, so a crash mid-request still leaves a trace
    try:
        charge = cyzora.charge_fields(cyzora.create_charge(
            attempt.amount_cents, phone.lstrip("+"), inv.number,
            {"invoice": inv.number, "school_id": inv.school_id, "attempt_id": attempt.id}, attempt.idempotency_key))
        if not charge["id"]:
            raise cyzora.CyzoraError("Payment provider sent an unexpected response")
    except cyzora.CyzoraError as e:
        attempt.status = "failed" if e.status and 400 <= e.status < 500 else "error"
        attempt.error = str(e)[:255]
        audit("billing.pay_failed", "invoice", inv.id, {"attempt_id": attempt.id, "http": e.status})
        db.session.commit()
        message, status = _provider_failure(e)
        return err(message, status)
    attempt.provider_charge_id = str(charge["id"])
    attempt.provider_status = charge["status"] if isinstance(charge["status"], str) else None
    attempt.status = "pending"
    audit("billing.pay_started", "invoice", inv.id, {"attempt_id": attempt.id})
    db.session.commit()
    return ok(inv.to_dict(), 202, message="Check your phone and enter your M-Pesa PIN.")


@bp.post("/invoices/<int:invoice_id>/refresh")
@roles_required("super_admin", *ADMIN_ROLES)
def refresh_invoice(invoice_id):
    """Ask Cyzora where the latest payment stands. Also recovers a payment whose webhook never arrived."""
    inv = _find(invoice_id)
    if not inv:
        return err("Invoice not found", 404)
    attempt = inv.latest_attempt()
    if inv.status == "unpaid" and attempt and attempt.status in ("pending", "error") and attempt.provider_charge_id:
        try:
            billing.apply_charge_result(attempt, cyzora.charge_fields(cyzora.get_charge(attempt.provider_charge_id)))
            db.session.commit()
        except cyzora.CyzoraError as e:
            db.session.rollback()
            return err(_provider_failure(e)[0], 502)
    return ok(inv.to_dict(with_school=g.user.role == "super_admin"))


@bp.post("/webhooks/cyzora")
def cyzora_webhook():
    secret = current_app.config.get("CYZORA_WEBHOOK_SECRET")
    if not secret or not cyzora.configured():
        return err("Webhooks are not configured", 503)  # non-2xx so Cyzora retries once we are set up
    if (request.content_length or 0) > MAX_WEBHOOK_BYTES:
        return err("Payload too large", 413)
    raw = request.get_data()  # the exact bytes: the signature covers them, so verify before parsing
    if not cyzora.verify_signature(raw, request.headers.get("X-Cyzora-Signature"), secret):
        return err("Invalid signature", 401)
    try:
        body = json.loads(raw)
    except ValueError:
        return err("Invalid JSON", 400)
    if not isinstance(body, dict):
        return err("Invalid JSON", 400)

    event = body.get("event")
    if event == "webhook.test":
        return ok({"received": True})
    if (body.get("livemode") is False) != (not cyzora.key_is_live()):
        # A test event must never settle a live invoice, and a live event never a test one.
        return ok({"ignored": "livemode does not match this server's key"})
    if event not in ("charge.succeeded", "charge.failed", "charge.expired"):
        return ok({"ignored": event})  # payout.* and anything new: acknowledged, not ours to act on

    charge_id = cyzora.charge_fields(body)["id"]
    attempt = PaymentAttempt.query.filter_by(provider_charge_id=str(charge_id)).first() if charge_id else None
    if not attempt:
        billing.log("billing.webhook_unmatched", details={"event": event, "charge_id": str(charge_id)[:80]})
        db.session.commit()
        return ok({"ignored": "unknown charge"})
    try:  # confirm with Cyzora rather than trusting the body alone
        outcome = billing.apply_charge_result(attempt, cyzora.charge_fields(cyzora.get_charge(attempt.provider_charge_id)))
    except cyzora.CyzoraError:
        db.session.rollback()
        return err("Could not confirm the charge, please retry", 502)  # Cyzora retries after 10s, 30s, 2m, 10m
    db.session.commit()
    return ok({"result": outcome})
