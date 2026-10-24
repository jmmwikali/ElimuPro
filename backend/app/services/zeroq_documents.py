"""ZeroQ admission documents: private storage, upload validation, automated checks, reviewer actions.

What the automated checks DO: confirm the file type from its bytes, confirm it opens, flag password-protected or
corrupt PDFs, report page count, flag low-resolution photos, and flag a file already uploaded for another
student. What they do NOT do (and say so in every result): read the text (no OCR service is configured), check fields,
names or dates, detect signatures or stamps, compare against templates or official records, or judge authenticity.
Passing the checks therefore never means "approved": a person still approves.
"""
import hashlib
import io
import os
import re
import secrets
from pathlib import Path

from flask import current_app
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.utils import secure_filename

from ..extensions import db
from ..models import ApplicationDocument, DocumentEvent
from ..models.core import now
from . import notifications

STATUS_LABELS = {
    "uploaded": "Uploaded",
    "processing": "Processing",
    "passed_automated_checks": "Passed automated checks",
    "human_review_required": "Human review required",
    "additional_information_required": "Correction needed",
    "rejected": "Rejected",
    "approved": "Approved",
}
STUDENT_MESSAGES = {
    "uploaded": "Received.",
    "processing": "Being checked.",
    "passed_automated_checks": "Passed the automated file checks. A reviewer at your school still has to look at it.",
    "human_review_required": "A reviewer at your school needs to look at this document.",
    "additional_information_required": "Please upload a corrected copy. The reason is shown below.",
    "rejected": "Your school could not accept this document. The reason is shown below.",
    "approved": "Approved by your school.",
}
KJSEA_DOC = {"doc_type": "kjsea_results", "label": "KJSEA results slip", "required": False,
             "instructions": "Upload a clear photo or scan of your results document. A school reviewer compares it with the "
                             "results you entered."}
ACCEPTED = {"pdf": "application/pdf", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}
EXT = {"pdf": ".pdf", "jpeg": ".jpg", "png": ".png", "webp": ".webp"}
MIN_SHORT_SIDE = 700   # pixels: a heuristic for "readable on a phone-camera photo", not a quality guarantee
LONG_PDF_PAGES = 25
MAX_IMAGE_PIXELS = 60_000_000
# What needs a reviewer to act, most urgent first
REVIEW_PRIORITY = {"human_review_required": 0, "passed_automated_checks": 1, "additional_information_required": 2,
                   "uploaded": 3, "processing": 3, "rejected": 4, "approved": 5}
NOT_PERFORMED = [
    ("text_extraction", "Reading the document text (OCR)", "No OCR service is configured."),
    ("required_fields", "Required fields are filled in", "Needs text extraction."),
    ("cross_document_consistency", "Names, dates and reference numbers match across documents", "Needs text extraction."),
    ("signature_stamp", "Signature or stamp is present", "No signature or stamp detection is configured."),
    ("template_and_records", "Comparison with school templates or official records", "No reference data is connected."),
    ("authenticity", "Judging whether the document is genuine or edited", "Automated tools cannot prove authenticity; "
                                                                        "a person decides."),
]


class UploadError(Exception):
    def __init__(self, message, status=422):
        super().__init__(message)
        self.status = status


# ---------- storage ----------
def _root():
    root = Path(current_app.config["ZEROQ_UPLOAD_DIR"])
    root.mkdir(parents=True, exist_ok=True)
    return root


def save_file(data, kind):
    key = secrets.token_hex(24) + EXT[kind]  # random, unguessable, no user-controlled path parts
    path = _root() / key
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as fh:
        fh.write(data)
    return key


def file_path(doc):
    """Resolve the stored file, refusing anything that could escape the upload folder."""
    if not doc.storage_key or not re.fullmatch(r"[0-9a-f]{48}\.(pdf|jpg|png|webp)", doc.storage_key):
        return None
    path = (_root() / doc.storage_key).resolve()
    return path if path.parent == _root().resolve() and path.is_file() else None


# ---------- signed, time-limited download links ----------
def _serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="zeroq-document-link")


def make_link_token(doc, user):
    return _serializer().dumps({"d": doc.id, "u": user.id, "s": doc.school_id})


def read_link_token(token):
    """Returns the payload, or None when the token is forged or older than the configured lifetime."""
    try:
        return _serializer().loads(token, max_age=current_app.config["ZEROQ_LINK_TTL_SECONDS"])
    except (BadSignature, SignatureExpired):
        return None


# ---------- inspecting an upload ----------
def sniff(data):
    if data.startswith(b"%PDF-"):
        return "pdf"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


def _check(check_id, label, status, detail):
    return {"id": check_id, "label": label, "status": status, "detail": detail}


