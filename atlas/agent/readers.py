"""Owner: Core. The readers: every way the system has to answer a question, behind one interface.

A reader is a function (question, store, day) -> Answer. Whatever it does inside, what it returns has passed
the same gate: every sentence it rests on is in a registered piece, and a date or a period given as the answer
is written in those sentences. A new reader is one call to register(); the router (atlas/agent/router.py)
then learns from the logged outcomes when to use it.
"""
from __future__ import annotations

import importlib
import os
from datetime import date
from typing import Callable

from atlas.contracts import Answer

Reader = Callable[[str, object, date], Answer]
READERS: dict[str, Reader] = {}
COST: dict[str, float] = {}      # rough cost of one run, in model calls; the router breaks ties with it


def register(name: str, reader: Reader, cost: float) -> None:
    READERS[name] = reader
    COST[name] = cost


def _facts(question: str, store, day: date) -> Answer:
    from atlas.agent.answer import from_facts
    return from_facts(question, store, day)


def _words(question: str, store, day: date) -> Answer:
    from atlas.agent import text
    found = text.answer(question, day)
    found.basis = "text"
    return found


def _search(question: str, store, day: date) -> Answer:
    from atlas.agent import text
    return text.search(question, day)


register("facts", _facts, 2)      # the fact store: procedures, the plant rule, list queries, facts
register("words", _words, 2)      # reading on demand, passages found by their words
register("search", _search, 6)    # a free search through the documents, by a model with read-only tools


def load_plugins() -> None:
    """Readers defined outside atlas/ (ATLAS_READER_PLUGINS, comma separated modules; each calls register())."""
    for module in filter(None, os.getenv("ATLAS_READER_PLUGINS", "evaluation.readers").split(",")):
        try:
            importlib.import_module(module.strip())
        except ImportError:
            continue   # an optional reader whose libraries are not installed is simply absent
