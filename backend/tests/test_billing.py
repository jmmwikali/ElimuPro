import hashlib
import hmac
import io
import json
import urllib.error
from datetime import timedelta

import pytest

from app.extensions import db
from app.models import AuditLog, Invoice, PaymentAttempt
from app.models.core import now
from app.services import cyzora
from conftest import login

SECRET, WEBHOOK = "sk_test_abc123", "whsec_test"
WEBHOOK_URL = "/api/v1/billing/webhooks/cyzora"


class Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def http_error(code, message="nope"):
    return urllib.error.HTTPError("https://x", code, message, {}, io.BytesIO(json.dumps({"error": message}).encode()))


class FakeCyzora:
    """Stands in for api.cyzora.co.ke. `queue` outcomes (exceptions or dicts) are used before the defaults."""

    def __init__(self):
        self.calls, self.queue, self.charges = [], [], {}

    def __call__(self, req, timeout):
        path = req.full_url.split("/api/v1", 1)[1]
        body = json.loads(req.data) if req.data else None
        self.calls.append({"method": req.get_method(), "path": path, "body": body,
                           "headers": {k.lower(): v for k, v in req.header_items()}})
        if self.queue:
            item = self.queue.pop(0)
            if isinstance(item, Exception):
                raise item
            return Resp(json.dumps(item).encode())
        if req.get_method() == "POST":
            cid = f"ch_{len(self.charges) + 1}"
            self.charges[cid] = {"id": cid, "status": "pending", "amount": body["amount"], "receipt": None}
            return Resp(json.dumps(self.charges[cid]).encode())
        cid = path.rsplit("/", 1)[1]
        if cid not in self.charges:
            raise http_error(404, "charge not found")
        return Resp(json.dumps(self.charges[cid]).encode())

    def settle(self, cid, status, amount=None, receipt="SJK4TEST1"):
        self.charges[cid].update(status=status, receipt=receipt if status == "succeeded" else None)
        if amount is not None:
            self.charges[cid]["amount"] = amount


@pytest.fixture()
def cz(app, monkeypatch):
    app.config.update(CYZORA_SECRET_KEY=SECRET, CYZORA_WEBHOOK_SECRET=WEBHOOK)
    fake = FakeCyzora()
    monkeypatch.setattr(cyzora.urllib.request, "urlopen", fake)
    return fake


@pytest.fixture()
def super_admin(client):
    return login(client, "super@elimupro.demo")


def issue(client, super_admin, app, component="academic_analytics", reference="Term 2 2026", **extra):
    body = {"school_id": app.ids["school1"], "component_key": component, "reference": reference, **extra}
    return client.post("/api/v1/billing/invoices", headers=super_admin, json=body)


def sign(raw, secret=WEBHOOK):
    return hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()


def webhook(client, body, signature=True, raw=None, secret=WEBHOOK):
    raw = raw if raw is not None else json.dumps(body).encode()
    headers = {"Content-Type": "application/json"}
    if signature:
        headers["X-Cyzora-Signature"] = sign(raw, secret)
    return client.post(WEBHOOK_URL, data=raw, headers=headers)


def event(name, cid, status, amount, livemode=False):
    return {"event": name, "livemode": livemode, "data": {"id": cid, "status": status, "amount": amount}}


@pytest.fixture()
def started(client, super_admin, admin, app, cz):
    """An invoice with an STK prompt sent. Returns (invoice_id, charge_id, cents)."""
    inv = issue(client, super_admin, app).get_json()["data"]
    r = client.post(f"/api/v1/billing/invoices/{inv['id']}/pay", headers=admin, json={"phone": "0712345678"})
    assert r.status_code == 202, r.get_json()
    return inv["id"], "ch_1", 1000000


def invoice_status(inv_id):
    db.session.expire_all()
    return db.session.get(Invoice, inv_id).status


