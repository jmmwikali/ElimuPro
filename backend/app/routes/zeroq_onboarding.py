import re

from flask import Blueprint, g, request, send_file
from sqlalchemy import or_

from ..extensions import db
from ..models import (ApplicationDocument, AssessmentResult, AuditLog, DocumentRequirement, Notification,
                      StudentApplication, User)
from ..services import zeroq_documents as docs
from ..services import zeroq_progress as progress
from ..services import zeroq_results as results
from ..services.apex import RateLimiter
from ..utils.responses import err, ok
from ..utils.security import ADMIN_ROLES, audit, roles_required, scoped_get
from ..utils.validation import paginate

bp = Blueprint("zeroq_onboarding", __name__, url_prefix="/api/zeroq")
upload_limiter = RateLimiter()
SLUG = re.compile(r"^[a-z0-9_]{2,60}$")


def _application():
    return StudentApplication.query.filter_by(applicant_user_id=g.user.id, school_id=g.user.school_id).first()


def _my_result(result_id):
    return AssessmentResult.query.filter_by(id=result_id, student_user_id=g.user.id, school_id=g.user.school_id).first()


def _requirements(school_id, include_inactive=False):
    q = DocumentRequirement.query.filter_by(school_id=school_id)
    if not include_inactive:
        q = q.filter_by(is_active=True)
    return q.order_by(DocumentRequirement.sort_order, DocumentRequirement.id).all()


def _doc_type_info(school_id, doc_type):
    if doc_type == docs.KJSEA_DOC["doc_type"]:
        return docs.KJSEA_DOC["label"]
    req = DocumentRequirement.query.filter_by(school_id=school_id, doc_type=doc_type, is_active=True).first()
    return req.label if req else None


# =============================== student: KJSEA results ===============================
@bp.get("/my/results")
@roles_required("student")
def my_results():
    rows = AssessmentResult.query.filter_by(student_user_id=g.user.id).order_by(AssessmentResult.assessment_year.desc()).all()
    return ok({"results": [results.to_dict(r, with_history=True) for r in rows]})


@bp.put("/my/results")
@roles_required("student")
def save_results():
    payload = request.get_json(silent=True) or {}
    clean, errors = results.validate(payload, for_submit=False)
    if errors:
        return err("Please fix the highlighted fields", 422, errors)
    row = AssessmentResult.query.filter_by(student_user_id=g.user.id, assessment_year=clean["assessment_year"]).first()
    if row and row.status not in results.STUDENT_EDITABLE:
        return err("These results are already with your school and can no longer be edited", 409)
    if not row:
        row = AssessmentResult(school_id=g.user.school_id, student_user_id=g.user.id,
                               assessment_year=clean["assessment_year"], subjects=[])
        db.session.add(row)
        db.session.flush()
        db.session.add(results.AssessmentResultEvent(result_id=row.id, school_id=row.school_id, to_status="draft",
                                                      actor_user_id=g.user.id, actor_role="student", note="Draft started"))
    row.candidate_number, row.subjects = clean["candidate_number"], clean["subjects"]
    db.session.commit()
    return ok(results.to_dict(row, with_history=True), message="Draft saved")


@bp.post("/my/results/<int:result_id>/submit")
@roles_required("student")
def submit_results(result_id):
    row = _my_result(result_id)
    if not row:
        return err("Results not found", 404)
    if row.status not in results.STUDENT_EDITABLE:
        return err("These results have already been submitted", 409)
    clean, errors = results.validate({"assessment_year": row.assessment_year, "candidate_number": row.candidate_number,
                                      "subjects": row.subjects}, for_submit=True)
    if errors:
        return err("Complete your results before submitting", 422, errors)
    row.candidate_number, row.subjects = clean["candidate_number"], clean["subjects"]
    results.submit(row, g.user)
    audit("zeroq.results.submitted", "assessment_result", row.id, {"year": row.assessment_year})
    db.session.commit()
    return ok(results.to_dict(row, with_history=True), message="Results submitted. Your school has not verified them yet.")


