"""
Network gate: single point of control for outbound HTTP.

Policies (from license tier):
- "blocked"    — all outbound calls raise
- "annotation" — only whitelisted annotation hosts allowed
- "full"       — all outbound allowed

The policy comes from the license system. Unlicensed = blocked.
"""
import httpx
from urllib.parse import urlparse
from typing import Optional


class OfflineModeError(RuntimeError):
    def __init__(self, url: str, policy: str = "blocked"):
        super().__init__(
            f"Blocked outbound call to {url} — network policy is '{policy}'. "
            f"Activate a license to enable annotation."
        )
        self.url = url
        self.policy = policy


# Hosts allowed under "annotation" policy
ANNOTATION_HOSTS = {
    "myvariant.info",
    "rest.ensembl.org",
    "eutils.ncbi.nlm.nih.gov",
    "ftp.ensembl.org",
    "ftp.ncbi.nlm.nih.gov",
}


_attempted_calls: list[dict] = []
_blocked_calls: list[dict] = []


def _host_allowed(url: str, policy: str) -> bool:
    if policy == "full":
        return True
    if policy == "blocked":
        return False
    if policy == "annotation":
        host = urlparse(url).hostname or ""
        return any(host.endswith(h) for h in ANNOTATION_HOSTS)
    return False


def _check_allowed(url: str, method: str = "GET"):
    from app.services.license import get_network_policy
    policy = get_network_policy()

    allowed = _host_allowed(url, policy)
    entry = {"url": url, "method": method, "policy": policy, "allowed": allowed}
    _attempted_calls.append(entry)
    if not allowed:
        _blocked_calls.append(entry)
        print(f"[NETGATE] BLOCKED {method} {url} (policy={policy})")
        raise OfflineModeError(url, policy)
    print(f"[NETGATE] ALLOWED {method} {url} (policy={policy})")


def safe_get(url: str, **kwargs) -> httpx.Response:
    _check_allowed(url, "GET")
    return httpx.get(url, **kwargs)


def safe_post(url: str, **kwargs) -> httpx.Response:
    _check_allowed(url, "POST")
    return httpx.post(url, **kwargs)


def safe_client(**kwargs) -> httpx.Client:
    return _GatedClient(**kwargs)


class _GatedClient(httpx.Client):
    def request(self, method, url, *args, **kwargs):
        _check_allowed(str(url), method)
        return super().request(method, url, *args, **kwargs)


def get_audit_summary() -> dict:
    from app.services.license import get_license_status
    status = get_license_status()
    return {
        "license_tier": status["tier"],
        "license_valid": status["valid"],
        "network_policy": status["network_policy"],
        "attempted_calls": len(_attempted_calls),
        "blocked_calls": len(_blocked_calls),
        "recent_blocked": _blocked_calls[-10:],
    }
