"""
SQLite-backed implementation for MODE=local.
This is a stub — it will be fully implemented in Batch 2B.
Every method currently raises NotImplementedError.
"""
from app.db.base import DatabaseBackend


class LocalBackend(DatabaseBackend):
    def __init__(self):
        raise NotImplementedError(
            "LocalBackend not yet implemented. This is Batch 2A (skeleton only). "
            "Set MODE=cloud in .env or wait for Batch 2B."
        )

    # All methods inherited from DatabaseBackend, none implemented yet.
    # Batch 2B fills these in.
