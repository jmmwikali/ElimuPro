"""Rules for when a student may be issued a ZeroQ admission pass.

A pass is proof the school accepts the student's arrival, so beyond being enrolled the school can require that the
student's KJSEA results have been verified by school staff and that every required document has been approved by a
person. Both rules are on by default and each school can switch them off (for example the results rule for grades
that do not sit the KJSEA). Automated checks never satisfy a rule: only a reviewer's approval does.
"""
from ..models import ApplicationDocument, AssessmentResult
from . import zeroq_progress

RESULT_PENDING = ("submitted", "awaiting_verification", "verification_in_progress")
DOC_WAITING = ("uploaded", "processing", "passed_automated_checks", "human_review_required")


def _latest_result(user_id):
    return AssessmentResult.query.filter_by(student_user_id=user_id).order_by(AssessmentResult.assessment_year.desc()).first()


def _results_message(result):
    if result is None or result.status == "draft":
        return "Submit your KJSEA results so your school can verify them."
    if result.status in RESULT_PENDING:
        return "Your KJSEA results are waiting for your school to verify them."
    if result.status == "additional_information_required":
        return "Your school needs more information about your KJSEA results."
    if result.status in ("rejected", "verification_failed"):
        return "Your school could not verify your KJSEA results."
    return None  # verified


def _document_message(label, doc):
    if doc is None:
        return f"{label}: upload it so your school can approve it."
    if doc.status == "approved":
        return None
    if doc.status in DOC_WAITING:
        return f"{label}: waiting for your school to approve it."
    if doc.status == "additional_information_required":
        return f"{label}: upload a corrected copy."
    return f"{label}: your school could not accept it."  # rejected


def pass_blockers(applicant, application, school):
    """What still stands between this student and a pass, as plain sentences. Empty means they may be issued one."""
    blockers = []
    if school.zeroq_require_results:
        message = _results_message(_latest_result(applicant.id))
        if message:
            blockers.append({"kind": "results", "message": message})
    if school.zeroq_require_documents:
        latest = zeroq_progress.latest_documents(application.id)
        for requirement in zeroq_progress.requirement_rows(application.school_id):
            if requirement.required:
                message = _document_message(requirement.label, latest.get(requirement.doc_type))
                if message:
                    blockers.append({"kind": "document", "message": message})
    return blockers


def requirements_status(applicant, application):
    """Facts for the person scanning a pass. Reported whether or not the school enforces the rules."""
    result = _latest_result(applicant.id)
    latest = zeroq_progress.latest_documents(application.id)
    required = [r for r in zeroq_progress.requirement_rows(application.school_id) if r.required]
    return {
        "results_verified": bool(result and result.status == "verified"),
        "documents_approved": all(latest.get(r.doc_type) is not None and latest[r.doc_type].status == "approved" for r in required),
        "required_documents": len(required),
    }