# =============================== student: documents ===============================
@bp.get("/my/requirements")
@roles_required("student")
def my_requirements():
    application = _application()
    latest = progress.latest_documents(application.id) if application else {}
    reqs = _requirements(g.user.school_id)
    items = [dict(r.to_dict(), current=docs.to_dict(latest[r.doc_type], r.label) if r.doc_type in latest else None) for r in reqs]
    kj = dict(docs.KJSEA_DOC, current=docs.to_dict(latest["kjsea_results"], docs.KJSEA_DOC["label"])
              if "kjsea_results" in latest else None)
    return ok({"requirements": items, "kjsea": kj,
               "configured": bool(reqs), "max_mb": docs.current_app.config["ZEROQ_MAX_UPLOAD_MB"]})


@bp.get("/my/documents")
@roles_required("student")
def my_documents():
    application = _application()
    if not application:
        return ok({"documents": []})
    reqs = _requirements(g.user.school_id, include_inactive=True)
    rows = ApplicationDocument.query.filter_by(application_id=application.id).order_by(ApplicationDocument.id.desc()).all()
    return ok({"documents": [docs.to_dict(d, docs.label_for(d.doc_type, reqs), with_events=True) for d in rows]})


@bp.post("/my/documents")
@roles_required("student")
def upload_document():
    application = _application()
    if not application:
        return err("No application found", 404)
    doc_type = (request.form.get("doc_type") or "").strip()
    label = _doc_type_info(g.user.school_id, doc_type)
    if not label:
        return err("Choose one of the documents your school asks for", 422, {"doc_type": "Not a requested document"})
    upload = request.files.get("file")
    if not upload:
        return err("Choose a file to upload", 422, {"file": "Required"})
    try:
        doc = docs.process_upload(g.user, application, doc_type, label, upload, upload_limiter)
    except docs.UploadError as e:
        return err(str(e), e.status, {"file": str(e)})
    audit("zeroq.document.uploaded", "application_document", doc.id,
          {"doc_type": doc_type, "version": doc.version, "outcome": doc.status})
    db.session.commit()
    return ok(docs.to_dict(doc, label, with_events=True), 201, message=docs.STUDENT_MESSAGES[doc.status])


def _link_response(doc):
    token = docs.make_link_token(doc, g.user)
    audit("zeroq.document.link", "application_document", doc.id)
    db.session.commit()
    return ok({"path": f"/zeroq/documents/file?token={token}",
               "expires_in": docs.current_app.config["ZEROQ_LINK_TTL_SECONDS"]})


@bp.post("/my/documents/<int:doc_id>/link")
@roles_required("student")
def my_document_link(doc_id):
    doc = scoped_get(ApplicationDocument, doc_id)
    if not doc or doc.application.applicant_user_id != g.user.id:
        return err("Document not found", 404)
    return _link_response(doc)


@bp.get("/documents/file")
def download_document():
    """No login header: the short-lived signed token IS the authorisation (it names the document, the user and the school)."""
    payload = docs.read_link_token(request.args.get("token", ""))
    doc = ApplicationDocument.query.filter_by(id=payload["d"], school_id=payload["s"]).first() if payload else None
    path = docs.file_path(doc) if doc else None
    if not path:
        return err("This download link is invalid or has expired. Open the document again to get a new one.", 410)
    db.session.add(AuditLog(school_id=doc.school_id, user_id=payload["u"], action="zeroq.document.downloaded",
                            entity="application_document", entity_id=doc.id, ip_address=request.remote_addr))
    db.session.commit()
    response = send_file(path, mimetype=doc.content_type, as_attachment=True, download_name=doc.file_name, max_age=0)
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


# =============================== student: progress and notifications ===============================
@bp.get("/my/progress")
@roles_required("student")
def my_progress():
    application = _application()
    if not application:
        return err("No application found", 404)
    return ok(progress.build(g.user, application))


@bp.get("/my/notifications")
@roles_required("student")
def my_notifications():
    q = Notification.query.filter_by(user_id=g.user.id).order_by(Notification.id.desc())
    items, meta = paginate(q, default_per_page=20)
    unread = Notification.query.filter_by(user_id=g.user.id, read_at=None).count()
    return ok([n.to_dict() for n in items], meta=dict(meta, unread=unread))


