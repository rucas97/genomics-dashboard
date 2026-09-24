"""
DB access point.
- `db` is the abstraction singleton (CloudBackend or LocalBackend).
- `sb_select`, `sb_insert`, `sb_update`, `sb_delete` are the legacy
  Supabase helpers used by routers that haven't been ported yet.
"""
from app.config import settings
from app.db.helpers import sb_select, sb_insert, sb_update, sb_delete

__all__ = [
    "get_db", "db",
    "sb_select", "sb_insert", "sb_update", "sb_delete",
]


def _make_backend():
    if settings.is_local:
        from app.db.local import LocalBackend
        return LocalBackend()
    else:
        from app.db.cloud import CloudBackend
        return CloudBackend()


db = None


def get_db():
    global db
    if db is None:
        db = _make_backend()
    return db


try:
    db = get_db()
except Exception as e:
    print(f"DB backend initialization deferred: {e}")
    db = None
