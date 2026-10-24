"""The ZeroQ pass waits for verified results and approved documents (both rules on by default, per school)."""
import io

import pytest
from pypdf import PdfWriter

from app.extensions import db
from app.models import AuditLog, School, ZeroQPass
from app.models.core import now
from app.routes.zeroq_onboarding import upload_limiter
from conftest import login

YEAR = now().year
RESULT = {"assessment_year": YEAR, "candidate_number": "KJ2026/0412", "subjects": [{"subject": "Mathematics", "result": "ME1"}]}


@pytest.fixture(autouse=True)
def _fresh(app, tmp_path):
    upload_limiter._hits.clear()
    app.config["ZEROQ_UPLOAD_DIR"] = str(tmp_path)


def pdf():
    w = PdfWriter()
    w.add_blank_page(width=595, height=842)
    out = io.BytesIO()
    w.write(out)
    return out.getvalue()


def require_doc(client, admin, code="birth_certificate", label="Birth certificate", required=True):
    r = client.post("/api/v1/zeroq/requirements", headers=admin, json={"doc_type": code, "label": label, "required": required})
    assert r.status_code == 201, r.get_json()
    return r.get_json()["data"]["id"]


def upload(client, headers, code="birth_certificate"):
    r = client.post("/api/v1/zeroq/my/documents", headers=headers, content_type="multipart/form-data",
                    data={"doc_type": code, "file": (io.BytesIO(pdf()), "scan.pdf")})
    assert r.status_code == 201, r.get_json()
    return r.get_json()["data"]["id"]


def approve_doc(client, admin, doc_id):
    assert client.post(f"/api/v1/zeroq/review/documents/{doc_id}/action", headers=admin, json={"action": "approve"}).status_code == 200


def verify_results(client, student, admin):
    client.put("/api/v1/zeroq/my/results", headers=student, json=RESULT)
    rid = client.get("/api/v1/zeroq/my/results", headers=student).get_json()["data"]["results"][0]["id"]
    client.post(f"/api/v1/zeroq/my/results/{rid}/submit", headers=student)
    for action, extra in (("start_review", {}), ("verify", {"basis": "Checked the results slip"})):
        assert client.post(f"/api/v1/zeroq/review/results/{rid}/action", headers=admin, json={"action": action, **extra}).status_code == 200
    return rid


def mine(client, student):
    return client.get("/api/v1/zeroq/my", headers=student).get_json()["data"]


def issue(client, student):
    return client.post("/api/v1/zeroq/my/pass", headers=student, json={})


def test_rules_are_on_by_default(app, client):
    super_admin = login(client, "super@elimupro.demo")
    r = client.post("/api/v1/schools", headers=super_admin, json={
        "name": "New Academy", "slug": "new-academy", "admin_email": "head@new.demo", "admin_password": "Strong123"})
    school = db.session.get(School, r.get_json()["data"]["id"])
    assert school.zeroq_require_results is True and school.zeroq_require_documents is True


def test_no_pass_until_results_are_verified(client, student, admin):
    state = mine(client, student)
    assert state["eligible"] is True and state["ready"] is False
    assert state["blockers"] == ["Submit your KJSEA results so your school can verify them."]
    blocked = issue(client, student)
    assert blocked.status_code == 409 and "not available yet" in blocked.get_json()["message"]
    assert blocked.get_json()["errors"]["blockers"] == state["blockers"]
    assert ZeroQPass.query.count() == 0

    client.put("/api/v1/zeroq/my/results", headers=student, json=RESULT)
    rid = client.get("/api/v1/zeroq/my/results", headers=student).get_json()["data"]["results"][0]["id"]
    client.post(f"/api/v1/zeroq/my/results/{rid}/submit", headers=student)
    assert mine(client, student)["blockers"] == ["Your KJSEA results are waiting for your school to verify them."]
    client.post(f"/api/v1/zeroq/review/results/{rid}/action", headers=admin, json={"action": "request_info", "note": "Number is unclear"})
    assert "needs more information" in mine(client, student)["blockers"][0]
    # the student corrects and resubmits; only then can the reviewer reject
    client.put("/api/v1/zeroq/my/results", headers=student, json=dict(RESULT, candidate_number="KJ2026/0413"))
    client.post(f"/api/v1/zeroq/my/results/{rid}/submit", headers=student)
    client.post(f"/api/v1/zeroq/review/results/{rid}/action", headers=admin, json={"action": "reject", "note": "Does not match"})
    assert "could not verify" in mine(client, student)["blockers"][0]
    assert issue(client, student).status_code == 409


def test_verified_results_open_the_gate_when_no_documents_are_required(client, student, admin):
    verify_results(client, student, admin)
    state = mine(client, student)
    assert state["ready"] is True and state["blockers"] == []
    r = issue(client, student)
    assert r.status_code == 201 and r.get_json()["data"]["qr_value"].startswith("ZEROQ1.")


