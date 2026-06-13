# Data Capture and Mapping Rubric

> Transcribes Protocol §8. **The unit of analysis is the individual attack
> action** — a discrete, observable step — not the chain as a whole, because a
> single chain mixes ATT&CK, ATLAS, dual, and gap actions. Each action gets one
> record. This rubric is the controlling methodology for the gap-analysis
> deliverable; the blank templates live in [`../templates/`](../templates/).

## 8.1 Per-action record template

Every executed action produces one record with these fields (blank form:
[`templates/per-action-record.md`](../templates/per-action-record.md)):

| Field | Content |
|-------|---------|
| **Action ID** | Sequential, scenario-scoped (e.g., `S03-A-07`) |
| **Timestamp / category** | When run + AI category (A / B / C) + model name+version if A/B |
| **Tier & component** | Which tier and service the action targeted |
| **Prompt (A/B)** | Exact prompt template used, verbatim |
| **Raw model output** | Verbatim — including refusals and partial/degraded output |
| **Executed command(s)** | What was actually run, plus result / artifact / screenshot ref |
| **Eval scores** | Operational completeness · technical accuracy · technique specificity |
| **Mapping outcome** | ATT&CK-mapped / ATLAS-mapped / Dual-mapped / Gap-flagged (+ technique ID) |
| **Deviation notes** | How observed behavior differs from the closest technique description |

> **Raw model output is preserved verbatim — including refusals — because a
> refusal is itself data** (§6). Uncensored Category-B output is sensitive
> research data: it is stored within project records (`captures/`, gitignored),
> never published as a runnable weapon (§7).

## 8.2 Four mapping outcomes

- **ATT&CK-mapped** — direct technique match by ID; behavior, prerequisites, and
  artifacts match without material deviation. Confirms the methodology correctly
  recognizes known-covered behavior.
- **ATLAS-mapped** — action targets an ML/AI component with a direct ATLAS match;
  **both target and mechanism must match** (dual confirmation) before classifying
  as cleanly mapped.
- **Dual-mapped** — involves traditional and AI infrastructure simultaneously;
  partially described by both frameworks, fully by neither. **Primary evidence
  for structural boundary gaps.**
- **Gap-flagged** — no adequate technique in either framework. Triggers the
  structured gap template (§8.3).

```
        ┌─ targets ML/AI component? ─┐
        │                            │
       no                          yes
        │                            │
  ATT&CK match?              ATLAS match (target
        │                    AND mechanism)?
   ┌────┴────┐                ┌─────┴─────┐
  yes        no              yes          no
   │          │               │            │
ATT&CK    involves BOTH    ATLAS     involves traditional
-mapped   trad + AI?       -mapped   infra too? ── yes ─► Dual-mapped
              │                                          │
             yes ───────────────────────────────────────┘
              │
        no adequate technique either side ─► GAP-FLAGGED ─► §8.3
```

## 8.3 Gap-flagged documentation template

Every gap-flagged action is expanded into this structure — the direct input to
the gap-analysis deliverable (blank form:
[`templates/gap-flagged.md`](../templates/gap-flagged.md)):

13. **Full description** of the observed behavior.
14. **Closest ATT&CK technique** and the specific ways observed behavior deviates
    from its description.
15. **Closest ATLAS technique** and the specific deviations.
16. **Proposed technique characterization**: tactic category, prerequisites,
    procedure example, observable artifacts — **written to the standard of an
    existing framework entry so it could be submitted as a community
    contribution.**

## 8.4 Gap categories (final taxonomy)

| Category | Definition + the case it's expected to capture |
|----------|------------------------------------------------|
| **Missing** | No technique exists in either framework. Expected heaviest bucket: AI-assisted attacks on traditional targets (e.g., an LLM generating a custom Kerberoasting script). ATT&CK doesn't model AI-assisted variants; ATLAS covers attacks *on* ML systems, not attacks *using* them. |
| **Vague** | Technique exists but is broad enough that materially different behaviors both satisfy it — a mapping-reliability problem. Expected in pre-RAG ATLAS prompt-injection coverage (AML.T0051) that doesn't separate retrieval-context manipulation from generation manipulation. |
| **Misaligned** | Technique exists and is specific, but assumed prerequisites/target/artifacts don't match observation. Expected where ATLAS assumes direct model-API access, while here the model is reached only through the Tier 2 web app — misdirecting defenders toward API logs instead of app-layer inputs. |

## Reproducibility discipline (§6)

1. **Clean state per scenario** — every scenario runs against a freshly recreated
   stack (`scripts/reset.sh`). Observations from one run never contaminate the next.
2. **One variable at a time** — within a task, only the AI category changes across
   A/B/C runs. Environment, target, and prompt template are held fixed.
3. **Snapshot before destroy** — minimize cloud cost and rebuild time (§3).
4. **Everything is logged** — commands, prompts, raw outputs, results, screenshots
   into the per-action record. Raw model output verbatim, refusals included.
5. **Architecture lock** — after the Week-3 walkthrough the environment is frozen;
   any later change is a versioned amendment with a one-line justification.
