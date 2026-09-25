"""
License verification and tier management.

Tokens are Ed25519-signed JSON blobs. Verification is offline — no
network call required once a token is stored locally.
"""
import base64
import hashlib
import json
import platform
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.exceptions import InvalidSignature

from app.config import settings


# Tier definitions
TIERS = {
    "unlicensed": {
        "name": "Unlicensed",
        "network_policy": "blocked",
        "features": [],
        "label": "No license active",
    },
    "trial": {
        "name": "Trial",
        "network_policy": "annotation",
        "features": ["annotation"],
        "label": "7-day trial",
    },
    "standard": {
        "name": "Standard",
        "network_policy": "annotation",
        "features": ["annotation", "fhir_export", "multi_user"],
        "label": "Standard license",
    },
    "enterprise": {
        "name": "Enterprise",
        "network_policy": "full",
        "features": ["annotation", "fhir_export", "multi_user", "custom_integrations"],
        "label": "Enterprise license",
    },
}


LICENSE_FILE = Path(settings.LOCAL_DATA_DIR).parent / "license.json"


from app.services.fingerprint import get_machine_fingerprint  # noqa: F401,E402


def _load_stored_token() -> Optional[dict]:
    if not LICENSE_FILE.exists():
        return None
    try:
        with open(LICENSE_FILE) as f:
            return json.load(f)
    except Exception:
        return None


def _save_token(token: dict):
    LICENSE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LICENSE_FILE, "w") as f:
        json.dump(token, f, indent=2)


def _verify_signature(payload: dict, signature_b64: str) -> bool:
    """Verify an Ed25519 signature against the embedded public key."""
    if not settings.LICENSE_PUBLIC_KEY:
        print("LICENSE_PUBLIC_KEY not set — signature verification skipped")
        return False

    try:
        pub_bytes = base64.b64decode(settings.LICENSE_PUBLIC_KEY)
        public_key = Ed25519PublicKey.from_public_bytes(pub_bytes)

        # Canonical JSON of the payload
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        signature = base64.b64decode(signature_b64)

        public_key.verify(signature, canonical)
        return True
    except InvalidSignature:
        print("License signature verification FAILED")
        return False
    except Exception as e:
        print(f"License verification error: {e}")
        return False


def _parse_date(s: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None


def get_license_status() -> dict:
    """
    Return the current license status.
    Never raises — always returns a dict.
    """
    result = {
        "tier": "unlicensed",
        "valid": False,
        "reason": "no_license",
        "network_policy": "blocked",
        "features": [],
        "expires_at": None,
        "customer_email": None,
        "license_id": None,
        "machine_fingerprint": get_machine_fingerprint(),
        "days_remaining": None,
        "grace_period_active": False,
    }

    token = _load_stored_token()
    if not token:
        return result

    payload = token.get("payload", {})
    signature = token.get("signature", "")

    # Verify signature
    if not _verify_signature(payload, signature):
        result["reason"] = "invalid_signature"
        return result

    # Check machine binding
    bound_machine = payload.get("machine_fingerprint")
    if bound_machine and bound_machine != get_machine_fingerprint():
        result["reason"] = "machine_mismatch"
        return result

    # Check expiry
    expires_at = _parse_date(payload.get("expires_at", ""))
    now = datetime.utcnow()
    grace_active = False
    days_remaining = None

    if expires_at:
        days_remaining = (expires_at - now).days
        if expires_at < now:
            # In grace period?
            grace_end = expires_at + timedelta(days=settings.LICENSE_GRACE_DAYS)
            if now < grace_end:
                grace_active = True
            else:
                result["reason"] = "expired"
                result["expires_at"] = payload.get("expires_at")
                return result

    tier = payload.get("tier", "unlicensed")
    tier_def = TIERS.get(tier, TIERS["unlicensed"])

    result.update({
        "tier": tier,
        "valid": True,
        "reason": "ok",
        "network_policy": tier_def["network_policy"],
        "features": tier_def["features"],
        "expires_at": payload.get("expires_at"),
        "customer_email": payload.get("customer_email"),
        "license_id": payload.get("license_id"),
        "days_remaining": days_remaining,
        "grace_period_active": grace_active,
    })
    return result


def activate_license(token: dict) -> dict:
    """Store a license token after verifying it."""
    payload = token.get("payload", {})
    signature = token.get("signature", "")

    if not _verify_signature(payload, signature):
        return {"ok": False, "error": "Invalid signature"}

    bound = payload.get("machine_fingerprint")
    if bound and bound != get_machine_fingerprint():
        return {"ok": False, "error": "License is bound to a different machine"}

    _save_token(token)
    return {"ok": True, "status": get_license_status()}


def deactivate_license() -> dict:
    """Remove the stored license."""
    if LICENSE_FILE.exists():
        LICENSE_FILE.unlink()
    return {"ok": True, "status": get_license_status()}


def can_use_feature(feature: str) -> bool:
    """Check if a feature is enabled by the current license."""
    status = get_license_status()
    if not status["valid"]:
        return False
    return feature in status["features"]


def get_network_policy() -> str:
    """Return 'blocked', 'annotation', or 'full'."""
    status = get_license_status()
    if not status["valid"]:
        return "blocked"
    return status["network_policy"]
