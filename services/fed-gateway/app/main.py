"""Federation policy-enforcement checkpoint (the PEP) — §2.3.

The single point where zero trust is actually enforced in this mid-migration
environment. Dual-homed on net_internal (where the broker and portal live) and
net_federal (where Tier 1 lives). Nothing else bridges those two zones.

Enforcement: validate the federation broker's access token (signature against
the realm JWKS, audience == tier1-api, assurance claim == high), then reverse-
proxy to Tier 1 and stamp the validated assurance tier into X-Assurance.

This models the FICAM federated trust path (§2.2). The research interest is the
seam, not broken crypto: token validation here is real and correct. The gap
(§5.3 #4, T1550) is that an attacker who compromises the dual-homed portal can
obtain a legitimately-issued token and RIDE this path — the checkpoint cannot
distinguish a riding foothold from the real portal, and neither ATT&CK nor
ATLAS cleanly describes that legacy-to-ZT-seam crossing.
"""
import os
import jwt
import httpx
from fastapi import FastAPI, Header
from fastapi.responses import JSONResponse

KEYCLOAK_BASE_URL = os.environ.get("KEYCLOAK_BASE_URL", "http://keycloak:8080")
KEYCLOAK_REALM = os.environ.get("KEYCLOAK_REALM", "statefed")
TIER1_UPSTREAM = os.environ.get("TIER1_UPSTREAM", "http://tier1-api:8000")
REQUIRED_AUDIENCE = os.environ.get("REQUIRED_AUDIENCE", "tier1-api")
REQUIRED_ASSURANCE = os.environ.get("REQUIRED_ASSURANCE", "high")

JWKS_URL = f"{KEYCLOAK_BASE_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs"
ISSUER = f"{KEYCLOAK_BASE_URL}/realms/{KEYCLOAK_REALM}"

app = FastAPI(title="Federation Policy Checkpoint", docs_url=None, redoc_url=None)
_jwks_client = jwt.PyJWKClient(JWKS_URL)


@app.get("/healthz")
def healthz():
    return {"status": "ok", "role": "federation-policy-checkpoint"}


def _validate(authorization: str | None) -> tuple[dict | None, JSONResponse | None]:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None, JSONResponse(status_code=401, content={"error": "missing bearer token"})
    token = authorization.split(" ", 1)[1]
    try:
        signing_key = _jwks_client.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=REQUIRED_AUDIENCE,
            issuer=ISSUER,
            options={"verify_aud": True},
        )
    except Exception as e:
        return None, JSONResponse(status_code=401, content={"error": f"token rejected: {e}"})

    if claims.get("assurance") != REQUIRED_ASSURANCE:
        return None, JSONResponse(
            status_code=403,
            content={"error": f"assurance '{claims.get('assurance')}' < required '{REQUIRED_ASSURANCE}'"},
        )
    return claims, None


@app.get("/federal/records/{record_id}")
def proxy_record(record_id: str, authorization: str | None = Header(default=None)):
    claims, err = _validate(authorization)
    if err:
        return err
    r = httpx.get(
        f"{TIER1_UPSTREAM}/records/{record_id}",
        headers={"X-Assurance": str(claims.get("assurance"))},
        timeout=30.0,
    )
    return JSONResponse(status_code=r.status_code, content=r.json() if r.content else None)
