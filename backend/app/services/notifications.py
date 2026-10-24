"""In-app notifications. Email/SMS are not wired up because no delivery provider is configured in this project."""
from ..extensions import db
from ..models import Notification


def notify(user_id, school_id, kind, title, body=None):
    db.session.add(Notification(user_id=user_id, school_id=school_id, kind=kind, title=title[:160],
                                body=body[:500] if body else None))