@bp.post("/my/notifications/read")
@roles_required("student")
def read_notifications():
    Notification.query.filter_by(user_id=g.user.id, read_at=None).update({Notification.read_at: results.now()})
    db.session.commit()
    return ok({"unread": 0})


# =============================== school: document requirements ===============================
@bp.get("/requirements")
@roles_required(*ADMIN_ROLES)
def list_requirements():
    return ok([r.to_dict() for r in _requirements(g.user.school_id, include_inactive=True)])


def _requirement_fields(payload, creating):
    clean, errors = {}, {}
    if creating or "label" in payload:
        label = payload.get("label").strip() if isinstance(payload.get("label"), str) else ""
        if not label or len(label) > 120:
            errors["label"] = "Enter a name (120 characters at most)"
        clean["label"] = label
    if "instructions" in payload:
        text = payload.get("instructions")
        if text is not None and (not isinstance(text, str) or len(text) > 2000):
            errors["instructions"] = "Instructions must be 2000 characters or fewer"
        clean["instructions"] = (text or "").strip() or None
    for flag in ("required", "is_active"):
        if flag in payload:
            if not isinstance(payload[flag], bool):
                errors[flag] = "Must be true or false"
            clean[flag] = payload[flag]
    if "sort_order" in payload:
        order = payload["sort_order"]
        if isinstance(order, bool) or not isinstance(order, int) or not 0 <= order <= 1000:
            errors["sort_order"] = "Whole number from 0 to 1000"
        clean["sort_order"] = order
    return clean, errors


@bp.post("/requirements")
@roles_required(*ADMIN_ROLES)
def create_requirement():
    payload = request.get_json(silent=True) or {}
    doc_type = payload.get("doc_type") if isinstance(payload.get("doc_type"), str) else ""
    clean, errors = _requirement_fields(payload, creating=True)
    if not SLUG.match(doc_type) or doc_type == docs.KJSEA_DOC["doc_type"]:
        errors["doc_type"] = "Use 2 to 60 lowercase letters, numbers or underscores (not 'kjsea_results', which is built in)"
    if errors:
        return err("Please fix the highlighted fields", 422, errors)
    if DocumentRequirement.query.filter_by(school_id=g.user.school_id, doc_type=doc_type).first():
        return err("Your school already has a requirement with that code", 409, {"doc_type": "Already exists"})
    row = DocumentRequirement(school_id=g.user.school_id, doc_type=doc_type, **clean)
    db.session.add(row)
    db.session.flush()
    audit("zeroq.requirement.created", "document_requirement", row.id, {"doc_type": doc_type})
    db.session.commit()
    return ok(row.to_dict(), 201)


@bp.patch("/requirements/<int:req_id>")
@roles_required(*ADMIN_ROLES)
def update_requirement(req_id):
    row = scoped_get(DocumentRequirement, req_id)
    if not row:
        return err("Requirement not found", 404)
    clean, errors = _requirement_fields(request.get_json(silent=True) or {}, creating=False)
    if errors or not clean:
        return err("Please fix the highlighted fields" if errors else "Nothing to update", 422, errors or None)
    for k, v in clean.items():
        setattr(row, k, v)
    audit("zeroq.requirement.updated", "document_requirement", row.id, clean)
    db.session.commit()
    return ok(row.to_dict())


# =============================== school: pass rules ===============================
SETTING_FIELDS = {"require_verified_results": "zeroq_require_results", "require_approved_documents": "zeroq_require_documents"}


def _settings(school):
    return {api_name: getattr(school, column) for api_name, column in SETTING_FIELDS.items()}


@bp.get("/settings")
@roles_required(*ADMIN_ROLES)
def get_settings():
    return ok(_settings(g.user.school))


@bp.patch("/settings")
@roles_required(*ADMIN_ROLES)
def update_settings():
    payload = request.get_json(silent=True) or {}
    changes = {k: payload[k] for k in SETTING_FIELDS if k in payload}
    if not changes:
        return err("Nothing to update", 422)
    bad = {k: "Must be true or false" for k, v in changes.items() if not isinstance(v, bool)}
    if bad:
        return err("Please fix the highlighted fields", 422, bad)
    before = _settings(g.user.school)
    for k, v in changes.items():
        setattr(g.user.school, SETTING_FIELDS[k], v)
    audit("zeroq.settings.updated", "school", g.user.school_id, {"before": before, "after": _settings(g.user.school)})
    db.session.commit()
    return ok(_settings(g.user.school))


