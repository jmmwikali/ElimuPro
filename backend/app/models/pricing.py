from ..extensions import db
from .core import now


class PriceComponent(db.Model):
    """One sellable ElimuNova component. Flat components use `amount`; tiered ones use `tiers`."""
    __tablename__ = "price_components"
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(40), nullable=False, unique=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(500))
    billing_unit = db.Column(db.String(30), nullable=False)
    currency = db.Column(db.String(3), default="KES", nullable=False)
    amount = db.Column(db.Numeric(12, 2))  # NULL when tiered
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    updated_at = db.Column(db.DateTime, default=now, onupdate=now, nullable=False)
    tiers = db.relationship("PriceTier", cascade="all, delete-orphan", order_by="PriceTier.id",
                            backref="component")


class PriceTier(db.Model):
    """Applies to schools with at most `up_to_students` students (inclusive); NULL = no upper limit."""
    __tablename__ = "price_tiers"
    id = db.Column(db.Integer, primary_key=True)
    component_id = db.Column(db.Integer, db.ForeignKey("price_components.id"), nullable=False, index=True)
    up_to_students = db.Column(db.Integer)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
