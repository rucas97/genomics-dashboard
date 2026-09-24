"""
Test that offline mode actually blocks outbound calls.
Run: python -m tests.test_offline_gate
"""
import os
os.environ["MODE"] = "local"
os.environ["OFFLINE_MODE"] = "true"

from app.config import settings
from app.netgate import safe_get, OfflineModeError


def test_offline_blocks_http():
    assert settings.is_offline, "offline mode should be True in this test"

    try:
        safe_get("https://example.com")
        print("✗ FAIL: outbound call was not blocked")
        return False
    except OfflineModeError as e:
        assert "example.com" in str(e)
        print(f"✓ PASS: blocked call to example.com")
        return True


def test_offline_can_be_disabled():
    os.environ["OFFLINE_MODE"] = "false"
    # Re-instantiate settings
    from importlib import reload
    import app.config
    reload(app.config)

    fresh = app.config.Settings()
    assert not fresh.is_offline, "offline should be disabled when OFFLINE_MODE=false"
    print("✓ PASS: offline mode can be disabled via env")


if __name__ == "__main__":
    print("Running offline gate tests...")
    test_offline_blocks_http()
    test_offline_can_be_disabled()
    print("Done.")
