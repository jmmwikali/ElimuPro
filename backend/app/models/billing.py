from ..extensions import db
from .core import now

INFLIGHT = ("created", "pending", "error")  # attempts whose outcome we may not know yet


class Invoice(db.Model):
    """What a school owes ElimuNova for a component. Prices are snapshotted when issued."""
    __tablename__ = "invoices"
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False, index=True)
    number = db.Column(db.String(30), nullable=False, unique=True)
    component_key = db.Column(db.String(40), nullable=False)
    description = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    student_count = db.Column(db.Integer)  # school size used to pick the price tier
    unit_price = db.Column(db.Numeric(12, 2), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)  # whole KES shillings
    currency = db.Column(db.String(3), default="KES", nullable=False)
    reference = db.Column(db.String(60), nullable=False)  # billing period or batch, e.g. "Term 2 2026"
    status = db.Column(db.String(10), default="unpaid", nullable=False, index=True)  # unpaid | paid | void
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=now, nullable=False)
    paid_at = db.Column(db.DateTime)
    school = db.relationship("School")
    attempts = db.relationship("PaymentAttempt", backref="invoice", order_by="PaymentAttempt.id")
    # The same component cannot be billed twice for the same period or batch.
    __table_args__ = (db.UniqueConstraint("school_id", "component_key", "reference"),)

    def latest_attempt(self):
        return self.attempts[-1] if self.attempts else None

    def to_dict(self, with_school=False):
        attempt = self.latest_attempt()
        d = {"id": self.id, "number": self.number, "component_key": self.component_key,
             "description": self.description, "quantity": self.quantity, "student_count": self.student_count,
             "unit_price": float(self.unit_price), "amount": float(self.amount), "currency": self.currency,
             "reference": self.reference, "status": self.status, "created_at": self.created_at.isoformat(),
             "paid_at": self.paid_at.isoformat() if self.paid_at else None,
             "attempt": attempt.to_dict() if attempt else None}
        if with_school:
            d.update(school_id=self.school_id, school=self.school.name)
        return d


class PaymentAttempt(db.Model):
    """One STK push for an invoice. created -> pending -> succeeded | failed | timeout | expired."""
    __tablename__ = "payment_attempts"
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoices.id"), nullable=False, index=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False, index=True)
    provider = db.Column(db.String(20), default="cyzora", nullable=False)
    provider_charge_id = db.Column(db.String(80), unique=True)
    idempotency_key = db.Column(db.String(80), nullable=False, unique=True)
    phone = db.Column(db.String(15), nullable=False)
    amount_cents = db.Column(db.BigInteger, nullable=False)
    status = db.Column(db.String(20), default="created", nullable=False, index=True)
    # also: error (outcome unknown) and amount_mismatch (provider says paid, amount differs: needs a human)
    provider_status = db.Column(db.String(30))
    receipt = db.Column(db.String(60))
    error = db.Column(db.String(255))
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=now, nullable=False)
    updated_at = db.Column(db.DateTime, default=now, onupdate=now, nullable=False)

    def to_dict(self):
        return {"id": self.id, "status": self.status, "phone_hint": "..." + self.phone[-3:],
                "receipt": self.receipt, "error": self.error, "created_at": self.created_at.isoformat()}
