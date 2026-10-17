import os
from datetime import timedelta

from dotenv import load_dotenv
from sqlalchemy.engine import make_url

load_dotenv()  # must run before Config reads os.environ below


def normalize_database_url(database_url):
    if not database_url:
        return database_url
    url = make_url(database_url)
    if url.drivername in ("postgres", "postgresql"):
        return url.set(drivername="postgresql+psycopg").render_as_string(hide_password=False)
    return url


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = normalize_database_url(os.environ.get("DATABASE_URL"))
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_recycle": 280}
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=int(os.environ.get("JWT_ACCESS_HOURS", 12)))
    FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")
    CORS_ORIGINS = [o.strip() for o in FRONTEND_URL.split(",") if o.strip()]
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
    GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    GEMINI_TIMEOUT = int(os.environ.get("GEMINI_TIMEOUT", 20))
    APEX_RATE_LIMIT_PER_MINUTE = int(os.environ.get("APEX_RATE_LIMIT_PER_MINUTE", 12))


class TestConfig(Config):
    TESTING = True
    BCRYPT_LOG_ROUNDS = 4
    SECRET_KEY = "test"
    JWT_SECRET_KEY = "test-jwt-secret-key-at-least-32-bytes-long"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS = {}
    GEMINI_API_KEY = None