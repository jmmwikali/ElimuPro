import io
import os
import stat
from datetime import timedelta

import pytest
from PIL import Image
from pypdf import PdfWriter

from app.extensions import db
from app.models import ApplicationDocument, AssessmentResult, AuditLog, Notification
from app.models.core import now
from app.routes.zeroq_onboarding import upload_limiter
from app.services import zeroq_documents as docs
from conftest import login

YEAR = now().year
GOOD_RESULT = {"assessment_year": YEAR, "candidate_number": "kj2026/0412", "subjects": [
    {"subject": "Mathematics", "result": "ME1"}, {"subject": "English", "result": "EE2"}]}


# ---------- file factories ----------
def pdf(pages=1, password=None):
    w = PdfWriter()
    for _ in range(pages):
        w.add_blank_page(width=595, height=842)
    if password:
        w.encrypt(password)
    out = io.BytesIO()
    w.write(out)
    return out.getvalue()


def png(size=(1200, 900), color=(30, 90, 160)):
    out = io.BytesIO()
    Image.new("RGB", size, color).save(out, "PNG")
    return out.getvalue()


def upload(client, headers, doc_type, data, name="scan.pdf"):
    return client.post("/api/v1/zeroq/my/documents", headers=headers, content_type="multipart/form-data",
                       data={"doc_type": doc_type, "file": (io.BytesIO(data), name)})


# ---------- fixtures ----------
@pytest.fixture(autouse=True)
def _reset_limiter():
    upload_limiter._hits.clear()


@pytest.fixture(autouse=True)
def _private_upload_dir(app, tmp_path):
    """Every test gets an empty private upload folder, so leftovers from other tests cannot hide a leak."""
    app.config["ZEROQ_UPLOAD_DIR"] = str(tmp_path)


@pytest.fixture()
def student2(client):
    return login(client, "baraka@mwangaza.demo")


@pytest.fixture()
def other_student(client):
    return login(client, "neema@tumaini.demo")


@pytest.fixture()
def reqs(client, admin):
    for code, label, required in (("birth_certificate", "Birth certificate", True), ("medical_form", "Medical form", True),
                                  ("passport_photo", "Passport photo", False)):
        r = client.post("/api/v1/zeroq/requirements", headers=admin, json={"doc_type": code, "label": label, "required": required})
        assert r.status_code == 201, r.get_json()


def submit_results(client, headers, body=None):
    client.put("/api/v1/zeroq/my/results", headers=headers, json=body or GOOD_RESULT)
    rid = client.get("/api/v1/zeroq/my/results", headers=headers).get_json()["data"]["results"][0]["id"]
    r = client.post(f"/api/v1/zeroq/my/results/{rid}/submit", headers=headers)
    assert r.status_code == 200, r.get_json()
    return rid


def act(client, headers, rid, action, **extra):
    return client.post(f"/api/v1/zeroq/review/results/{rid}/action", headers=headers, json={"action": action, **extra})


# =============================== KJSEA results ===============================
def test_results_draft_then_submit_with_honest_status_wording(client, student, admin):
    r = client.put("/api/v1/zeroq/my/results", headers=student, json=GOOD_RESULT)
    d = r.get_json()["data"]
    assert r.status_code == 200 and d["status"] == "draft" and d["candidate_number"] == "KJ2026/0412"
    assert "Nobody at the school can see it" in d["message"]
    assert client.get("/api/v1/zeroq/review/results", headers=admin).get_json()["data"] == []  # drafts are private

    sub = client.post(f"/api/v1/zeroq/my/results/{d['id']}/submit", headers=student).get_json()
    data = sub["data"]
    assert data["status"] == "awaiting_verification" and "not been verified" in data["message"].lower()
    assert "verified" not in data["status_label"].lower()
    assert [h["to"] for h in data["history"]] == ["draft", "submitted", "awaiting_verification"]


