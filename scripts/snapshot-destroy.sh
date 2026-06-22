#!/usr/bin/env bash
# =============================================================================
# END-OF-SESSION cost discipline (§3) — all-Vultr.
#
# Vultr bills an instance for as long as it EXISTS; powering off does NOT stop
# billing — only destroying does. This snapshots, then DESTROYS each instance;
# recreate from the snapshot at the next session. This is the single most
# important cost rule in the project.
#
# Usage (IDs from `vultr-cli instance list`):
#   VULTR_INSTANCE_IDS="<linux-id> <windows-id>" ./scripts/snapshot-destroy.sh
#
# Requires: vultr-cli (winget install Vultr.CLI) with VULTR_API_KEY set.
# DRY_RUN=1 prints actions without executing. ASSUME_YES=1 skips confirmation.
# =============================================================================
set -euo pipefail

STAMP="lab-$(date +%F-%H%M)"
DRY="${DRY_RUN:-0}"
IDS="${VULTR_INSTANCE_IDS:-}"

run() {
    if [[ "$DRY" == "1" ]]; then echo "  DRY-RUN> $*"; else echo "  > $*"; "$@"; fi
}
confirm() {
    [[ "${ASSUME_YES:-0}" == "1" ]] && return 0
    read -r -p "$1 [type DESTROY to proceed] " ans
    [[ "$ans" == "DESTROY" ]] || { echo "aborted."; exit 1; }
}

[[ -n "$IDS" ]] || {
    echo "Set VULTR_INSTANCE_IDS=\"id1 id2\" (list them with: vultr-cli instance list)"; exit 1; }
command -v vultr-cli >/dev/null || {
    echo "vultr-cli not found — winget install Vultr.CLI, then set VULTR_API_KEY"; exit 1; }

echo "[1/3] snapshotting each instance (snapshot label: $STAMP)…"
for id in $IDS; do
    run vultr-cli snapshot create --id "$id" --description "$STAMP-$id"
done

echo "[2/3] wait until EVERY snapshot reports 'complete' before destroying:"
echo "        vultr-cli snapshot list"
confirm "All snapshots complete — DESTROY all listed instances now?"

echo "[3/3] destroying…"
for id in $IDS; do
    run vultr-cli instance delete "$id"
    echo "  destroyed $id"
done

echo
echo "Verify in the Vultr console that NO instance remains (powered-off still bills)."
echo "Account spending limit + billing alert (\$40) are the backstop (§3)."
echo "Next session, recreate from a snapshot:"
echo "  vultr-cli instance create --region <r> --plan <p> --snapshot <snapshot-id>"
