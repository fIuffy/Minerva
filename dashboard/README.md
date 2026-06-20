# Research dashboard

A local control panel and attack console for the lab: monitor status, browse
records and findings, and operate attack steps from a single page. Runs on the
host, alongside the harness.

## Run
```bash
py -m pip install -r dashboard/requirements.txt
py dashboard/app.py          # http://127.0.0.1:8090
```

## Capabilities
- **Status** — portal / Keycloak / Ollama availability, loaded models, pgvector chunk count.
- **Runs** — A/B/C tallies and refusal counts across every per-action record in `captures/`.
- **Findings** — links to the gap records in `findings/`.
- **Records** — per-action record list with category, technique, and outcome; rendered on click.
- **Operate** — select a task and category; for Category B the local model proposes a step;
  the operator reviews and edits the payload, then executes it against the lab. Each
  execution writes a per-action record (§8.1).
- **Probe** — issue `/ask` or `/lookup` against the lab to observe an effect.

## Safety model
Execution is human-in-the-loop (§4): no action runs until the operator reviews the
payload and clicks Execute — the model only advises. Containment (§7) is enforced in
code: every request passes through the harness host allowlist (`harness/lab.py`),
which refuses any target outside the lab. There is no autonomous or looped execution;
bounded-autonomous operation would require a documented amendment to the rules of
engagement.

Markdown viewing is path-restricted to the repository, and no port is exposed beyond
`127.0.0.1`.
