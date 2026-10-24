from ..extensions import db
from .core import now


class Student(db.Model):
    __tablename__ = "students"
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True)
    admission_number = db.Column(db.String(30), nullable=False)
    first_name = db.Column(db.String(80), nullable=False)
    middle_name = db.Column(db.String(80))
    last_name = db.Column(db.String(80), nullable=False)
    date_of_birth = db.Column(db.Date)
    gender = db.Column(db.String(10))
    nationality = db.Column(db.String(60))
    county = db.Column(db.String(80))
    previous_school = db.Column(db.String(200))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(255))
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id"), index=True)
    stream_id = db.Column(db.Integer, db.ForeignKey("streams.id"))
    status = db.Column(db.String(20), default="active", nullable=False, index=True)  # active|inactive|transferred|graduated
    admitted_on = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=now, nullable=False)

    user = db.relationship("User")
    school_class = db.relationship("SchoolClass")
    stream = db.relationship("Stream")
    guardians = db.relationship("Guardian", backref="student", cascade="all, delete-orphan")
    __table_args__ = (db.UniqueConstraint("school_id", "admission_number"),)

    @property
    def full_name(self):
        return " ".join(p for p in (self.first_name, self.middle_name, self.last_name) if p)

    def to_dict(self):
        return {"id": self.id, "admission_number": self.admission_number, "full_name": self.full_name,
                "first_name": self.first_name, "last_name": self.last_name,
                "date_of_birth": self.date_of_birth.isoformat() if self.date_of_birth else None,
                "gender": self.gender, "nationality": self.nationality, "county": self.county,
                "previous_school": self.previous_school, "phone": self.phone, "email": self.email,
                "class": self.school_class.name if self.school_class else None, "class_id": self.class_id,
                "stream": self.stream.name if self.stream else None, "stream_id": self.stream_id,
                "status": self.status, "admitted_on": self.admitted_on.isoformat() if self.admitted_on else None,
                "guardians": [g.to_dict() for g in self.guardians]}


class Guardian(db.Model):
    __tablename__ = "guardians"
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))  # set when a parent account is linked (phase 5)
    full_name = db.Column(db.String(160), nullable=False)
    relationship_type = db.Column(db.String(40))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(255))
    is_emergency_contact = db.Column(db.Boolean, default=False, nullable=False)

    def to_dict(self):
        return {"id": self.id, "full_name": self.full_name, "relationship": self.relationship_type,
                "phone": self.phone, "email": self.email, "is_emergency_contact": self.is_emergency_contact,
                "has_account": self.user_id is not None}


class StudentApplication(db.Model):
    __tablename__ = "student_applications"
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False, index=True)
    applicant_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"))  # set on enrolment
    reference_no = db.Column(db.String(30), unique=True)
    status = db.Column(db.String(20), default="draft", nullable=False, index=True)
    # draft|submitted|under_review|changes_required|approved|rejected|enrolled
    first_name = db.Column(db.String(80))
    middle_name = db.Column(db.String(80))
    last_name = db.Column(db.String(80))
    date_of_birth = db.Column(db.Date)
    gender = db.Column(db.String(10))
    nationality = db.Column(db.String(60), default="Kenyan")
    county = db.Column(db.String(80))
    previous_school = db.Column(db.String(200))
    applying_class_id = db.Column(db.Integer, db.ForeignKey("classes.id"))
    guardian_name = db.Column(db.String(160))
    guardian_relationship = db.Column(db.String(40))
    guardian_phone = db.Column(db.String(20))
    guardian_email = db.Column(db.String(255))
    emergency_contact_name = db.Column(db.String(160))
    emergency_contact_phone = db.Column(db.String(20))
    review_note = db.Column(db.Text)
    reviewed_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    reviewed_at = db.Column(db.DateTime)
    submitted_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=now, nullable=False)
    updated_at = db.Column(db.DateTime, default=now, onupdate=now, nullable=False)

    applicant = db.relationship("User", foreign_keys=[applicant_user_id])
    applying_class = db.relationship("SchoolClass")
    documents = db.relationship("ApplicationDocument", backref="application", cascade="all, delete-orphan")

    EDITABLE = ("first_name", "middle_name", "last_name", "date_of_birth", "gender", "nationality", "county",
                "previous_school", "applying_class_id", "guardian_name", "guardian_relationship",
                "guardian_phone", "guardian_email", "emergency_contact_name", "emergency_contact_phone")

    def to_dict(self, detail=False):
        d = {"id": self.id, "reference_no": self.reference_no, "status": self.status,
             "first_name": self.first_name, "last_name": self.last_name,
             "applicant_name": " ".join(p for p in (self.first_name, self.middle_name, self.last_name) if p),
             "applying_class": self.applying_class.name if self.applying_class else None,
             "applying_class_id": self.applying_class_id,
             "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
             "review_note": self.review_note}
        if detail:
            d.update({k: (getattr(self, k).isoformat() if k == "date_of_birth" and self.date_of_birth
                          else getattr(self, k)) for k in self.EDITABLE if k not in d})
            d["middle_name"] = self.middle_name
            d["date_of_birth"] = self.date_of_birth.isoformat() if self.date_of_birth else None
            d["email"] = self.applicant.email
            d["phone"] = self.applicant.phone
            d["student_id"] = self.student_id
            d["documents"] = [x.to_dict() for x in self.documents]
        return d


class ApplicationDocument(db.Model):
    """An admission document a student uploaded. The file lives in private storage (never a public URL);
    `file_url` holds the internal reference `private:<storage_key>`."""
    __tablename__ = "application_documents"
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False, index=True)
    application_id = db.Column(db.Integer, db.ForeignKey("student_applications.id"), nullable=False, index=True)
    doc_type = db.Column(db.String(60), nullable=False)
    file_name = db.Column(db.String(255), nullable=False)
    file_url = db.Column(db.String(500), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=now, nullable=False)
    # ZeroQ verification workflow
    storage_key = db.Column(db.String(120), unique=True)
    content_type = db.Column(db.String(60))
    size_bytes = db.Column(db.Integer)
    sha256 = db.Column(db.String(64), index=True)
    status = db.Column(db.String(30), default="uploaded", server_default="uploaded", nullable=False, index=True)
    version = db.Column(db.Integer, default=1, server_default="1", nullable=False)
    supersedes_id = db.Column(db.Integer, db.ForeignKey("application_documents.id"))
    uploaded_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    verification = db.Column(db.JSON)  # structured result of the automated checks
    escalated_at = db.Column(db.DateTime)
    reviewed_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    reviewed_at = db.Column(db.DateTime)
    review_note = db.Column(db.Text)
    events = db.relationship("DocumentEvent", backref="document", order_by="DocumentEvent.id",
                             cascade="all, delete-orphan")

    def to_dict(self):
        return {"id": self.id, "doc_type": self.doc_type, "file_name": self.file_name, "status": self.status,
                "version": self.version, "size_bytes": self.size_bytes, "content_type": self.content_type,
                "uploaded_at": self.uploaded_at.isoformat(), "escalated": self.escalated_at is not None}
