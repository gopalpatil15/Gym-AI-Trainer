from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import numpy as np


@dataclass
class VectorItem:
    embedding: np.ndarray
    metadata: Dict[str, Any]


class VectorStore:
    def __init__(self) -> None:
        self._items: List[VectorItem] = []

    def add(self, embedding: np.ndarray, metadata: Dict[str, Any]) -> None:
        self._items.append(VectorItem(embedding=embedding.astype(np.float32), metadata=metadata))

    def add_many(self, embeddings: np.ndarray, metadatas: List[Dict[str, Any]]) -> None:
        for i, md in zip(embeddings, metadatas):
            self.add(i, md)

    def _cosine_sim(self, a: np.ndarray, b: np.ndarray) -> float:
        denom = (np.linalg.norm(a) * np.linalg.norm(b))
        if denom == 0:
            return 0.0
        return float(np.dot(a, b) / denom)

    def search(self, query_embedding: np.ndarray, top_k: int = 5) -> List[Tuple[float, Dict[str, Any]]]:
        scored = [(self._cosine_sim(query_embedding, it.embedding), it.metadata) for it in self._items]
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[:top_k]

    def size(self) -> int:
        return len(self._items)
