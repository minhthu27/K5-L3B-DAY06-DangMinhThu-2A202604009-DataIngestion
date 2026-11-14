"""PostgreSQL + pgvector: lưu vector, metadata, tìm cosine (exact scan, không index ANN)."""
from typing import Any

import psycopg

from .models import Chunk

# Chỉ cho phép lọc theo các cột này (tránh SQL injection qua tên cột).
FILTERABLE = {"chapter", "document_id", "page"}


def _vec(v: list[float]) -> str:
    return "[" + ",".join(f"{x:.8f}" for x in v) + "]"


class PgVectorStore:
    def __init__(self, database_url: str, dimensions: int) -> None:
        self.database_url = database_url
        self.dimensions = dimensions
        # Kết nối thử: lỗi backend phải nổi lên, không âm thầm bỏ qua.
        with psycopg.connect(database_url) as conn:
            conn.execute("SELECT 1")

    def _conn(self):
        return psycopg.connect(self.database_url)

    def create_schema(self) -> None:
        with self._conn() as conn:
            conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            conn.execute(f"""
                CREATE TABLE IF NOT EXISTS chunks (
                    strategy    text    NOT NULL,
                    chunk_id    text    NOT NULL,
                    document_id text    NOT NULL,
                    source      text    NOT NULL,
                    page        integer NOT NULL,
                    chapter     text,
                    text        text    NOT NULL,
                    embedding   vector({self.dimensions}) NOT NULL,
                    PRIMARY KEY (strategy, chunk_id)
                )""")
            conn.execute("CREATE INDEX IF NOT EXISTS chunks_filter_idx ON chunks (strategy, chapter)")
            dim = conn.execute(
                "SELECT atttypmod FROM pg_attribute WHERE attrelid='chunks'::regclass AND attname='embedding'"
            ).fetchone()[0]
            if dim != self.dimensions:
                raise ValueError(f"Bảng chunks có vector({dim}) nhưng model là {self.dimensions} chiều")

    def upsert(self, strategy: str, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        if len(chunks) != len(vectors):
            raise ValueError("Số chunk và số vector không khớp")
        if any(len(v) != self.dimensions for v in vectors):
            raise ValueError("Có vector sai số chiều")
        rows = [(strategy, c.chunk_id, c.document_id, c.source, c.page,
                 c.metadata.get("chapter"), c.text, _vec(v)) for c, v in zip(chunks, vectors)]
        ids = [c.chunk_id for c in chunks]
        docs = sorted({c.document_id for c in chunks})
        with self._conn() as conn, conn.cursor() as cur:
            cur.executemany("""
                INSERT INTO chunks (strategy, chunk_id, document_id, source, page, chapter, text, embedding)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s::vector)
                ON CONFLICT (strategy, chunk_id) DO UPDATE SET
                    document_id=EXCLUDED.document_id, source=EXCLUDED.source, page=EXCLUDED.page,
                    chapter=EXCLUDED.chapter, text=EXCLUDED.text, embedding=EXCLUDED.embedding""", rows)
            # xóa chunk cũ không còn trong lần nạp này (tài liệu đổi)
            cur.execute("DELETE FROM chunks WHERE strategy=%s AND document_id = ANY(%s) AND NOT (chunk_id = ANY(%s))",
                        (strategy, docs, ids))

    def count(self, strategy: str) -> int:
        with self._conn() as conn:
            return conn.execute("SELECT count(*) FROM chunks WHERE strategy=%s", (strategy,)).fetchone()[0]

    def search(self, strategy: str, query_vector: list[float], top_k: int = 3,
               filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        if len(query_vector) != self.dimensions:
            raise ValueError("Vector truy vấn sai số chiều")
        where, params = ["strategy = %s"], [strategy]
        for k, v in (filters or {}).items():
            if k not in FILTERABLE:
                raise ValueError(f"Không cho phép lọc theo '{k}'")
            where.append(f"{k} = %s")
            params.append(v)
        qv = _vec(query_vector)
        sql = f"""SELECT chunk_id, document_id, source, page, chapter, text,
                         1 - (embedding <=> %s::vector) AS score
                  FROM chunks WHERE {' AND '.join(where)}
                  ORDER BY embedding <=> %s::vector LIMIT %s"""
        with self._conn() as conn:
            rows = conn.execute(sql, [qv, *params, qv, top_k]).fetchall()
        return [{"chunk_id": r[0], "document_id": r[1], "source": r[2], "page": r[3],
                 "chapter": r[4], "text": r[5], "score": float(r[6])} for r in rows]
