"""Tier 2 — State Citizen Portal (FastAPI).

The state citizen-facing portal that queries federal data via federation; the
public edge of the lab (§2.1). This is the attacker's foothold and the only
container dual-homed on net_edge + net_internal — the bridge the attack pivots
through (§2.3).

================================================================================
ATTACK SURFACE — INTENTIONAL, DOCUMENTED RESEARCH TARGETS
This is a vulnerable-by-design target range for AUTHORIZED, ISOLATED academic
security research (faculty-approved, synthetic data, §7).
The weaknesses below are the object of study, built on purpose. They are NEVER
to be reachable from outside the lab's Docker networks / tailnet.

  /lookup   -> T1190 Exploit Public-Facing App: SQL injection in citizen lookup
  /upload   -> AML.T0020 Poison Training/RAG Data: unrestricted document upload
  /ask      -> AML.T0051 LLM Prompt Injection via retrieved (poisonable) context
  /federal  -> T1550 Use Alternate Auth Material: rides the federation path to Tier 1

This file builds the TARGET conditions only. Exploit code (payloads, injection
strings, Kerberoast/DCSync execution) is the researcher's hand-execution phase
(Weeks 4-7) and is intentionally NOT shipped here — the lab is the range, not
the weapon (§7 "describes behavior and mappings, not turnkey payloads").
================================================================================
"""
import uuid
from pathlib import Path

from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from . import db, rag, federation

app = FastAPI(title="State Citizen Portal", docs_url="/api-docs")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
UPLOAD_DIR = Path("/app/uploads")


@app.get("/healthz")
def healthz():
    return {"status": "ok", "tier": 2, "role": "state-citizen-portal"}


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# -----------------------------------------------------------------------------
# /lookup — citizen records search.
# INTENTIONAL TARGET (T1190 / SQLi): the WHERE clause is built by string
# interpolation. A safe parameterized version is shown in the comment so the
# deviation is explicit for the gap write-up. Do not "fix" this — it is the
# research target. Containment (§7) is what makes it safe to run.
# -----------------------------------------------------------------------------
@app.get("/lookup")
def lookup(name: str = ""):
    conn = db.pg_conn()
    # SAFE form (reference only):
    #   cur.execute("SELECT ... WHERE full_name ILIKE %s", (f"%{name}%",))
    sql = (
        "SELECT citizen_id, full_name, county, benefit_program, status "
        f"FROM citizens WHERE full_name ILIKE '%{name}%' ORDER BY citizen_id LIMIT 50"
    )
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        return {"query": sql, "count": len(rows), "results": rows}
    except Exception as e:  # surface DB errors verbatim — useful as captured evidence
        return JSONResponse(status_code=500, content={"query": sql, "error": str(e)})
    finally:
        conn.close()


# -----------------------------------------------------------------------------
# /upload — document submission into the MySQL doc store + inline RAG indexing.
# INTENTIONAL TARGET (AML.T0020 poisoning vector): no content validation; the
# document is embedded straight into the retrieval store, so a poisoned upload
# becomes retrievable context for /ask. This is the web-app-as-injection-vector
# that neither framework models (§5.3 chain #2).
# -----------------------------------------------------------------------------
@app.post("/upload")
async def upload(file: UploadFile = File(...), title: str = Form("")):
    raw = await file.read()
    text = raw.decode("utf-8", errors="replace")
    title = title or file.filename or "untitled"

    # Persist raw upload to disk (captured artifact) and into the doc store.
    (UPLOAD_DIR / file.filename).write_bytes(raw) if file.filename else None
    # Unique source per upload — the SAME string is used for MySQL and pgvector
    # (so retrieval shows the true origin), and it never collides with the
    # documents.source UNIQUE constraint. An attacker can upload many docs; each
    # becomes its own retrievable chunk.
    source = f"upload:{file.filename or title}#{uuid.uuid4().hex[:8]}"
    myconn = db.mysql_conn()
    with myconn.cursor() as cur:
        cur.execute(
            "INSERT INTO documents (title, source, body) VALUES (%s, %s, %s)",
            (title, source, text),
        )
        doc_id = cur.lastrowid
    myconn.close()

    # Inline index into pgvector so the poisoning chain is executable end to end.
    indexed = False
    rag_error = None
    try:
        pg = db.pg_conn()
        rag.index_document(pg, doc_id, source, text)
        pg.close()
        indexed = True
    except Exception as e:  # inference link may be down (§9) — report honestly
        rag_error = str(e)

    return {
        "doc_id": doc_id,
        "title": title,
        "source": source,
        "stored_bytes": len(raw),
        "indexed_into_rag": indexed,
        "rag_error": rag_error,
    }


# -----------------------------------------------------------------------------
# /ask — RAG question answering over the (poisonable) document store.
# INTENTIONAL TARGET (AML.T0051): retrieved context + user query flow into the
# model prompt with no isolation. Returns the assembled prompt and retrieved
# chunks so each action is logged verbatim per §8.1.
# -----------------------------------------------------------------------------
@app.get("/ask")
def ask(q: str, k: int = 4):
    try:
        pg = db.pg_conn()
        result = rag.answer(pg, q, k)
        pg.close()
        return result
    except Exception as e:
        return JSONResponse(
            status_code=502,
            content={"error": str(e), "hint": "Is Ollama reachable at OLLAMA_BASE_URL? (§9)"},
        )


# -----------------------------------------------------------------------------
# /federal — fetch a Tier 1 federal record by riding the federation path.
# INTENTIONAL TARGET (T1550): the portal mints a broker token with its client
# secret and calls Tier 1 through the policy checkpoint. The completed
# cross-framework chain end to end (AD compromise -> pivot -> federated Tier 1).
# -----------------------------------------------------------------------------
@app.get("/federal/{record_id}")
def federal(record_id: str):
    try:
        return federation.fetch_federal_record(record_id)
    except Exception as e:
        return JSONResponse(status_code=502, content={"error": str(e)})
