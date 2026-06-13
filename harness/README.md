# AI-assisted attack harness

The research instrument for the **AI-assisted attack** question: it runs each
attack task across **Categories A / B / C** (§4), and — because it auto-writes a
per-action record every time — *running it is the data collection*.

**Human-in-the-loop (Protocol §4).** The model only **proposes**; you **approve**
(and may edit) before anything executes; the harness then runs the approved
action against the **self-owned lab only** and logs everything. The researcher is
always the executor — no protocol amendment required. (For bounded-autonomous
mode you'd need a logged mentor amendment first; not built here by design.)

**Containment (§7).** [`lab.py`](lab.py) enforces a host allowlist. Pointing the
harness at anything you don't own is refused in code, not by convention.

## Setup
```bash
py -m pip install -r harness/requirements.txt
# Lab must be up (docker compose up -d) and Ollama serving for Category B.
```

Config (env / repo `.env`):
| Var | For | Default |
|-----|-----|---------|
| `LAB_BASE_URL` | the target portal | `http://127.0.0.1:8088` |
| `LAB_ALLOWED_HOSTS` | extra lab hosts (tailnet) | `127.0.0.1,localhost,::1` |
| `OLLAMA_URL` | Category B (local) | `http://127.0.0.1:11434` |
| `GEMINI_API_KEY` / `GEMINI_MODEL` | Category A (Gemini) | — / `gemini-1.5-flash` |
| `OPENAI_API_KEY` / `OPENAI_MODEL` | Category A (OpenAI/Azure) | — / `gpt-4o-mini` |

## Use
```bash
py harness/runner.py --list
py harness/runner.py --task sqli_lookup --category B               # local model proposes
py harness/runner.py --task rag_prompt_injection --category A --provider gemini
py harness/runner.py --task sqli_lookup --category C               # manual baseline, no model
```
Per run: the model proposes → you enter/confirm the exact value → approve → it
executes against the lab → a record lands in `captures/<scenario>/`.

## Categories (and the Copilot/Gemini reality)
- **A — commercial/guardrailed:** Gemini or OpenAI/Azure over their **cloud APIs**.
  Copilot/Gemini cannot run locally (no weights); your lab calls out to them.
- **B — local/open-source:** Ollama on the laptop GPU (e.g. `llama3`, `mistral`,
  or an uncensored variant; Gemma is the Google-flavored *local* option — not Gemini).
- **C — manual baseline:** no model; the control.

## Tasks
HTTP-executed (against the lab portal): `sqli_lookup`, `rag_prompt_injection`,
`rag_poison_upload`, `federated_access`. Recorded-only (run AD attacks with your
own tooling against the DC node): `ad_kerberoast`, `ad_dcsync`. Edit
[`tasks.yaml`](tasks.yaml) to refine the fixed prompt templates in Week 4.
