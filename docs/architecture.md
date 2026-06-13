# Environment Architecture

> Transcribes Protocol §2 into the as-built stack. The lab models a U.S.
> federal/state enterprise **mid-migration to zero trust** — the coexistence
> seam between legacy implicit trust and AI-enabled services is the research
> surface. A fully zero-trust build would neutralize the very attack chains
> under study (Kerberoasting, Pass-the-Hash, AD→AI pivots all depend on residual
> implicit trust); a purely legacy build would not reflect any current agency.

## Tier model (FICAM-aligned, §2.1)

| Tier | Federal analogue | As-built component(s) | Framework territory |
|------|------------------|------------------------|---------------------|
| **Tier 1 — Federal** | Federal data authority (benefits/eligibility cross-check); high-value, not externally reachable | `tier1-api` (FastAPI) on `net_federal` | ATT&CK (collection, exfil) |
| **Tier 2 — State** | State citizen-facing portal; the public edge | `tier2-portal` (FastAPI) + Postgres + MySQL | ATT&CK baseline + ATLAS injection vector |
| **Tier 3 — Shared** | Shared identity + AI services; legacy AD + federation broker + RAG | `keycloak`, `fed-gateway`, RAG (pgvector + Ollama), Samba/Windows AD | ATT&CK lateral/cred + ATLAS core |

## Network segmentation (microsegmentation analogue, §2.3)

Two layers. (1) In the real lab, an encrypted Tailscale (WireGuard) mesh links
the three hosts privately. (2) Inside the droplet, Docker bridge networks model
the trust boundaries among containerized tiers, mirroring NIST 800-207.

| Docker network | Federal zone analogue | Attached components | Notes |
|----------------|-----------------------|---------------------|-------|
| `net_edge` | Public edge / DMZ | `tier2-portal` (edge side), attacker foothold | Only externally reachable surface |
| `net_internal` | Internal (legacy implicit trust) | Postgres, MySQL, Keycloak, RAG retrieval, `tier2-portal` (internal side), AD node | `internal: true` — legacy implicit trust, no egress |
| `net_federal` | Restricted federal (ZT-guarded) | `tier1-api`, `fed-gateway` (federal side) | `internal: true` — reachable only via the checkpoint |

**Key design consequence (§2.3).** `tier2-portal` is the **only** container
dual-homed on `net_edge` + `net_internal` — the bridge the attacker pivots
through. Inside `net_internal`, legacy AD trust lets a compromised foothold move
laterally the old way. The RAG pipeline is reachable three ways (AD-compromise
pivot, Tier 2 upload poisoning, or direct internal access), each crossing the
framework boundary differently. Tier 1 sits behind `fed-gateway` on
`net_federal` — the one place zero trust is actually enforced — so reaching it
requires defeating or **riding** the federation path, where the most
defensively significant gaps surface.

```
                 net_edge (DMZ)
                    │
              ┌─────┴───────┐
              │ tier2-portal │  ← only dual-homed container (the pivot bridge)
              └─────┬───────┘
                    │ net_internal (legacy implicit trust)
   ┌──────────┬─────┴─────┬───────────┬──────────────┐
 postgres   mysql      keycloak    rag (pgvector    AD node
 (citizens  (doc       (broker)    + Ollama infer)  (Samba/Windows)
 + pgvector) store)        │
                           │ net_federal (ZT-guarded)
                     ┌─────┴──────┐
                     │ fed-gateway │  ← single policy-enforcement checkpoint
                     └─────┬──────┘
                           │
                      ┌────┴─────┐
                      │ tier1-api │  ← final exfil target (no other route in)
                      └──────────┘
```

## Federal reference mapping (§2.2)

| Lab construct | Federal reference | How it's modeled here |
|---------------|-------------------|------------------------|
| Identity federation (fed↔state) | FICAM / ICAM segment architecture; idmanagement.gov | Keycloak broker issues tokens the Tier 2 portal uses to reach Tier 1 |
| Credential / assurance levels | PIV (FIPS 201); NIST 800-63 IAL/AAL | `assurance` token claim: `high` (portal) vs `standard` (clerk) — the checkpoint rejects standard |
| Legacy trust core | On-prem Active Directory (pre-ZT norm) | Genuine Windows Server AD DC (preferred) or Samba AD DC fallback; realistic Kerberos/SPN config |
| Zero-trust target state | NIST 800-207; OMB M-22-09; CISA ZT Maturity Model | Partial: one policy-enforcement checkpoint + microsegmented networks |
| System boundary / authorization | FISMA; NIST 800-53 | Each tier is a labeled boundary; the gap analysis notes where attacks cross boundaries undetected |

## What is built for real vs. represented (§2.6)

| Aspect | Status in lab | Why |
|--------|---------------|-----|
| Legacy AD trust + Kerberos | **Built for real** (genuine Windows; Samba fallback) | Authentic AD makes T1558/T1110/T1021/DCSync findings non-dismissible |
| Web portal + injection/upload paths | **Built for real** | The actual ATT&CK + ATLAS-vector attack surface |
| RAG pipeline (pgvector + remote LLM) | **Built for real** | The ATLAS core and pivot target; behaves like a production RAG service |
| Federation broker (Keycloak) | **Built minimally for real** | Real OIDC broker enforcing one ZT boundary; not a full IdP deployment |
| PIV smart-card / Federal PKI | **Represented, not implemented** | Modeled as an assurance-tier claim; real PKI is weeks of yak-shaving with no added finding |
| Full zero-trust (all 5 pillars) | **Partially represented** | A complete ZT build would neutralize the chains under study |
| Category-B inference endpoint | **External (split hosting)** | Ollama on the RTX 4050 laptop over the tailnet — a documented mesh dependency, not hidden |

## Minimum Viable Environment (build contingency, §2.7)

| Tier | Includes | Supports |
|------|----------|----------|
| **FLOOR** (must have) | Tier 2 portal + AD (Windows or Samba) + RAG on the droplet, meshed via Tailscale, wired so the **AD-compromise → RAG-access pivot is executable** | The single strongest primary-contribution chain |
| **TARGET** (planned) | FLOOR + Tier 1 API + Keycloak checkpoint + the upload-poisoning path | All four §5.3 cross-framework targets |
| **STRETCH** (if ahead) | TARGET + richer federal data, more service accounts, expanded baseline surface | Deeper baselines + stronger secondary comparison |

This repo builds the **TARGET** stack as code (FLOOR + Tier 1 + checkpoint +
poisoning path). The genuine Windows AD node, the Tailscale mesh, and the laptop
GPU inference are infrastructure the researcher provisions (see `runbook.md`).
