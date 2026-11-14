"""Baseline: plain retrieval over the same chunks, with the same model, no ontology. Owner: Product.

To build: embed api.corpus() with atlas.llm.embed, take the 5 most similar chunks,
answer with atlas.llm.chat using only those chunks, return an Answer with mode "rag".
"""
from __future__ import annotations

import os
from datetime import date

from atlas.contracts import Answer


def answer(question: str, as_of: date | None = None) -> Answer:
    if os.getenv("ATLAS_FAKE", "1") == "1":
        from atlas import fake
        return fake.rag_answer(question, as_of)
    raise NotImplementedError("product: RAG baseline")
