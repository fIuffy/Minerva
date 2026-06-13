# Minerva

**Attacking the Playbook — Cross-Framework Coverage Gap Analysis (ATT&CK / ATLAS)**
A digital lab for framework fuzzing and gap-analysis research.

> An undergraduate security-research lab. Built to an internal Lab Testing
> Protocol v1.0; section references (§) throughout point to that protocol.

---

## What this is

A self-owned, network-isolated research range that models a **U.S. federal/state
enterprise mid-migration to zero trust** as it realistically exists in 2026 —
legacy Active Directory and implicit network trust coexisting with newer
identity-federated and AI-enabled (RAG/LLM) services. That coexistence seam is
the research surface.

**Research question (§1):** *When AI-assisted attack techniques are run against a
hybrid environment containing both traditional and AI-enabled services, do MITRE
ATT&CK and ATLAS — individually and together — fail to adequately cover the
resulting attack chains?* The lab is engineered so every executed action
produces a defensible mapping decision — **ATT&CK-mapped, ATLAS-mapped,
Dual-mapped, or Gap-flagged** — with evidence attached.

This is **defensive research**: the deliverable is a gap analysis with proposed
technique characterizations written to MITRE-entry standard, framed as community
contributions that help defenders close documented blind spots.

## Scope: what's code vs. what's provisioned

This repository is the **DigitalOcean droplet's Dockerized environment** — the
**TARGET build** (§2.7) as code, validated and runnable. The wider three-node
mesh is infrastructure the researcher stands up (see [`docs/runbook.md`](docs/runbook.md)):

| Built here as code | Provisioned by the researcher (runbook §B) |
|--------------------|---------------------------------------------|
| 3 segmented Docker networks (edge / internal / federal) | Tailscale (WireGuard) mesh across 3 hosts |
| Tier 2 portal, Tier 1 API, federation checkpoint | Genuine Windows Server 2022 AD DC on Vultr |
| Postgres+pgvector, MySQL, Keycloak broker | Ollama on the RTX 4050 laptop (GPU inference) |
| RAG pipeline + ingestion job | Cloud firewalls, snapshots, billing alerts |
| Samba AD DC **fallback** overlay (§2.7) | |
| Seed data, methodology package, ops scripts | |

The intentionally-vulnerable services here are the **target range** for
authorized research. **Exploit code is deliberately not shipped** — building
payloads (injection strings, Kerberoast/DCSync execution, prompt-injection
content) is the researcher's hand-execution phase (Weeks 4–7). Per §7 the lab
*"describes behavior and mappings, not turnkey malicious payloads."*

## Architecture at a glance

Three FICAM-aligned tiers across three microsegmented networks (full detail in
[`docs/architecture.md`](docs/architecture.md)):

```
        net_edge (DMZ)
            │
      ┌─────┴────────┐
      │ tier2-portal │  ← only container dual-homed edge+internal: THE PIVOT
      └─────┬────────┘
            │ net_internal  (legacy implicit trust — no egress)
  ┌─────────┼──────────┬───────────────┬──────────────────┐
postgres  mysql     keycloak      RAG (pgvector +     AD node
(citizens (doc       (federation   Ollama inference)   (Windows / Samba)
+ pgvector) store)    broker)           │
                                        │ net_federal  (ZT-guarded — no egress)
                                  ┌─────┴───────┐
                                  │ fed-gateway │  ← single policy checkpoint
                                  └─────┬───────┘
                                  ┌─────┴─────┐
                                  │ tier1-api │  ← final target, no other route in
                                  └───────────┘
```

## The attack surface (intentional, documented research targets)

Every weakness below is built **on purpose** as the object of study, and is only
ever reachable inside the lab's isolated networks (§7). Mapping these against the
frameworks is the entire point of the project.

