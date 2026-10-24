import hashlib
import secrets
from datetime import date, datetime, timedelta

from flask import Blueprint, g, request
from sqlalchemy import or_

from ..extensions import db
from ..models import Student, StudentApplication, ZeroQPass, ZeroQScan
from ..services import zeroq_gate
from ..utils.responses import err, ok
from ..utils.security import ADMIN_ROLES, audit, roles_required
from ..utils.validation import paginate

bp = Blueprint("zeroq", __name__, url_prefix="/api/zeroq")
PASS_LIFETIME_DAYS = 30


def _digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _application_for_student():
    return StudentApplication.query.filter_by(
        applicant_user_id=g.user.id, school_id=g.user.school_id
    ).first()


def _record_scan(fingerprint, outcome, admission_pass=None):
    local_pass = admission_pass if admission_pass and admission_pass.school_id == g.user.school_id else None
    db.session.add(ZeroQScan(
        school_id=g.user.school_id,
        pass_id=local_pass.id if local_pass else None,
        scanned_by=g.user.id,
        token_fingerprint=fingerprint,
        outcome=outcome,
    ))
    audit("zeroq.scan", "admission_pass", local_pass.id if local_pass else None,
          {"outcome": outcome, "token_fingerprint": fingerprint})
    db.session.commit()


@bp.get("/my")
@roles_required("student")
def my_pass():
    application = _application_for_student()
    if not application or not application.student_id:
        return ok({"eligible": False, "ready": False, "blockers": [], "pass": None})
    current = ZeroQPass.query.filter_by(
        school_id=g.user.school_id, application_id=application.id
    ).order_by(ZeroQPass.created_at.desc()).first()
    eligible = application.status == "enrolled"
    blockers = zeroq_gate.pass_blockers(g.user, application, g.user.school) if eligible else []
    return ok({"eligible": eligible, "ready": eligible and not blockers, "blockers": [b["message"] for b in blockers],
               "pass": current.to_dict() if current else None})


@bp.post("/my/pass")
@roles_required("student")
def issue_pass():
    application = _application_for_student()
    if not application or not application.student_id or application.status != "enrolled":
        return err("A ZeroQ pass is available after your admission is approved", 409)
    # The school's pass rules are checked BEFORE anything is changed, so a blocked student keeps any pass they already hold.
    blockers = zeroq_gate.pass_blockers(g.user, application, g.user.school)
    if blockers:
        messages = [b["message"] for b in blockers]
        return err("Your admission pass is not available yet. " + " ".join(messages), 409, {"blockers": messages})
    previous = ZeroQPass.query.filter_by(
        school_id=g.user.school_id, application_id=application.id, revoked_at=None
    ).all()
    if any(item.used_at for item in previous):
        return err("A scanned pass cannot be replaced; contact your school", 409)

    expected_on = date.today()
    supplied_date = (request.get_json(silent=True) or {}).get("expected_on")
    if supplied_date:
        try:
            expected_on = date.fromisoformat(supplied_date)
        except (TypeError, ValueError):
            return err("Enter a valid expected arrival date", 422, {"expected_on": "Use YYYY-MM-DD"})
        if expected_on < date.today():
            return err("Expected arrival date cannot be in the past", 422,
                       {"expected_on": "Choose today or a future date"})

    for item in previous:
        item.revoked_at = datetime.utcnow()

    raw_token = secrets.token_urlsafe(32)
    token = f"ZEROQ1.{raw_token}"
    pass_record = ZeroQPass(
        school_id=g.user.school_id,
        application_id=application.id,
        student_id=application.student_id,
        reference=f"ZQ-{date.today().year}-{secrets.token_hex(4).upper()}",
        token_hash=_digest(token),
        expected_on=expected_on,
        expires_at=datetime.utcnow() + timedelta(days=PASS_LIFETIME_DAYS),
        issued_by=g.user.id,
    )
    db.session.add(pass_record)
    db.session.flush()
    audit("zeroq.pass.issued", "admission_pass", pass_record.id,
          {"reference": pass_record.reference, "expected_on": expected_on.isoformat()})
    db.session.commit()
    return ok({"pass": pass_record.to_dict(), "qr_value": token}, status=201,
              message="Your ZeroQ admission pass is ready")


