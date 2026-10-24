"""What a student sees about their admission: where they are, what is missing, what happens next."""
from ..models import ApplicationDocument, AssessmentResult, DocumentRequirement, Notification
from . import zeroq_documents as docs
from . import zeroq_results as results

CORRECTION = ("additional_information_required", "rejected")
WAITING_ON_SCHOOL = ("uploaded", "processing", "passed_automated_checks", "human_review_required")


def requirement_rows(school_id):
    rows = DocumentRequirement.query.filter_by(school_id=school_id, is_active=True).order_by(
        DocumentRequirement.sort_order, DocumentRequirement.id).all()
    return rows


def latest_documents(application_id):
    latest = {}
    for doc in ApplicationDocument.query.filter_by(application_id=application_id).order_by(ApplicationDocument.version):
        latest[doc.doc_type] = doc
    return latest


def build(user, application):
    reqs = requirement_rows(application.school_id)
    latest = latest_documents(application.id)
    all_results = AssessmentResult.query.filter_by(student_user_id=user.id).order_by(
        AssessmentResult.assessment_year.desc()).all()
    result = all_results[0] if all_results else None

    required = [r for r in reqs if r.required]
    missing = [r.label for r in required if r.doc_type not in latest]
    needs_correction = [docs.label_for(t, reqs) for t, d in latest.items() if d.status in CORRECTION]
    awaiting = [d for d in latest.values() if d.status in WAITING_ON_SCHOOL]
    checks_completed = sum(1 for d in latest.values() if d.verification)
    approved_required = [r for r in required if latest.get(r.doc_type) and latest[r.doc_type].status == "approved"]

    # --- stages ---
    app_state = {"draft": "action", "changes_required": "action", "submitted": "waiting", "under_review": "waiting",
                 "approved": "done", "enrolled": "done", "rejected": "blocked"}[application.status]
    app_text = {"draft": "Complete and submit your application.",
                "changes_required": "Your school asked for changes to your application. Update it and submit again.",
                "rejected": "Your school did not accept this application."}.get(application.status)
    if result is None or result.status == "draft":
        res_state, res_text = "action", "Enter and submit your KJSEA results."
    elif result.status == "additional_information_required":
        res_state, res_text = "action", "Update your KJSEA results as your school asked, then submit again."
    elif result.status in ("rejected", "verification_failed"):
        res_state, res_text = "blocked", "Your school could not verify your results. Read the reason and contact them."
    elif result.status == "verified":
        res_state, res_text = "done", None
    else:
        res_state, res_text = "waiting", None
    if not reqs:
        doc_state, doc_text = "not_applicable", None
    elif missing or needs_correction:
        doc_state = "action"
        doc_text = (f"Upload: {', '.join(missing)}." if missing else f"Upload a corrected copy of: {', '.join(needs_correction)}.")
    elif awaiting:
        doc_state, doc_text = "waiting", None
    else:
        doc_state, doc_text = ("done", None) if required and len(approved_required) == len(required) else ("waiting", None)
    decision = {"approved": "done", "enrolled": "done", "rejected": "blocked"}.get(application.status, "waiting")

    stages = [
        {"key": "application", "label": "Application", "state": app_state, "detail": application.status.replace("_", " ")},
        {"key": "results", "label": "KJSEA results", "state": res_state,
         "detail": results.STATUS_LABELS[result.status] if result else "Not started"},
        {"key": "documents", "label": "Documents", "state": doc_state,
         "detail": ("Your school has not listed required documents yet" if not reqs else
                    f"{len(required) - len(missing)} of {len(required)} required received")},
        {"key": "decision", "label": "School decision", "state": decision,
         "detail": {"approved": "Approved", "enrolled": "Admitted", "rejected": "Not accepted"}.get(application.status, "Pending")},
    ]
    issues = ([app_text] if app_state in ("action", "blocked") and app_text else []) \
        + ([res_text] if res_state in ("action", "blocked") and res_text else []) \
        + ([doc_text] if doc_state == "action" and doc_text else [])
    nxt = issues[0] if issues else ("Nothing for you to do right now. Your school is reviewing." if any(
        s["state"] == "waiting" for s in stages) else "You are all set.")
    last = Notification.query.filter_by(user_id=user.id).order_by(Notification.id.desc()).first()
    return {
        "submission_date": application.submitted_at.isoformat() if application.submitted_at else None,
        "stages": stages, "next_action": nxt, "outstanding_issues": issues,
        "documents": {"required": len(required), "received": len(required) - len(missing), "missing": missing,
                      "needs_correction": needs_correction, "awaiting_review": len(awaiting),
                      "checks_completed": checks_completed},
        "latest_update": {"title": last.title, "body": last.body, "at": last.created_at.isoformat()} if last else None,
        "deadline": None, "deadline_note": "No deadline has been set for you in ZeroQ. Ask your school if one applies.",
    }
