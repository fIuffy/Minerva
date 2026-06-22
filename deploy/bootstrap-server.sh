#!/usr/bin/env bash
# =============================================================================
# Minerva — Vultr Linux instance bootstrap (the environment node, §3).
# Run as root on a FRESH Ubuntu 22.04/24.04 Vultr Cloud Compute instance:
#
#   ssh root@<instance-ip>
#   curl -fsSL https://raw.githubusercontent.com/fIuffy/Minerva/main/deploy/bootstrap-server.sh | bash
#
# Installs Docker + Tailscale, fetches the repo, brings up the TARGET stack, and
# locks the host firewall. Idempotent enough to re-run. Reads optional env:
#   REPO_URL          (default https://github.com/fIuffy/Minerva.git)
#   TAILSCALE_AUTHKEY (skip interactive `tailscale up` auth if provided)
#   SSH_ALLOW_IP      (your IP for the UFW SSH allow; default: anywhere — tighten!)
# =============================================================================
set -euo pipefail
REPO_URL="${REPO_URL:-https://github.com/fIuffy/Minerva.git}"
APP_DIR="/opt/minerva"

echo "[1/6] base packages…"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y ca-certificates curl git ufw

echo "[2/6] Docker engine + compose plugin…"
if ! command -v docker >/dev/null; then
    curl -fsSL https://get.docker.com | sh
fi
docker --version && docker compose version

echo "[3/6] Tailscale…"
if ! command -v tailscale >/dev/null; then
    curl -fsSL https://tailscale.com/install.sh | sh
fi
if [[ -n "${TAILSCALE_AUTHKEY:-}" ]]; then
    tailscale up --authkey "${TAILSCALE_AUTHKEY}" --ssh || true
else
    echo "  -> run 'tailscale up' after this script and open the printed auth URL."
fi

echo "[4/6] fetch the lab…"
if [[ ! -d "$APP_DIR/.git" ]]; then
    git clone "$REPO_URL" "$APP_DIR"
else
    git -C "$APP_DIR" pull --ff-only || true
fi
cd "$APP_DIR"
[[ -f .env ]] || cp .env.example .env
echo "  -> EDIT $APP_DIR/.env : set OLLAMA_BASE_URL=http://<laptop-tailnet-ip>:11434"

echo "[5/6] host firewall (lab ports stay loopback-only; reach them via SSH tunnel)…"
ufw --force reset >/dev/null
ufw default deny incoming
ufw default allow outgoing
if [[ -n "${SSH_ALLOW_IP:-}" ]]; then ufw allow from "${SSH_ALLOW_IP}" to any port 22 proto tcp;
else ufw allow 22/tcp; echo "  !! SSH open to the world — set SSH_ALLOW_IP to your IP and re-run."; fi
ufw allow in on tailscale0
ufw --force enable
ufw status verbose

echo "[6/6] build + start the stack…"
docker compose up -d --build
echo
echo "DONE. Next:"
echo "  1) tailscale up   (if not already) and note this instance's 100.x IP"
echo "  2) on the laptop:  OLLAMA_HOST=0.0.0.0:11434 ollama serve   (note its 100.x IP)"
echo "  3) set OLLAMA_BASE_URL in $APP_DIR/.env to the laptop's 100.x IP, then:"
echo "        docker compose up -d && docker compose run --rm rag-ingest && ./scripts/healthcheck.sh"
echo "  4) add Active Directory — Samba on this instance:"
echo "        docker compose -f docker-compose.yml -f docker-compose.ad.yml up -d --build"
echo "     (or a genuine Windows Server 2022 Vultr instance — see deploy/SETUP.md)"
echo "  5) reach the portal/dashboard from your laptop WITHOUT exposing them:"
echo "        ssh -L 8088:127.0.0.1:8088 -L 8090:127.0.0.1:8090 root@<instance-tailnet-ip>"
echo "  6) END OF SESSION: snapshot then DESTROY (powering off still bills) — see deploy/SETUP.md"
