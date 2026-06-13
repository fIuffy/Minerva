#!/usr/bin/env bash
# =============================================================================
# END-OF-SESSION cost discipline (§3 / §6) — the single most important cost rule.
#
# "Powering off does NOT stop billing on either provider. SNAPSHOT THEN DESTROY
#  between sessions on both; recreate from the snapshot next session." Ignoring
#  this on the Windows node is the difference between ~$15 and ~$106 (§3.2).
#
# This is DESTRUCTIVE. It snapshots, then DESTROYS the cloud nodes. You recreate
# from the snapshot at the start of the next session. Pass IDs explicitly:
#
#   DO_DROPLET_ID=12345678 VULTR_INSTANCE_ID=abcd-… ./scripts/snapshot-destroy.sh
#
# Requires: doctl (authenticated) and/or vultr-cli (VULTR_API_KEY set).
# Set DRY_RUN=1 to print actions without executing.
# =============================================================================
set -euo pipefail

STAMP="lab-$(date +%F-%H%M)"
DRY="${DRY_RUN:-0}"

run() {
    if [[ "$DRY" == "1" ]]; then echo "  DRY-RUN> $*"; else echo "  > $*"; "$@"; fi
}

confirm() {
    [[ "${ASSUME_YES:-0}" == "1" ]] && return 0
    read -r -p "$1 [type DESTROY to proceed] " ans
    [[ "$ans" == "DESTROY" ]] || { echo "aborted."; exit 1; }
}

# ---- DigitalOcean droplet (environment node) --------------------------------
if [[ -n "${DO_DROPLET_ID:-}" ]]; then
    command -v doctl >/dev/null || { echo "doctl not found"; exit 1; }
    echo "[DO] snapshot then destroy droplet $DO_DROPLET_ID (snapshot: $STAMP)"
    confirm "[DO] DESTROY droplet $DO_DROPLET_ID after snapshot?"
    run doctl compute droplet-action snapshot "$DO_DROPLET_ID" \
        --snapshot-name "$STAMP" --wait
    run doctl compute droplet delete "$DO_DROPLET_ID" --force
    echo "[DO] destroyed. Recreate next session from snapshot '$STAMP'."
else
    echo "[DO] DO_DROPLET_ID unset — skipping DigitalOcean."
fi

# ---- Vultr Windows AD node --------------------------------------------------
if [[ -n "${VULTR_INSTANCE_ID:-}" ]]; then
    command -v vultr-cli >/dev/null || { echo "vultr-cli not found"; exit 1; }
    echo "[Vultr] snapshot then destroy instance $VULTR_INSTANCE_ID"
    confirm "[Vultr] DESTROY instance $VULTR_INSTANCE_ID after snapshot?"
    run vultr-cli snapshot create --id "$VULTR_INSTANCE_ID" --description "$STAMP"
    echo "[Vultr] WAIT for snapshot to reach 'complete' before destroying:"
    echo "        vultr-cli snapshot list"
    confirm "[Vultr] snapshot complete — DESTROY instance now?"
    run vultr-cli instance delete "$VULTR_INSTANCE_ID"
    echo "[Vultr] destroyed. Recreate next session from snapshot '$STAMP'."
else
    echo "[Vultr] VULTR_INSTANCE_ID unset — skipping Vultr."
fi

echo
echo "Reminder (§3 hard guardrails): verify in BOTH provider consoles that no"
echo "instance is merely powered-off — powered-off still bills. Billing alerts:"
echo "DO \$50 / Vultr \$40. Combined cloud has ~\$110+ headroom by design."
