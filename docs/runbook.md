# Runbook — build, mesh, run, tear down

> Operational guide. The **Dockerized stack in this repo** is the DigitalOcean
> droplet's tier and runs anywhere Docker does. The **three-node mesh, cloud
> provisioning, genuine Windows AD, and laptop GPU inference** are infrastructure
> the researcher provisions — covered here so the boundary between "scaffolded as
> code" and "stood up by hand" is explicit (§2.5 build philosophy, §3).

## A. Local single-host standup (development / dry run)

Everything in one place to exercise the chains before cloud spend.

```bash
cp .env.example .env                      # adjust if needed
# Point RAG at an Ollama you control. For local dev, run Ollama on the host:
#   ollama serve &  ;  ollama pull llama3  ;  ollama pull nomic-embed-text
# .env default OLLAMA_BASE_URL=http://host.docker.internal:11434 then works.

docker compose up -d --build              # base TARGET stack
docker compose run --rm rag-ingest        # build the pgvector store from the corpus
./scripts/healthcheck.sh                  # confirm all tiers healthy

# Optional: add the Samba AD DC fallback node
docker compose -f docker-compose.yml -f docker-compose.ad.yml up -d --build
```

Portal: <http://127.0.0.1:8088>  ·  Keycloak admin: <http://127.0.0.1:8080>
(`admin`/`admin`). Tier 1 has no host port by design — reach it only through
the portal's `/federal/{id}` (which rides the federation path).

## B. Three-node mesh standup (the real lab, §3)

Verified-price budget: ~$30–40 cloud over the full period under
snapshot-and-destroy discipline, well inside the $150 cloud allocation.

1. **DigitalOcean droplet (environment, 8 GB / 4 vCPU).** Install Docker + this
   repo. Install Tailscale: `curl -fsSL https://tailscale.com/install.sh | sh && tailscale up`.
   Lock the cloud firewall: inbound only from researcher IP (SSH) + tailnet.
   Set `OLLAMA_BASE_URL=http://<laptop-tailnet-ip>:11434` in `.env`.
2. **Vultr Windows AD node (~2 vCPU / 4 GB).** Deploy Windows Server 2022,
   install Tailscale for Windows, promote to Domain Controller, seed a realistic
   domain (SPNs on service accounts, a Kerberoastable account, a DCSync-capable
   account). Droplet containers join/authenticate to this DC over the tailnet.
   **Timeboxed fallback (§2.7):** if real Windows AD + cross-provider meshing
   isn't stable in the Week-2 window, drop to the Samba AD DC overlay
   (`docker-compose.ad.yml`) on the droplet — without hesitation — and record it
   as a documented limitation.
3. **Laptop inference (RTX 4050 / 32 GB).** Install Ollama + Tailscale. Bind
   Ollama to the tailnet: `OLLAMA_HOST=0.0.0.0:11434 ollama serve`. Confirm the
   model runs on the GPU (not CPU fallback). 7B–8B quantized (Llama 3 8B,
   Mistral 7B) is the assumed Category-B configuration.
4. **Validate + pin.** End-to-end: a portal query flows droplet → RAG → laptop
   GPU, and an AD auth flows droplet → DC. **Pin model name+digest and fix
   temperature/seed** for reproducible Category-B output (§9 nondeterminism).

## C. Start-of-session checklist (§3 guardrail #5)

1. **Recreate** both cloud nodes from last session's snapshots.
2. `tailscale status` — confirm all three hosts on the tailnet.
3. Confirm the **laptop is awake** and Ollama answers on its tailnet IP.
4. `./scripts/reset.sh` (or `--with-ad`) — pristine stack + healthcheck + re-ingest.
5. Confirm **billing alerts** active: DO $50, Vultr $40.

## D. End-of-session checklist — THE cost rule (§3, §6)

> Powering off does **not** stop billing on either provider. **Snapshot then
> destroy.** Ignoring this on the Windows node is the difference between ~$15 and
> ~$106 over the period (§3.2).

```bash
# 1. Snapshot any captured data out of the droplet first (captures/ is gitignored).
# 2. Snapshot THEN DESTROY both cloud nodes; recreate from snapshot next session:
DO_DROPLET_ID=<id> VULTR_INSTANCE_ID=<id> ./scripts/snapshot-destroy.sh
# 3. Verify in BOTH provider consoles that nothing is merely powered-off.
```

`doctl` reference (§6):
```bash
doctl compute droplet-action snapshot <id> --snapshot-name "lab-$(date +%F)" --wait
doctl compute droplet delete <id> --force
```

## E. Per-scenario reset (§6 clean state)

```bash
./scripts/reset.sh            # docker compose down -v && up -d, re-ingest, healthcheck
./scripts/reset.sh --with-ad  # include the AD overlay
```

Run this between every A/B/C category run so observations never carry over.
Only the AI category changes within a task; environment, target, and prompt
template are held fixed (§6 "one variable at a time").

## F. Capturing evidence

Per-action records and raw model output go in `captures/` (gitignored — Cat-B
output is sensitive research data, §7). Use the blank forms in
[`../templates/`](../templates/). The portal returns the assembled RAG prompt
and retrieved chunks on `/ask`, and the raw SQL on `/lookup`, so each action's
artifact is captured verbatim per §8.1.

## Troubleshooting

| Symptom | Likely cause / fix |
|---------|--------------------|
| `/ask` returns 502, "inference link" | Ollama not reachable at `OLLAMA_BASE_URL`. Check tailnet / `ollama serve` / GPU (§9). |
| `rag-ingest` FATAL dim mismatch | `EMBED_DIM` ≠ `EMBED_MODEL` output. Set `EMBED_DIM` to match (nomic-embed-text=768). |
| `/federal/{id}` 403 at checkpoint | Token assurance ≠ `high`. The `state-clerk` client is meant to be rejected — that's the control. |
| Keycloak slow to go healthy | Dev-mode realm import; allow ~40s `start_period`. |
| Samba AD won't provision | Needs `cap_add: SYS_ADMIN` + `seccomp:unconfined` (set in the overlay). Prefer genuine Windows AD (§2.6). |
