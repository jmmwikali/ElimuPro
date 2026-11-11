from datetime import datetime
from ..extensions import db
from .core import now


class PlatformModule(db.Model):
    """Independent modules available in the ElimuNova ecosystem."""
    __tablename__ = "platform_modules"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(40), unique=True, nullable=False)  # academics, zeroq, careergps
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    is_core = db.Column(db.Boolean, default=False, nullable=False)  # academics is always on
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=now, nullable=False)

    def to_dict(self):
        return {
            "id": self.id, "code": self.code, "name": self.name,
            "description": self.description, "is_core": self.is_core, "is_active": self.is_active,
        }


class SchoolModule(db.Model):
    """Per-school module enablement and configuration."""
    __tablename__ = "school_modules"
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False, index=True)
    module_code = db.Column(db.String(40), nullable=False, index=True)
    is_enabled = db.Column(db.Boolean, default=True, nullable=False)
    settings = db.Column(db.JSON, default=dict)
    enabled_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime, default=now, onupdate=now, nullable=False)
    __table_args__ = (db.UniqueConstraint("school_id", "module_code"),)

    def to_dict(self):
        return {
            "school_id": self.school_id, "module_code": self.module_code,
            "is_enabled": self.is_enabled, "settings": self.settings or {},
            "enabled_at": self.enabled_at.isoformat() if self.enabled_at else None,
        }


class LeadershipProfile(db.Model):
    """Editable leadership acknowledgement (Rose Seko by default)."""
    __tablename__ = "leadership_profiles"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, default="Rose Seko")
    designation = db.Column(db.String(120), nullable=False, default="Company Owner")
    acknowledgement = db.Column(db.Text, nullable=False)
    photo_url = db.Column(db.String(500))
    is_visible = db.Column(db.Boolean, default=True, nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    updated_at = db.Column(db.DateTime, default=now, onupdate=now, nullable=False)

    def to_dict(self):
        return {
            "id": self.id, "name": self.name, "designation": self.designation,
            "acknowledgement": self.acknowledgement, "photo_url": self.photo_url,
            "is_visible": self.is_visible,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class CareerPath(db.Model):
    """Career exploration paths in CareerGPS."""
    __tablename__ = "career_paths"
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(80))  # STEM, Business, Arts, Health, etc.
    related_subjects = db.Column(db.JSON, default=list)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=now, nullable=False)

    def to_dict(self):
        return {
            "id": self.id, "title": self.title, "description": self.description,
            "category": self.category, "related_subjects": self.related_subjects or [],
            "is_active": self.is_active,
        }


class StudentCareerInterest(db.Model):
    """Student career interests and progress tracking."""
    __tablename__ = "student_career_interests"
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False, index=True)
    career_path_id = db.Column(db.Integer, db.ForeignKey("career_paths.id"), nullable=False)
    interest_level = db.Column(db.Integer, default=3)  # 1-5
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=now, nullable=False)
    updated_at = db.Column(db.DateTime, default=now, onupdate=now, nullable=False)

    career_path = db.relationship("CareerPath")

    def to_dict(self):
        return {
            "id": self.id, "career_path_id": self.career_path_id,
            "career_path": self.career_path.to_dict() if self.career_path else None,
            "interest_level": self.interest_level, "notes": self.notes,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