@pytest.mark.parametrize("body,field", [
    ({"assessment_year": 1999}, "assessment_year"), ({"assessment_year": "2026"}, "assessment_year"),
    ({"assessment_year": True}, "assessment_year"), ({"candidate_number": "x"}, "candidate_number"),
    ({"candidate_number": "has spaces!"}, "candidate_number"),
    ({"subjects": [{"subject": "Maths", "result": "ME1"}, {"subject": "maths", "result": "EE1"}]}, "subjects"),
    ({"subjects": [{"subject": "", "result": "ME1"}]}, "subjects"),
    ({"subjects": [{"subject": "Maths", "result": ""}]}, "subjects"),
    ({"subjects": ["Maths"]}, "subjects"),
    ({"subjects": [{"subject": f"Subject {i}", "result": "ME1"} for i in range(21)]}, "subjects"),
])
def test_results_validation(client, student, body, field):
    r = client.put("/api/v1/zeroq/my/results", headers=student, json={**GOOD_RESULT, **body})
    assert r.status_code == 422 and field in r.get_json()["errors"]
    assert AssessmentResult.query.count() == 0


def test_submit_needs_a_candidate_number_and_subjects(client, student):
    client.put("/api/v1/zeroq/my/results", headers=student, json={"assessment_year": YEAR, "subjects": []})
    rid = client.get("/api/v1/zeroq/my/results", headers=student).get_json()["data"]["results"][0]["id"]
    r = client.post(f"/api/v1/zeroq/my/results/{rid}/submit", headers=student)
    assert r.status_code == 422 and {"candidate_number", "subjects"} <= set(r.get_json()["errors"])


def test_submitted_results_cannot_be_edited_or_resubmitted(client, student):
    rid = submit_results(client, student)
    assert client.put("/api/v1/zeroq/my/results", headers=student, json=GOOD_RESULT).status_code == 409
    assert client.post(f"/api/v1/zeroq/my/results/{rid}/submit", headers=student).status_code == 409


def test_reviewer_verification_path_and_wording(client, student, admin):
    rid = submit_results(client, student)
    queue = client.get("/api/v1/zeroq/review/results?status=needs_action", headers=admin).get_json()["data"]
    assert [q["id"] for q in queue] == [rid]
    # can't skip straight to verified, and verifying needs a stated basis
    assert act(client, admin, rid, "verify", basis="Checked results slip").status_code == 409
    assert act(client, admin, rid, "start_review").status_code == 200
    assert act(client, admin, rid, "verify").status_code == 422
    done = act(client, admin, rid, "verify", basis="Compared with the results slip upload")
    d = done.get_json()["data"]
    assert done.status_code == 200 and d["status"] == "verified" and d["status_label"] == "Verified by school"
    assert "not an official placement" in d["message"]
    mine = client.get("/api/v1/zeroq/my/results", headers=student).get_json()["data"]["results"][0]
    assert mine["verification_basis"] == "Compared with the results slip upload"
    assert [h["to"] for h in mine["history"]] == ["draft", "submitted", "awaiting_verification",
                                                    "verification_in_progress", "verified"]
    assert Notification.query.filter_by(kind="results").count() >= 3
    assert AuditLog.query.filter_by(action="zeroq.results.verify").count() == 1


def test_request_info_then_student_corrects_and_resubmits(client, student, admin):
    rid = submit_results(client, student)
    assert act(client, admin, rid, "request_info").status_code == 422  # note required
    assert act(client, admin, rid, "request_info", note="Candidate number does not match your slip").status_code == 200
    mine = client.get("/api/v1/zeroq/my/results", headers=student).get_json()["data"]["results"][0]
    assert mine["status"] == "additional_information_required" and "does not match" in mine["review_note"] and mine["editable"]
    fixed = dict(GOOD_RESULT, candidate_number="KJ2026/0413")
    assert client.put("/api/v1/zeroq/my/results", headers=student, json=fixed).status_code == 200
    assert client.post(f"/api/v1/zeroq/my/results/{rid}/submit", headers=student).get_json()["data"]["status"] == "awaiting_verification"


