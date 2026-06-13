"""RAG ingestion job — the cross-boundary pivot's data layer (§2.1).

Two steps, idempotent so it doubles as a clean-state re-index (§6):
  1. Load the seed document corpus (/seed/documents/*) into the MySQL doc store
     if absent. MySQL is the RAG ingestion source — the dual-role data layer.
  2. Embed every document in MySQL and (re)build the pgvector store, so retrieval
     reflects exactly what is in the doc store right now.

Embeddings are served by Ollama on the laptop GPU over the tailnet
(OLLAMA_BASE_URL). Run with:  docker compose run --rm rag-ingest

The MySQL store is reachable three ways (AD-pivot, Tier 2 upload poisoning, or
direct internal access, §2.3) — re-running this job is how a poisoned corpus
becomes live retrieval context for the next scenario.
"""
import os
import sys
import glob
import psycopg
import pymysql
import httpx

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "nomic-embed-text")
EMBED_DIM = int(os.environ.get("EMBED_DIM", "768"))
SEED_DIR = "/seed/documents"


def pg_conn():
    return psycopg.connect(
        host=os.environ.get("POSTGRES_HOST", "postgres"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        dbname=os.environ.get("POSTGRES_DB", "statedata"),
        user=os.environ.get("POSTGRES_USER", "portal_svc"),
        password=os.environ.get("POSTGRES_PASSWORD", "portal_svc_pw"),
        autocommit=True,
    )


def mysql_conn():
    return pymysql.connect(
        host=os.environ.get("MYSQL_HOST", "mysql"),
        port=int(os.environ.get("MYSQL_PORT", "3306")),
        database=os.environ.get("MYSQL_DATABASE", "docstore"),
        user=os.environ.get("MYSQL_USER", "docstore_svc"),
        password=os.environ.get("MYSQL_PASSWORD", "docstore_svc_pw"),
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )


def embed(text: str) -> list[float]:
    r = httpx.post(
        f"{OLLAMA_BASE_URL}/api/embeddings",
        json={"model": EMBED_MODEL, "prompt": text},
        timeout=120.0,
    )
    r.raise_for_status()
    vec = r.json()["embedding"]
    if len(vec) != EMBED_DIM:
        raise SystemExit(
            f"FATAL: embedding dim {len(vec)} != EMBED_DIM {EMBED_DIM}. "
            f"Set EMBED_DIM to match EMBED_MODEL ({EMBED_MODEL})."
        )
    return vec


def vec_literal(vec: list[float]) -> str:
    return "[" + ",".join(repr(float(x)) for x in vec) + "]"


def load_seed_corpus(my) -> None:
    files = sorted(glob.glob(os.path.join(SEED_DIR, "*")))
    if not files:
        print(f"  (no seed files in {SEED_DIR})")
        return
    with my.cursor() as cur:
        for path in files:
            title = os.path.basename(path)
            source = f"seed:{title}"
            cur.execute("SELECT id FROM documents WHERE source = %s", (source,))
            if cur.fetchone():
                continue  # already loaded — keep idempotent
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                body = fh.read()
            cur.execute(
                "INSERT INTO documents (title, source, body) VALUES (%s, %s, %s)",
                (title, source, body),
            )
            print(f"  + loaded seed doc: {title}")


def reindex(my, pg) -> int:
    with my.cursor() as cur:
        cur.execute("SELECT id, title, source, body FROM documents ORDER BY id")
        docs = cur.fetchall()
    with pg.cursor() as cur:
        cur.execute("TRUNCATE rag_chunks RESTART IDENTITY")
    n = 0
    for d in docs:
        vec = embed(d["body"])
        with pg.cursor() as cur:
            cur.execute(
                "INSERT INTO rag_chunks (doc_id, source, content, embedding) "
                "VALUES (%s, %s, %s, %s::vector)",
                (d["id"], d["source"], d["body"], vec_literal(vec)),
            )
        n += 1
        print(f"  ~ indexed doc #{d['id']}: {d['title']}")
    return n


def main() -> None:
    print(f"[rag-ingest] Ollama @ {OLLAMA_BASE_URL} · embed={EMBED_MODEL} (dim {EMBED_DIM})")
    try:
        my = mysql_conn()
        pg = pg_conn()
    except Exception as e:
        sys.exit(f"FATAL: cannot reach data layer: {e}")
    print("[1/2] loading seed corpus into MySQL doc store…")
    load_seed_corpus(my)
    print("[2/2] embedding doc store -> pgvector…")
    try:
        n = reindex(my, pg)
    except httpx.HTTPError as e:
        sys.exit(f"FATAL: inference link down ({e}). Is Ollama up at OLLAMA_BASE_URL? (§9)")
    print(f"[rag-ingest] done — {n} documents indexed into pgvector.")


if __name__ == "__main__":
    main()
