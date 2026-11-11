from datetime import datetime
from flask import Blueprint, request, g
from sqlalchemy import func

from ..extensions import db
from ..models import (PlatformModule, SchoolModule, LeadershipProfile, CareerPath,
                      StudentCareerInterest, School, Student, User)
from ..utils.responses import ok, err
from ..utils.security import roles_required, audit, ADMIN_ROLES

bp = Blueprint("modules", __name__, url_prefix="/api/modules")


def _ensure_default_modules():
    """Seed core modules if they do not exist."""
    defaults = [
        ("academics", "Academics & Financial Management", "Core school management: students, classes, results, fees, timetable.", True),
        ("zeroq", "ZeroQ", "Smart school queue management, appointments and service requests.", False),
        ("careergps", "CareerGPS", "Career exploration, course discovery and personalised guidance.", False),
    ]
    for code, name, desc, is_core in defaults:
        if not PlatformModule.query.filter_by(code=code).first():
            db.session.add(PlatformModule(code=code, name=name, description=desc, is_core=is_core))
    db.session.commit()


@bp.get("")
@roles_required("super_admin", *ADMIN_ROLES)
def list_modules():
    _ensure_default_modules()
    modules = PlatformModule.query.order_by(PlatformModule.is_core.desc(), PlatformModule.name).all()
    return ok([m.to_dict() for m in modules])


@bp.get("/school/<int:school_id>")
@roles_required("super_admin", *ADMIN_ROLES)
def school_modules(school_id):
    if g.user.role != "super_admin" and g.user.school_id != school_id:
        return err("Forbidden", 403)
    rows = SchoolModule.query.filter_by(school_id=school_id).all()
    return ok([r.to_dict() for r in rows])


@bp.put("/school/<int:school_id>/<code>")
@roles_required("super_admin")
def toggle_school_module(school_id, code):
    d = request.get_json(silent=True) or {}
    sm = SchoolModule.query.filter_by(school_id=school_id, module_code=code).first()
    if not sm:
        sm = SchoolModule(school_id=school_id, module_code=code)
        db.session.add(sm)
    sm.is_enabled = bool(d.get("is_enabled", True))
    if "settings" in d:
        sm.settings = d["settings"]
    if sm.is_enabled and not sm.enabled_at:
        sm.enabled_at = datetime.utcnow()
    audit("module.updated", "school_module", sm.id, {"code": code, "enabled": sm.is_enabled})
    db.session.commit()
    return ok(sm.to_dict())


# ---------- Leadership ----------
@bp.get("/leadership")
def get_leadership():
    profile = LeadershipProfile.query.first()
    if not profile:
        profile = LeadershipProfile(
            name="Rose Seko",
            designation="Company Owner",
            acknowledgement=(
                "Behind every meaningful innovation is a vision worth pursuing. "
                "We proudly acknowledge Rose Seko, whose leadership and vision contribute to "
                "building a smarter, more connected and accessible education ecosystem."
            ),
            photo_url="/brand/rose-seko.jpg",
            is_visible=True,
        )
        db.session.add(profile)
        db.session.commit()
    return ok(profile.to_dict())


@bp.put("/leadership")
@roles_required("super_admin")
def update_leadership():
    d = request.get_json(silent=True) or {}
    profile = LeadershipProfile.query.first()
    if not profile:
        profile = LeadershipProfile()
        db.session.add(profile)
    for k in ("name", "designation", "acknowledgement", "photo_url", "is_visible"):
        if k in d:
            setattr(profile, k, d[k])
    profile.updated_by = g.user.id
    audit("leadership.updated", "leadership_profile", profile.id)
    db.session.commit()
    return ok(profile.to_dict())


# ---------- CareerGPS ----------
@bp.get("/careergps/paths")
@roles_required(*ADMIN_ROLES, "teacher", "class_teacher", "student", "parent", "super_admin")
def list_career_paths():
    sid = request.args.get("school_id", type=int) or g.user.school_id
    if g.user.role != "super_admin" and sid != g.user.school_id:
        return err("Forbidden", 403)
    paths = CareerPath.query.filter_by(school_id=sid, is_active=True).order_by(CareerPath.title).all()
    return ok([p.to_dict() for p in paths])


@bp.post("/careergps/paths")
@roles_required("super_admin", *ADMIN_ROLES)
def create_career_path():
    d = request.get_json(silent=True) or {}
    sid = d.get("school_id") or g.user.school_id
    if g.user.role != "super_admin" and sid != g.user.school_id:
        return err("Forbidden", 403)
    path = CareerPath(
        school_id=sid,
        title=d.get("title", "").strip(),
        description=d.get("description"),
        category=d.get("category"),
        related_subjects=d.get("related_subjects") or [],
    )
    if not path.title:
        return err("Title is required", 422)
    db.session.add(path)
    audit("careergps.path.created", "career_path", None, {"title": path.title})
    db.session.commit()
    return ok(path.to_dict(), 201)


@bp.get("/careergps/student/<int:student_id>")
@roles_required("student", "parent", *ADMIN_ROLES, "teacher", "super_admin")
def student_career_interests(student_id):
    # Basic ownership check would go here in a fuller implementation
    interests = StudentCareerInterest.query.filter_by(student_id=student_id).all()
    return ok([i.to_dict() for i in interests])


@bp.post("/careergps/interest")
@roles_required("student", *ADMIN_ROLES)
def set_career_interest():
    d = request.get_json(silent=True) or {}
    student_id = d.get("student_id")
    path_id = d.get("career_path_id")
    if not student_id or not path_id:
        return err("student_id and career_path_id required", 422)
    interest = StudentCareerInterest.query.filter_by(
        student_id=student_id, career_path_id=path_id).first()
    if not interest:
        interest = StudentCareerInterest(
            school_id=g.user.school_id,
            student_id=student_id,
            career_path_id=path_id,
        )
        db.session.add(interest)
    interest.interest_level = d.get("interest_level", 3)
    interest.notes = d.get("notes")
    db.session.commit()
    return ok(interest.to_dict())