def test_reject_fail_and_retry_rules(client, student, admin):
    rid = submit_results(client, student)
    assert act(client, admin, rid, "reject").status_code == 422
    act(client, admin, rid, "start_review")
    assert act(client, admin, rid, "fail").status_code == 422
    assert act(client, admin, rid, "fail", note="Could not confirm the candidate number").status_code == 200
    # a failed verification can be re-opened by a reviewer, a rejection cannot
    assert act(client, admin, rid, "start_review").get_json()["data"]["status"] == "verification_in_progress"
    assert act(client, admin, rid, "reject", note="Results do not match the slip").status_code == 200
    assert act(client, admin, rid, "start_review").status_code == 409
    assert act(client, admin, rid, "verify", basis="x").status_code == 409
    mine = client.get("/api/v1/zeroq/my/results", headers=student).get_json()["data"]["results"][0]
    assert mine["status"] == "rejected" and "do not match" in mine["review_note"] and not mine["editable"]


def test_results_are_private_to_the_student_and_their_school(client, student, student2, admin, admin2, other_student):
    rid = submit_results(client, student)
    assert client.get("/api/v1/zeroq/my/results", headers=student2).get_json()["data"]["results"] == []
    assert client.post(f"/api/v1/zeroq/my/results/{rid}/submit", headers=student2).status_code == 404
    assert client.get(f"/api/v1/zeroq/review/results/{rid}", headers=admin2).status_code == 404
    assert act(client, admin2, rid, "start_review").status_code == 404
    assert client.get("/api/v1/zeroq/review/results", headers=admin2).get_json()["data"] == []
    for headers in (student, other_student):
        assert client.get("/api/v1/zeroq/review/results", headers=headers).status_code == 403
    assert client.get("/api/v1/zeroq/my/results", headers=admin).status_code == 403
    assert client.get("/api/v1/zeroq/review/results").status_code == 401


def test_duplicate_candidate_number_is_flagged_for_the_reviewer(client, student, student2, admin):
    a = submit_results(client, student)
    submit_results(client, student2)
    detail = client.get(f"/api/v1/zeroq/review/results/{a}", headers=admin).get_json()["data"]
    assert detail["flags"] and "Baraka" in detail["flags"][0]


# =============================== requirements ===============================
def test_requirements_crud_and_isolation(client, admin, admin2, student, reqs):
    listed = client.get("/api/v1/zeroq/requirements", headers=admin).get_json()["data"]
    assert [r["doc_type"] for r in listed] == ["birth_certificate", "medical_form", "passport_photo"]
    dup = client.post("/api/v1/zeroq/requirements", headers=admin, json={"doc_type": "medical_form", "label": "X"})
    assert dup.status_code == 409
    for bad in ({"doc_type": "kjsea_results", "label": "x"}, {"doc_type": "Bad Code", "label": "x"}, {"doc_type": "ok_code", "label": ""}):
        assert client.post("/api/v1/zeroq/requirements", headers=admin, json=bad).status_code == 422
    rid = listed[1]["id"]
    assert client.patch(f"/api/v1/zeroq/requirements/{rid}", headers=admin, json={"is_active": False}).status_code == 200
    mine = client.get("/api/v1/zeroq/my/requirements", headers=student).get_json()["data"]
    assert [r["doc_type"] for r in mine["requirements"]] == ["birth_certificate", "passport_photo"]
    assert mine["kjsea"]["doc_type"] == "kjsea_results" and mine["configured"] is True
    assert client.patch(f"/api/v1/zeroq/requirements/{rid}", headers=admin2, json={"label": "hijack"}).status_code == 404
    assert client.get("/api/v1/zeroq/requirements", headers=admin2).get_json()["data"] == []
    assert client.get("/api/v1/zeroq/requirements", headers=student).status_code == 403