@bp.post("/my/pass/revoke")
@roles_required("student")
def revoke_my_pass():
    application = _application_for_student()
    if not application:
        return err("No active ZeroQ pass was found", 404)
    current = ZeroQPass.query.filter_by(
        school_id=g.user.school_id, application_id=application.id, revoked_at=None
    ).order_by(ZeroQPass.created_at.desc()).first()
    if not current:
        return err("No active ZeroQ pass was found", 404)
    current.revoked_at = datetime.utcnow()
    audit("zeroq.pass.revoked", "admission_pass", current.id, {"reference": current.reference})
    db.session.commit()
    return ok(current.to_dict(), message="ZeroQ pass revoked")


@bp.get("/dashboard")
@roles_required(*ADMIN_ROLES)
def dashboard():
    school_id = g.user.school_id
    applications = StudentApplication.query.filter_by(school_id=school_id).filter(
        StudentApplication.status != "draft"
    ).all()
    passes = ZeroQPass.query.filter_by(school_id=school_id).order_by(ZeroQPass.created_at.desc()).all()
    today = date.today()
    scans_today = ZeroQScan.query.filter_by(school_id=school_id).filter(
        ZeroQScan.scanned_at >= datetime.combine(today, datetime.min.time())
    ).count()
    latest_by_application = {}
    for pass_record in passes:
        if pass_record.application_id not in latest_by_application:
            latest_by_application[pass_record.application_id] = pass_record
    latest = list(latest_by_application.values())
    return ok({
        "total_applicants": len(applications),
        "pending_admissions": sum(a.status in ("submitted", "under_review", "changes_required") for a in applications),
        "verified": sum(p.state() in ("ready", "checked_in") for p in latest),
        "rejected": sum(a.status == "rejected" for a in applications),
        "completed": sum(p.state() == "completed" for p in latest),
        "today_arrivals": sum(p.expected_on == today and p.state() not in ("revoked", "expired") for p in latest),
        "qr_scans_today": scans_today,
    })


@bp.get("/queue")
@roles_required(*ADMIN_ROLES)
def queue():
    term = (request.args.get("q") or "").strip()
    query = ZeroQPass.query.filter_by(school_id=g.user.school_id)
    requested_date = request.args.get("date")
    if requested_date:
        try:
            day = date.fromisoformat(requested_date)
        except ValueError:
            return err("Enter a valid queue date", 422, {"date": "Use YYYY-MM-DD"})
    else:
        day = date.today()
    query = query.filter(ZeroQPass.expected_on == day, ZeroQPass.revoked_at.is_(None),
                         ZeroQPass.expires_at > datetime.utcnow())
    if term:
        like = f"%{term}%"
        query = query.join(ZeroQPass.student).filter(or_(
            ZeroQPass.reference.like(like),
            Student.admission_number.like(like),
            Student.first_name.like(like),
            Student.last_name.like(like),
            Student.phone.like(like),
        ))
    items, meta = paginate(query.order_by(ZeroQPass.created_at.desc()))
    return ok([item.to_dict() for item in items], meta=meta)


