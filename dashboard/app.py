#!/usr/bin/env python3
"""Minerva research dashboard — a local control panel + attack console.

Runs on the HOST (like the harness). It lets you OPERATE the lab end to end:
  - monitor status (portal / Keycloak / Ollama / containers / vector store)
  - browse per-action records (captures/) and gap findings (findings/)
  - PROPOSE an attack step (local Ollama, Category B) — read-only
  - REVIEW + EDIT the exact payload, then EXECUTE it against the lab
  - PROBE the lab (/ask, /lookup) to observe the effect
  - every execution auto-writes a per-action record (§8.1)

Human-in-the-loop (§4) is preserved: nothing runs until YOU click Execute on a
payload YOU reviewed — you are the executor, the model only advises. Containment
(§7) is enforced by lab.py's host allowlist: the console can only hit the lab.
There is no auto/loop execution (bounded-autonomous would need a mentor amendment).

Run:  py dashboard/app.py     →  http://127.0.0.1:8090
"""
from __future__ import annotations
import sys
import uuid
import datetime as dt
import subprocess
from pathlib import Path

import httpx
import yaml
import markdown as md
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse

ROOT = Path(__file__).resolve().parent.parent
CAPTURES = ROOT / "captures"
FINDINGS = ROOT / "findings"
sys.path.insert(0, str(ROOT / "harness"))
import backends   # noqa: E402  A/B/C model abstraction
import lab        # noqa: E402  containment-guarded executor (host allowlist)
import record     # noqa: E402  per-action record writer

TASKS = yaml.safe_load((ROOT / "harness" / "tasks.yaml").read_text(encoding="utf-8"))
HTTP_TASKS = {k: v for k, v in TASKS.items() if v.get("executor") == "http"}
PROPOSALS: dict[str, dict] = {}   # token -> model proposal (carried run->execute)

app = FastAPI(title="Minerva Research Dashboard")

STYLE = """<style>
:root{--navy:#112e51;--navy2:#1a4480;--ink:#1b1b1b;--muted:#5d6b78;--gold:#ffbe2e;
--link:#005ea2;--line:#dfe3e8;--bg:#f4f6f9;--card:#fff;--ok:#00824d;--err:#b50909;--warn:#8a6100;}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);
font-family:"Segoe UI",system-ui,-apple-system,Roboto,Arial,sans-serif;line-height:1.5}
a{color:var(--link);text-decoration:none}a:hover{text-decoration:underline}
header{background:linear-gradient(180deg,var(--navy),var(--navy2));color:#fff;border-bottom:4px solid var(--gold);padding:1rem 1.25rem}
header h1{margin:0;font-size:1.25rem}header .sub{color:#cdd9ea;font-size:.85rem}
main{max-width:1080px;margin:0 auto;padding:1.25rem}
.grid{display:grid;gap:1rem;grid-template-columns:repeat(auto-fit,minmax(280px,1fr))}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;box-shadow:0 1px 3px rgba(16,32,57,.1);padding:1rem 1.15rem;margin-bottom:1rem}
.card h2{margin:0 0 .6rem;font-size:1rem;color:var(--navy)}
.pill{font-size:.72rem;font-weight:700;padding:.12rem .5rem;border-radius:999px;background:#e3e9f0;color:#33424f}
.pill.ok{background:#e3f5ec;color:var(--ok)}.pill.err{background:#fde8e8;color:var(--err)}
.pill.A{background:#ede3f7;color:#5b2a86}.pill.B{background:#e3eefb;color:#1a4480}.pill.C{background:#eef0f2;color:#444}
.pill.warn{background:#fff3d6;color:var(--warn)}
table{width:100%;border-collapse:collapse;font-size:.85rem}th,td{text-align:left;padding:.4rem .5rem;border-bottom:1px solid var(--line)}
th{background:#f7f9fb;font-size:.72rem;text-transform:uppercase;letter-spacing:.3px;color:#33424f}
tr:hover td{background:#fafcfe}
.row{display:flex;gap:.5rem;align-items:center;flex-wrap:wrap}
input,select,button,textarea{font:inherit;padding:.5rem .6rem;border:1px solid #9aa7b3;border-radius:6px}
textarea{width:100%;min-height:120px;font-family:ui-monospace,Consolas,monospace;font-size:.85rem}
input[type=text]{width:100%}
button{background:var(--navy2);color:#fff;border:0;cursor:pointer;font-weight:600}button:hover{background:var(--navy)}
button.danger{background:var(--err)}button.danger:hover{background:#8f0707}
.muted{color:var(--muted);font-size:.85rem}code,pre{background:#0e1b26;color:#d6e6f2;border-radius:6px}
code{padding:.1rem .35rem;font-size:.82rem}pre{padding:.8rem;overflow:auto;font-size:.82rem;white-space:pre-wrap}
.mono{font-family:ui-monospace,Consolas,monospace}
.banner{background:#1b1b1b;color:#e9ecf1;font-size:.78rem;padding:.4rem 1.25rem}.banner b{color:var(--gold)}
.warnbox{background:#fff8e6;border:1px solid #f0d27a;border-radius:6px;padding:.5rem .7rem;font-size:.82rem;color:#5b4a13}
.quick a{display:inline-block;margin:.15rem .5rem .15rem 0;padding:.3rem .6rem;background:#eef2f7;border-radius:6px}
</style>"""


