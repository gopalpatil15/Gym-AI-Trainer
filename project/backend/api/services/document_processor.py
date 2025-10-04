from __future__ import annotations

import asyncio
import os
import re
from typing import Any, Dict, List, Tuple

import numpy as np

try:
    from sentence_transformers import SentenceTransformer
except Exception:  # noqa: BLE001
    SentenceTransformer = None  # type: ignore

try:
    from docx import Document as DocxDocument  # type: ignore
except Exception:  # noqa: BLE001
    DocxDocument = None  # type: ignore

try:
    import pandas as pd  # type: ignore
except Exception:  # noqa: BLE001
    pd = None  # type: ignore

try:
    from pypdf import PdfReader  # type: ignore
except Exception:  # noqa: BLE001
    PdfReader = None  # type: ignore

from ..utils.logger import get_logger
from ..utils.vector_store import VectorStore

_logger = get_logger(__name__)


class EmbeddingProvider:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> None:
        self.model_name = model_name
        self._model = None

    def _ensure_model(self):
        if SentenceTransformer is None:
            return None
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        model = self._ensure_model()
        if model is not None:
            vectors = np.asarray(model.encode(texts, show_progress_bar=False))
            return vectors.astype(np.float32)
        # Fallback: simple bag-of-words hashing projection
        return self._hashing_embed(texts)

    def _hashing_embed(self, texts: List[str], dim: int = 256) -> np.ndarray:
        vectors = np.zeros((len(texts), dim), dtype=np.float32)
        for i, t in enumerate(texts):
            for tok in re.findall(r"\w+", t.lower()):
                idx = hash(tok) % dim
                vectors[i, idx] += 1.0
        # L2 normalize
        norms = np.linalg.norm(vectors, axis=1, keepdims=True) + 1e-9
        return (vectors / norms).astype(np.float32)


class DocumentProcessor:
    def __init__(self, vector_store: VectorStore, embedding_provider: EmbeddingProvider | None = None) -> None:
        self.vector_store = vector_store
        self.embedding_provider = embedding_provider or EmbeddingProvider()

    async def process_documents(self, file_paths: List[str], job_cb=None) -> None:
        texts: List[str] = []
        metadatas: List[Dict[str, Any]] = []
        for idx, path in enumerate(file_paths, start=1):
            try:
                content, meta = await self._extract_text_with_meta(path)
                chunks = self.dynamic_chunking(content, meta.get("doc_type", "txt"))
                for ci, chunk in enumerate(chunks):
                    texts.append(chunk)
                    md = {**meta, "chunk_index": ci}
                    metadatas.append(md)
            except Exception as exc:  # noqa: BLE001
                _logger.error("Failed to process %s: %s", path, exc)
            if job_cb:
                await job_cb(idx)

        if not texts:
            return
        # Embed in batches
        batch = 32
        all_vecs: List[np.ndarray] = []
        for i in range(0, len(texts), batch):
            batch_texts = texts[i : i + batch]
            vecs = self.embedding_provider.embed_texts(batch_texts)
            all_vecs.append(vecs)
        vectors = np.vstack(all_vecs)
        self.vector_store.add_many(vectors, metadatas)

    async def _extract_text_with_meta(self, path: str) -> Tuple[str, Dict[str, Any]]:
        ext = os.path.splitext(path)[1].lower()
        meta: Dict[str, Any] = {"path": path, "filename": os.path.basename(path)}
        if ext == ".pdf" and PdfReader is not None:
            meta["doc_type"] = "pdf"
            reader = PdfReader(path)
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            return text, meta
        if ext in (".docx",) and DocxDocument is not None:
            meta["doc_type"] = "docx"
            doc = DocxDocument(path)
            text = "\n".join(p.text for p in doc.paragraphs)
            return text, meta
        if ext in (".csv",) and pd is not None:
            meta["doc_type"] = "csv"
            try:
                df = pd.read_csv(path)
            except Exception:
                df = pd.read_csv(path, encoding_errors="ignore")
            text = df.to_csv(index=False)
            return text, meta
        # default txt
        meta["doc_type"] = "txt"
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read(), meta

    def dynamic_chunking(self, content: str, doc_type: str) -> List[str]:
        content = content.strip()
        if not content:
            return []
        # Heuristics per type
        if doc_type in ("pdf", "docx", "txt"):
            # Resume-like or review-like: split on headers but keep sections together
            sections = re.split(r"\n\s*(?:Skills|Experience|Projects|Education|Summary|Review|Performance)\s*:?[\n]+", content, flags=re.IGNORECASE)
            chunks: List[str] = []
            for sec in sections:
                paragraphs = [p.strip() for p in sec.split("\n\n") if p.strip()]
                buf = ""
                for p in paragraphs:
                    if len(buf) + len(p) > 1500:  # target char length ~ chunk size
                        chunks.append(buf)
                        buf = p
                    else:
                        buf = (buf + "\n\n" + p) if buf else p
                if buf:
                    chunks.append(buf)
            return chunks[:50]
        if doc_type == "csv":
            # chunk by rows groups
            lines = content.splitlines()
            header = lines[:1]
            rows = lines[1:]
            size = 200
            chunks = ["\n".join(header + rows[i : i + size]) for i in range(0, len(rows), size)]
            return chunks[:50]
        return [content[:2000]]
