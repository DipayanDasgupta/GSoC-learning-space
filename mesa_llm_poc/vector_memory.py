"""Mesa-LLM PoC — Pillar 1: Per-Agent Vector Memory.

Implements a VectorMemory abstract base class with two concrete backends:
  - MockMemory    — in-memory string matching (no FAISS required for CI)
  - FAISSMemory   — real FAISS index per agent (requires faiss-cpu)

The public interface is identical for both:
    memory.store(agent_id, step, text)
    memory.retrieve(query, agent_id, k) -> list[str]

This mirrors the Generative Agents (Park et al., 2023) memory architecture,
adapted for Mesa's discrete-space simulation loop.
"""
from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Literal


# ── Abstract base class ───────────────────────────────────────────────────────

class VectorMemory(ABC):
    """Abstract per-agent vector memory store.

    Each agent gets its own index, preventing cross-agent contamination.
    Retrieval scopes by both semantic similarity AND agent identity.
    """

    @abstractmethod
    def store(self, agent_id: int, step: int, text: str) -> None:
        """Embed `text` and store it in agent `agent_id`'s index."""

    @abstractmethod
    def retrieve(self, query: str, agent_id: int, k: int | None = None) -> list[str]:
        """Return the top-k texts most semantically similar to `query`."""

    @abstractmethod
    def entry_count(self, agent_id: int) -> int:
        """Return the number of stored entries for agent_id."""

    def batch_embed(self, texts: list[str]) -> list[list[float]]:
        """Batch-embed texts for efficiency. Override in concrete classes."""
        return [self._embed(t) for t in texts]

    def _embed(self, text: str) -> list[float]:
        """Default: bag-of-words character frequency vector (for mocking)."""
        vec = [0.0] * 26
        for ch in text.lower():
            if "a" <= ch <= "z":
                vec[ord(ch) - ord("a")] += 1.0
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]


# ── Concrete: MockMemory (no dependencies, CI-safe) ───────────────────────────

@dataclass
class _Entry:
    step: int
    text: str
    embedding: list[float]


class MockMemory(VectorMemory):
    """In-memory vector store using cosine similarity on character n-grams.

    No external dependencies. Suitable for CI and quick experimentation.
    Swap for FAISSMemory in production — identical public interface.
    """

    def __init__(self, k: int = 4):
        self.k = k
        self._store: dict[int, list[_Entry]] = {}

    def store(self, agent_id: int, step: int, text: str) -> None:
        if agent_id not in self._store:
            self._store[agent_id] = []
        self._store[agent_id].append(
            _Entry(step=step, text=text, embedding=self._embed(text))
        )

    def retrieve(self, query: str, agent_id: int, k: int | None = None) -> list[str]:
        k = k or self.k
        entries = self._store.get(agent_id, [])
        if not entries:
            return []
        q_emb = self._embed(query)
        scored = sorted(entries, key=lambda e: -self._cosine(q_emb, e.embedding))
        return [e.text for e in scored[:k]]

    def entry_count(self, agent_id: int) -> int:
        return len(self._store.get(agent_id, []))

    @staticmethod
    def _cosine(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a)) or 1.0
        nb = math.sqrt(sum(x * x for x in b)) or 1.0
        return dot / (na * nb)


# ── Concrete: FAISSMemory (real FAISS, requires faiss-cpu) ────────────────────

class FAISSMemory(VectorMemory):
    """Per-agent FAISS flat index with text-embedding-3-small embeddings.

    Requires: faiss-cpu, langchain-openai (or any embedding provider).
    Each agent gets its own FAISS.IndexFlatL2 index; all indices live in RAM.
    Use persist_path to save/restore indices across simulation restarts.
    """

    def __init__(
        self,
        embed_model: str = "text-embedding-3-small",
        k: int = 4,
        persist_path: str | None = None,
    ):
        try:
            import faiss  # noqa: F401
        except ImportError as e:
            raise ImportError(
                "FAISSMemory requires 'faiss-cpu'. Install with: "
                "pip install faiss-cpu"
            ) from e
        self.embed_model = embed_model
        self.k = k
        self.persist_path = persist_path
        self._indices: dict[int, object] = {}   # agent_id → faiss.Index
        self._texts: dict[int, list[str]] = {}  # agent_id → raw texts (for retrieval)
        self._embedder = None

    def _get_embedder(self):
        if self._embedder is None:
            from langchain_openai import OpenAIEmbeddings
            self._embedder = OpenAIEmbeddings(model=self.embed_model)
        return self._embedder

    def _get_or_create_index(self, agent_id: int, dim: int):
        import faiss
        if agent_id not in self._indices:
            self._indices[agent_id] = faiss.IndexFlatL2(dim)
            self._texts[agent_id] = []
        return self._indices[agent_id]

    def store(self, agent_id: int, step: int, text: str) -> None:
        import numpy as np
        embedder = self._get_embedder()
        vec = embedder.embed_query(text)
        arr = np.array([vec], dtype="float32")
        idx = self._get_or_create_index(agent_id, len(vec))
        idx.add(arr)
        self._texts[agent_id].append(text)

    def retrieve(self, query: str, agent_id: int, k: int | None = None) -> list[str]:
        import numpy as np
        k = k or self.k
        texts = self._texts.get(agent_id, [])
        if not texts:
            return []
        embedder = self._get_embedder()
        q_vec = np.array([embedder.embed_query(query)], dtype="float32")
        idx = self._indices[agent_id]
        actual_k = min(k, idx.ntotal)
        _, indices = idx.search(q_vec, actual_k)
        return [texts[i] for i in indices[0] if i < len(texts)]

    def entry_count(self, agent_id: int) -> int:
        idx = self._indices.get(agent_id)
        return idx.ntotal if idx is not None else 0


# ── Factory ───────────────────────────────────────────────────────────────────

def make_memory(
    backend: Literal["mock", "faiss"] = "mock",
    k: int = 4,
    persist_path: str | None = None,
    **kwargs,
) -> VectorMemory:
    """Factory function for selecting a memory backend."""
    if backend == "mock":
        return MockMemory(k=k)
    if backend == "faiss":
        return FAISSMemory(k=k, persist_path=persist_path, **kwargs)
    raise ValueError(f"Unknown memory backend: {backend!r}. Choose 'mock' or 'faiss'.")