| Endpoint / component | Closest technique(s) | Why it's here |
|----------------------|----------------------|---------------|
| `tier2-portal` `/lookup` | T1190 / SQLi | Baseline ATT&CK web exploitation (§5.1) |
| `tier2-portal` `/upload` | AML.T0020 Poison Data | Web-app-as-injection-vector — §5.3 chain #2 |
| RAG `/ask` (context→prompt, no isolation) | AML.T0051 Prompt Injection | ATLAS core; §8.4 "Vague" gap candidate |
| `fed-gateway` / portal client secret | T1550 Use Alternate Auth Material | Riding federated trust to Tier 1 — §5.3 chain #4 |
| AD `svc_sql` (SPN, weak pw) | T1558 Kerberoasting | Legacy cred access (§5.1) |
| AD `backup_admin` (Domain Admin) | T1003.006 DCSync | The AD-compromise → RAG-pivot root (§5.3 chain #1) |

## Quickstart (local single-host dry run)

Requires Docker + an [Ollama](https://ollama.com) you control for the RAG path.

```bash
cp .env.example .env

# RAG needs a model + embeddings. For local dev, run Ollama on the host:
ollama serve &                     # OLLAMA_BASE_URL defaults to host.docker.internal
ollama pull llama3                 # GEN_MODEL   (Category-B local model under study)
ollama pull nomic-embed-text       # EMBED_MODEL (768-dim — matches EMBED_DIM)

docker compose up -d --build       # base TARGET stack
docker compose run --rm rag-ingest # build the pgvector store from the doc corpus
./scripts/healthcheck.sh           # confirm all tiers healthy

# Add the Samba AD DC fallback node (§2.7) when you need the AD chain locally:
docker compose -f docker-compose.yml -f docker-compose.ad.yml up -d --build
```

- Portal: <http://127.0.0.1:8088>   ·   Keycloak admin: <http://127.0.0.1:8080> (`admin`/`admin`)
- Tier 1 has **no host port** — reach it only via the portal's `/federal/{id}`, which rides the federation path.
- Reset to a pristine state between scenarios: `./scripts/reset.sh` (§6). Windows: `./scripts/reset.ps1`.

## Build tiers (contingency, §2.7)

The build is tiered so a partial standup still supports the primary contribution.
**Every contingency cuts the same direction: reduce breadth, protect the §5.3 core.**

- **FLOOR** (must have): Tier 2 portal + AD + RAG, wired so the **AD-compromise → RAG-access pivot is executable**.
- **TARGET** (this repo): FLOOR + Tier 1 API + Keycloak checkpoint + the upload-poisoning path → all four §5.3 chains.
- **STRETCH**: richer federal data, more service accounts, expanded baseline surface.

## Repository layout

```
docker-compose.yml          Base TARGET stack (3 networks + 6 services)
docker-compose.ad.yml       Samba AD DC fallback overlay (§2.7)
.env.example                Config (Ollama/tailnet IP, lab creds, model pins)
services/
  tier2-portal/             FastAPI citizen portal — the edge pivot
  tier1-api/                FastAPI federal data authority — final target
  fed-gateway/              Federation policy-enforcement checkpoint (JWT PEP)
  rag-ingest/               MySQL docs → pgvector embedding job
  samba-ad/                 Samba AD DC fallback (kerberoastable + DCSync accts)
seed/                       Postgres citizen schema/data, MySQL doc store, RAG corpus
keycloak/                   statefed realm export (OIDC broker, assurance claims)
scripts/                    reset · healthcheck · snapshot-destroy (cost discipline)
docs/                       architecture · attack-task-matrix · data-capture-rubric · runbook
templates/                  Blank per-action-record + gap-flagged forms (§8.1/§8.3)
captures/                   Where per-action records land (gitignored; sensitive §7)
```

## Methodology package (the reproducible deliverable, §10)

The lab is self-documenting so the "method that shows it" is a deliverable in its
own right:

- [`docs/architecture.md`](docs/architecture.md) — tier model, segmentation, federal reference mapping, fidelity.
- [`docs/attack-task-matrix.md`](docs/attack-task-matrix.md) — §5 task matrix, technique baselines, A/B/C categories.
- [`docs/data-capture-rubric.md`](docs/data-capture-rubric.md) — §8 per-action record, four mapping outcomes, gap taxonomy.
- [`docs/runbook.md`](docs/runbook.md) — mesh standup, start/end session checklists, troubleshooting.
- [`templates/`](templates/) — blank per-action-record and gap-flagged forms.

## Containment, safety, and ethics (§7 — non-negotiable)

- **Attack isolation.** All targets are self-owned containers inside the lab
  networks. No scan, payload, or AI-generated artifact is ever pointed at any
  system outside this environment — no exceptions, no "quick tests."
- **Egress control.** `net_internal` and `net_federal` are Docker `internal`
  networks (no egress). The portal binds to host loopback here; in the real lab
  the cloud firewall restricts inbound to the researcher's IP + tailnet, never public.
- **Synthetic data only.** Every "federal/state/citizen" record is fabricated.
  No real PII, credentials, or proprietary data. The synthetic SSN field uses the
  invalid `900-xx-xxxx` range. Weak creds are part of the attack surface under
  study, **not secrets** — never reuse them anywhere.
- **Local-model output handling.** Uncensored Category-B output is sensitive
  research data: kept in `captures/` (gitignored), never published as a runnable
  weapon.
- **Responsible disclosure framing.** Proposed technique additions are written as
  community contributions to ATT&CK/ATLAS — defensive, aimed at closing blind spots.
- **CITI compliance.** Responsible Conduct of Research training completed before
  data collection.

## Verification status

Validated on this machine (Docker 27.3 / Compose v2.30):

- ✅ `docker compose config` valid (base **and** AD overlay).
- ✅ All five service images build; all Python compiles; realm JSON + bash scripts parse.
- ✅ Stack boots; Postgres/MySQL seed, Keycloak imports the `statefed` realm.
- ✅ **Full federated chain end-to-end:** portal → broker client-credentials token
  (with `audience` + `assurance=high` mappers) → gateway JWT validation → Tier 1 record.
- ✅ **Policy checkpoint is real:** high-assurance passes (200); standard-assurance `state-clerk` rejected (403).
- ✅ **Segmentation enforced:** the edge portal cannot resolve/reach `tier1-api` on `net_federal`.
- ✅ RAG `/ask` degrades gracefully (502) when Ollama is unreachable, per §9.
- ⚙️ LLM inference (RAG generation/embeddings) requires the researcher's Ollama
  endpoint — by design it runs on the RTX 4050 laptop over the tailnet (§2.6).

## Status & schedule (§10)

Protocol approved Week 1 (June 4–7, 2026). Build Weeks 2–3 (architecture lock end
of Week 3) · attack execution Weeks 4–7 · analysis Week 8 · write-up Weeks 9–10.
**Primary deliverable:** the gap analysis — each §5.3 chain characterized to
MITRE-entry standard with a proposed technique addition.