def esc(s) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def page(title: str, body: str) -> str:
    return (f"<!doctype html><html lang=en><head><meta charset=utf-8>"
            f"<meta name=viewport content='width=device-width,initial-scale=1'>"
            f"<title>{esc(title)}</title>{STYLE}</head><body>"
            f"<div class=banner>🔬 <b>Minerva research dashboard</b> — local attack console · "
            f"isolated self-owned lab · synthetic data (§7) · you approve every step (§4)</div>"
            f"<header><h1>{esc(title)}</h1><div class=sub>Attacking the Playbook — ATT&CK / ATLAS gap analysis</div></header>"
            f"<main>{body}</main></body></html>")


# ---------- status helpers ----------
def ping(url: str) -> bool:
    try:
        return httpx.get(url, timeout=2.0).status_code < 500
    except Exception:
        return False


def ollama_models() -> list[str]:
    try:
        tags = httpx.get(f"{backends.OLLAMA_URL}/api/tags", timeout=2.0).json().get("models", [])
        return [m.get("name", "?") for m in tags]
    except Exception:
        return []


def _docker(*args: str, timeout: int = 10) -> str:
    try:
        return subprocess.run(["docker", *args], cwd=ROOT, capture_output=True,
                              text=True, timeout=timeout).stdout.strip()
    except Exception as e:
        return f"(docker unavailable: {e})"


def pgvector_count() -> str:
    out = _docker("compose", "exec", "-T", "postgres", "psql", "-U", "portal_svc",
                  "-d", "statedata", "-tAc", "SELECT count(*) FROM rag_chunks;")
    return out.splitlines()[-1].strip() if out and out[:1].isdigit() else "—"


# ---------- record helpers ----------
def parse_record(p: Path) -> dict:
    d = {"path": p, "category": "?", "technique": "", "refused": False, "mapping": "unmapped", "ts": ""}
    try:
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            low = line.lower()
            if line.startswith("- **AI category:**"):
                d["category"] = line.split("**AI category:**")[1].strip()[:1].upper()
                d["refused"] = "refusal" in low
            elif line.startswith("- **Baseline technique"):
                d["technique"] = line.split("**")[-1].strip(" :*")
            elif line.startswith("- **Timestamp:**"):
                d["ts"] = line.split("**Timestamp:**")[1].strip()
            elif line.startswith("- [x]") and "gap-flagged" in low:
                d["mapping"] = "Gap-flagged"
            elif line.startswith("- [x]") and "mapped" in low:
                d["mapping"] = line.split("]")[1].split("—")[0].strip()
    except Exception:
        pass
    return d


def list_records() -> list[dict]:
    if not CAPTURES.exists():
        return []
    recs = [parse_record(p) for p in CAPTURES.rglob("*.md") if p.name != "README.md"]
    return sorted(recs, key=lambda r: r["ts"], reverse=True)


def safe_md_path(rel: str) -> Path | None:
    try:
        p = (ROOT / rel).resolve()
        if p.is_file() and p.suffix == ".md" and ROOT in p.parents:
            return p
    except Exception:
        pass
    return None


def build_action(task: dict, value: str) -> dict:
    method, path = task["method"], task["path"]
    if "{record_id}" in path:
        return {"method": method, "path": path.format(record_id=value)}
    if task.get("upload"):
        return {"method": method, "path": path,
                "files": {"file": ("harness-payload.txt", value, "text/plain")},
                "data": {"title": "dashboard-upload"}}
    if task.get("inject_param"):
        return {"method": method, "path": path, "params": {task["inject_param"]: value}}
    return {"method": method, "path": path}


