"""ZeroQ student onboarding: assessment results, document history, school document requirements, notifications."""
from ..extensions import db
from .core import now


class AssessmentResult(db.Model):
    """A student's KJSEA results as THEY submitted them. Nothing here is official until a school reviewer
    has verified it, and the status always says which of those two things it is."""
    __tablename__ = "assessment_results"
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False, index=True)
    student_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    assessment_year = db.Column(db.Integer, nullable=False)
    candidate_number = db.Column(db.String(30))
    subjects = db.Column(db.JSON, nullable=False, default=list)  # [{"subject": "...", "result": "..."}]
    status = db.Column(db.String(30), default="draft", nullable=False, index=True)
    review_note = db.Column(db.Text)  # reason shown to the student (corrections, rejection, failure)
    verification_basis = db.Column(db.String(200))  # what the reviewer checked it against
    submitted_at = db.Column(db.DateTime)
    verified_at = db.Column(db.DateTime)
    verified_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=now, nullable=False)
    updated_at = db.Column(db.DateTime, default=now, onupdate=now, nullable=False)
    events = db.relationship("AssessmentResultEvent", backref="result", order_by="AssessmentResultEvent.id",
                             cascade="all, delete-orphan")
    student = db.relationship("User", foreign_keys=[student_user_id])
    __table_args__ = (db.UniqueConstraint("student_user_id", "assessment_year"),)


class AssessmentResultEvent(db.Model):
    """Append-only history of every status change."""
    __tablename__ = "assessment_result_events"
    id = db.Column(db.Integer, primary_key=True)
    result_id = db.Column(db.Integer, db.ForeignKey("assessment_results.id"), nullable=False, index=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False, index=True)
    from_status = db.Column(db.String(30))
    to_status = db.Column(db.String(30), nullable=False)
    actor_user_id = db.Column(db.Integer, db.ForeignKey("users.id"))  # NULL = the system
    actor_role = db.Column(db.String(30))
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=now, nullable=False)


class DocumentEvent(db.Model):
    """Append-only history for an uploaded document: automated checks and every reviewer action."""
    __tablename__ = "document_events"
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey("application_documents.id"), nullable=False, index=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False, index=True)
    action = db.Column(db.String(30), nullable=False)  # uploaded|automated_checks|approve|request_correction|reject|escalate|note
    from_status = db.Column(db.String(30))
    to_status = db.Column(db.String(30))
    actor_user_id = db.Column(db.Integer, db.ForeignKey("users.id"))  # NULL = the system
    actor_role = db.Column(db.String(30))
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=now, nullable=False)


class DocumentRequirement(db.Model):
    """A document a school asks for. Stored in the database so schools can change it without a deploy."""
    __tablename__ = "document_requirements"
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False, index=True)
    doc_type = db.Column(db.String(60), nullable=False)  # slug, e.g. "birth_certificate"
    label = db.Column(db.String(120), nullable=False)
    instructions = db.Column(db.Text)
    required = db.Column(db.Boolean, default=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    __table_args__ = (db.UniqueConstraint("school_id", "doc_type"),)

    def to_dict(self):
        return {"id": self.id, "doc_type": self.doc_type, "label": self.label, "instructions": self.instructions,
                "required": self.required, "is_active": self.is_active, "sort_order": self.sort_order}


class Notification(db.Model):
    """In-app notification. Email and SMS are not connected (no provider is configured in this project)."""
    __tablename__ = "notifications"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), index=True)
    kind = db.Column(db.String(40), nullable=False)
    title = db.Column(db.String(160), nullable=False)
    body = db.Column(db.String(500))
    read_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=now, nullable=False, index=True)

    def to_dict(self):
        return {"id": self.id, "kind": self.kind, "title": self.title, "body": self.body,
                "read": self.read_at is not None, "created_at": self.created_at.isoformat()}
