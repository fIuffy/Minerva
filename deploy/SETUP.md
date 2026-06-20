# Cloud Setup — three-node mesh (§3)

This guide deploys the lab across the three-node mesh: a **DigitalOcean droplet**
(the Docker environment), an optional **Vultr Windows** node (genuine Active
Directory), and the **researcher's laptop** (Ollama GPU inference), joined
privately over **Tailscale**. Projected cloud spend under snapshot-and-destroy
discipline is approximately $30–40 for the full project period, within the $150
cloud allocation.

Provisioning, account setup, Tailscale authentication, and the snapshot/destroy
lifecycle are performed by the operator; the bootstrap script automates the
on-host configuration. Keeping these steps under direct operator control is the
basis of the cost and containment guarantees in §3 and §7.

---

## 1. Provisioning requirements

### Minimal (FLOOR) deployment — single host
The entire Docker stack and the Samba AD fallback run on a single droplet, with
Ollama on the researcher's laptop. This is the lowest-cost configuration.

| Component | Specification | Reference | Approx. cost |
|-----------|---------------|-----------|--------------|
| DigitalOcean droplet | Basic, 8 GB / 4 vCPU, Ubuntu 24.04 | [create](https://cloud.digitalocean.com/droplets/new) · [pricing](https://www.digitalocean.com/pricing/droplets) | $48/mo (≈ $19 under snapshot+destroy) |
| Tailscale | Personal tier (free) | [login.tailscale.com/start](https://login.tailscale.com/start) | $0 |
| Researcher laptop (Ollama) | RTX 4050 (6 GB) or comparable | provided | $0 |

### Full-fidelity deployment — genuine Windows AD (optional)
The protocol's preferred legacy-trust node.

| Component | Specification | Reference | Approx. cost |
|-----------|---------------|-----------|--------------|
| Vultr Cloud Compute | Windows Server 2022, ~2 vCPU / 4 GB | [deploy](https://my.vultr.com/deploy/) · [pricing](https://www.vultr.com/pricing/) | ~$0.07/hr + license (≈ $11–20, AD weeks only) |

Cost figures reflect the protocol's June-2026 verified pricing; confirm current
pricing at checkout. Sign-up: [DigitalOcean](https://www.digitalocean.com/) ·
[Vultr](https://www.vultr.com/). Configure billing alerts before provisioning —
DigitalOcean $50, Vultr $40 (§3 hard guardrail).

---

## 2. Provision the droplet
1. Create a droplet: Ubuntu 24.04, Basic / 8 GB / 4 vCPU, a region near the
   researcher, with an SSH key attached.
2. Attach a DigitalOcean Cloud Firewall: inbound SSH (22) restricted to the
   researcher's IP; all other inbound denied. Lab ports are never exposed publicly.

## 3. Bootstrap the droplet
```bash
ssh root@<droplet-ip>
curl -fsSL https://raw.githubusercontent.com/fIuffy/Minerva/main/deploy/bootstrap-droplet.sh | bash
```
The script installs Docker and Tailscale, clones the repository to `/opt/minerva`,
builds the stack, and locks UFW to SSH and the tailnet only. Then authenticate to
the tailnet:
```bash
tailscale up          # open the printed auth URL; record this node's 100.x address
```

## 4. Configure inference (laptop Ollama over the tailnet)
On the laptop (with Tailscale and Ollama installed):
```powershell
setx OLLAMA_HOST "0.0.0.0:11434"   # restart Ollama afterward; `tailscale ip -4` shows the 100.x address
```
On the droplet, point the stack at the laptop and relaunch:
```bash
cd /opt/minerva
sed -i 's#^OLLAMA_BASE_URL=.*#OLLAMA_BASE_URL=http://<laptop-tailnet-ip>:11434#' .env
docker compose up -d
docker compose run --rm rag-ingest
./scripts/healthcheck.sh
```

## 5. Add Active Directory
- Samba fallback, on the droplet:
  ```bash
  docker compose -f docker-compose.yml -f docker-compose.ad.yml up -d --build
  ```
- Genuine Windows, on a Vultr node: deploy Windows Server 2022, install Tailscale,
  then promote a domain controller and seed the domain to match the lab in an
  elevated PowerShell session:
  ```powershell
  Install-WindowsFeature AD-Domain-Services -IncludeManagementTools
  Install-ADDSForest -DomainName "statefed.lab" -InstallDns -SafeModeAdministratorPassword (ConvertTo-SecureString "Sup3rS3cret-Admin!" -AsPlainText -Force) -Force
  # after reboot — kerberoastable and DCSync-capable accounts:
  New-ADUser -Name svc_sql -SamAccountName svc_sql -AccountPassword (ConvertTo-SecureString "Summer2026" -AsPlainText -Force) -Enabled $true -ServicePrincipalNames "MSSQLSvc/statedata.statefed.lab:1433"
  New-ADUser -Name backup_admin -SamAccountName backup_admin -AccountPassword (ConvertTo-SecureString "Backup-Adm1n-2026" -AsPlainText -Force) -Enabled $true
  Add-ADGroupMember -Identity "Domain Admins" -Members backup_admin
  ```

## 6. Access the portal and dashboard
Lab ports remain bound to `127.0.0.1` on the droplet. Forward them over SSH rather
than exposing them:
```bash
ssh -L 8088:127.0.0.1:8088 -L 8090:127.0.0.1:8090 root@<droplet-tailnet-ip>
# laptop: http://127.0.0.1:8088 (portal) · http://127.0.0.1:8090 (dashboard)
```
The dashboard may run on the droplet (`py dashboard/app.py`) or on the laptop; the
harness requires only tailnet reachability to the droplet.

## 7. End-of-session cost discipline (§3)
Powering off does not stop billing on either provider. Snapshot, then destroy, and
recreate from the snapshot at the next session.
```bash
# copy any captures off the droplet first (scp), then:
DO_DROPLET_ID=<id> VULTR_INSTANCE_ID=<id> ./scripts/snapshot-destroy.sh
```
Confirm in both provider consoles that no instance remains merely powered-off.
`scripts/reset.sh` returns a recreated host to a clean stack.

## 8. End-to-end validation
- `./scripts/healthcheck.sh` reports healthy; the portal answers `/ask` (RAG via the laptop GPU).
- Federated chain: `curl http://127.0.0.1:8088/federal/F-100277` returns a record with `assurance: high`.
- The AD node is reachable from the droplet over the tailnet (Samba: `docker compose exec samba-ad samba-tool user list`).
