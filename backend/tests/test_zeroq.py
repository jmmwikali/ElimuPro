from datetime import datetime, timedelta

import pytest

from app.extensions import db
from app.models import AuditLog, School, ZeroQPass, ZeroQScan
from conftest import login


@pytest.fixture(autouse=True)
def _pass_rules_off(app):
    """These tests are about issuing, scanning and revoking a pass. The results/documents rules have their own tests."""
    School.query.update({School.zeroq_require_results: False, School.zeroq_require_documents: False})
    db.session.commit()


def issue(client, student_headers):
    response = client.post("/api/zeroq/my/pass", headers=student_headers, json={})
    assert response.status_code == 201, response.get_json()
    return response.get_json()["data"]


def test_student_pass_is_opaque_and_scan_is_one_time(client, app, student, admin):
    issued = issue(client, student)
    qr_value = issued["qr_value"]
    pass_record = ZeroQPass.query.filter_by(reference=issued["pass"]["reference"]).one()
    assert qr_value.startswith("ZEROQ1.")
    assert pass_record.token_hash != qr_value
    assert qr_value not in str(pass_record.to_dict())
    assert "qr_value" not in client.get("/api/zeroq/my", headers=student).get_json()["data"]

    first = client.post("/api/zeroq/scan", headers=admin, json={"qr_value": qr_value}).get_json()["data"]
    assert first["valid"] is True and first["status"] == "verified"
    assert first["student"]["full_name"] == "Achieng Otieno"
    assert first["student"]["admission_number"].startswith("MWA")
    assert "phone" not in first["student"]
    assert client.post("/api/zeroq/scan", headers=admin, json={"qr_value": qr_value}).get_json()["data"]["status"] == "already_used"

    completed = client.post(f"/api/zeroq/{pass_record.id}/complete", headers=admin)
    assert completed.status_code == 200
    assert completed.get_json()["data"]["status"] == "completed"
    assert client.post(f"/api/zeroq/{pass_record.id}/complete", headers=admin).status_code == 409
    assert ZeroQScan.query.filter_by(pass_id=pass_record.id).count() == 2
    assert AuditLog.query.filter_by(action="zeroq.admission.completed", entity_id=pass_record.id).count() == 1


def test_pass_revoke_expiry_and_school_binding(client, app, student, admin, admin2):
    revoked = issue(client, student)
    pass_id = ZeroQPass.query.filter_by(reference=revoked["pass"]["reference"]).one().id
    assert client.post(f"/api/zeroq/{pass_id}/revoke", headers=admin).status_code == 200
    result = client.post("/api/zeroq/scan", headers=admin, json={"qr_value": revoked["qr_value"]}).get_json()["data"]
    assert result["status"] == "revoked" and "student" not in result

    expired = issue(client, student)
    expired_record = ZeroQPass.query.filter_by(reference=expired["pass"]["reference"]).one()
    expired_record.expires_at = datetime.utcnow() - timedelta(seconds=1)
    db.session.commit()
    result = client.post("/api/zeroq/scan", headers=admin, json={"qr_value": expired["qr_value"]}).get_json()["data"]
    assert result["status"] == "expired" and "student" not in result

    neema = login(client, "neema@tumaini.demo")
    other_school = issue(client, neema)
    result = client.post("/api/zeroq/scan", headers=admin, json={"qr_value": other_school["qr_value"]}).get_json()["data"]
    assert result["status"] == "wrong_institution" and "student" not in result
    other_pass = ZeroQPass.query.filter_by(reference=other_school["pass"]["reference"]).one()
    assert client.post(f"/api/zeroq/{other_pass.id}/revoke", headers=admin).status_code == 404
    assert client.post(f"/api/zeroq/{pass_id}/revoke", headers=admin2).status_code == 404


def test_zeroq_permissions_queue_and_dashboard_are_school_scoped(client, app, student, admin, admin2):
    assert client.get("/api/zeroq/dashboard", headers=student).status_code == 403
    assert client.post("/api/zeroq/scan", headers=student, json={"qr_value": "ZEROQ1.bad"}).status_code == 403

    issued = issue(client, student)
    queue = client.get("/api/zeroq/queue", headers=admin)
    assert queue.status_code == 200
    assert any(row["reference"] == issued["pass"]["reference"] for row in queue.get_json()["data"])
    assert client.get("/api/zeroq/queue", headers=admin2).get_json()["data"] == []
    dashboard = client.get("/api/zeroq/dashboard", headers=admin).get_json()["data"]
    assert dashboard["today_arrivals"] == 1
    assert dashboard["verified"] == 1
    assert client.get("/api/zeroq/queue?date=not-a-date", headers=admin).status_code == 422


def test_invalid_qr_is_logged_without_storing_raw_value(client, admin):
    raw = "ZEROQ1.not-a-real-token"
    result = client.post("/api/zeroq/scan", headers=admin, json={"qr_value": raw}).get_json()["data"]
    assert result["status"] == "invalid"
    scan_record = ZeroQScan.query.one()
    assert scan_record.token_fingerprint != raw
    assert scan_record.outcome == "invalid"