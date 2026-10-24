from datetime import datetime

from sqlalchemy import true

from ..extensions import db, bcrypt


def now():
    return datetime.utcnow()


class School(db.Model):
    __tablename__ = "schools"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(120), unique=True, nullable=False)
    school_type = db.Column(db.String(30), default="primary")  # primary | junior_secondary | senior_secondary | mixed
    county = db.Column(db.String(80))
    motto = db.Column(db.String(255))
    address = db.Column(db.String(255))
    phone = db.Column(db.String(30))
    email = db.Column(db.String(255))
    website = db.Column(db.String(255))
    logo_url = db.Column(db.String(500))
    primary_color = db.Column(db.String(9), default="#14213D")
    admission_prefix = db.Column(db.String(10), default="")
    admissions_open = db.Column(db.Boolean, default=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_demo = db.Column(db.Boolean, default=False, nullable=False)
    # ZeroQ pass rules: both on by default. A school turns the results rule off for grades that do not sit the KJSEA.
    zeroq_require_results = db.Column(db.Boolean, default=True, server_default=true(), nullable=False)
    zeroq_require_documents = db.Column(db.Boolean, default=True, server_default=true(), nullable=False)
    created_at = db.Column(db.DateTime, default=now, nullable=False)

    def to_dict(self, public=False):
        d = {"id": self.id, "name": self.name, "slug": self.slug, "school_type": self.school_type,
             "county": self.county, "motto": self.motto, "logo_url": self.logo_url,
             "primary_color": self.primary_color, "admissions_open": self.admissions_open}
        if not public:
            d.update(address=self.address, phone=self.phone, email=self.email,
                     website=self.website, is_active=self.is_active, is_demo=self.is_demo)
        return d


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), index=True)  # NULL only for platform super admin
    email = db.Column(db.String(255), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(80), nullable=False)
    middle_name = db.Column(db.String(80))
    last_name = db.Column(db.String(80), nullable=False)
    # super_admin | school_admin | principal | deputy_principal | bursar | teacher | class_teacher | parent | student
    role = db.Column(db.String(30), nullable=False, index=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=now, nullable=False)
    school = db.relationship("School")

    def set_password(self, pw):
        self.password_hash = bcrypt.generate_password_hash(pw).decode("utf-8")

    def check_password(self, pw):
        return bcrypt.check_password_hash(self.password_hash, pw)

    @property
    def full_name(self):
        return " ".join(p for p in (self.first_name, self.middle_name, self.last_name) if p)

    def to_dict(self):
        return {"id": self.id, "email": self.email, "phone": self.phone, "first_name": self.first_name,
                "last_name": self.last_name, "full_name": self.full_name, "role": self.role,
                "school_id": self.school_id, "school": self.school.to_dict(public=True) if self.school else None}


class AcademicYear(db.Model):
    __tablename__ = "academic_years"
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False, index=True)
    name = db.Column(db.String(20), nullable=False)
    is_current = db.Column(db.Boolean, default=False, nullable=False)
    __table_args__ = (db.UniqueConstraint("school_id", "name"),)


class Term(db.Model):
    __tablename__ = "terms"
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False, index=True)
    academic_year_id = db.Column(db.Integer, db.ForeignKey("academic_years.id"), nullable=False)
    name = db.Column(db.String(40), nullable=False)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    is_current = db.Column(db.Boolean, default=False, nullable=False)
    academic_year = db.relationship("AcademicYear")

    def to_dict(self):
        return {"id": self.id, "name": self.name, "year": self.academic_year.name,
                "start_date": self.start_date.isoformat() if self.start_date else None,
                "end_date": self.end_date.isoformat() if self.end_date else None,
                "is_current": self.is_current}


class AuditLog(db.Model):
    __tablename__ = "audit_logs"
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    action = db.Column(db.String(80), nullable=False)
    entity = db.Column(db.String(60))
    entity_id = db.Column(db.Integer)
    details = db.Column(db.JSON)
    ip_address = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, default=now, nullable=False)