# =============================== uploads and automated checks ===============================
def test_good_pdf_passes_checks_but_is_not_approved_and_says_what_was_not_checked(client, student, admin, reqs, app):
    r = upload(client, student, "birth_certificate", pdf(2))
    d = r.get_json()["data"]
    assert r.status_code == 201 and d["status"] == "passed_automated_checks"
    assert "still has to look at it" in d["message"]
    assert d["version"] == 1 and d["content_type"] == "application/pdf"
    detail = client.get(f"/api/v1/zeroq/review/documents/{d['id']}", headers=admin).get_json()["data"]
    v = detail["verification"]
    assert {c["id"] for c in v["checks"]} >= {"file_type", "readable", "page_count", "duplicate_file", "metadata"}
    assert all(c["status"] in ("passed", "info") for c in v["checks"])
    assert {n["id"] for n in v["not_performed"]} >= {"text_extraction", "signature_stamp", "authenticity"}
    assert "does not make it genuine" in v["recommended_action"]
    assert "score" not in str(v).lower() and "confidence" not in str(v).lower()  # no invented probabilities
    assert [h["action"] for h in detail["history"]] == ["uploaded", "automated_checks"]


def test_file_is_stored_privately_with_a_random_name(client, student, reqs, app):
    d = upload(client, student, "birth_certificate", pdf(), name="../../etc/passwd.pdf").get_json()["data"]
    doc = db.session.get(ApplicationDocument, d["id"])
    assert doc.file_url == f"private:{doc.storage_key}" and doc.file_name == "etc_passwd.pdf"
    path = docs.file_path(doc)
    assert path and path.parent == docs._root().resolve() and "static" not in str(path)
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600
    assert len(doc.storage_key) == 52 and doc.storage_key.endswith(".pdf")
    assert "storage_key" not in str(d) and "private:" not in str(d)  # never exposed to the browser


def test_file_path_refuses_anything_outside_the_upload_folder(app):
    for key in ("../secret.pdf", "/etc/passwd", "a" * 48 + ".exe", "..\\x.pdf", None, ""):
        assert docs.file_path(ApplicationDocument(storage_key=key)) is None


@pytest.mark.parametrize("data,name", [
    (b"MZ\x90\x00 pretend this is a program", "form.pdf"),       # wrong bytes behind a PDF name
    (b"<html><script>alert(1)</script></html>", "form.png"),
    (b"GIF89a....", "form.gif"),
    (b"PK\x03\x04 zip", "form.docx"),
])
def test_unsupported_files_are_refused_and_not_stored(client, student, reqs, data, name):
    r = upload(client, student, "birth_certificate", data, name)
    assert r.status_code == 422 and "PDF, JPEG, PNG or WebP" in r.get_json()["message"]
    assert ApplicationDocument.query.count() == 0 and os.listdir(docs._root()) == []


def test_upload_input_validation(client, student, reqs):
    assert upload(client, student, "not_requested", pdf()).status_code == 422
    assert upload(client, student, "", pdf()).status_code == 422
    assert upload(client, student, "birth_certificate", b"").status_code == 422
    no_file = client.post("/api/v1/zeroq/my/documents", headers=student, data={"doc_type": "birth_certificate"},
                          content_type="multipart/form-data")
    assert no_file.status_code == 422


def test_inactive_requirement_cannot_be_uploaded(client, student, admin, reqs):
    rid = client.get("/api/v1/zeroq/requirements", headers=admin).get_json()["data"][1]["id"]
    client.patch(f"/api/v1/zeroq/requirements/{rid}", headers=admin, json={"is_active": False})
    assert upload(client, student, "medical_form", pdf()).status_code == 422


def test_oversize_files_are_refused(client, student, reqs, app):
    app.config["ZEROQ_MAX_UPLOAD_MB"] = 1
    r = upload(client, student, "birth_certificate", pdf() + b"0" * (1024 * 1024 + 10))
    assert r.status_code == 413 and "larger than 1 MB" in r.get_json()["message"]
    assert ApplicationDocument.query.count() == 0


def test_request_bodies_far_over_the_limit_get_a_json_413(client, student, reqs):
    r = upload(client, student, "birth_certificate", b"%PDF-" + b"0" * (15 * 1024 * 1024))
    assert r.status_code == 413 and r.get_json()["success"] is False


