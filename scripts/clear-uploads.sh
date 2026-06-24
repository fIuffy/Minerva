#!/usr/bin/env bash
# =============================================================================
# Clear UPLOADED documents without a full reset — removes only the `upload:*`
# rows from the retrieval store (pgvector), the MySQL doc store, and the raw
# files, leaving the seed corpus intact. No container restart, no re-ingest.
#
# Use this for fast iteration while crafting/testing injection documents.
# Use scripts/reset.sh for a FORMAL clean-state scenario (§6) — it drops all
# volumes and rebuilds, guaranteeing nothing at all carries over.
# =============================================================================
set -euo pipefail
cd "$(dirname "$0")/.."

echo "[clear-uploads] removing upload:* chunks from pgvector (retrieval store)…"
docker compose exec -T postgres psql -U "${POSTGRES_USER:-portal_svc}" \
  -d "${POSTGRES_DB:-statedata}" -c "DELETE FROM rag_chunks WHERE source LIKE 'upload:%';"

echo "[clear-uploads] removing upload:* rows from the MySQL doc store…"
docker compose exec -T mysql mysql -u "${MYSQL_USER:-docstore_svc}" \
  -p"${MYSQL_PASSWORD:-docstore_svc_pw}" "${MYSQL_DATABASE:-docstore}" \
  -e "DELETE FROM documents WHERE source LIKE 'upload:%';" 2>/dev/null || true

echo "[clear-uploads] clearing raw uploaded files…"
docker compose exec -T tier2-portal sh -c 'rm -f /app/uploads/*' 2>/dev/null || true

echo "[clear-uploads] done. Remaining sources in the retrieval store:"
docker compose exec -T postgres psql -U "${POSTGRES_USER:-portal_svc}" \
  -d "${POSTGRES_DB:-statedata}" -c "SELECT source, count(*) FROM rag_chunks GROUP BY source ORDER BY source;"