# ---------- pages ----------
@app.get("/", response_class=HTMLResponse)
def home():
    st = {
        "Portal (:8088)": ping("http://127.0.0.1:8088/healthz"),
        "Keycloak realm": ping("http://127.0.0.1:8080/realms/statefed/.well-known/openid-configuration"),
        "Ollama (:11434)": ping(f"{backends.OLLAMA_URL}/api/tags"),
    }
    status_html = "".join(
        f"<div class=row><span class='pill {'ok' if v else 'err'}'>{'UP' if v else 'DOWN'}</span> {k}</div>"
        for k, v in st.items())
    status_html += (f"<div class=muted style='margin-top:.5rem'>models: {', '.join(ollama_models()) or '—'} · "
                    f"vector chunks: {pgvector_count()}</div>")

    recs = list_records()
    tally = {"A": 0, "B": 0, "C": 0}
    refusals = sum(1 for r in recs if r["refused"])
    for r in recs:
        tally[r["category"]] = tally.get(r["category"], 0) + 1
    rec_rows = "".join(
        f"<tr><td>{esc(r['ts'][5:16])}</td><td><span class='pill {r['category']}'>{esc(r['category'])}</span></td>"
        f"<td>{esc(r['technique'][:38])}</td>"
        f"<td>{'<span class=pill.warn>refusal</span> ' if r['refused'] else ''}{esc(r['mapping'])}</td>"
        f"<td><a href='/view?path={esc(r['path'].relative_to(ROOT).as_posix())}'>open</a></td></tr>"
        for r in recs[:25]) or "<tr><td colspan=5 class=muted>no records yet</td></tr>"

    find_items = ""
    if FINDINGS.exists():
        for p in sorted(FINDINGS.glob("*.md")):
            if p.name == "README.md":
                continue
            title = next((l for l in p.read_text(encoding="utf-8", errors="replace").splitlines()
                          if l.startswith("# ")), p.stem).lstrip("# ").strip()
            find_items += f"<li><a href='/view?path={esc(p.relative_to(ROOT).as_posix())}'>{esc(title)}</a></li>"
    find_items = find_items or "<li class=muted>none yet</li>"

    # Operate: pick an http task + category, prepare a step
    opts = "".join(f"<option value='{k}'>{k} — {esc(v['technique'])}</option>" for k, v in HTTP_TASKS.items())
    operate = (
        "<form method=get action=/run class=row>"
        f"<select name=task>{opts}</select>"
        "<select name=category><option value=B>B — local Ollama</option><option value=C>C — manual</option></select>"
        "<button>Prepare step →</button></form>"
        "<div class=muted>Model proposes (B) or you author (C); you review + edit, then Execute.</div>")

    probe = (
        "<form method=get action=/probe class=row>"
        "<select name=kind><option value=ask>/ask (RAG)</option><option value=lookup>/lookup (SQL)</option></select>"
        "<input type=text name=q placeholder='question or name…' style='flex:1' value='how do I request emergency benefit reactivation'>"
        "<button>Probe</button></form>"
        "<div class=muted>Observe the lab's live response (e.g. confirm a poisoning effect).</div>")

    quick = ("<div class=quick>"
             "<a href='http://127.0.0.1:8088' target=_blank>Portal ↗</a>"
             "<a href='http://127.0.0.1:8080' target=_blank>Keycloak ↗</a>"
             "<a href='/view?path=findings/README.md'>Findings</a>"
             "<a href='/view?path=docs/demo-script.md'>Demo script</a>"
             "<a href='/view?path=docs/attack-task-matrix.md'>Task matrix</a></div>")

    body = f"""{quick}
    <div class=grid>
      <div class=card><h2>Lab status</h2>{status_html}</div>
      <div class=card><h2>Runs</h2>
        <div class=row><span class='pill A'>A {tally.get('A',0)}</span>
        <span class='pill B'>B {tally.get('B',0)}</span>
        <span class='pill C'>C {tally.get('C',0)}</span>
        <span class='pill warn'>refusals {refusals}</span></div>
        <div class=muted style='margin-top:.4rem'>{len(recs)} records in <span class=mono>captures/</span></div></div>
      <div class=card><h2>Findings</h2><ul style='margin:.2rem 0'>{find_items}</ul></div>
    </div>
    <div class=card><h2>⚔ Operate — prepare an attack step</h2>{operate}</div>
    <div class=card><h2>🔎 Probe the lab</h2>{probe}</div>
    <div class=card><h2>Per-action records</h2>
      <table><thead><tr><th>when</th><th>cat</th><th>technique</th><th>outcome</th><th></th></tr></thead>
      <tbody>{rec_rows}</tbody></table></div>"""
    return page("Minerva Dashboard", body)


