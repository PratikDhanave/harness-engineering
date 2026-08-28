"""Long-term retrieval — the agent's knowledge base (Lesson 4).

The `KnowledgeStore` protocol is the swap point: a local in-memory keyword index
for offline dev/tests, and (later) Azure AI Search — same interface, so the agent
retrieves grounding documents the same way regardless of backend.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol


@dataclass
class Hit:
    doc_id: str
    text: str
    score: float


class KnowledgeStore(Protocol):
    def add(self, doc_id: str, text: str) -> None: ...

    def search(self, query: str, k: int = 3) -> list[Hit]: ...


# Split on any run of non-alphanumeric characters, lowercased — a crude tokenizer,
# but deterministic and dependency-free.
_TOKEN = re.compile(r"[a-z0-9]+")


def _terms(text: str) -> set[str]:
    return set(_TOKEN.findall(text.lower()))


class InMemoryKnowledgeStore:
    """In-memory keyword index — local stand-in for Azure AI Search.

    Scoring is the fraction of *distinct query terms* that appear in a document
    (case-insensitive), so more overlap ranks higher and the score is a stable
    0.0-1.0 number. Ties break by `doc_id` for determinism.

    Where this is weaker than the managed service (state the leak): this is a pure
    keyword *overlap* match, NOT semantic search. It cannot tell that "car" and
    "automobile" are related, ignores word order and phrases, and has no vector
    embeddings, synonyms, stemming, or relevance tuning. Azure AI Search does real
    vector / semantic ranking (and hybrid keyword+vector). Documents that would
    rank well semantically can score 0.0 here, and vice versa.
    """

    def __init__(self) -> None:
        # doc_id -> (raw text, precomputed term set)
        self._docs: dict[str, tuple[str, set[str]]] = {}

    def add(self, doc_id: str, text: str) -> None:
        # Upsert: re-adding a doc_id replaces it, mirroring an AI Search index merge.
        self._docs[doc_id] = (text, _terms(text))

    def search(self, query: str, k: int = 3) -> list[Hit]:
        q_terms = _terms(query)
        if not q_terms:
            return []

        hits: list[Hit] = []
        for doc_id, (text, doc_terms) in self._docs.items():
            overlap = len(q_terms & doc_terms)
            if overlap == 0:
                continue  # no matching terms -> not a hit
            score = overlap / len(q_terms)
            hits.append(Hit(doc_id=doc_id, text=text, score=score))

        # Highest score first; ties broken by doc_id so results are deterministic.
        hits.sort(key=lambda h: (-h.score, h.doc_id))
        return hits[:k]