def test_corrupt_pdf_asks_for_a_corrected_copy(client, student, reqs):
    r = upload(client, student, "birth_certificate", b"%PDF-1.4\nthis is not really a pdf")
    d = r.get_json()["data"]
    assert r.status_code == 201 and d["status"] == "additional_information_required"
    assert any("damaged" in x for x in d["verification"]["reasons"])
    assert Notification.query.filter(Notification.title.like("%correction needed%")).count() == 1


def test_password_protected_pdf_is_flagged(client, student, reqs):
    d = upload(client, student, "birth_certificate", pdf(password="secret")).get_json()["data"]
    assert d["status"] == "additional_information_required"
    assert any("password-protected" in x for x in d["verification"]["reasons"])


def test_images_good_and_low_resolution(client, student, student2, reqs):
    good = upload(client, student, "passport_photo", png((1200, 900)), "photo.png").get_json()["data"]
    assert good["status"] == "passed_automated_checks"
    low = upload(client, student2, "passport_photo", png((300, 200)), "photo.png").get_json()["data"]
    assert low["status"] == "human_review_required" and any("700 px" in r for r in low["verification"]["reasons"])


def test_fake_image_with_png_header_is_unreadable(client, student, reqs):
    d = upload(client, student, "passport_photo", b"\x89PNG\r\n\x1a\n" + b"junk" * 50).get_json()["data"]
    assert d["status"] == "additional_information_required"


def test_same_file_for_another_student_goes_to_a_human(client, student, student2, admin, reqs):
    data = pdf(3)
    assert upload(client, student, "birth_certificate", data).get_json()["data"]["status"] == "passed_automated_checks"
    second = upload(client, student2, "birth_certificate", data).get_json()["data"]
    assert second["status"] == "human_review_required"
    detail = client.get(f"/api/v1/zeroq/review/documents/{second['id']}", headers=admin).get_json()["data"]
    assert any("different student" in r for r in detail["reasons"])
    assert "Achieng" not in str(second)  # the student is never told who


def test_reupload_creates_a_new_version_and_keeps_the_old_one(client, student, reqs):
    first = upload(client, student, "birth_certificate", b"%PDF-1.4 broken").get_json()["data"]
    second = upload(client, student, "birth_certificate", pdf()).get_json()["data"]
    assert (first["version"], second["version"]) == (1, 2)
    assert db.session.get(ApplicationDocument, second["id"]).supersedes_id == first["id"]
    listed = client.get("/api/v1/zeroq/my/documents", headers=student).get_json()["data"]["documents"]
    assert {d["version"] for d in listed} == {1, 2}


def test_unchanged_reupload_is_flagged(client, student, admin, reqs):
    data = pdf()
    first = upload(client, student, "birth_certificate", data).get_json()["data"]
    client.post(f"/api/v1/zeroq/review/documents/{first['id']}/action", headers=admin,
                json={"action": "request_correction", "note": "Scan is cut off"})
    again = upload(client, student, "birth_certificate", data).get_json()["data"]
    assert again["status"] == "human_review_required" and any("same file" in r for r in again["verification"]["reasons"])


def test_upload_rate_limit(client, student, reqs, app):
    app.config["ZEROQ_UPLOADS_PER_MINUTE"] = 2
    codes = [upload(client, student, "passport_photo", png((1200 + i, 900))).status_code for i in range(3)]
    assert codes == [201, 201, 429]


def test_uploads_are_for_students_only(client, admin, reqs):
    assert upload(client, admin, "birth_certificate", pdf()).status_code == 403
    assert upload(client, {}, "birth_certificate", pdf()).status_code == 401


# =============================== human review ===============================
def doc_action(client, headers, doc_id, action, note=None):
    return client.post(f"/api/v1/zeroq/review/documents/{doc_id}/action", headers=headers,
                       json={"action": action, **({"note": note} if note else {})})


