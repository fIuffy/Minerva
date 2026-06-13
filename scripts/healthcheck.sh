#!/usr/bin/env bash
# =============================================================================
# Confirm all tiers are healthy before a scenario runs (§6 "confirm all tiers
# healthy"). Exits non-zero if any required check fails.
# =============================================================================
set -uo pipefail
cd "$(dirname "$0")/.."

fail=0
check() {  # name, command...
    local name="$1"; shift
    if "$@" >/dev/null 2>&1; then
        printf '  \033[32m✓\033[0m %s\n' "$name"
    else
        printf '  \033[31m✗\033[0m %s\n' "$name"
        fail=1
    fi
}

echo "[healthcheck] container states:"
docker compose ps --format '  {{.Name}}\t{{.Status}}' 2>/dev/null || docker compose ps

echo "[healthcheck] endpoint probes:"
check "Tier 2 portal  (/healthz)"   curl -fsS http://127.0.0.1:8088/healthz
# Health is on Keycloak's internal mgmt port (9000); from the host, the realm's
# OIDC discovery doc on 8080 confirms Keycloak is up AND the realm imported.
check "Keycloak realm (statefed discovery)" \
        curl -fsS http://127.0.0.1:8080/realms/statefed/.well-known/openid-configuration

# Internal services (no host ports) — probe from inside the edge container.
check "fed-gateway   (internal)"    docker compose exec -T tier2-portal \
        python -c "import urllib.request as u; u.urlopen('http://fed-gateway:8000/healthz')"
check "Tier 1 isolation (portal must NOT reach net_federal directly)" bash -c '
    ! docker compose exec -T tier2-portal python -c "import socket; socket.create_connection((\"tier1-api\",8000),2)" 2>/dev/null'

if [[ $fail -eq 0 ]]; then
    echo "[healthcheck] all checks passed."
else
    echo "[healthcheck] one or more checks FAILED." >&2
fi
exit $fail