# ---------- issuing invoices ----------
def test_issue_invoice_snapshots_price(client, super_admin, app):
    r = issue(client, super_admin, app)
    d = r.get_json()["data"]
    assert r.status_code == 201 and d["amount"] == 10000 and d["unit_price"] == 10000 and d["status"] == "unpaid"
    assert d["number"].startswith("INV-") and d["school"] == "Mwangaza Academy"
    client.put("/api/v1/pricing/academic_analytics", headers=super_admin, json={"tiers": [
        {"up_to_students": 5, "amount": 1}, {"up_to_students": None, "amount": 2}]})
    assert client.get(f"/api/v1/billing/invoices/{d['id']}", headers=super_admin).get_json()["data"]["amount"] == 10000


def test_quantity_units_multiply(client, super_admin, app):
    d = issue(client, super_admin, app, "zeroq_admissions", "Oct 2026 admissions", quantity=12).get_json()["data"]
    assert d["amount"] == 5400 and d["quantity"] == 12
    d = issue(client, super_admin, app, "careergps", "Year 2026", quantity=300).get_json()["data"]
    assert d["amount"] == 300000


@pytest.mark.parametrize("body,field", [
    ({"component_key": "apex_ai_pro_monthly"}, "component_key"),   # USD cannot go through M-Pesa
    ({"component_key": "nope"}, "component_key"),
    ({"reference": ""}, "reference"), ({"reference": "x" * 61}, "reference"),
    ({"component_key": "academic_analytics", "quantity": 2}, "quantity"),  # per-term is always 1
    ({"component_key": "zeroq_admissions", "quantity": 0}, "quantity"),
    ({"component_key": "zeroq_admissions", "quantity": True}, "quantity"),
    ({"component_key": "zeroq_admissions", "quantity": 1.5}, "quantity"),
])
def test_issue_rejects_bad_input(client, super_admin, app, body, field):
    base = {"school_id": app.ids["school1"], "component_key": "zeroq_admissions", "reference": "R1", "quantity": 1}
    r = client.post("/api/v1/billing/invoices", headers=super_admin, json={**base, **body})
    assert r.status_code == 422 and field in r.get_json()["errors"]
    assert Invoice.query.count() == 0


def test_inactive_component_cannot_be_invoiced(client, super_admin, app):
    client.put("/api/v1/pricing/careergps", headers=super_admin, json={"is_active": False})
    assert issue(client, super_admin, app, "careergps", quantity=1).status_code == 422


def test_cannot_bill_the_same_period_twice(client, super_admin, app):
    assert issue(client, super_admin, app).status_code == 201
    r = issue(client, super_admin, app)
    assert r.status_code == 422 and "already invoiced" in r.get_json()["errors"]["reference"]
    assert issue(client, super_admin, app, reference="Term 3 2026").status_code == 201


def test_fractional_shilling_total_is_rejected(client, super_admin, app):
    client.put("/api/v1/pricing/zeroq_transfers", headers=super_admin, json={"amount": "400.50"})
    r = issue(client, super_admin, app, "zeroq_transfers", quantity=1)
    assert r.status_code == 422 and "whole number of shillings" in r.get_json()["errors"]["component_key"]


def test_only_super_admin_issues_or_voids(client, admin, student, app):
    body = {"school_id": app.ids["school1"], "component_key": "careergps", "reference": "R", "quantity": 1}
    for headers in (admin, student, {}):
        assert client.post("/api/v1/billing/invoices", headers=headers, json=body).status_code in (401, 403)
    assert client.post("/api/v1/billing/invoices/1/void", headers=admin).status_code == 403


# ---------- schools see only their own invoices ----------
def test_schools_are_isolated(client, super_admin, admin, admin2, app, cz):
    inv = issue(client, super_admin, app).get_json()["data"]
    assert [i["id"] for i in client.get("/api/v1/billing/invoices", headers=admin).get_json()["data"]] == [inv["id"]]
    assert client.get("/api/v1/billing/invoices", headers=admin2).get_json()["data"] == []
    for method, path in (("get", ""), ("post", "/pay"), ("post", "/refresh")):
        r = getattr(client, method)(f"/api/v1/billing/invoices/{inv['id']}{path}", headers=admin2,
                                    json={"phone": "0712345678"})
        assert r.status_code == 404
    assert cz.calls == []


