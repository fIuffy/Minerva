# research/

Working material for the document-embedding injection study (§5.3 chain #2).

- **[injection-taxonomy.md](injection-taxonomy.md)** — one-page taxonomy of how a
  malicious instruction is embedded in a legitimate document, with the demo doc,
  benign marker, and test question for each technique. Tracked (methodology).
- **`injection-corpus/`** — the demo documents themselves: legit-looking benefits
  documents that each hide an injection a different way, using **benign markers**
  (a document that fires makes the assistant emit `PI-XXX-NN`, nothing harmful).
  **Gitignored by default** — the same private-vs-public split as `captures/`
  (raw attack material stays local; the taxonomy and findings are the public
  deliverable). Un-ignore only if you and the mentor decide to publish them.

## Testing quickstart (next session, after recreating the Vultr instance)

1. Recreate the instance from your snapshot, note the new IP, and connect with a
   port-forwarding tunnel from your **laptop**:
   ```bash
   ssh -L 8088:127.0.0.1:8088 -L 8090:127.0.0.1:8090 root@<new-instance-ip>
   ```
2. On the instance, clean stack: `cd /opt/minerva && ./scripts/reset.sh`
3. Make sure your **laptop Ollama** is running (local model, Category B).
4. Open in your laptop browser (these tunnel to the cloud, ports never public):

   | What | URL |
   |------|-----|
   | **Portal** (upload docs, ask, see markers fire) | http://127.0.0.1:8088 |
   | **Dashboard** (status, records, operate) | http://127.0.0.1:8090 |
   | Keycloak admin (`admin`/`admin`) | http://127.0.0.1:8080 |

   The dashboard needs its deps on the instance first (`pip install -r dashboard/requirements.txt`)
   or run it from your laptop. The portal is the main place for this study.

## Running the experiment (per document)
In the portal's **Ask** card:
1. **Upload** a corpus doc (Document submission card).
2. **Ask** its test question (from the taxonomy) — watch for the marker in the answer.
3. Switch the **Model backend** dropdown to compare Ollama vs Gemini vs Copilot-class
   (the commercial ones need an API key in `.env`).
4. Use **"Get prompt (manual UI)"** (`/ask?dry_run=true`) to grab the assembled
   prompt and paste it into a licensed Gemini / Copilot chat by hand — the manual
   Category-A path, no automation.
5. `./scripts/reset.sh` between documents so a prior upload doesn't contaminate the next.

Direct test URLs (or just use the UI):
```
http://127.0.0.1:8088/ask?q=how%20do%20I%20get%20a%20replacement%20benefit%20card&provider=ollama
http://127.0.0.1:8088/ask?q=...&dry_run=true        # prompt only, for manual UI testing
```

Each run auto-writes a per-action record; `scp` the `captures/` folder to your
laptop before you destroy the instance.
