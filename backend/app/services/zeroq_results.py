"""KJSEA results a student submits to their school, and the review workflow around them.

A submission is the STUDENT's claim. It only becomes "verified" when a school reviewer records that they checked it,
and the wording shown to the student always says which of the two it is. No official placement or results
source is connected, so nothing here is ever described as officially verified by the examination authority.
"""
import re
from datetime import date

from ..extensions import db
from ..models import AssessmentResultEvent
from ..models.core import now
from . import notifications

STATUS_LABELS = {
    "draft": "Draft",
    "submitted": "Submitted",
    "awaiting_verification": "Awaiting verification",
    "verification_in_progress": "Verification in progress",
    "additional_information_required": "Additional information required",
    "verified": "Verified by school",
    "rejected": "Rejected",
    "verification_failed": "Verification failed",
}
STUDENT_MESSAGES = {
    "draft": "Saved as a draft. Nobody at the school can see it until you submit it.",
    "submitted": "Received. Your school has not checked these results yet.",
    "awaiting_verification": "Received and waiting in your school's verification queue. It has not been verified yet.",
    "verification_in_progress": "A school reviewer has started checking your results. It is not verified yet.",
    "additional_information_required": "Your school needs more information before it can verify your results. Update them and submit again.",
    "verified": "A reviewer at your school checked these results. This is a school check, not an official placement.",
    "rejected": "Your school could not accept these results. The reason is shown below.",
    "verification_failed": "The school could not complete verification. The reason is shown below; the school may try again.",
}
STUDENT_EDITABLE = ("draft", "additional_information_required")
MAX_SUBJECTS = 20
CANDIDATE_RE = re.compile(r"^[A-Za-z0-9/\-]{4,30}$")

# action -> (statuses it may start from, resulting status, note required, basis required)
REVIEWER_ACTIONS = {
    "start_review": (("awaiting_verification", "verification_failed"), "verification_in_progress", False, False),
    "request_info": (("awaiting_verification", "verification_in_progress"), "additional_information_required", True, False),
    "verify": (("verification_in_progress",), "verified", False, True),
    "reject": (("awaiting_verification", "verification_in_progress"), "rejected", True, False),
    "fail": (("verification_in_progress",), "verification_failed", True, False),
}


def _text(value, low, high):
    value = re.sub(r"\s+", " ", value).strip() if isinstance(value, str) else ""
    return value if low <= len(value) <= high and not re.search(r"[\x00-\x1f\x7f]", value) else None


def validate(payload, for_submit):
    """Returns (clean, errors). Checks structure and internal consistency only; it cannot know the official grading scale."""
    clean, errors = {}, {}
    year = payload.get("assessment_year")
    this_year = date.today().year
    if isinstance(year, bool) or not isinstance(year, int) or not this_year - 5 <= year <= this_year + 1:
        errors["assessment_year"] = f"Enter the year you sat the assessment ({this_year - 5} to {this_year + 1})"
    else:
        clean["assessment_year"] = year

    cand = payload.get("candidate_number")
    cand = cand.strip() if isinstance(cand, str) else cand
    if cand in (None, ""):
        if for_submit:
            errors["candidate_number"] = "Enter your assessment or candidate number"
        clean["candidate_number"] = None
    elif not isinstance(cand, str) or not CANDIDATE_RE.match(cand):
        errors["candidate_number"] = "Use 4 to 30 letters, numbers, slashes or hyphens"
    else:
        clean["candidate_number"] = cand.upper()

    rows = payload.get("subjects")
    subjects, seen = [], set()
    if not isinstance(rows, list):
        rows = []
    if len(rows) > MAX_SUBJECTS:
        errors["subjects"] = f"At most {MAX_SUBJECTS} subjects"
    else:
        for i, row in enumerate(rows):
            subject = _text(row.get("subject"), 2, 80) if isinstance(row, dict) else None
            result = _text(row.get("result"), 1, 20) if isinstance(row, dict) else None
            if not subject or not result:
                errors["subjects"] = f"Row {i + 1}: enter both the subject and the result you received"
                break
            if subject.lower() in seen:
                errors["subjects"] = f"'{subject}' is listed twice"
                break
            seen.add(subject.lower())
            subjects.append({"subject": subject, "result": result})
    if for_submit and not subjects and "subjects" not in errors:
        errors["subjects"] = "Add at least one subject and its result"
    clean["subjects"] = subjects
    return clean, errors


def to_dict(result, with_history=False, for_reviewer=False):
    d = {"id": result.id, "assessment_year": result.assessment_year, "candidate_number": result.candidate_number,
         "subjects": result.subjects or [], "status": result.status, "status_label": STATUS_LABELS[result.status],
         "message": STUDENT_MESSAGES[result.status], "editable": result.status in STUDENT_EDITABLE,
         "submitted_at": result.submitted_at.isoformat() if result.submitted_at else None,
         "verified_at": result.verified_at.isoformat() if result.verified_at else None,
         "updated_at": result.updated_at.isoformat()}
    if result.status in ("additional_information_required", "rejected", "verification_failed", "verified"):
        d["review_note"] = result.review_note
    if result.status == "verified":
        d["verification_basis"] = result.verification_basis
    if with_history:
        d["history"] = [{"from": e.from_status, "to": e.to_status, "to_label": STATUS_LABELS[e.to_status],
                         "by": "System" if e.actor_user_id is None else
                         ("You" if not for_reviewer and e.actor_role == "student" else e.actor_role.replace("_", " ")),
                         "note": e.note if (for_reviewer or e.actor_role != "student") else None,
                         "at": e.created_at.isoformat()} for e in result.events]
    return d


def transition(result, to_status, actor, note=None):
    """Move a result to a new status, record the history, and tell the student about review outcomes."""
    previous = result.status
    result.status = to_status
    db.session.add(AssessmentResultEvent(
        result_id=result.id, school_id=result.school_id, from_status=previous, to_status=to_status,
        actor_user_id=actor.id if actor else None, actor_role=actor.role if actor else "system", note=note))
    if actor and actor.role != "student":
        notifications.notify(result.student_user_id, result.school_id, "results",
                             f"KJSEA results: {STATUS_LABELS[to_status].lower()}", note or STUDENT_MESSAGES[to_status])


def submit(result, student):
    """draft or corrected -> submitted -> awaiting verification (there is no automatic pre-check, so it queues straight away)."""
    result.submitted_at = now()
    transition(result, "submitted", student)
    transition(result, "awaiting_verification", None, "Added to the school's verification queue")
    notifications.notify(student.id, result.school_id, "results", "KJSEA results received",
                         "Your school has not verified them yet. You will be told when that changes.")


def review(result, reviewer, action, note, basis):
    """Returns an error string, or None when the action was applied."""
    rule = REVIEWER_ACTIONS.get(action)
    if not rule:
        return "Unknown action"
    allowed_from, to_status, note_required, basis_required = rule
    if result.status not in allowed_from:
        return f"Cannot {action.replace('_', ' ')} results that are '{STATUS_LABELS[result.status]}'"
    if note_required and not note:
        return "A note is required so the student knows why"
    if basis_required and not basis:
        return "Say what you checked these results against before verifying them"
    result.review_note = note  # always the latest reviewer note, so a stale reason is never shown with a new status
    if to_status == "verified":
        result.verified_at, result.verified_by, result.verification_basis = now(), reviewer.id, basis
    transition(result, to_status, reviewer, note)
    return None