def test_queue_puts_what_needs_a_human_first(client, student, student2, admin, reqs):
    ok_doc = upload(client, student, "birth_certificate", pdf()).get_json()["data"]
    flagged = upload(client, student2, "passport_photo", png((300, 200))).get_json()["data"]
    upload(client, student2, "medical_form", b"%PDF-1.4 broken")  # waiting on the student: not in the default queue
    queue = client.get("/api/v1/zeroq/review/documents", headers=admin).get_json()["data"]
    assert [q["id"] for q in queue] == [flagged["id"], ok_doc["id"]]
    assert queue[0]["student"] == "Baraka Mwangi" and queue[0]["application_reference"]
    everything = client.get("/api/v1/zeroq/review/documents?status=all", headers=admin).get_json()["data"]
    assert len(everything) == 3


def test_reviewer_decisions_are_recorded_and_the_student_is_told(client, student, admin, reqs):
    d = upload(client, student, "birth_certificate", pdf()).get_json()["data"]
    assert doc_action(client, admin, d["id"], "request_correction").status_code == 422     # note required
    assert doc_action(client, admin, d["id"], "reject").status_code == 422
    assert doc_action(client, admin, d["id"], "note", "Looks like a photocopy").get_json()["data"]["status"] == "passed_automated_checks"
    assert doc_action(client, admin, d["id"], "escalate", "Need the principal to confirm").get_json()["data"]["escalated"] is True
    approved = doc_action(client, admin, d["id"], "approve", "Original seen at the office").get_json()["data"]
    assert approved["status"] == "approved" and approved["reviewer"] == "Grace Wambui"
    assert [h["action"] for h in approved["history"]] == ["uploaded", "automated_checks", "note", "escalate", "approve"]
    assert approved["history"][-1]["by"] == "Grace Wambui" and approved["history"][0]["by"] != "System"
    titles = [n.title for n in Notification.query.filter_by(kind="document").all()]
    assert "Birth certificate: approved" in titles
    # upload + note + escalate + approve; the two refused attempts (missing notes) correctly leave no audit entry
    assert sorted(a.action for a in AuditLog.query.filter(AuditLog.action.like("zeroq.document.%"))) == [
        "zeroq.document.approve", "zeroq.document.escalate", "zeroq.document.note", "zeroq.document.uploaded"]
    # an approved document is final for the student too
    assert upload(client, student, "birth_certificate", pdf(2)).status_code == 409


def test_correction_loop(client, student, admin, reqs):
    d = upload(client, student, "medical_form", pdf()).get_json()["data"]
    r = doc_action(client, admin, d["id"], "request_correction", "Doctor's signature is missing")
    assert r.get_json()["data"]["status"] == "additional_information_required"
    mine = client.get("/api/v1/zeroq/my/documents", headers=student).get_json()["data"]["documents"][0]
    assert mine["status"] == "additional_information_required" and "signature" in mine["review_note"]
    assert doc_action(client, admin, d["id"], "approve").status_code == 409  # waiting on the student
    fixed = upload(client, student, "medical_form", pdf(2)).get_json()["data"]
    assert fixed["version"] == 2 and fixed["status"] == "passed_automated_checks"
    assert doc_action(client, admin, d["id"], "reject", "x").status_code == 409  # old version is no longer reviewable
    assert doc_action(client, admin, fixed["id"], "approve").status_code == 200


def test_rejecting_requires_a_reason_and_is_visible_to_the_student(client, student, admin, reqs):
    d = upload(client, student, "passport_photo", png()).get_json()["data"]
    assert doc_action(client, admin, d["id"], "reject", "Photo is of a different person").status_code == 200
    mine = client.get("/api/v1/zeroq/my/documents", headers=student).get_json()["data"]["documents"][0]
    assert mine["status"] == "rejected" and mine["review_note"] == "Photo is of a different person"


def test_unknown_review_action(client, student, admin, reqs):
    d = upload(client, student, "passport_photo", png()).get_json()["data"]
    assert doc_action(client, admin, d["id"], "delete_everything").status_code == 422


