# =============================================================================
# Confirm all tiers are healthy (§6) — PowerShell, for local Windows dev.
# =============================================================================
$ErrorActionPreference = "Continue"
Set-Location (Join-Path $PSScriptRoot "..")
$fail = $false

function Check($name, $scriptblock) {
    try { & $scriptblock | Out-Null; Write-Host "  [OK]   $name" -ForegroundColor Green }
    catch { Write-Host "  [FAIL] $name" -ForegroundColor Red; $script:fail = $true }
}

Write-Host "[healthcheck] container states:"
docker compose ps

Write-Host "[healthcheck] endpoint probes:"
Check "Tier 2 portal  (/healthz)"        { Invoke-RestMethod http://127.0.0.1:8088/healthz }
Check "Keycloak realm (statefed discovery)" { Invoke-RestMethod http://127.0.0.1:8080/realms/statefed/.well-known/openid-configuration }
Check "fed-gateway (internal)"           { docker compose exec -T tier2-portal python -c "import urllib.request as u; u.urlopen('http://fed-gateway:8000/healthz')" }

if (-not $fail) { Write-Host "[healthcheck] all checks passed." -ForegroundColor Green }
else { Write-Host "[healthcheck] one or more checks FAILED." -ForegroundColor Red; exit 1 }
