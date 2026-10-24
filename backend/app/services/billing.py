"""Invoicing for ElimuPro components and the one place an invoice becomes paid."""
import secrets
from decimal import Decimal

from flask import request

from ..extensions import db
from ..models import AuditLog, Invoice, Student
from ..models.core import now
from . import pricing

QUANTITY_UNITS = ("per_admission", "per_transfer", "per_student_year")  # others are always quantity 1
MAX_QUANTITY = 100000
TERMINAL_FAILURES = ("failed", "timeout", "expired")


def log(action, attempt=None, invoice=None, details=None):
    """Audit entry for system events (webhooks, reconciliation) that have no signed-in user."""
    invoice = invoice or (attempt.invoice if attempt else None)
    db.session.add(AuditLog(school_id=invoice.school_id if invoice else None, action=action,
                            entity="invoice" if invoice else None, entity_id=invoice.id if invoice else None,
                            details=details, ip_address=request.remote_addr if request else None))


def issue_invoice(school, component_key, quantity, reference, user):
    """Returns (invoice, errors). The price is read now and stored, so later price edits never change it."""
    errors = {}
    component = pricing.get_component(component_key)
    if not component:
        return None, {"component_key": "Choose a valid component"}
    reference = reference.strip() if isinstance(reference, str) else ""
    if not reference or len(reference) > 60:
        errors["reference"] = "Required: the billing period or batch, e.g. Term 2 2026 (60 characters at most)"
    unit = component["billing_unit"]
    if unit in QUANTITY_UNITS:
        if isinstance(quantity, bool) or not isinstance(quantity, int) or not 1 <= quantity <= MAX_QUANTITY:
            errors["quantity"] = f"Enter a whole number from 1 to {MAX_QUANTITY:,}"
    elif quantity not in (None, 1):
        errors["quantity"] = f"{component['name']} is billed {pricing.BILLING_UNITS[unit]}; quantity is always 1"
        quantity = 1
    else:
        quantity = 1
    if component["currency"] != "KES":
        errors["component_key"] = f"{component['name']} is priced in {component['currency']} and cannot be paid by M-Pesa"
    elif not component["is_active"]:
        errors["component_key"] = f"{component['name']} is not currently on sale"
    if errors:
        return None, errors

    students = Student.query.filter_by(school_id=school.id, status="active").count()
    unit_price = pricing.price_for(component, students)
    amount = unit_price * quantity
    if amount != amount.to_integral_value() or amount <= 0:
        return None, {"component_key": "The total must be a whole number of shillings above zero; adjust the price"}
    if Invoice.query.filter_by(school_id=school.id, component_key=component_key, reference=reference).first():
        return None, {"reference": f"{component['name']} is already invoiced to this school for '{reference}'"}

    invoice = Invoice(
        school_id=school.id, number=f"INV-{now():%Y}-{secrets.token_hex(3).upper()}", component_key=component_key,
        description=f"{component['name']}: {reference}", quantity=quantity, student_count=students,
        unit_price=unit_price, amount=amount, currency="KES", reference=reference, created_by=user.id)
    db.session.add(invoice)
    return invoice, None


def apply_charge_result(attempt, charge):
    """Apply a charge that was fetched from Cyzora (never a browser redirect or an unverified body).

    Idempotent: webhooks repeat, so a settled attempt is never changed again. Only a `succeeded`
    charge whose amount equals the invoice amount can mark the invoice paid.
    Returns the outcome as a string.
    """
    if attempt.status == "succeeded":
        return "already_succeeded"
    status = charge["status"]
    attempt.provider_status = status if isinstance(status, str) else None
    if status == "succeeded":
        if charge["amount_cents"] is None or charge["amount_cents"] != attempt.amount_cents:
            attempt.status = "amount_mismatch"
            log("billing.amount_mismatch", attempt, details={
                "attempt_id": attempt.id, "expected_cents": attempt.amount_cents, "reported": charge["amount_cents"]})
            return "amount_mismatch"
        attempt.status = "succeeded"
        attempt.receipt = str(charge["receipt"])[:60] if charge.get("receipt") else None
        invoice = attempt.invoice
        if invoice.status == "unpaid":
            invoice.status = "paid"
            invoice.paid_at = now()
            log("billing.invoice_paid", attempt, details={"attempt_id": attempt.id, "receipt": attempt.receipt})
            return "paid"
        # Money arrived for an invoice that is already settled or voided: keep it visible for a refund.
        log("billing.unexpected_payment", attempt, details={"attempt_id": attempt.id, "invoice_status": invoice.status})
        return "unexpected_payment"
    if status in TERMINAL_FAILURES:
        attempt.status = status
        return status
    return "pending"
