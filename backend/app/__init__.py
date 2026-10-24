from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from .config import Config
from .extensions import db, jwt, bcrypt, migrate
from .utils.responses import err

load_dotenv()


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)
    if not app.config.get("TESTING"):
        for key in ("SECRET_KEY", "JWT_SECRET_KEY"):
            value = app.config.get(key)
            if not value or len(value) < 32:
                raise RuntimeError(f"{key} must contain at least 32 characters")
        if app.config["SECRET_KEY"] == app.config["JWT_SECRET_KEY"]:
            raise RuntimeError("SECRET_KEY and JWT_SECRET_KEY must be different")
        if not app.config.get("SQLALCHEMY_DATABASE_URI"):
            raise RuntimeError("Missing required environment variable for SQLALCHEMY_DATABASE_URI")

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    bcrypt.init_app(app)
    CORS(app, resources={r"/api(?:/.*)?$": {"origins": app.config["CORS_ORIGINS"]}})

    from . import models  # noqa: F401
    from .routes import register_blueprints
    register_blueprints(app)

    @jwt.unauthorized_loader
    def _missing(reason):
        return err("Authentication required", 401)

    @jwt.invalid_token_loader
    def _invalid(reason):
        return err("Invalid token", 401)

    @jwt.expired_token_loader
    def _expired(header, payload):
        return err("Session expired, please log in again", 401)

    @app.errorhandler(404)
    def _404(e):
        return err("Not found", 404)

    @app.errorhandler(405)
    def _405(e):
        return err("Method not allowed", 405)

    @app.errorhandler(500)
    def _500(e):
        db.session.rollback()
        return err("Something went wrong on our side", 500)

    @app.get("/api/health")
    @app.get("/api/v1/health")
    def health():
        # `service` is a machine-readable identifier that uptime monitors may match on, so it keeps its original value.
        return {"success": True, "data": {"status": "ok", "service": "ElimuPro API"}}

    @app.get("/api/v1/health/ready")
    def readiness():
        try:
            db.session.execute(text("SELECT 1"))
        except SQLAlchemyError:
            db.session.rollback()
            return err("Database unavailable", 503)
        return health()

    return app
