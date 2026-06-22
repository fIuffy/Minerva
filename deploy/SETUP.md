# Cloud Setup — Vultr (§3)

This guide deploys the lab on **Vultr**: a Linux Cloud Compute instance (the
Docker environment), an optional Windows Server 2022 instance (genuine Active
Directory), and the researcher's laptop (Ollama GPU inference), joined privately
over **Tailscale**. A single provider keeps billing and teardown in one place.
Projected cloud spend under snapshot-and-destroy discipline is approximately
$30–40 for the full project period, within the $150 cloud allocation.

Provisioning, account setup, Tailscale authentication, and the snapshot/destroy
lifecycle are performed by the operator; the bootstrap script automates the
on-host configuration. Keeping these steps under direct operator control is the
basis of the cost and containment guarantees in §3 and §7.

> Provider note: the protocol references a two-provider split (a DigitalOcean
> Linux node plus a Vultr Windows node). This deployment consolidates both onto
> Vultr; the three-tier segmented architecture and the gap-analysis role of every
> component are unchanged (a documented build substitution, §2.5).

---

## 1. Provisioning requirements

### Minimal (FLOOR) deployment — single Linux instance
The entire Docker stack and the Samba AD fallback run on one Vultr Linux
instance, with Ollama on the researcher's laptop. The lowest-cost configuration.

| Component | Specification | Reference | Approx. cost |
|-----------|---------------|-----------|--------------|
| Vultr Cloud Compute (Linux) | Ubuntu 24.04, 2 vCPU / 4 GB (FLOOR) or 4 vCPU / 8 GB (TARGET) | [deploy](https://my.vultr.com/deploy/) · [pricing](https://www.vultr.com/pricing/) | ~$24/mo (FLOOR) to ~$48/mo (TARGET); ≈ $10–19 under snapshot+destroy |
| Tailscale | Personal tier (free) | [login.tailscale.com/start](https://login.tailscale.com/start) | $0 |
| Researcher laptop (Ollama) | RTX 4050 (6 GB) or comparable | provided | $0 |

### Full-fidelity deployment — genuine Windows AD (optional)
A second Vultr instance running genuine Active Directory.

| Component | Specification | Reference | Approx. cost |
|-----------|---------------|-----------|--------------|
| Vultr Cloud Compute (Windows) | Windows Server 2022, ~2 vCPU / 4 GB | [deploy](https://my.vultr.com/deploy/) · [pricing](https://www.vultr.com/pricing/) | ~$0.07/hr + license (≈ $11–20, AD weeks only) |

Confirm current pricing at checkout. Sign-up: [Vultr](https://www.vultr.com/).
Accepted payment includes cards, PayPal, and crypto via BitPay
([methods](https://docs.vultr.com/support/platform/billing/what-payment-methods-do-you-accept)).

---

## 2. Cost guardrails (configure before provisioning)
1. **Account spending limit** — [console.vultr.com/billing](https://console.vultr.com/billing) →
   **Limits** → set a **Maximum Instance Cost** (e.g. $70). Vultr will not provision
   beyond it — a hard cap, not just a notice.
2. **Billing alert / notifications** — [console.vultr.com/settings](https://console.vultr.com/settings/#settingsusers).
3. Vultr bills an instance for as long as it exists; **powering off does not stop
   billing — only destroying does** (§3). The snapshot-and-destroy lifecycle in
   §8 is what keeps spend at the projected figure.

## 3. Provision the Linux instance
On [my.vultr.com/deploy](https://my.vultr.com/deploy/): Cloud Compute, Ubuntu 24.04,
the chosen plan, with an SSH key attached. Restrict inbound access to SSH from the
researcher's IP using Vultr's firewall; lab ports are never exposed publicly.

## 4. Bootstrap the instance
```bash
ssh root@<instance-ip>
curl -fsSL https://raw.githubusercontent.com/fIuffy/Minerva/main/deploy/bootstrap-server.sh | bash
```
The script installs Docker and Tailscale, clones the repository to `/opt/minerva`,
builds the stack, and locks UFW to SSH and the tailnet only. Then authenticate to
the tailnet:
```bash
tailscale up          # open the printed auth URL; record this instance's 100.x address
```

## 5. Configure inference (laptop Ollama over the tailnet)
On the laptop (with Tailscale and Ollama installed):
```powershell
setx OLLAMA_HOST "0.0.0.0:11434"   # restart Ollama afterward; `tailscale ip -4` shows the 100.x address
```
On the instance, point the stack at the laptop and relaunch:
```bash
cd /opt/minerva
sed -i 's#^OLLAMA_BASE_URL=.*#OLLAMA_BASE_URL=http://<laptop-tailnet-ip>:11434#' .env
docker compose up -d
docker compose run --rm rag-ingest
./scripts/healthcheck.sh
```

## 6. Add Active Directory
- Samba fallback, on the Linux instance:
  ```bash
  docker compose -f docker-compose.yml -f docker-compose.ad.yml up -d --build
  ```
- Genuine Windows, on a second Vultr instance: deploy Windows Server 2022, install
  Tailscale, then promote a domain controller and seed the domain to match the lab
  in an elevated PowerShell session:
  ```powershell
  Install-WindowsFeature AD-Domain-Services -IncludeManagementTools
  Install-ADDSForest -DomainName "statefed.lab" -InstallDns -SafeModeAdministratorPassword (ConvertTo-SecureString "Sup3rS3cret-Admin!" -AsPlainText -Force) -Force
  # after reboot — kerberoastable and DCSync-capable accounts:
  New-ADUser -Name svc_sql -SamAccountName svc_sql -AccountPassword (ConvertTo-SecureString "Summer2026" -AsPlainText -Force) -Enabled $true -ServicePrincipalNames "MSSQLSvc/statedata.statefed.lab:1433"
  New-ADUser -Name backup_admin -SamAccountName backup_admin -AccountPassword (ConvertTo-SecureString "Backup-Adm1n-2026" -AsPlainText -Force) -Enabled $true
  Add-ADGroupMember -Identity "Domain Admins" -Members backup_admin
  ```

## 7. Access the portal and dashboard
Lab ports remain bound to `127.0.0.1` on the instance. Forward them over SSH rather
than exposing them:
```bash
ssh -L 8088:127.0.0.1:8088 -L 8090:127.0.0.1:8090 root@<instance-tailnet-ip>
# laptop: http://127.0.0.1:8088 (portal) · http://127.0.0.1:8090 (dashboard)
```

## 8. End-of-session cost discipline (§3)
Powering off does not stop Vultr billing. Snapshot, then destroy every instance,
and recreate from the snapshot at the next session.
```bash
# copy any captures off the instance first (scp), then list IDs and tear down:
vultr-cli instance list
VULTR_INSTANCE_IDS="<linux-id> <windows-id>" ./scripts/snapshot-destroy.sh
```
Confirm in the Vultr console that no instance remains. Recreate next session:
```bash
vultr-cli instance create --region <r> --plan <p> --snapshot <snapshot-id>
```
`scripts/reset.sh` returns a recreated instance to a clean stack.

## 9. End-to-end validation
- `./scripts/healthcheck.sh` reports healthy; the portal answers `/ask` (RAG via the laptop GPU).
- Federated chain: `curl http://127.0.0.1:8088/federal/F-100277` returns a record with `assurance: high`.
- The AD node is reachable over the tailnet (Samba: `docker compose exec samba-ad samba-tool user list`).
