"""ElimuNova rebrand guards: public text uses the new name and the old one does not creep back in."""
import re
from pathlib import Path

import pytest

from app.config import BRAND_NAME
from app.services import apex

ROOT = Path(__file__).resolve().parents[2]
OLD = re.compile(r"Elimu\s?Pro|ELIMUPRO|Elimu<b>Pro")


def test_brand_name():
    assert BRAND_NAME == "ElimuNova"


@pytest.mark.parametrize("component", list(apex.COMPONENTS))
def test_apex_prompts_use_the_new_name(app, component):
    prompt = apex.system_prompt(component)
    assert "ElimuNova" in prompt and not OLD.search(prompt)
    assert "{brand}" not in prompt and "{pricing}" not in prompt


def test_apex_component_names_and_signed_in_context(app, client, student):
    names = [c["name"] for c in apex.component_list()]
    assert "ElimuNova (general)" in names and not any(OLD.search(n) for n in names)
    assert not OLD.search(client.get("/api/v1/apex/components").get_data(as_text=True))


def test_apex_unknown_component_message(client):
    r = client.post("/api/v1/apex/chat", json={"component": "nope", "message": "hi"})
    assert "ElimuNova" in r.get_json()["errors"]["component"]


def test_billing_messages_use_the_new_name(client, super_admin_headers, admin, app):
    body = {"school_id": app.ids["school1"], "component_key": "careergps", "reference": "R", "quantity": 1}
    inv = client.post("/api/v1/billing/invoices", headers=super_admin_headers, json=body).get_json()["data"]
    r = client.post(f"/api/v1/billing/invoices/{inv['id']}/pay", headers=admin, json={"phone": "0712345678"})
    assert r.status_code == 503 and "ElimuNova support" in r.get_json()["message"]


def test_no_old_brand_in_user_facing_frontend_files():
    """Source, HTML, manifest and SVGs. Internal identifiers (lowercase `elimupro_token` etc.) are allowed."""
    files = [p for p in (ROOT / "frontend" / "src").rglob("*") if p.suffix in (".js", ".css")]
    files += [ROOT / "frontend" / "public" / n for n in ("index.html", "manifest.json", "zeroq-logo.svg", "service-worker.js")]
    offenders = [f"{f.relative_to(ROOT)}: {m.group(0)}" for f in files for m in OLD.finditer(f.read_text(encoding="utf-8"))]
    assert offenders == []


def test_user_facing_docs_use_the_new_name():
    for name in ("README.md", "docs/APEX_AI.md", "docs/BILLING.md", "docs/ZEROQ.md"):
        text = (ROOT / name).read_text(encoding="utf-8").replace("(Formerly ElimuPro.", "")  # one deliberate note
        assert not OLD.search(text), name
        assert "ElimuNova" in text or name != "README.md"


def test_manifest_and_index_carry_the_new_name():
    manifest = (ROOT / "frontend/public/manifest.json").read_text()
    index = (ROOT / "frontend/public/index.html").read_text()
    assert '"short_name": "ElimuNova"' in manifest and "<title>ElimuNova</title>" in index
    assert 'property="og:title" content="ElimuNova"' in index and "twitter:card" in index
    for asset in ("icon-192.png", "icon-512.png", "favicon-32.png", "og-image.png", "brand/elimunova-mark.png"):
        assert (ROOT / "frontend/public" / asset).stat().st_size > 1000


def test_brand_config_exists_for_the_frontend():
    text = (ROOT / "frontend/src/config/brand.js").read_text()
    assert "name: 'ElimuNova'" in text and "REACT_APP_BRAND_TAGLINE" in text
