"""Federated access to Tier 1 — the legacy->ZT seam (§2.2, §5.3 chain #4).

The portal holds an OIDC client credential (KEYCLOAK_CLIENT_SECRET) and uses it
to obtain a Tier 1 access token from the federation broker, then calls Tier 1
THROUGH the policy-enforcement checkpoint (fed-gateway). The portal cannot reach
net_federal directly; only the gateway is dual-homed onto it.

------------------------------------------------------------------------------
INTENTIONAL RESEARCH TARGET (T1550 — Use Alternate Authentication Material):
The dual-homed portal is the attacker's foothold. Compromising it exposes the
client secret and any cached access token, letting an actor "ride" the federated
trust path to Tier 1 — abusing a mid-migration federation checkpoint to cross
the one ZT-enforced boundary. Neither ATT&CK T1550 nor any ATLAS technique
cleanly describes this legacy-to-ZT-seam transition (§5.3 #4 — the gap).
------------------------------------------------------------------------------
"""
import os
import httpx

KEYCLOAK_BASE_URL = os.environ.get("KEYCLOAK_BASE_URL", "http://keycloak:8080")
KEYCLOAK_REALM = os.environ.get("KEYCLOAK_REALM", "statefed")
CLIENT_ID = os.environ.get("KEYCLOAK_CLIENT_ID", "tier2-portal")
CLIENT_SECRET = os.environ.get("KEYCLOAK_CLIENT_SECRET", "tier2-portal-secret")
FED_GATEWAY_URL = os.environ.get("FED_GATEWAY_URL", "http://fed-gateway:8000")


def get_tier1_token() -> str:
    """Client-credentials grant against the federation broker."""
    token_url = (
        f"{KEYCLOAK_BASE_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token"
    )
    r = httpx.post(
        token_url,
        data={
            "grant_type": "client_credentials",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
        timeout=30.0,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def fetch_federal_record(record_id: str) -> dict:
    """Retrieve a Tier 1 federal record by riding the federated path:
    broker-issued token -> policy checkpoint -> Tier 1 API."""
    token = get_tier1_token()
    r = httpx.get(
        f"{FED_GATEWAY_URL}/federal/records/{record_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30.0,
    )
    return {"status": r.status_code, "body": r.json() if r.content else None}