def test_student_cannot_see_billing(client, student):
    assert client.get("/api/v1/billing/invoices", headers=student).status_code == 403


# ---------- starting a payment ----------
def test_pay_without_configuration_returns_503(client, super_admin, admin, app):
    inv = issue(client, super_admin, app).get_json()["data"]
    r = client.post(f"/api/v1/billing/invoices/{inv['id']}/pay", headers=admin, json={"phone": "0712345678"})
    assert r.status_code == 503 and PaymentAttempt.query.count() == 0


def test_pay_sends_the_documented_request_and_does_not_mark_paid(client, started, cz):
    inv_id, cid, cents = started
    call = cz.calls[0]
    assert call["method"] == "POST" and call["path"] == "/charges"
    assert call["headers"]["x-api-key"] == SECRET and call["headers"]["idempotency-key"].startswith("INV-")
    body = call["body"]
    assert body["amount"] == cents and isinstance(body["amount"], int) and body["amount"] % 100 == 0
    assert body["phone"] == "254712345678"
    assert body["account_ref"].startswith("INV-")
    assert all(isinstance(v, str) for v in body["metadata"].values())
    attempt = PaymentAttempt.query.one()
    assert attempt.status == "pending" and attempt.provider_charge_id == cid
    assert invoice_status(inv_id) == "unpaid"  # the golden rule: starting a payment never marks it paid


def test_pay_validates_phone(client, super_admin, admin, app, cz):
    inv = issue(client, super_admin, app).get_json()["data"]
    for phone in ("", "123", "0612345678", None, 712345678):
        r = client.post(f"/api/v1/billing/invoices/{inv['id']}/pay", headers=admin, json={"phone": phone})
        assert r.status_code == 422 and "phone" in r.get_json()["errors"]
    assert cz.calls == []


def test_second_prompt_is_blocked_then_allowed_after_two_minutes(client, started, admin, cz):
    inv_id = started[0]
    r = client.post(f"/api/v1/billing/invoices/{inv_id}/pay", headers=admin, json={"phone": "0712345678"})
    assert r.status_code == 409 and len(cz.calls) == 1
    PaymentAttempt.query.update({"created_at": now() - timedelta(minutes=3)})
    db.session.commit()
    r = client.post(f"/api/v1/billing/invoices/{inv_id}/pay", headers=admin, json={"phone": "0712345678"})
    assert r.status_code == 202
    keys = {c["headers"]["idempotency-key"] for c in cz.calls}
    assert len(keys) == 2  # a new prompt is a new charge, so it gets its own key


def test_paid_invoice_cannot_be_paid_again(client, started, admin, cz):
    inv_id, cid, cents = started
    cz.settle(cid, "succeeded")
    assert webhook(client, event("charge.succeeded", cid, "succeeded", cents)).status_code == 200
    r = client.post(f"/api/v1/billing/invoices/{inv_id}/pay", headers=admin, json={"phone": "0712345678"})
    assert r.status_code == 409


@pytest.mark.parametrize("outcome,code,status,fragment", [
    (http_error(422, "Invalid phone number"), 422, "failed", "Invalid phone number"),
    (http_error(401, "bad key"), 502, "failed", "misconfigured"),
    (http_error(500, "boom"), 502, "error", "could not confirm"),
    (urllib.error.URLError("down"), 502, "error", "could not confirm"),
    ({"status": "pending"}, 502, "error", "could not confirm"),  # no charge id in the response
])
def test_provider_errors_are_clear_and_leave_invoice_unpaid(client, super_admin, admin, app, cz, outcome, code, status, fragment):
    inv = issue(client, super_admin, app).get_json()["data"]
    cz.queue.append(outcome)
    r = client.post(f"/api/v1/billing/invoices/{inv['id']}/pay", headers=admin, json={"phone": "0712345678"})
    assert r.status_code == code and fragment.lower() in r.get_json()["message"].lower()
    assert SECRET not in r.get_data(as_text=True)
    assert PaymentAttempt.query.one().status == status
    assert invoice_status(inv["id"]) == "unpaid"


