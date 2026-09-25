"""
Audit log service. Uses the DB abstraction so it works in both cloud and local mode.
"""
from app.db import get_db


def log_action(user_id, action, resource_type=None, resource_id=None, details=None):
    """Record an audit event. Never raises — audit failures shouldn't break the app."""
    if not user_id:
        # System actions with no user
        user_id = None

    entry = {
        "user_id": user_id,
        "action": action,
        "resource_type": resource_type,
        "resource_id": str(resource_id) if resource_id else None,
        "details": details or {},
    }

    try:
        db = get_db()
        db.log_audit(entry)
    except Exception as e:
        # Never let audit failure crash the request
        print(f"audit log failed: {e}")