# =============================== school: review ===============================
def _person(user_id):
    user = db.session.get(User, user_id) if user_id else None
    return user.full_name if user else None


@bp.get("/review/summary")
@roles_required(*ADMIN_ROLES)
def review_summary():
    sid = g.user.school_id
    by_result = dict(db.session.query(AssessmentResult.status, db.func.count()).filter_by(school_id=sid)
                     .filter(AssessmentResult.status != "draft").group_by(AssessmentResult.status).all())
    latest = {}
    for d in ApplicationDocument.query.filter_by(school_id=sid).filter(ApplicationDocument.storage_key.isnot(None)).order_by(
            ApplicationDocument.version):
        latest[(d.application_id, d.doc_type)] = d
    by_doc = {}
    for d in latest.values():
        by_doc[d.status] = by_doc.get(d.status, 0) + 1
    return ok({
        "results": {"awaiting_verification": by_result.get("awaiting_verification", 0),
                    "verification_in_progress": by_result.get("verification_in_progress", 0),
                    "additional_information_required": by_result.get("additional_information_required", 0),
                    "verified": by_result.get("verified", 0), "submitted_total": sum(by_result.values())},
        "documents": {"total": len(latest), "passed_automated_checks": by_doc.get("passed_automated_checks", 0),
                      "human_review_required": by_doc.get("human_review_required", 0),
                      "corrections_outstanding": by_doc.get("additional_information_required", 0),
                      "approved": by_doc.get("approved", 0), "rejected": by_doc.get("rejected", 0),
                      "escalated": sum(1 for d in latest.values() if d.escalated_at and d.status == "human_review_required")},
        "requirements_configured": DocumentRequirement.query.filter_by(school_id=sid, is_active=True).count(),
    })


def _candidate_clash(result):
    if not result.candidate_number:
        return []
    others = AssessmentResult.query.filter(
        AssessmentResult.school_id == result.school_id, AssessmentResult.assessment_year == result.assessment_year,
        AssessmentResult.candidate_number == result.candidate_number, AssessmentResult.id != result.id,
        AssessmentResult.status != "draft").all()
    return [o.student.full_name for o in others]


def _result_row(r, detail=False):
    clash = _candidate_clash(r)
    d = results.to_dict(r, with_history=detail, for_reviewer=True)
    d.update(student=r.student.full_name, student_phone=r.student.phone if detail else None,
             flags=[f"The same candidate number was submitted by: {', '.join(clash)}"] if clash else [],
             review_note=r.review_note)
    return d


@bp.get("/review/results")
@roles_required(*ADMIN_ROLES)
def review_results():
    q = AssessmentResult.query.filter_by(school_id=g.user.school_id).filter(AssessmentResult.status != "draft")
    status = request.args.get("status")
    if status == "needs_action":
        q = q.filter(AssessmentResult.status.in_(("awaiting_verification", "verification_in_progress", "verification_failed")))
    elif status in results.STATUS_LABELS:
        q = q.filter_by(status=status)
    items, meta = paginate(q.order_by(AssessmentResult.submitted_at.asc()))
    return ok([_result_row(r) for r in items], meta=meta)


@bp.get("/review/results/<int:result_id>")
@roles_required(*ADMIN_ROLES)
def review_result_detail(result_id):
    row = scoped_get(AssessmentResult, result_id)
    if not row or row.status == "draft":
        return err("Results not found", 404)
    return ok(_result_row(row, detail=True))


@bp.post("/review/results/<int:result_id>/action")
@roles_required(*ADMIN_ROLES)
def review_result_action(result_id):
    row = scoped_get(AssessmentResult, result_id)
    if not row or row.status == "draft":
        return err("Results not found", 404)
    payload = request.get_json(silent=True) or {}
    note = payload.get("note").strip() if isinstance(payload.get("note"), str) else None
    basis = payload.get("basis").strip()[:200] if isinstance(payload.get("basis"), str) else None
    problem = results.review(row, g.user, payload.get("action"), note or None, basis or None)
    if problem:
        db.session.rollback()
        return err(problem, 409 if "Cannot" in problem else 422)
    audit(f"zeroq.results.{payload['action']}", "assessment_result", row.id, {"note": note, "basis": basis})
    db.session.commit()
    return ok(_result_row(row, detail=True))