def test_rate_limit_is_retried_with_the_same_idempotency_key(client, super_admin, admin, app, cz):
    inv = issue(client, super_admin, app).get_json()["data"]
    cz.queue += [http_error(429, "slow down"), http_error(409, "request in flight")]
    r = client.post(f"/api/v1/billing/invoices/{inv['id']}/pay", headers=admin, json={"phone": "0712345678"})
    assert r.status_code == 202 and len(cz.calls) == 3
    assert len({c["headers"]["idempotency-key"] for c in cz.calls}) == 1


def test_persistent_rate_limit_gives_up_politely(client, super_admin, admin, app, cz):
    inv = issue(client, super_admin, app).get_json()["data"]
    cz.queue += [http_error(429)] * 3
    r = client.post(f"/api/v1/billing/invoices/{inv['id']}/pay", headers=admin, json={"phone": "0712345678"})
    assert r.status_code == 429 and len(cz.calls) == 3


# ---------- webhook: signature ----------
def test_webhook_rejects_missing_wrong_or_tampered_signature(client, started, cz):
    _, cid, cents = started
    cz.settle(cid, "succeeded")
    body = event("charge.succeeded", cid, "succeeded", cents)
    raw = json.dumps(body).encode()
    assert webhook(client, body, signature=False).status_code == 401
    assert webhook(client, body, secret="whsec_wrong").status_code == 401
    bad = client.post(WEBHOOK_URL, data=raw + b" ", headers={"X-Cyzora-Signature": sign(raw)})  # body changed in transit
    assert bad.status_code == 401
    assert client.post(WEBHOOK_URL, data=raw, headers={"X-Cyzora-Signature": "zz"}).status_code == 401
    assert PaymentAttempt.query.one().status == "pending" and len(cz.calls) == 1


def test_webhook_unconfigured_returns_503_so_cyzora_retries(client, app):
    assert webhook(client, {"event": "webhook.test"}).status_code == 503


def test_webhook_accepts_signed_test_event(client, cz):
    r = webhook(client, {"event": "webhook.test", "livemode": False})
    assert r.status_code == 200 and cz.calls == []


def test_webhook_rejects_non_json_after_valid_signature(client, cz):
    assert webhook(client, None, raw=b"not json").status_code == 400
    assert webhook(client, None, raw=b"[1]").status_code == 400


@pytest.mark.parametrize("raw,header,secret,ok_", [
    (b"{}", None, "s", False), (b"{}", "", "s", False), (b"{}", "abc", "s", False), (b"{}", "abc", None, False),
    ("{}", "abc", "s", False)])
def test_verify_signature_rejects_garbage(raw, header, secret, ok_):
    assert cyzora.verify_signature(raw, header, secret) is ok_


def test_verify_signature_accepts_correct_and_ignores_case():
    raw = b'{"a":1}'
    assert cyzora.verify_signature(raw, sign(raw), WEBHOOK)
    assert cyzora.verify_signature(raw, sign(raw).upper(), WEBHOOK)


# ---------- webhook: marking paid ----------
def test_signed_success_marks_invoice_paid_after_verifying_with_cyzora(client, started, cz):
    inv_id, cid, cents = started
    cz.settle(cid, "succeeded", receipt="SJK4TEST1")
    r = webhook(client, event("charge.succeeded", cid, "succeeded", cents))
    assert r.status_code == 200 and r.get_json()["data"]["result"] == "paid"
    assert cz.calls[-1]["method"] == "GET" and cz.calls[-1]["path"] == f"/charges/{cid}"
    db.session.expire_all()
    inv = db.session.get(Invoice, inv_id)
    assert inv.status == "paid" and inv.paid_at and inv.attempts[0].receipt == "SJK4TEST1"
    assert AuditLog.query.filter_by(action="billing.invoice_paid").count() == 1