@bp.post("/scan")
@roles_required(*ADMIN_ROLES)
def scan():
    payload = request.get_json(silent=True) or {}
    value = payload.get("qr_value")
    if not isinstance(value, str) or len(value) > 128 or not value.startswith("ZEROQ1."):
        fingerprint = _digest(value[:128] if isinstance(value, str) else "")
        _record_scan(fingerprint, "invalid")
        return ok({"valid": False, "status": "invalid", "message": "This is not a valid ZeroQ admission pass."})

    fingerprint = _digest(value)
    admission_pass = ZeroQPass.query.filter_by(token_hash=fingerprint).first()
    if not admission_pass:
        _record_scan(fingerprint, "invalid")
        return ok({"valid": False, "status": "invalid", "message": "This QR code could not be validated."})
    if admission_pass.school_id != g.user.school_id:
        _record_scan(fingerprint, "wrong_institution", admission_pass)
        return ok({"valid": False, "status": "wrong_institution",
                   "message": "This pass belongs to a different institution."})
    if admission_pass.revoked_at:
        _record_scan(fingerprint, "revoked", admission_pass)
        return ok({"valid": False, "status": "revoked", "message": "This admission pass has been revoked."})
    if admission_pass.expires_at <= datetime.utcnow():
        _record_scan(fingerprint, "expired", admission_pass)
        return ok({"valid": False, "status": "expired", "message": "This admission pass has expired."})
    if admission_pass.used_at:
        outcome = "completed" if admission_pass.completed_at else "already_used"
        _record_scan(fingerprint, outcome, admission_pass)
        message = "Admission is already complete." if admission_pass.completed_at else "This pass has already been scanned."
        return ok({"valid": False, "status": outcome, "message": message})

    if admission_pass.application.status != "enrolled" or admission_pass.student.status != "active":
        _record_scan(fingerprint, "admission_status", admission_pass)
        return ok({"valid": False, "status": "admission_status",
                   "message": "This admission is not currently eligible for check-in."})

    scanned_at = datetime.utcnow()
    claimed = ZeroQPass.query.filter_by(
        id=admission_pass.id, school_id=g.user.school_id, used_at=None, revoked_at=None
    ).filter(ZeroQPass.expires_at > scanned_at).update(
        {ZeroQPass.used_at: scanned_at}, synchronize_session=False
    )
    if not claimed:
        db.session.expire(admission_pass)
        admission_pass = db.session.get(ZeroQPass, admission_pass.id)
        if admission_pass.revoked_at:
            outcome, message = "revoked", "This admission pass has been revoked."
        elif admission_pass.expires_at <= scanned_at:
            outcome, message = "expired", "This admission pass has expired."
        else:
            outcome, message = "already_used", "This pass has already been scanned."
        _record_scan(fingerprint, outcome, admission_pass)
        return ok({"valid": False, "status": outcome, "message": message})
    db.session.expire(admission_pass)
    admission_pass = db.session.get(ZeroQPass, admission_pass.id)
    _record_scan(fingerprint, "verified", admission_pass)
    student = admission_pass.student
    return ok({
        "valid": True,
        "status": "verified",
        "message": "Pass verified. Confirm the student before completing admission.",
        "pass": admission_pass.to_dict(),
        "student": {
            "full_name": student.full_name,
            "admission_number": student.admission_number,
            "class": student.school_class.name if student.school_class else None,
            "institution": g.user.school.name,
            "admission_status": admission_pass.application.status,
            "document_count": len(admission_pass.application.documents),
            "requirements": zeroq_gate.requirements_status(admission_pass.application.applicant, admission_pass.application),
        },
    })


@bp.post("/<int:pass_id>/complete")
@roles_required(*ADMIN_ROLES)
def complete_admission(pass_id):
    admission_pass = ZeroQPass.query.filter_by(id=pass_id, school_id=g.user.school_id).first()
    if not admission_pass:
        return err("Admission pass not found", 404)
    if admission_pass.revoked_at or admission_pass.expires_at <= datetime.utcnow():
        return err("This admission pass is no longer valid", 409)
    if not admission_pass.used_at:
        return err("Scan and verify this admission pass before completing admission", 409)
    if admission_pass.completed_at:
        return err("Admission has already been completed", 409)
    admission_pass.completed_at = datetime.utcnow()
    audit("zeroq.admission.completed", "admission_pass", admission_pass.id,
          {"reference": admission_pass.reference})
    db.session.commit()
    return ok(admission_pass.to_dict(), message="Admission completed")


@bp.post("/<int:pass_id>/revoke")
@roles_required(*ADMIN_ROLES)
def revoke_pass(pass_id):
    admission_pass = ZeroQPass.query.filter_by(id=pass_id, school_id=g.user.school_id).first()
    if not admission_pass:
        return err("Admission pass not found", 404)
    if admission_pass.revoked_at:
        return err("Admission pass is already revoked", 409)
    admission_pass.revoked_at = datetime.utcnow()
    audit("zeroq.pass.revoked", "admission_pass", admission_pass.id,
          {"reference": admission_pass.reference})
    db.session.commit()
    return ok(admission_pass.to_dict(), message="Admission pass revoked")