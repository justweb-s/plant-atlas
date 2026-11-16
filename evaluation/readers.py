"""A reader plugged in from outside atlas/: passages found by similarity (the RAG way), read under the gate.

Same reading prompt and same quote check as the other readers; only the way the passages are found differs
(embeddings computed on this machine, evaluation/local_embed.py). Registered as "similar".
"""
from __future__ import annotations

from datetime import date

from atlas.agent import readers


def _similar(question: str, store, day: date):
    from atlas.agent import text
    from evaluation import rag

    found = text.answer(question, day, finder=lambda q: rag.retrieve(q, top=12))
    found.basis = "similar"
    return found


readers.register("similar", _similar, 2)
