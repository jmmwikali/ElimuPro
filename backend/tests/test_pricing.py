import json
from decimal import Decimal

import pytest

from app.extensions import db
from app.models import AuditLog, PriceComponent
from app.services import apex, pricing
from conftest import login


@pytest.fixture()
def super_admin(client):
    return login(client, "super@elimupro.demo")


def component(key):
    return pricing.get_component(key)


@pytest.mark.parametrize("students,expected", [
    (0, 10000), (999, 10000), (1000, 10000),  # exactly 1,000 is the lower tier, never a gap
    (1001, 15000), (5000, 15000)])
def test_analytics_boundary_has_no_gap(app, students, expected):
    for key in ("academic_analytics", "financial_analytics"):
        assert pricing.price_for(component(key), students) == expected


def test_defaults_match_launch_prices(app):
    prices = {c["key"]: pricing.price_for(c, 10) for c in pricing.get_components()}
    assert prices == {"academic_analytics": 10000, "financial_analytics": 10000, "zeroq_admissions": 450,
                      "zeroq_transfers": 400, "careergps": 1000, "apex_ai_pro_monthly": 5,
                      "apex_ai_pro_yearly": 40}


def test_inactive_component_has_no_price(app, client, super_admin):
    client.put("/api/v1/pricing/careergps", headers=super_admin, json={"is_active": False})
    assert pricing.price_for(component("careergps"), 10) is None


def test_only_super_admin_can_view_or_edit(client, admin, student):
    for headers in (admin, student, {}):
        assert client.get("/api/v1/pricing", headers=headers).status_code in (401, 403)
        assert client.put("/api/v1/pricing/careergps", headers=headers, json={"amount": 1}).status_code in (401, 403)


def test_list_shows_every_component_even_before_any_edit(client, super_admin):
    data = client.get("/api/v1/pricing", headers=super_admin).get_json()["data"]
    assert [c["key"] for c in data] == [d["key"] for d in pricing.DEFAULTS]
    assert PriceComponent.query.count() == 0  # reading never writes
    analytics = data[0]
    assert analytics["tiers"] == [{"up_to_students": 1000, "amount": 10000.0},
                                  {"up_to_students": None, "amount": 15000.0}]
    assert analytics["billing_label"] == "per school per term"


def test_edit_flat_price_persists_and_is_audited(client, super_admin, app):
    r = client.put("/api/v1/pricing/zeroq_admissions", headers=super_admin,
                   json={"amount": "500.50", "description": "Launch offer"})
    assert r.status_code == 200, r.get_json()
    assert r.get_json()["data"]["amount"] == 500.5
    assert pricing.price_for(component("zeroq_admissions"), 1) == Decimal("500.50")
    assert component("zeroq_admissions")["description"] == "Launch offer"
    log = AuditLog.query.filter_by(action="pricing.updated").one()
    assert log.details["before"]["amount"] == 450.0 and log.details["after"]["amount"] == 500.5
    # an untouched component keeps its default
    assert pricing.price_for(component("zeroq_transfers"), 1) == 400


def test_edit_tiers_moves_the_boundary(client, super_admin):
    r = client.put("/api/v1/pricing/academic_analytics", headers=super_admin, json={"tiers": [
        {"up_to_students": 500, "amount": 8000}, {"up_to_students": 1500, "amount": 12000},
        {"up_to_students": None, "amount": 20000}]})
    assert r.status_code == 200, r.get_json()
    c = component("academic_analytics")
    assert [pricing.price_for(c, n) for n in (500, 501, 1500, 1501)] == [8000, 12000, 12000, 20000]
    assert PriceComponent.query.one().key == "academic_analytics"
    # financial analytics is priced independently
    assert pricing.price_for(component("financial_analytics"), 500) == 10000


@pytest.mark.parametrize("amount", [-1, "abc", 1.234, True, "NaN", 10**9])
def test_flat_component_rejects_bad_amount(client, super_admin, amount):
    r = client.put("/api/v1/pricing/careergps", headers=super_admin, json={"amount": amount})
    assert r.status_code == 422 and "amount" in r.get_json()["errors"]
    assert component("careergps")["amount"] == 1000


def test_flat_component_rejects_tiers(client, super_admin):
    tiers = [{"up_to_students": 1, "amount": 1}, {"up_to_students": None, "amount": 1}]
    r = client.put("/api/v1/pricing/careergps", headers=super_admin, json={"tiers": tiers})
    assert r.status_code == 422 and r.get_json()["errors"]["tiers"]


