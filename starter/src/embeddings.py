"""Embedding thật, chạy local bằng Sentence Transformers (không cần API key, chi phí 0).

Model: BAAI/bge-small-en-v1.5 (384 chiều, corpus tiếng Anh).
Cùng model cho cả ba cấu hình. Query có prefix hướng dẫn của BGE; document thì không.
Không có fallback sang vector giả: lỗi tải model sẽ ném exception.
"""
from typing import Protocol

DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


class Embedder(Protocol):
    model_name: str
    dimensions: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, question: str) -> list[float]: ...


class MyEmbedder:
    def __init__(self, model_name: str = DEFAULT_MODEL) -> None:
        from sentence_transformers import SentenceTransformer  # lỗi import/tải model -> báo lỗi thật

        self.model_name = model_name
        self._model = SentenceTransformer(model_name, device="cpu")
        self.dimensions = int(self._model.get_sentence_embedding_dimension())

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vecs = self._model.encode(texts, batch_size=32, normalize_embeddings=True,
                                  show_progress_bar=False)
        return [v.tolist() for v in vecs]

    def embed_query(self, question: str) -> list[float]:
        vec = self._model.encode([QUERY_PREFIX + question], normalize_embeddings=True,
                                 show_progress_bar=False)[0]
        return vec.tolist()
