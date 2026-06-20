# Research dashboard

A local control panel for the lab — monitor, browse, and plan experiments from
one page. Runs on the **host** (like the harness), read-only by design.

```bash
py -m pip install -r dashboard/requirements.txt
py dashboard/app.py          # → http://127.0.0.1:8090
```

**What it shows**
- **Lab status** — portal / Keycloak / Ollama up-down, loaded models, pgvector chunk count.
- **Runs** — A/B/C tallies + refusal count across every per-action record in `captures/`.
- **Findings** — links to the gap records in `findings/`.
- **Per-action records** — sortable list with category, technique, outcome; click to render.
- **Propose** — pick a task + category and get the model's proposed step (read-only).

**What it does NOT do:** execute attacks. It only *proposes* (a model call) and hands you
the exact `harness` command. Execution stays in the terminal because that is where the
human-in-the-loop approval gate lives (§4). The dashboard never touches the lab targets.

Markdown viewing is path-restricted to the repo. Nothing here is exposed beyond
`127.0.0.1`.
