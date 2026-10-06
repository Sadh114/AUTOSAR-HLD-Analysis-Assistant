"""SQLite persistence for documents, Q&A history and audit log."""
import sqlite3
import json
import time
from contextlib import contextmanager

from backend import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    doc_id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    pages INTEGER NOT NULL,
    chunks INTEGER NOT NULL,
    ocr_pages INTEGER NOT NULL DEFAULT 0,
    uploaded_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS queries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_ids TEXT NOT NULL,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    citations TEXT NOT NULL,
    confidence TEXT NOT NULL,
    asked_at REAL NOT NULL
);
"""


@contextmanager
def get_conn():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)


def add_document(doc_id: str, filename: str, pages: int, chunks: int, ocr_pages: int = 0):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO documents (doc_id, filename, pages, chunks, ocr_pages, uploaded_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (doc_id, filename, pages, chunks, ocr_pages, time.time()),
        )


def list_documents():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM documents ORDER BY uploaded_at DESC").fetchall()
        return [dict(r) for r in rows]


def delete_document(doc_id: str):
    with get_conn() as conn:
        conn.execute("DELETE FROM documents WHERE doc_id = ?", (doc_id,))


def log_query(doc_ids, question: str, answer: str, citations: list, confidence: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO queries (doc_ids, question, answer, citations, confidence, asked_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (json.dumps(doc_ids), question, answer, json.dumps(citations), confidence, time.time()),
        )


def list_queries(limit: int = 200):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM queries ORDER BY asked_at DESC LIMIT ?", (limit,)
        ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["doc_ids"] = json.loads(d["doc_ids"])
            d["citations"] = json.loads(d["citations"])
            out.append(d)
        return out
