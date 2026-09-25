"""
Local web tool for minting licenses.
Run this once: python mint_web.py
Open http://localhost:5555 in your browser.
"""
from flask import Flask, request, render_template_string, jsonify
import base64
import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from pathlib import Path

app = Flask(__name__)

# Load private key from .env.mint
def load_private_key():
    env_file = Path(__file__).parent / ".env.mint"
    if not env_file.exists():
        return None
    for line in env_file.read_text().splitlines():
        if line.startswith("LICENSE_PRIVATE_KEY="):
            return line.split("=", 1)[1].strip()
    return None


HTML = """
<!DOCTYPE html>
<html>
<head>
<title>GenomicsOps License Minting</title>
<style>
  body { font-family: system-ui, sans-serif; background: #0f172a; color: #e2e8f0; padding: 40px; max-width: 800px; margin: 0 auto; }
  h1 { color: #10b981; }
  label { display: block; margin-top: 16px; font-size: 13px; color: #94a3b8; }
  input, select, textarea { width: 100%; padding: 10px; background: #1e293b; border: 1px solid #334155; color: #e2e8f0; border-radius: 6px; font-family: inherit; box-sizing: border-box; }
  button { margin-top: 20px; background: #10b981; color: white; padding: 12px 24px; border: none; border-radius: 6px; font-size: 14px; font-weight: 600; cursor: pointer; }
  button:hover { background: #059669; }
  pre { background: #020617; padding: 16px; border-radius: 6px; overflow-x: auto; font-size: 12px; border: 1px solid #1e293b; }
  .error { color: #f87171; }
  .success { color: #10b981; }
</style>
</head>
<body>
  <h1>License Minting</h1>
  <p style="color:#94a3b8;font-size:13px;">Generate a signed license token for a customer. Paste their machine fingerprint below.</p>

  <form id="mintForm">
    <label>Customer email</label>
    <input name="email" type="email" placeholder="lab@example.org" required>

    <label>Tier</label>
    <select name="tier">
      <option value="trial">Trial</option>
      <option value="standard">Standard</option>
      <option value="enterprise">Enterprise</option>
    </select>

    <label>Duration (days)</label>
    <input name="days" type="number" value="365" min="1" required>

    <label>Machine fingerprint</label>
    <input name="fingerprint" placeholder="e.g. 6be3d770e216e75ec672a11a4a13479f" required>

    <button type="submit">Generate License</button>
  </form>

  <div id="result" style="margin-top: 30px;"></div>

<script>
document.getElementById('mintForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const form = new FormData(e.target);
  const data = Object.fromEntries(form);
  const res = await fetch('/api/mint', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(data),
  });
  const json = await res.json();
  const resultDiv = document.getElementById('result');
  if (json.error) {
    resultDiv.innerHTML = '<div class="error">Error: ' + json.error + '</div>';
  } else {
    resultDiv.innerHTML = '<div class="success">✓ License generated. Copy the JSON below and email it to ' + data.email + '</div><pre>' + JSON.stringify(json.token, null, 2) + '</pre><button onclick="copyToken()">Copy to clipboard</button>';
    window._lastToken = JSON.stringify(json.token, null, 2);
  }
});

function copyToken() {
  navigator.clipboard.writeText(window._lastToken);
  alert('Copied!');
}
</script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/api/mint", methods=["POST"])
def mint():
    data = request.get_json()
    private_key_b64 = load_private_key()
    if not private_key_b64:
        return jsonify({"error": "LICENSE_PRIVATE_KEY not found in .env.mint"}), 500

    try:
        private_bytes = base64.b64decode(private_key_b64)
        private_key = Ed25519PrivateKey.from_private_bytes(private_bytes)

        now = datetime.now(timezone.utc)
        expires = now + timedelta(days=int(data["days"]))

        payload = {
            "license_id": str(uuid.uuid4()),
            "customer_email": data["email"],
            "tier": data["tier"],
            "issued_at": now.isoformat().replace("+00:00", "Z"),
            "expires_at": expires.isoformat().replace("+00:00", "Z"),
            "machine_fingerprint": data["fingerprint"],
        }

        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        signature = private_key.sign(canonical)
        signature_b64 = base64.b64encode(signature).decode()

        return jsonify({"token": {"payload": payload, "signature": signature_b64}})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print()
    print("=" * 60)
    print("  License Minting Tool")
    print("  Open http://localhost:5555 in your browser")
    print("=" * 60)
    print()
    app.run(host="127.0.0.1", port=5555, debug=False)
