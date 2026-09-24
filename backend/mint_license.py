"""
License minting tool. Run this to generate a license token for a customer.

Usage:
    python mint_license.py \
      --email customer@lab.org \
      --tier standard \
      --days 365 \
      --fingerprint <customer-machine-fingerprint> \
      --private-key <base64-private-key>

Outputs a JSON token to stdout. Email it to the customer.
"""
import argparse
import base64
import json
import sys
import uuid
from datetime import datetime, timedelta, timezone

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def mint(email, tier, days, fingerprint, private_key_b64, license_id=None):
    private_bytes = base64.b64decode(private_key_b64)
    private_key = Ed25519PrivateKey.from_private_bytes(private_bytes)

    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=days)

    payload = {
        "license_id": license_id or str(uuid.uuid4()),
        "customer_email": email,
        "tier": tier,
        "issued_at": now.isoformat().replace("+00:00", "Z"),
        "expires_at": expires.isoformat().replace("+00:00", "Z"),
        "machine_fingerprint": fingerprint,
    }

    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    signature = private_key.sign(canonical)
    signature_b64 = base64.b64encode(signature).decode()

    return {
        "payload": payload,
        "signature": signature_b64,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--tier", required=True, choices=["trial", "standard", "enterprise"])
    parser.add_argument("--days", type=int, required=True)
    parser.add_argument("--fingerprint", required=True)
    parser.add_argument("--private-key", required=True, help="Base64 private key")
    parser.add_argument("--license-id", default=None)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    token = mint(
        email=args.email,
        tier=args.tier,
        days=args.days,
        fingerprint=args.fingerprint,
        private_key_b64=args.private_key,
        license_id=args.license_id,
    )

    if args.pretty:
        print(json.dumps(token, indent=2))
    else:
        print(json.dumps(token))


if __name__ == "__main__":
    main()