def _inspect_pdf(data):
    from pypdf import PdfReader
    checks, readable = [], False
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            checks.append(_check("readable", "File opens", "failed", "The PDF is password-protected."))
            return checks, False
        pages = len(reader.pages)
        if pages < 1:
            raise ValueError("no pages")
        reader.pages[0].mediabox  # touch the first page: broken page trees fail here
        readable = True
        checks.append(_check("readable", "File opens", "passed", "The PDF opened normally."))
        checks.append(_check("page_count", "Page count", "warning" if pages > LONG_PDF_PAGES else "passed",
                             f"{pages} page(s)." + (" Unusually long for an admission form." if pages > LONG_PDF_PAGES else "")))
        meta = reader.metadata
        producer = str(getattr(meta, "producer", "") or "")[:80]
        creator = str(getattr(meta, "creator", "") or "")[:80]
        checks.append(_check("metadata", "File metadata (information only)", "info",
                             f"Created with: {creator or 'not recorded'}; produced by: {producer or 'not recorded'}. "
                             "Metadata is easy to change, so its presence or absence proves nothing."))
    except Exception:  # pypdf raises many types for damaged files
        checks.append(_check("readable", "File opens", "failed", "The PDF is damaged or could not be read."))
    return checks, readable


def _inspect_image(data):
    from PIL import Image, UnidentifiedImageError
    Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS
    try:
        with Image.open(io.BytesIO(data)) as im:
            im.verify()
        with Image.open(io.BytesIO(data)) as im:
            width, height = im.size
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, SyntaxError, ValueError):
        return [_check("readable", "File opens", "failed", "The image is damaged or could not be read.")], False
    short = min(width, height)
    checks = [_check("readable", "File opens", "passed", f"The image opened normally ({width} x {height} pixels)."),
              _check("resolution", "Resolution (rough guide to legibility)", "warning" if short < MIN_SHORT_SIDE else "passed",
                     f"Shortest side is {short} px." + (f" Under {MIN_SHORT_SIDE} px, so small print may be hard to read."
                                                      if short < MIN_SHORT_SIDE else ""))]
    return checks, True


def run_checks(data, kind, digest, document):
    """Returns the structured verification result. `document` is excluded from the duplicate search."""
    checks = [_check("file_type", "File type", "passed", f"Confirmed from the file's contents: {ACCEPTED[kind]}.")]
    inspected, readable = _inspect_pdf(data) if kind == "pdf" else _inspect_image(data)
    checks += inspected

    if readable:
        other = ApplicationDocument.query.filter(
            ApplicationDocument.school_id == document.school_id, ApplicationDocument.sha256 == digest,
            ApplicationDocument.application_id != document.application_id).first()
        same = ApplicationDocument.query.filter(
            ApplicationDocument.application_id == document.application_id, ApplicationDocument.sha256 == digest,
            ApplicationDocument.id != document.id).first()
        if other:
            checks.append(_check("duplicate_file", "File not used by another student", "warning",
                                 "This exact file was already uploaded for a different student at your school."))
        elif same:
            checks.append(_check("duplicate_file", "File changed since the last upload", "warning",
                                 "This is the same file as an earlier upload. If a correction was requested, it may be unchanged."))
        else:
            checks.append(_check("duplicate_file", "File not used by another student", "passed", "No identical file found."))

    failed = [c for c in checks if c["status"] == "failed"]
    warnings = [c for c in checks if c["status"] == "warning"]
    if failed:
        outcome, human = "additional_information_required", False
        action = "Ask the student for a readable, unprotected copy."
    elif warnings:
        outcome, human = "human_review_required", True
        action = "Inspect the document, then approve, request a correction or reject it."
    else:
        outcome, human = "passed_automated_checks", False
        action = "Open the document and decide. Passing these checks does not make it genuine or complete."
    return {
        "checks": checks,
        "not_performed": [{"id": i, "label": l, "reason": r} for i, l, r in NOT_PERFORMED],
        "outcome": outcome, "human_review_required": human,
        "reasons": [c["detail"] for c in failed + warnings],
        "recommended_action": action,
    }


# ---------- events and student wording ----------
def add_event(doc, action, from_status, to_status, actor=None, note=None):
    db.session.add(DocumentEvent(
        document_id=doc.id, school_id=doc.school_id, action=action, from_status=from_status, to_status=to_status,
        actor_user_id=actor.id if actor else None, actor_role=actor.role if actor else "system", note=note))


def label_for(doc_type, requirements):
    if doc_type == KJSEA_DOC["doc_type"]:
        return KJSEA_DOC["label"]
    return next((r.label for r in requirements if r.doc_type == doc_type), doc_type.replace("_", " ").title())


def to_dict(doc, label, with_events=False, for_reviewer=False):
    d = doc.to_dict()
    d.update(label=label, status_label=STATUS_LABELS[doc.status], message=STUDENT_MESSAGES[doc.status],
             can_replace=doc.status != "approved")
    if doc.status in ("additional_information_required", "rejected", "approved"):
        d["review_note"] = doc.review_note
    if doc.verification:
        d["verification"] = doc.verification if for_reviewer else {
            "reasons": doc.verification.get("reasons", []), "recommended_action": None,
            "checks": [{"label": c["label"], "status": c["status"]} for c in doc.verification.get("checks", [])
                       if c["status"] != "info"]}
    if with_events:
        d["history"] = [{"action": e.action, "to": STATUS_LABELS.get(e.to_status), "by": "System" if not e.actor_user_id
                         else e.actor_role.replace("_", " "), "note": e.note, "at": e.created_at.isoformat()}
                        for e in doc.events]
    return d


