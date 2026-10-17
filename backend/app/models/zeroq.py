from ..extensions import db
from .core import now


class ZeroQPass(db.Model):
    __tablename__ = "zeroq_passes"
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False, index=True)
    application_id = db.Column(db.Integer, db.ForeignKey("student_applications.id"), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False, index=True)
    reference = db.Column(db.String(30), nullable=False, unique=True)
    token_hash = db.Column(db.String(64), nullable=False, unique=True)
    expected_on = db.Column(db.Date, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    revoked_at = db.Column(db.DateTime)
    used_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    issued_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=now, nullable=False)

    application = db.relationship("StudentApplication")
    student = db.relationship("Student")
    scans = db.relationship("ZeroQScan", backref="admission_pass", cascade="all, delete-orphan")

    def state(self, at=None):
        at = at or now()
        if self.revoked_at:
            return "revoked"
        if self.completed_at:
            return "completed"
        if self.used_at:
            return "checked_in"
        if self.expires_at <= at:
            return "expired"
        return "ready"

    def to_dict(self):
        student = self.student
        return {
            "id": self.id,
            "reference": self.reference,
            "expected_on": self.expected_on.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "status": self.state(),
            "created_at": self.created_at.isoformat(),
            "student": {
                "full_name": student.full_name,
                "admission_number": student.admission_number,
                "class": student.school_class.name if student.school_class else None,
            },
        }


class ZeroQScan(db.Model):
    __tablename__ = "zeroq_scans"
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False, index=True)
    pass_id = db.Column(db.Integer, db.ForeignKey("zeroq_passes.id"), index=True)
    scanned_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    token_fingerprint = db.Column(db.String(64), nullable=False)
    outcome = db.Column(db.String(30), nullable=False, index=True)
    scanned_at = db.Column(db.DateTime, default=now, nullable=False, index=True)