@pytest.mark.parametrize("tiers", [
    [{"up_to_students": 1000, "amount": 1}],                                                   # one tier
    [{"up_to_students": 1000, "amount": 1}, {"up_to_students": 2000, "amount": 2}],            # no open top tier
    [{"up_to_students": 1000, "amount": 1}, {"up_to_students": 1000, "amount": 2},
     {"up_to_students": None, "amount": 3}],                                                   # overlap
    [{"up_to_students": 2000, "amount": 1}, {"up_to_students": 1000, "amount": 2},
     {"up_to_students": None, "amount": 3}],                                                   # unordered
    [{"up_to_students": 0, "amount": 1}, {"up_to_students": None, "amount": 3}],              # zero limit
    [{"up_to_students": "1000", "amount": 1}, {"up_to_students": None, "amount": 3}],         # not an int
    [{"up_to_students": 1000, "amount": -5}, {"up_to_students": None, "amount": 3}],          # bad amount
    "nonsense", [1, 2],
])
def test_tiered_component_rejects_gaps_overlaps_and_bad_values(client, super_admin, tiers):
    r = client.put("/api/v1/pricing/academic_analytics", headers=super_admin, json={"tiers": tiers})
    assert r.status_code == 422 and r.get_json()["errors"]["tiers"]
    assert pricing.price_for(component("academic_analytics"), 1001) == 15000


def test_tiered_component_rejects_flat_amount(client, super_admin):
    r = client.put("/api/v1/pricing/academic_analytics", headers=super_admin, json={"amount": 5})
    assert r.status_code == 422 and "tiers" in r.get_json()["errors"]["amount"]


def test_unknown_component_and_empty_update(client, super_admin):
    assert client.put("/api/v1/pricing/nope", headers=super_admin, json={"amount": 1}).status_code == 404
    assert client.put("/api/v1/pricing/careergps", headers=super_admin, json={}).status_code == 422
    assert client.put("/api/v1/pricing/careergps", headers=super_admin, json=[1]).status_code == 400


def test_failed_edit_leaves_prices_untouched(client, super_admin):
    client.put("/api/v1/pricing/careergps", headers=super_admin, json={"amount": -5, "name": "Renamed"})
    assert PriceComponent.query.count() == 0
    assert component("careergps")["name"] == "CareerGPS"


@pytest.mark.parametrize("amount,cur,text", [(10000, "KES", "KSh 10,000"), (Decimal("500.50"), "KES", "KSh 500.50"),
                                             (5, "USD", "USD 5")])
def test_money_text(amount, cur, text):
    assert pricing.money_text(amount, cur) == text


def test_describe_states_the_boundary_explicitly(app):
    text = pricing.describe(component("academic_analytics"))
    assert "up to 1,000 students (including exactly 1,000): KSh 10,000 per school per term" in text
    assert "more than 1,000 students: KSh 15,000 per school per term" in text


def test_apex_quotes_live_prices(client, super_admin, app):
    client.put("/api/v1/pricing/careergps", headers=super_admin, json={"amount": 1250})
    client.put("/api/v1/pricing/academic_analytics", headers=super_admin, json={"tiers": [
        {"up_to_students": 800, "amount": 9000}, {"up_to_students": None, "amount": 14000}]})
    careergps = apex.system_prompt("careergps")
    assert "KSh 1,250 per student per academic year" in careergps and "KSh 1,000" not in careergps
    academic = apex.system_prompt("academic_analytics")
    assert "up to 800 students" in academic and "KSh 14,000" in academic
    general = apex.system_prompt("general")
    assert "KSh 450 per admission" in general and "KSh 1,250" in general
    assert "USD 5 per month" in general and "USD 40 per year" in general
    assert "USD 5 per month" in apex.system_prompt("apex_ai") and "yearly plan is a discount" in apex.system_prompt("apex_ai")


def test_apex_says_when_a_component_is_off_sale(client, super_admin, app):
    client.put("/api/v1/pricing/zeroq_transfers", headers=super_admin, json={"is_active": False})
    assert "not currently on sale" in apex.system_prompt("zeroq_transfers")
    assert "KSh 400" not in apex.system_prompt("general")


def test_api_response_is_json_serialisable(client, super_admin):
    r = client.get("/api/v1/pricing", headers=super_admin)
    json.dumps(r.get_json())