def process_upload(user, application, doc_type, label, upload, rate_limiter):
    """Validate, store, check and record one upload. Raises UploadError for anything that should not be stored."""
    if not rate_limiter.allow(f"zeroq-upload:{user.id}", current_app.config["ZEROQ_UPLOADS_PER_MINUTE"]):
        raise UploadError("You are uploading too quickly. Please wait a minute and try again.", 429)
    max_bytes = current_app.config["ZEROQ_MAX_UPLOAD_MB"] * 1024 * 1024
    data = upload.read(max_bytes + 1)
    if not data:
        raise UploadError("That file is empty.")
    if len(data) > max_bytes:
        raise UploadError(f"That file is larger than {current_app.config['ZEROQ_MAX_UPLOAD_MB']} MB.", 413)
    kind = sniff(data)
    if not kind:
        raise UploadError("Upload a PDF, JPEG, PNG or WebP file. Other file types are not accepted.")

    latest = ApplicationDocument.query.filter_by(application_id=application.id, doc_type=doc_type).order_by(
        ApplicationDocument.version.desc()).first()
    if latest and latest.status == "approved":
        raise UploadError("This document is already approved. Contact your school if it needs to change.", 409)

    digest = hashlib.sha256(data).hexdigest()
    key = save_file(data, kind)
    try:
        safe_name = secure_filename(upload.filename or "") or f"document{EXT[kind]}"
        doc = ApplicationDocument(
            school_id=application.school_id, application_id=application.id, doc_type=doc_type, file_name=safe_name[:255],
            file_url=f"private:{key}", storage_key=key, content_type=ACCEPTED[kind], size_bytes=len(data), sha256=digest,
            version=(latest.version + 1) if latest else 1, supersedes_id=latest.id if latest else None,
            uploaded_by=user.id, status="uploaded")
        db.session.add(doc)
        db.session.flush()
        add_event(doc, "uploaded", None, "uploaded", user, "Version %d" % doc.version)
        notifications.notify(user.id, doc.school_id, "document", f"{label} received",
                             "We are checking the file. Your school still has to review it.")

        doc.status = "processing"
        result = run_checks(data, kind, digest, doc)
        doc.verification = result
        doc.status = result["outcome"]
        performed = [c for c in result["checks"] if c["status"] != "info"]
        add_event(doc, "automated_checks", "processing", doc.status, None,
                  f"{len(performed)} automated checks ran; {len(result['not_performed'])} kinds of checking were not performed.")
        messages = {"passed_automated_checks": "The file checks passed. A reviewer at your school will look at it next.",
                    "human_review_required": "A reviewer at your school needs to look at it.",
                    "additional_information_required": "Please upload a corrected copy: " + " ".join(result["reasons"])}
        notifications.notify(user.id, doc.school_id, "document", f"{label}: {STATUS_LABELS[doc.status].lower()}",
                             messages[doc.status])
    except BaseException:
        # Nothing is left behind if recording the upload fails after the file was written.
        (_root() / key).unlink(missing_ok=True)
        raise
    return doc


DOC_ACTIONS = {
    # action -> (statuses it may start from, resulting status or None for "unchanged", note required)
    "approve": (("passed_automated_checks", "human_review_required"), "approved", False),
    "request_correction": (("passed_automated_checks", "human_review_required"), "additional_information_required", True),
    "reject": (("passed_automated_checks", "human_review_required", "additional_information_required"), "rejected", True),
    "escalate": (("passed_automated_checks", "human_review_required"), "human_review_required", True),
    "note": (tuple(STATUS_LABELS), None, True),
}


def review(doc, reviewer, action, note, label):
    """Apply a reviewer decision. Returns an error string, or None when applied."""
    rule = DOC_ACTIONS.get(action)
    if not rule:
        return "Unknown action"
    allowed_from, to_status, note_required = rule
    newest = ApplicationDocument.query.filter_by(application_id=doc.application_id, doc_type=doc.doc_type).order_by(
        ApplicationDocument.version.desc()).first()
    if newest.id != doc.id:
        return "A newer version of this document exists; review that one."
    if doc.status not in allowed_from:
        return f"Cannot {action.replace('_', ' ')} a document that is '{STATUS_LABELS[doc.status]}'"
    if note_required and not note:
        return "A note is required"
    previous = doc.status
    if to_status:
        doc.status = to_status
        doc.reviewed_by, doc.reviewed_at, doc.review_note = reviewer.id, now(), note
    if action == "escalate":
        doc.escalated_at = now()
    add_event(doc, action, previous, doc.status, reviewer, note)
    student_id = doc.application.applicant_user_id
    if action in ("approve", "request_correction", "reject"):
        notifications.notify(student_id, doc.school_id, "document", f"{label}: {STATUS_LABELS[doc.status].lower()}",
                             note or STUDENT_MESSAGES[doc.status])
    return None