def test_required_documents_must_be_approved_by_a_person(client, student, admin):
    verify_results(client, student, admin)
    require_doc(client, admin)
    assert mine(client, student)["blockers"] == ["Birth certificate: upload it so your school can approve it."]
    doc = upload(client, student)  # passes the automated checks, which is NOT approval
    assert mine(client, student)["blockers"] == ["Birth certificate: waiting for your school to approve it."]
    assert issue(client, student).status_code == 409
    client.post(f"/api/v1/zeroq/review/documents/{doc}/action", headers=admin, json={"action": "request_correction", "note": "Cut off"})
    assert mine(client, student)["blockers"] == ["Birth certificate: upload a corrected copy."]
    fixed = upload(client, student)
    client.post(f"/api/v1/zeroq/review/documents/{fixed}/action", headers=admin, json={"action": "reject", "note": "Wrong person"})
    assert mine(client, student)["blockers"] == ["Birth certificate: your school could not accept it."]
    final = upload(client, student)
    approve_doc(client, admin, final)
    assert mine(client, student)["ready"] is True and issue(client, student).status_code == 201


def test_optional_and_hidden_documents_never_block(client, student, admin):
    verify_results(client, student, admin)
    require_doc(client, admin, "passport_photo", "Passport photo", required=False)
    hidden = require_doc(client, admin, "medical_form", "Medical form")
    client.patch(f"/api/v1/zeroq/requirements/{hidden}", headers=admin, json={"is_active": False})
    assert mine(client, student)["ready"] is True


def test_every_missing_requirement_is_listed_together(client, student, admin):
    require_doc(client, admin, "birth_certificate", "Birth certificate")
    require_doc(client, admin, "medical_form", "Medical form")
    blockers = mine(client, student)["blockers"]
    assert len(blockers) == 3 and blockers[0].startswith("Submit your KJSEA")
    assert {b.split(":")[0] for b in blockers[1:]} == {"Birth certificate", "Medical form"}


def test_a_school_can_switch_each_rule_off(client, student, admin, admin2):
    require_doc(client, admin)
    assert client.get("/api/v1/zeroq/settings", headers=admin).get_json()["data"] == {
        "require_verified_results": True, "require_approved_documents": True}
    r = client.patch("/api/v1/zeroq/settings", headers=admin, json={"require_verified_results": False})
    assert r.status_code == 200 and r.get_json()["data"]["require_verified_results"] is False
    assert [b.split(":")[0] for b in mine(client, student)["blockers"]] == ["Birth certificate"]  # documents still enforced
    client.patch("/api/v1/zeroq/settings", headers=admin, json={"require_approved_documents": False})
    assert mine(client, student)["ready"] is True and issue(client, student).status_code == 201
    log = AuditLog.query.filter_by(action="zeroq.settings.updated").all()
    assert len(log) == 2 and log[0].details["before"]["require_verified_results"] is True
    # another school is untouched
    assert client.get("/api/v1/zeroq/settings", headers=admin2).get_json()["data"]["require_verified_results"] is True


@pytest.mark.parametrize("body", [{}, {"require_verified_results": "no"}, {"require_approved_documents": 1}, {"unknown": True}])
def test_settings_validation(client, admin, body):
    assert client.patch("/api/v1/zeroq/settings", headers=admin, json=body).status_code == 422


def test_only_school_admins_change_the_rules(client, student, admin2):
    for headers in (student, {}):
        assert client.get("/api/v1/zeroq/settings", headers=headers).status_code in (401, 403)
        assert client.patch("/api/v1/zeroq/settings", headers=headers, json={"require_verified_results": False}).status_code in (401, 403)
    client.patch("/api/v1/zeroq/settings", headers=admin2, json={"require_verified_results": False})
    assert School.query.filter_by(slug="mwangaza").one().zeroq_require_results is True  # a different school's change never leaks


def test_blocked_student_keeps_the_pass_they_already_hold(client, student, admin):
    client.patch("/api/v1/zeroq/settings", headers=admin, json={"require_verified_results": False, "require_approved_documents": False})
    held = issue(client, student).get_json()["data"]["pass"]["reference"]
    client.patch("/api/v1/zeroq/settings", headers=admin, json={"require_verified_results": True})
    assert issue(client, student).status_code == 409  # cannot regenerate while blocked
    record = ZeroQPass.query.filter_by(reference=held).one()
    assert record.revoked_at is None  # and the existing pass was NOT revoked by the failed attempt


def test_scanner_is_told_whether_results_and_documents_are_verified(client, student, admin):
    client.patch("/api/v1/zeroq/settings", headers=admin, json={"require_verified_results": False, "require_approved_documents": False})
    require_doc(client, admin)
    qr = issue(client, student).get_json()["data"]["qr_value"]
    scan = client.post("/api/v1/zeroq/scan", headers=admin, json={"qr_value": qr}).get_json()["data"]
    assert scan["valid"] is True
    assert scan["student"]["requirements"] == {"results_verified": False, "documents_approved": False, "required_documents": 1}


def test_other_schools_students_are_not_affected_by_this_schools_documents(client, admin, student):
    neema = login(client, "neema@tumaini.demo")
    require_doc(client, admin)
    assert all("Birth certificate" not in b for b in mine(client, neema)["blockers"])