def test_review_summary_counts(client, student, student2, admin, admin2, reqs):
    upload(client, student, "birth_certificate", pdf())
    upload(client, student2, "passport_photo", png((300, 200)))
    upload(client, student2, "medical_form", b"%PDF-1.4 broken")
    submit_results(client, student)
    s = client.get("/api/v1/zeroq/review/summary", headers=admin).get_json()["data"]
    assert s["documents"]["total"] == 3 and s["documents"]["human_review_required"] == 1
    assert s["documents"]["passed_automated_checks"] == 1 and s["documents"]["corrections_outstanding"] == 1
    assert s["results"]["awaiting_verification"] == 1 and s["requirements_configured"] == 3
    other = client.get("/api/v1/zeroq/review/summary", headers=admin2).get_json()["data"]
    assert other["documents"]["total"] == 0 and other["results"]["submitted_total"] == 0


# =============================== access control and downloads ===============================
def test_documents_are_isolated_between_students_and_schools(client, student, student2, admin, admin2, other_student, reqs):
    d = upload(client, student, "birth_certificate", pdf()).get_json()["data"]
    assert client.get("/api/v1/zeroq/my/documents", headers=student2).get_json()["data"]["documents"] == []
    for headers in (student2, other_student):
        assert client.post(f"/api/v1/zeroq/my/documents/{d['id']}/link", headers=headers).status_code == 404
    assert client.get(f"/api/v1/zeroq/review/documents/{d['id']}", headers=admin2).status_code == 404
    assert doc_action(client, admin2, d["id"], "approve").status_code == 404
    assert client.post(f"/api/v1/zeroq/review/documents/{d['id']}/link", headers=admin2).status_code == 404
    assert client.get("/api/v1/zeroq/review/documents", headers=admin2).get_json()["data"] == []
    assert client.get("/api/v1/zeroq/review/documents", headers=student).status_code == 403
    assert client.get("/api/v1/zeroq/review/documents").status_code == 401
    # even a student's own file cannot be fetched by guessing a path: there is no static route
    assert client.get("/zeroq_uploads/anything.pdf").status_code == 404


def test_signed_download_link_serves_the_file_once_authorised(client, student, admin, reqs):
    data = pdf(2)
    d = upload(client, student, "birth_certificate", data, "my birth cert.pdf").get_json()["data"]
    for headers in (student, admin):
        path = client.post(f"/api/v1/zeroq/{'my' if headers is student else 'review'}/documents/{d['id']}/link",
                           headers=headers).get_json()["data"]["path"]
        r = client.get("/api/v1" + path)   # no Authorization header: the signed token is the authorisation
        assert r.status_code == 200 and r.data == data
        assert r.headers["Content-Type"] == "application/pdf" and "attachment" in r.headers["Content-Disposition"]
        assert r.headers["Cache-Control"] == "private, no-store" and r.headers["X-Content-Type-Options"] == "nosniff"
    assert AuditLog.query.filter_by(action="zeroq.document.downloaded").count() == 2


def test_download_links_expire_and_cannot_be_forged(client, student, reqs, app):
    d = upload(client, student, "birth_certificate", pdf()).get_json()["data"]
    path = client.post(f"/api/v1/zeroq/my/documents/{d['id']}/link", headers=student).get_json()["data"]["path"]
    token = path.split("token=")[1]
    assert client.get("/api/v1/zeroq/documents/file?token=" + token + "x").status_code == 410
    assert client.get("/api/v1/zeroq/documents/file").status_code == 410
    assert client.get("/api/v1/zeroq/documents/file?token=garbage").status_code == 410
    app.config["ZEROQ_LINK_TTL_SECONDS"] = -1
    assert client.get("/api/v1/zeroq/documents/file?token=" + token).status_code == 410
    app.config["ZEROQ_LINK_TTL_SECONDS"] = 300
    os.remove(docs.file_path(db.session.get(ApplicationDocument, d["id"])))
    assert client.get("/api/v1/zeroq/documents/file?token=" + token).status_code == 410  # file gone: no crash


def test_token_for_another_school_document_is_useless(client, student, admin2, reqs, app):
    """A token is bound to its document and school; changing the school in a re-signed token cannot reach other data."""
    d = upload(client, student, "birth_certificate", pdf()).get_json()["data"]
    doc = db.session.get(ApplicationDocument, d["id"])
    forged = docs._serializer().dumps({"d": doc.id, "u": 1, "s": doc.school_id + 1})
    assert client.get("/api/v1/zeroq/documents/file?token=" + forged).status_code == 410


