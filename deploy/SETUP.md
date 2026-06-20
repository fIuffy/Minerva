# Cloud Setup — three-node mesh (§3)

Stand the lab up across the real topology: a **DigitalOcean droplet** (the Docker
environment), an optional **Vultr Windows** node (genuine AD), and your **laptop**
(Ollama GPU), joined privately by **Tailscale**. Budget is ~$30–40 cloud over the
whole period under snapshot-and-destroy discipline — well inside the $150 allocation.

> **You run these steps on your own accounts.** I'm not driving your cloud — the
> bootstrap script does ~90% of the on-box work; you do the purchases, the
> Tailscale auth, and the snapshot/destroy. That keeps billing and exposure under
> your hand, which is the whole point of §3/§7.

---

## 1. What to buy (tonight)

### Minimal FLOOR path — one purchase
Run the entire Docker stack **plus the Samba AD fallback** on a single droplet;
Ollama stays on your laptop. Cheapest and fastest.

| Item | Spec | Where | ~Cost |
|------|------|-------|-------|
| **DigitalOcean droplet** | Basic, **8 GB / 4 vCPU**, Ubuntu 24.04 | https://cloud.digitalocean.com/droplets/new · pricing https://www.digitalocean.com/pricing/droplets | **$48/mo** (≈ **$19** with snapshot+destroy) |
| **Tailscale** | Personal (free) | https://login.tailscale.com/start | **$0** |
| Laptop (Ollama) | already owned (RTX 4050) | — | $0 |

### Full-fidelity path — add genuine Windows AD (optional, the protocol's preferred node)
| Item | Spec | Where | ~Cost |
|------|------|-------|-------|
| **Vultr Cloud Compute** | **Windows Server 2022**, ~2 vCPU / 4 GB | https://my.vultr.com/deploy/ · pricing https://www.vultr.com/pricing/ | ~**$0.07/hr** + Win license (≈ **$11–20** AD-weeks only) |

> Prices are the protocol's June-2026 figures — **confirm live at checkout**. Sign-ups:
> DigitalOcean https://www.digitalocean.com/ · Vultr https://www.vultr.com/.
> Set **billing alerts now**: DigitalOcean $50, Vultr $40 (§3 hard guardrail).

---

## 2. Provision the droplet
1. Create droplet → **Ubuntu 24.04**, **Basic / 8 GB / 4 vCPU**, a region near you, add your **SSH key**.
2. (Recommended) Create a **DigitalOcean Cloud Firewall** and attach it: inbound **SSH (22) from your IP only**; everything else denied. Lab ports are never public.

## 3. Bootstrap it (one command)
```bash
ssh root@<droplet-ip>
curl -fsSL https://raw.githubusercontent.com/fIuffy/Minerva/main/deploy/bootstrap-droplet.sh | bash
```
Installs Docker + Tailscale, clones the repo to `/opt/minerva`, builds the stack,
and locks UFW (SSH + tailnet only). Then:
```bash
tailscale up          # open the printed auth URL → note this node's 100.x IP
```

## 4. Wire inference (laptop Ollama over the tailnet)
On the **laptop** (Tailscale already installed, Ollama already set up):
```powershell
# bind Ollama to the tailnet and note the laptop's 100.x address
setx OLLAMA_HOST "0.0.0.0:11434"   # restart Ollama after; `tailscale ip -4` shows the 100.x IP
```
On the **droplet**, point the stack at the laptop and (re)launch:
```bash
cd /opt/minerva
sed -i 's#^OLLAMA_BASE_URL=.*#OLLAMA_BASE_URL=http://<laptop-tailnet-ip>:11434#' .env
docker compose up -d
docker compose run --rm rag-ingest
./scripts/healthcheck.sh
```

## 5. Add Active Directory
- **Samba fallback (on the droplet, fast):**
  ```bash
  docker compose -f docker-compose.yml -f docker-compose.ad.yml up -d --build
  ```
- **Genuine Windows (Vultr, fidelity):** deploy Windows Server 2022, install
  Tailscale, then in an elevated PowerShell promote a DC and seed the domain to
  match the lab:
  ```powershell
  Install-WindowsFeature AD-Domain-Services -IncludeManagementTools
  Install-ADDSForest -DomainName "statefed.lab" -InstallDns -SafeModeAdministratorPassword (ConvertTo-SecureString "Sup3rS3cret-Admin!" -AsPlainText -Force) -Force
  # after reboot: kerberoastable + DCSync-capable accounts
  New-ADUser -Name svc_sql -SamAccountName svc_sql -AccountPassword (ConvertTo-SecureString "Summer2026" -AsPlainText -Force) -Enabled $true -ServicePrincipalNames "MSSQLSvc/statedata.statefed.lab:1433"
  New-ADUser -Name backup_admin -SamAccountName backup_admin -AccountPassword (ConvertTo-SecureString "Backup-Adm1n-2026" -AsPlainText -Force) -Enabled $true
  Add-ADGroupMember -Identity "Domain Admins" -Members backup_admin
  ```

## 6. Reach the portal + dashboard (without exposing them)
Lab ports stay bound to `127.0.0.1` on the droplet. Tunnel over SSH:
```bash
ssh -L 8088:127.0.0.1:8088 -L 8090:127.0.0.1:8090 root@<droplet-tailnet-ip>
# then on the laptop: http://127.0.0.1:8088 (portal) · http://127.0.0.1:8090 (dashboard)
```
Run the dashboard on the droplet with `py dashboard/app.py` (or keep driving the
lab from your laptop terminal — the harness only needs to reach the tailnet).

## 7. END OF SESSION — the cost rule (§3, the single most important one)
**Powering off does NOT stop billing.** Snapshot, then DESTROY; recreate next time.
```bash
# pull any captures off the droplet first (scp), then from your machine:
DO_DROPLET_ID=<id> VULTR_INSTANCE_ID=<id> ./scripts/snapshot-destroy.sh
```
Verify in **both** provider consoles that nothing is merely powered-off. Recreate
from the snapshot at the next session start (`scripts/reset.sh` for a clean stack).

## 8. Validate end-to-end
- `./scripts/healthcheck.sh` green · portal answers `/ask` (RAG via laptop GPU)
- federated chain: `curl http://127.0.0.1:8088/federal/F-100277` → record, `assurance: high`
- AD reachable from the droplet over the tailnet (Samba: `docker compose exec samba-ad samba-tool user list`)