def _doc_row(d, reqs, detail=False):
    label = docs.label_for(d.doc_type, reqs)
    out = docs.to_dict(d, label, with_events=detail, for_reviewer=True)
    app = d.application
    out.update(student=" ".join(p for p in (app.first_name, app.last_name) if p), application_reference=app.reference_no,
               escalated=d.escalated_at is not None, reviewer=_person(d.reviewed_by),
               reasons=(d.verification or {}).get("reasons", []))
    if detail:
        out["history"] = [dict(h, by=_person(e.actor_user_id) or h["by"]) for h, e in zip(out["history"], d.events)]
        out["versions"] = [{"id": v.id, "version": v.version, "status": v.status, "uploaded_at": v.uploaded_at.isoformat()}
                           for v in ApplicationDocument.query.filter_by(application_id=d.application_id, doc_type=d.doc_type)
                           .order_by(ApplicationDocument.version.desc())]
    return out


@bp.get("/review/documents")
@roles_required(*ADMIN_ROLES)
def review_documents():
    reqs = _requirements(g.user.school_id, include_inactive=True)
    q = ApplicationDocument.query.filter_by(school_id=g.user.school_id).filter(ApplicationDocument.storage_key.isnot(None))
    term = (request.args.get("q") or "").strip()
    if term:
        like = f"%{term}%"
        q = q.join(StudentApplication, StudentApplication.id == ApplicationDocument.application_id).filter(or_(
            StudentApplication.reference_no.like(like), StudentApplication.first_name.like(like),
            StudentApplication.last_name.like(like)))
    rows, newest = q.order_by(ApplicationDocument.version).all(), {}
    for d in rows:  # only the newest version of each document needs a decision
        newest[(d.application_id, d.doc_type)] = d
    items = list(newest.values())
    status = request.args.get("status", "needs_action")
    if status == "needs_action":
        items = [d for d in items if d.status in ("human_review_required", "passed_automated_checks")]
    elif status in docs.STATUS_LABELS:
        items = [d for d in items if d.status == status]
    items.sort(key=lambda d: (docs.REVIEW_PRIORITY[d.status], 0 if d.escalated_at else 1, d.uploaded_at))
    return ok([_doc_row(d, reqs) for d in items], meta={"total": len(items)})


@bp.get("/review/documents/<int:doc_id>")
@roles_required(*ADMIN_ROLES)
def review_document_detail(doc_id):
    doc = scoped_get(ApplicationDocument, doc_id)
    if not doc or not doc.storage_key:
        return err("Document not found", 404)
    return ok(_doc_row(doc, _requirements(g.user.school_id, include_inactive=True), detail=True))


@bp.post("/review/documents/<int:doc_id>/action")
@roles_required(*ADMIN_ROLES)
def review_document_action(doc_id):
    doc = scoped_get(ApplicationDocument, doc_id)
    if not doc or not doc.storage_key:
        return err("Document not found", 404)
    payload = request.get_json(silent=True) or {}
    note = payload.get("note").strip() if isinstance(payload.get("note"), str) else None
    reqs = _requirements(g.user.school_id, include_inactive=True)
    problem = docs.review(doc, g.user, payload.get("action"), note or None, docs.label_for(doc.doc_type, reqs))
    if problem:
        db.session.rollback()
        return err(problem, 409 if ("Cannot" in problem or "newer version" in problem) else 422)
    audit(f"zeroq.document.{payload['action']}", "application_document", doc.id, {"note": note, "status": doc.status})
    db.session.commit()
    return ok(_doc_row(doc, reqs, detail=True))


@bp.post("/review/documents/<int:doc_id>/link")
@roles_required(*ADMIN_ROLES)
def review_document_link(doc_id):
    doc = scoped_get(ApplicationDocument, doc_id)
    if not doc or not doc.storage_key:
        return err("Document not found", 404)
    return _link_response(doc)