# =============================== progress and notifications ===============================
def test_progress_tells_the_student_what_to_do_next(client, student, admin, reqs):
    p = client.get("/api/v1/zeroq/my/progress", headers=student).get_json()["data"]
    assert [s["key"] for s in p["stages"]] == ["application", "results", "documents", "decision"]
    states = {s["key"]: s["state"] for s in p["stages"]}
    assert states["results"] == "action" and states["documents"] == "action"
    assert p["documents"]["missing"] == ["Birth certificate", "Medical form"] and p["documents"]["required"] == 2
    assert p["next_action"].startswith("Enter and submit your KJSEA results")
    assert p["deadline"] is None and "No deadline" in p["deadline_note"] and p["latest_update"] is None

    submit_results(client, student)
    upload(client, student, "birth_certificate", pdf())
    bad = upload(client, student, "medical_form", b"%PDF-1.4 broken").get_json()["data"]
    p = client.get("/api/v1/zeroq/my/progress", headers=student).get_json()["data"]
    states = {s["key"]: s["state"] for s in p["stages"]}
    assert states["results"] == "waiting" and states["documents"] == "action"
    assert p["documents"]["received"] == 2 and p["documents"]["needs_correction"] == ["Medical form"]
    assert p["documents"]["awaiting_review"] == 1 and p["documents"]["checks_completed"] == 2
    assert "corrected copy of: Medical form" in p["next_action"] and p["latest_update"]["title"]

    upload(client, student, "medical_form", pdf(2))
    ids = [d["id"] for d in client.get("/api/v1/zeroq/my/documents", headers=student).get_json()["data"]["documents"]
           if d["status"] == "passed_automated_checks"]
    for i in ids:
        doc_action(client, admin, i, "approve")
    p = client.get("/api/v1/zeroq/my/progress", headers=student).get_json()["data"]
    assert {s["key"]: s["state"] for s in p["stages"]}["documents"] == "done"


def test_progress_when_the_school_has_not_listed_documents(client, student):
    p = client.get("/api/v1/zeroq/my/progress", headers=student).get_json()["data"]
    docs_stage = next(s for s in p["stages"] if s["key"] == "documents")
    assert docs_stage["state"] == "not_applicable" and "not listed required documents" in docs_stage["detail"]
    assert client.get("/api/v1/zeroq/my/requirements", headers=student).get_json()["data"]["configured"] is False


def test_notifications_list_and_mark_read(client, student, student2, reqs):
    submit_results(client, student)
    upload(client, student, "birth_certificate", pdf())
    page = client.get("/api/v1/zeroq/my/notifications", headers=student).get_json()
    titles = [n["title"] for n in page["data"]]
    assert "KJSEA results received" in titles and "Birth certificate received" in titles
    assert page["meta"]["unread"] == len(titles) == 3
    assert client.get("/api/v1/zeroq/my/notifications", headers=student2).get_json()["data"] == []  # not theirs
    assert client.post("/api/v1/zeroq/my/notifications/read", headers=student).get_json()["data"]["unread"] == 0
    assert client.get("/api/v1/zeroq/my/notifications", headers=student).get_json()["meta"]["unread"] == 0


def test_kjsea_results_slip_can_be_uploaded_without_school_configuration(client, student):
    d = upload(client, student, "kjsea_results", png((1400, 1000)), "slip.png").get_json()["data"]
    assert d["label"] == "KJSEA results slip" and d["status"] == "passed_automated_checks"


def test_a_failure_after_the_file_is_written_leaves_no_orphan_file(client, student, reqs, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("database went away")
    monkeypatch.setattr(docs, "run_checks", boom)
    client.application.config["PROPAGATE_EXCEPTIONS"] = False
    r = upload(client, student, "birth_certificate", pdf())
    assert r.status_code == 500
    assert os.listdir(docs._root()) == []
