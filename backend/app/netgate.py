"""
Network gate: single point of control for outbound HTTP.

When settings.is_offline is True, every call through safe_get / safe_post
raises OfflineModeError before any socket is opened.

Every service in the app must use these helpers instead of httpx directly.
"""
import httpx
from typing import Optional, Any


class OfflineModeError(RuntimeError):
    """Raised when an outbound call is attempted while offline mode is active."""
    def __init__(self, url: str):
        super().__init__(
            f"Blocked outbound call to {url} — app is in offline mode. "
            f"Disable OFFLINE_MODE in config to allow network access."
        )
        self.url = url


# Track every attempted outbound call for the audit log
_attempted_calls: list[dict] = []
_blocked_calls: list[dict] = []


def record_attempt(url: str, method: str, blocked: bool):
    entry = {"url": url, "method": method, "blocked": blocked}
    _attempted_calls.append(entry)
    if blocked:
        _blocked_calls.append(entry)
        print(f"[NETGATE] BLOCKED {method} {url}")
    else:
        print(f"[NETGATE] ALLOWED {method} {url}")


def _check_allowed(url: str, method: str = "GET"):
    """Raise if offline mode is active."""
    from app.config import settings
    if settings.is_offline:
        record_attempt(url, method, blocked=True)
        raise OfflineModeError(url)
    record_attempt(url, method, blocked=False)


def safe_get(url: str, **kwargs) -> httpx.Response:
    """httpx.get with offline enforcement."""
    _check_allowed(url, "GET")
    return httpx.get(url, **kwargs)


def safe_post(url: str, **kwargs) -> httpx.Response:
    """httpx.post with offline enforcement."""
    _check_allowed(url, "POST")
    return httpx.post(url, **kwargs)


def safe_client(**kwargs) -> httpx.Client:
    """Return an httpx.Client subclass that enforces offline mode."""
    return _GatedClient(**kwargs)


class _GatedClient(httpx.Client):
    def request(self, method, url, *args, **kwargs):
        _check_allowed(str(url), method)
        return super().request(method, url, *args, **kwargs)


def get_audit_summary() -> dict:
    """Return stats for the /health/offline endpoint."""
    from app.config import settings
    return {
        "offline_mode": settings.is_offline,
        "mode": settings.MODE,
        "attempted_calls": len(_attempted_calls),
        "blocked_calls": len(_blocked_calls),
        "recent_blocked": _blocked_calls[-10:],
    }
