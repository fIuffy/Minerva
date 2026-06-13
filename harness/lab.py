"""Lab target execution with hard containment (§7).

This is the ONLY module that touches a target, and it refuses any host that is
not an explicitly allowlisted lab endpoint. Repointing the harness at a system
you do not own violates the containment principle and is out of scope — the
allowlist makes that a code-level guarantee, not a guideline.
"""
from __future__ import annotations
import os
from urllib.parse import urlparse
import httpx

LAB_BASE_URL = os.environ.get("LAB_BASE_URL", "http://127.0.0.1:8088").rstrip("/")

# Only these hosts may ever be targeted. Add a lab tailnet host via
# LAB_ALLOWED_HOSTS="100.x.y.z,dc1.statefed.lab" if driving the real mesh.
_DEFAULT_ALLOWED = {"127.0.0.1", "localhost", "::1"}
LAB_ALLOWED_HOSTS = _DEFAULT_ALLOWED | {
    h.strip() for h in os.environ.get("LAB_ALLOWED_HOSTS", "").split(",") if h.strip()
}


class ContainmentError(RuntimeError):
    """Raised when an action would touch a non-lab host."""


def _guard(url: str) -> None:
    host = urlparse(url).hostname
    if host not in LAB_ALLOWED_HOSTS:
        raise ContainmentError(
            f"REFUSED: '{host}' is not an allowlisted lab host {sorted(LAB_ALLOWED_HOSTS)}. "
            f"The harness only targets the self-owned lab (§7)."
        )


def execute(method: str, path: str, *, params=None, data=None, files=None) -> dict:
    """Send one researcher-approved request to the lab. Returns status + body."""
    url = LAB_BASE_URL + path
    _guard(url)
    with httpx.Client(timeout=300.0) as client:
        r = client.request(method.upper(), url, params=params, data=data, files=files)
    try:
        body = r.json()
    except Exception:
        body = r.text
    return {"url": str(r.request.url), "method": method.upper(),
            "status": r.status_code, "body": body}