def test_repeated_webhooks_are_idempotent(client, started, cz):
    inv_id, cid, cents = started
    cz.settle(cid, "succeeded")
    webhook(client, event("charge.succeeded", cid, "succeeded", cents))
    paid_at = db.session.get(Invoice, inv_id).paid_at
    for _ in range(3):
        r = webhook(client, event("charge.succeeded", cid, "succeeded", cents))
        assert r.status_code == 200 and r.get_json()["data"]["result"] == "already_succeeded"
    db.session.expire_all()
    assert db.session.get(Invoice, inv_id).paid_at == paid_at
    assert AuditLog.query.filter_by(action="billing.invoice_paid").count() == 1


def test_a_forged_success_body_cannot_pay_when_cyzora_says_pending(client, started, cz):
    """Even with a valid signature, the body alone is not trusted: Cyzora must confirm."""
    inv_id, cid, cents = started
    r = webhook(client, event("charge.succeeded", cid, "succeeded", cents))
    assert r.status_code == 200 and r.get_json()["data"]["result"] == "pending"
    assert invoice_status(inv_id) == "unpaid"


@pytest.mark.parametrize("reported", [100, 999900, 10000, None])
def test_amount_mismatch_never_marks_paid(client, started, cz, reported):
    inv_id, cid, cents = started
    cz.settle(cid, "succeeded", amount=reported)
    if reported is None:
        cz.charges[cid].pop("amount")
    r = webhook(client, event("charge.succeeded", cid, "succeeded", cents))
    assert r.get_json()["data"]["result"] == "amount_mismatch"
    assert invoice_status(inv_id) == "unpaid"
    assert PaymentAttempt.query.one().status == "amount_mismatch"
    assert AuditLog.query.filter_by(action="billing.amount_mismatch").count() == 1


@pytest.mark.parametrize("name,status", [("charge.failed", "failed"), ("charge.expired", "expired")])
def test_failed_or_expired_marks_attempt_not_invoice(client, started, cz, name, status):
    inv_id, cid, cents = started
    cz.settle(cid, status)
    assert webhook(client, event(name, cid, status, cents)).status_code == 200
    assert PaymentAttempt.query.one().status == status and invoice_status(inv_id) == "unpaid"


def test_a_settled_success_is_never_downgraded(client, started, cz):
    inv_id, cid, cents = started
    cz.settle(cid, "succeeded")
    webhook(client, event("charge.succeeded", cid, "succeeded", cents))
    cz.settle(cid, "failed")
    webhook(client, event("charge.failed", cid, "failed", cents))
    assert PaymentAttempt.query.one().status == "succeeded" and invoice_status(inv_id) == "paid"


def test_test_event_is_ignored_by_a_live_key(client, started, cz, app):
    inv_id, cid, cents = started
    app.config["CYZORA_SECRET_KEY"] = "sk_live_abc"
    cz.settle(cid, "succeeded")
    r = webhook(client, event("charge.succeeded", cid, "succeeded", cents, livemode=False))
    assert r.status_code == 200 and "ignored" in r.get_json()["data"]
    assert invoice_status(inv_id) == "unpaid"


def test_live_event_is_ignored_by_a_test_key(client, started, cz):
    inv_id, cid, cents = started
    cz.settle(cid, "succeeded")
    r = webhook(client, event("charge.succeeded", cid, "succeeded", cents, livemode=True))
    assert "ignored" in r.get_json()["data"] and invoice_status(inv_id) == "unpaid"


