# =============================================================================
# Clean-state scenario reset (§6) — PowerShell, for local Windows dev standup.
#   .\scripts\reset.ps1            # base droplet stack
#   .\scripts\reset.ps1 -WithAd   # include the Samba AD DC fallback overlay
# =============================================================================
param([switch]$WithAd)
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

$files = @("-f", "docker-compose.yml")
if ($WithAd) { $files += @("-f", "docker-compose.ad.yml") }

Write-Host "[reset] tearing down (dropping volumes)…"
docker compose @files down -v --remove-orphans

Write-Host "[reset] recreating stack…"
docker compose @files up -d

Write-Host "[reset] rebuilding RAG vector store from the document store…"
docker compose @files run --rm rag-ingest
if ($LASTEXITCODE -ne 0) {
    Write-Host "[reset] WARN: rag-ingest failed — is Ollama reachable at OLLAMA_BASE_URL? (§9)"
}

docker compose @files ps
Write-Host "[reset] done. Stack is pristine and ready for the next scenario."