@app.get("/run", response_class=HTMLResponse)
def run(task: str, category: str = "B"):
    if task not in HTTP_TASKS:
        return RedirectResponse("/")
    t = {"id": task, **HTTP_TASKS[task]}
    category = category.upper()
    prompt = t["prompt_template"].format(base_url=lab.LAB_BASE_URL)
    if category == "C":
        prop = {"category": "C", "provider": "manual", "model": None,
                "raw_output": "(Category C — you author the payload)", "refused": False, "error": None}
    else:
        prop = backends.complete("B", prompt)  # local Ollama only
    token = uuid.uuid4().hex
    PROPOSALS[token] = prop
    flag = "<span class='pill warn'>heuristic refusal</span>" if prop.get("refused") else ""
    err = f"<div class=warnbox>backend error: {esc(prop.get('error'))}</div>" if prop.get("error") else ""
    default_val = t.get("example_payload", "")
    body = f"""<p><a href=/>← dashboard</a></p>
    <div class=card><h2>{esc(t['name'])}</h2>
      <div class=muted>{esc(t['technique'])} · {esc(t.get('chain',''))} · target {esc(t.get('target_desc',''))}</div>
      <p>Category <span class='pill {category}'>{category}</span> · {esc(prop.get('provider'))}/{esc(prop.get('model'))} {flag}</p>{err}
      <h2>Model proposal (advice only — not executed)</h2>
      <pre>{esc(prop.get('raw_output') or '')}</pre>
      <form method=post action=/execute>
        <input type=hidden name=task value="{esc(task)}">
        <input type=hidden name=category value="{esc(category)}">
        <input type=hidden name=token value="{token}">
        <h2>Payload to send — review &amp; edit (this is the value injected)</h2>
        <textarea name=payload>{esc(default_val)}</textarea>
        <div class=warnbox style='margin:.6rem 0'>Clicking Execute sends this against the lab
          (<span class=mono>{esc(lab.LAB_BASE_URL)}</span>). You are the executor (§4); the lab
          allowlist refuses anything off-lab (§7).</div>
        <button class=danger>Execute against lab ▶</button>
      </form>
    </div>"""
    return page(f"Operate · {task}", body)


@app.post("/execute", response_class=HTMLResponse)
async def execute(request: Request):
    form = await request.form()
    task = form.get("task")
    category = (form.get("category") or "B").upper()
    value = form.get("payload", "")
    prop = PROPOSALS.pop(form.get("token", ""), None) or {
        "category": category, "provider": "ollama" if category == "B" else "manual",
        "model": backends.DEFAULT_MODELS["ollama"] if category == "B" else None,
        "raw_output": "(proposal not carried)", "refused": False, "error": None}
    if task not in HTTP_TASKS:
        return RedirectResponse("/")
    t = {"id": task, **HTTP_TASKS[task]}
    action = build_action(t, value)
    try:
        result = lab.execute(action["method"], action["path"], params=action.get("params"),
                             data=action.get("data"), files=action.get("files"))
        status_pill = "ok" if isinstance(result, dict) and result.get("status", 0) < 400 else "err"
    except lab.ContainmentError as e:
        result = {"refused": str(e)}
        status_pill = "err"

    prompt = t["prompt_template"].format(base_url=lab.LAB_BASE_URL)
    executed = {"value": value, **{k: v for k, v in action.items() if k != "files"}}
    rid = f"{task}-{category}-{dt.datetime.now():%H%M%S}"
    rec_path = record.write_record("dashboard", rid, t, prop, prompt, executed, result)
    rel = rec_path.relative_to(ROOT).as_posix()

    import json
    probe_hint = ""
    if t.get("upload"):
        probe_hint = ("<p>Now test the effect: "
                      "<a href='/probe?kind=ask&q=how%20do%20I%20request%20emergency%20benefit%20reactivation'>probe /ask →</a></p>")
    body = f"""<p><a href=/>← dashboard</a></p>
    <div class=card><h2>Executed: {esc(t['name'])} <span class='pill {status_pill}'>{status_pill.upper()}</span></h2>
      <div class=muted>{esc(t['technique'])}</div>
      <h2>Sent</h2><pre>{esc(json.dumps(executed, indent=2))}</pre>
      <h2>Lab response</h2><pre>{esc(json.dumps(result, indent=2)[:4000])}</pre>
      {probe_hint}
      <p>✓ record written: <a href='/view?path={esc(rel)}'>{esc(rel)}</a></p>
    </div>"""
    return page("Executed", body)


@app.get("/probe", response_class=HTMLResponse)
def probe(kind: str = "ask", q: str = ""):
    import json
    path, param = ("/ask", "q") if kind == "ask" else ("/lookup", "name")
    try:
        result = lab.execute("GET", path, params={param: q})
    except lab.ContainmentError as e:
        result = {"refused": str(e)}
    body = f"""<p><a href=/>← dashboard</a></p>
    <div class=card><h2>Probe {esc(path)}?{esc(param)}={esc(q)}</h2>
      <pre>{esc(json.dumps(result, indent=2)[:6000])}</pre></div>"""
    return page("Probe", body)


@app.get("/view", response_class=HTMLResponse)
def view(path: str):
    p = safe_md_path(path)
    if not p:
        return RedirectResponse("/")
    html = md.markdown(p.read_text(encoding="utf-8", errors="replace"),
                       extensions=["tables", "fenced_code"])
    return page(p.name, f"<p><a href=/>← dashboard</a> · <span class=mono>{esc(path)}</span></p>"
                        f"<div class=card>{html}</div>")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8090)