def test_unknown_charge_and_other_events_are_acknowledged_without_effect(client, started, cz):
    inv_id, cid, cents = started
    n = len(cz.calls)
    assert webhook(client, event("charge.succeeded", "ch_other", "succeeded", cents)).status_code == 200
    assert AuditLog.query.filter_by(action="billing.webhook_unmatched").count() == 1
    assert webhook(client, {"event": "payout.paid", "livemode": False, "data": {"id": cid}}).status_code == 200
    assert webhook(client, {"event": "something.new", "livemode": False}).status_code == 200
    assert len(cz.calls) == n and invoice_status(inv_id) == "unpaid"


def test_if_cyzora_cannot_confirm_we_ask_for_a_retry(client, started, cz):
    inv_id, cid, cents = started
    cz.settle(cid, "succeeded")
    cz.queue.append(urllib.error.URLError("down"))
    r = webhook(client, event("charge.succeeded", cid, "succeeded", cents))
    assert r.status_code == 502 and invoice_status(inv_id) == "unpaid"
    assert webhook(client, event("charge.succeeded", cid, "succeeded", cents)).status_code == 200  # the retry works
    assert invoice_status(inv_id) == "paid"


def test_payment_on_a_voided_invoice_is_flagged_not_hidden(client, started, super_admin, cz):
    inv_id, cid, cents = started
    PaymentAttempt.query.update({"created_at": now() - timedelta(hours=1)})
    db.session.commit()
    assert client.post(f"/api/v1/billing/invoices/{inv_id}/void", headers=super_admin).status_code == 200
    cz.settle(cid, "succeeded")
    r = webhook(client, event("charge.succeeded", cid, "succeeded", cents))
    assert r.get_json()["data"]["result"] == "unexpected_payment"
    assert invoice_status(inv_id) == "void" and AuditLog.query.filter_by(action="billing.unexpected_payment").count() == 1


# ---------- refresh (recovers a missed webhook) ----------
def test_refresh_settles_a_payment_whose_webhook_never_arrived(client, started, admin, cz):
    inv_id, cid, cents = started
    cz.settle(cid, "succeeded")
    r = client.post(f"/api/v1/billing/invoices/{inv_id}/refresh", headers=admin)
    assert r.status_code == 200 and r.get_json()["data"]["status"] == "paid"
    assert r.get_json()["data"]["attempt"]["phone_hint"] == "...678"  # never the full number


def test_refresh_while_pending_changes_nothing_and_survives_cyzora_outage(client, started, admin, cz):
    inv_id = started[0]
    assert client.post(f"/api/v1/billing/invoices/{inv_id}/refresh", headers=admin).get_json()["data"]["status"] == "unpaid"
    cz.queue.append(urllib.error.URLError("down"))
    assert client.post(f"/api/v1/billing/invoices/{inv_id}/refresh", headers=admin).status_code == 502


# ---------- voiding ----------
def test_void_rules(client, super_admin, admin, app, cz):
    inv = issue(client, super_admin, app).get_json()["data"]
    assert client.post(f"/api/v1/billing/invoices/{inv['id']}/void", headers=super_admin).get_json()["data"]["status"] == "void"
    assert client.post(f"/api/v1/billing/invoices/{inv['id']}/void", headers=super_admin).status_code == 409
    assert client.post(f"/api/v1/billing/invoices/{inv['id']}/pay", headers=admin, json={"phone": "0712345678"}).status_code == 409


def test_cannot_void_while_a_prompt_is_in_flight_or_after_payment(client, started, super_admin, cz):
    inv_id, cid, cents = started
    assert client.post(f"/api/v1/billing/invoices/{inv_id}/void", headers=super_admin).status_code == 409
    cz.settle(cid, "succeeded")
    webhook(client, event("charge.succeeded", cid, "succeeded", cents))
    assert client.post(f"/api/v1/billing/invoices/{inv_id}/void", headers=super_admin).status_code == 409


def test_secrets_never_appear_in_responses(client, started, admin, super_admin):
    for headers in (admin, super_admin):
        text = client.get("/api/v1/billing/invoices", headers=headers).get_data(as_text=True)
        assert SECRET not in text and WEBHOOK not in text and "0712345678" not in text
