# captures/

Per-action records, raw model output, and screenshots land here, one subfolder
per scenario (e.g. `captures/S03-ad-to-rag-pivot/`). Use the blank forms in
[`../templates/`](../templates/).

**This directory is gitignored** (except this README). Uncensored Category-B
model output is treated as sensitive research data (§7): stored within project
records, never committed or published as a runnable weapon. The write-up
describes behavior and mappings, not turnkey payloads.

Suggested layout:

```
captures/
  S01-web-exploitation/
    S01-A-01.md            # per-action record (commercial model run)
    S01-B-01.md            # per-action record (local model run)
    S01-C-01.md            # per-action record (manual baseline)
    artifacts/             # screenshots, raw SQL responses, command transcripts
  S03-ad-to-rag-pivot/
    ...
    gaps/
      G-03-1.md            # gap-flagged record (expanded)
```
