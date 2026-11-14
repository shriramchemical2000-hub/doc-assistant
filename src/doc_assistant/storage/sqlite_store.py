from __future__ import annotations

import json
import os
import sqlite3
import uuid
import numpy as np


class SQLiteStore:
    """SQLite-backed document, governance metadata and embedding store."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        parent = os.path.dirname(db_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        self._initialize()

    def _connect(self):
        connection = sqlite3.connect(self.db_path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def _initialize(self):
        with self._connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("""CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY, filename TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                owner TEXT DEFAULT '', status TEXT DEFAULT 'Draft',
                version TEXT DEFAULT '1.0', review_date TEXT DEFAULT '',
                category TEXT DEFAULT 'Unclassified'
            )""")
            columns = {row["name"] for row in db.execute("PRAGMA table_info(documents)").fetchall()}
            migrations = {
                "owner": "TEXT DEFAULT ''",
                "status": "TEXT DEFAULT 'Draft'",
                "version": "TEXT DEFAULT '1.0'",
                "review_date": "TEXT DEFAULT ''",
                "category": "TEXT DEFAULT 'Unclassified'",
            }
            for name, definition in migrations.items():
                if name not in columns:
                    db.execute(f"ALTER TABLE documents ADD COLUMN {name} {definition}")
            db.execute("""CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                text TEXT NOT NULL, page INTEGER NOT NULL, embedding TEXT NOT NULL
            )""")

    def add_document(self, filename, chunks, vectors):
        if len(chunks) != len(vectors):
            raise ValueError("Each chunk must have exactly one embedding vector")
        document_id = uuid.uuid4().hex
        with self._connect() as db:
            db.execute("INSERT INTO documents(id, filename) VALUES (?, ?)", (document_id, filename))
            db.executemany(
                "INSERT INTO chunks(document_id, text, page, embedding) VALUES (?, ?, ?, ?)",
                [(document_id, chunk.text, int(chunk.page), json.dumps(np.asarray(vector, dtype=float).tolist()))
                 for chunk, vector in zip(chunks, vectors)],
            )
        return document_id

    def list_documents(self):
        with self._connect() as db:
            rows = db.execute("""SELECT d.id, d.filename, COUNT(c.id) AS chunks
                FROM documents d LEFT JOIN chunks c ON c.document_id=d.id
                GROUP BY d.id ORDER BY d.created_at DESC""").fetchall()
        return [dict(row) for row in rows]

    def list_document_records(self):
        with self._connect() as db:
            rows = db.execute("""SELECT d.id, d.filename, d.created_at, d.owner, d.status,
                d.version, d.review_date, d.category, COUNT(c.id) AS chunks
                FROM documents d LEFT JOIN chunks c ON c.document_id=d.id
                GROUP BY d.id ORDER BY d.created_at DESC""").fetchall()
        return [dict(row) for row in rows]

    def update_document_metadata(self, document_id, owner, status, version, review_date, category):
        allowed_status = {"Draft", "In Review", "Approved", "Archived"}
        allowed_categories = {"Unclassified", "Policy", "Procedure", "Guideline", "Form", "Reference", "Other"}
        if status not in allowed_status or category not in allowed_categories:
            raise ValueError("Invalid document status or category.")
        with self._connect() as db:
            db.execute("""UPDATE documents SET owner=?, status=?, version=?, review_date=?, category=?
                WHERE id=?""", (owner.strip(), status, version.strip(), review_date.strip(), category, document_id))

    def get_document_texts(self):
        with self._connect() as db:
            docs = db.execute("SELECT id, filename FROM documents ORDER BY created_at DESC").fetchall()
            result = []
            for doc in docs:
                rows = db.execute("SELECT text, page FROM chunks WHERE document_id=? ORDER BY page, id",
                                  (doc["id"],)).fetchall()
                result.append({
                    "id": doc["id"],
                    "filename": doc["filename"],
                    "text": "\n\n".join(f"[Page {row['page']}] {row['text']}" for row in rows),
                })
        return result

    def count_chunks(self):
        with self._connect() as db:
            return int(db.execute("SELECT COUNT(*) FROM chunks").fetchone()[0])

    def delete_document(self, document_id):
        with self._connect() as db:
            db.execute("DELETE FROM chunks WHERE document_id=?", (document_id,))
            db.execute("DELETE FROM documents WHERE id=?", (document_id,))

    def clear(self):
        with self._connect() as db:
            db.execute("DELETE FROM chunks")
            db.execute("DELETE FROM documents")

    def search_chunks(self, query_vector, top_k=5):
        query = np.asarray(query_vector, dtype=float)
        qnorm = np.linalg.norm(query)
        if qnorm == 0:
            return []
        with self._connect() as db:
            rows = db.execute("""SELECT c.id, c.text, c.page, c.embedding, d.filename
                FROM chunks c JOIN documents d ON d.id=c.document_id""").fetchall()
        scored = []
        for row in rows:
            vector = np.asarray(json.loads(row["embedding"]), dtype=float)
            denom = qnorm * np.linalg.norm(vector)
            score = float(np.dot(query, vector) / denom) if denom else 0.0
            scored.append({"id": row["id"], "text": row["text"], "page": row["page"],
                           "filename": row["filename"], "score": score})
        return sorted(scored, key=lambda item: item["score"], reverse=True)[:max(0, top_k)]
