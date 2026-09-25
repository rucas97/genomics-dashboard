"""
Stable machine fingerprint for license binding.
Uses a persisted random UUID instead of MAC address.
Survives VM cloning, container restarts, and hardware changes.
"""
import hashlib
import platform
import uuid
from pathlib import Path
from app.config import settings


FINGERPRINT_FILE = Path(settings.LOCAL_DATA_DIR).parent / "machine.id"


def _get_or_create_machine_uuid() -> str:
    if FINGERPRINT_FILE.exists():
        return FINGERPRINT_FILE.read_text().strip()
    FINGERPRINT_FILE.parent.mkdir(parents=True, exist_ok=True)
    new_id = str(uuid.uuid4())
    FINGERPRINT_FILE.write_text(new_id)
    return new_id


def get_machine_fingerprint() -> str:
    parts = [
        _get_or_create_machine_uuid(),
        platform.node(),
        platform.system(),
    ]
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:32]
