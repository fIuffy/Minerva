"""Database connections for the Tier 2 portal.

Postgres holds the relational citizen records (and the pgvector RAG store).
MySQL holds the document store that feeds RAG ingestion.

Both live on net_internal — the legacy implicit-trust zone. The portal is the
only thing dual-homed onto net_edge, which is exactly why it is the pivot.
"""
import os
import psycopg
import pymysql


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
