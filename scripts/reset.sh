#!/usr/bin/env bash
# =============================================================================
# Clean-state scenario reset (§6 Execution Discipline).
# "Every attack scenario runs against a freshly recreated stack. Observations
#  from one run never contaminate the next."
#
#   ./scripts/reset.sh            # base droplet stack
#   ./scripts/reset.sh --with-ad  # include the Samba AD DC fallback overlay
# =============================================================================
set -euo pipefail
cd "$(dirname "$0")/.."

FILES=(-f docker-compose.yml)
if [[ "${1:-}" == "--with-ad" ]]; then
    FILES+=(-f docker-compose.ad.yml)
fi

echo "[reset] tearing down (dropping volumes for a pristine state)…"
docker compose "${FILES[@]}" down -v --remove-orphans

echo "[reset] recreating stack…"
docker compose "${FILES[@]}" up -d

echo "[reset] waiting for tiers to report healthy…"
"$(dirname "$0")/healthcheck.sh" || echo "[reset] (some services still starting)"

echo "[reset] rebuilding RAG vector store from the document store…"
if ! docker compose "${FILES[@]}" run --rm rag-ingest; then
    echo "[reset] WARN: rag-ingest failed — is Ollama reachable at OLLAMA_BASE_URL? (§9)"
fi

echo "[reset] current state:"
docker compose "${FILES[@]}" ps
echo "[reset] done. Stack is pristine and ready for the next scenario."
