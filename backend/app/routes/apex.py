from flask import Blueprint, current_app, request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from flask_jwt_extended.exceptions import JWTExtendedException
from jwt.exceptions import PyJWTError

from ..extensions import db
from ..services import apex
from ..utils.responses import err, ok

bp = Blueprint("apex", __name__, url_prefix="/api/apex")


def _optional_user():
    """Apex AI answers visitors too; a valid token only adds role and school context."""
    from ..models import User
    try:
        verify_jwt_in_request(optional=True)
        identity = get_jwt_identity()
    except (JWTExtendedException, PyJWTError):
        return None
    user = db.session.get(User, int(identity)) if identity else None
    return user if user and user.is_active else None


@bp.get("/components")
def components():
    return ok({"components": apex.component_list(),
               "enabled": bool(current_app.config.get("GEMINI_API_KEY"))})


@bp.post("/chat")
def chat():
    body = request.get_json(silent=True) or {}
    component = body.get("component") or "general"
    message = body.get("message")
    if component not in apex.COMPONENTS:
        return err("Unknown component", 422, {"component": "Choose a valid ElimuPro component"})
    if not isinstance(message, str) or not message.strip():
        return err("Type a message", 422, {"message": "Message is required"})
    if len(message) > apex.MAX_MESSAGE_CHARS:
        return err(f"Keep messages under {apex.MAX_MESSAGE_CHARS} characters", 422)

    user = _optional_user()
    caller = f"user:{user.id}" if user else f"ip:{request.remote_addr}"
    if not apex.limiter.allow(caller, current_app.config["APEX_RATE_LIMIT_PER_MINUTE"]):
        return err("You are sending messages too quickly. Please wait a minute and try again.", 429)

    try:
        reply = apex.ask_gemini(apex.system_prompt(component, user),
                                apex.clean_history(body.get("history")), message.strip())
    except apex.ApexUnavailable as e:
        return err(f"{e}. Please try again later or contact your school administrator.", 503)
    return ok({"reply": reply, "component": component})
