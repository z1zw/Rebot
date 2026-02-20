"""Postgres pgvector-backed memory store."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class PgVectorMemory:
    dsn: str
    table: str = "rebot_vector_memory"
    dim: int = 256

    def _connect(self):
        try:
            import psycopg
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                "psycopg is required for PgVectorMemory. Install with `pip install psycopg[binary]`."
            ) from exc
        return psycopg.connect(self.dsn)

    def init(self) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                cur.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS {self.table} (
                        id bigserial PRIMARY KEY,
                        content text NOT NULL,
                        metadata jsonb DEFAULT '{{}}',
                        embedding vector({self.dim})
                    );
                    """
                )
            conn.commit()

    def add(self, content: str, embedding: list[float], metadata: dict[str, Any] | None = None) -> None:
        self.init()
        meta = metadata or {}
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"INSERT INTO {self.table} (content, metadata, embedding) VALUES (%s, %s, %s)",
                    (content, meta, embedding),
                )
            conn.commit()

    def search(self, embedding: list[float], top_k: int = 5) -> list[dict[str, Any]]:
        self.init()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT content, metadata, embedding <-> %s as score
                    FROM {self.table}
                    ORDER BY embedding <-> %s
                    LIMIT %s
                    """,
                    (embedding, embedding, top_k),
                )
                rows = cur.fetchall()
        return [
            {"text": row[0], "metadata": row[1], "score": float(row[2])}
            for row in rows
        ]
