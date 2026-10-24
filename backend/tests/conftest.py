import pytest

from app import create_app
from app.config import TestConfig
from app.extensions import db
from app.seed import seed_demo, DEMO_PASSWORD


@pytest.fixture()
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        app.ids = seed_demo()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def login(client, email, password=DEMO_PASSWORD):
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.get_json()
    return {"Authorization": "Bearer " + r.get_json()["data"]["token"]}


@pytest.fixture()
def admin(client):
    return login(client, "admin@mwangaza.demo")


@pytest.fixture()
def admin2(client):
    return login(client, "admin@tumaini.demo")


@pytest.fixture()
def student(client):
    return login(client, "achieng@mwangaza.demo")


@pytest.fixture()
def super_admin_headers(client):
    return login(client, "super@elimupro.demo")
