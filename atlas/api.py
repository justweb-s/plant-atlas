"""The only functions the app calls. SHARED FILE: see AGENTS.md §2 before changing it.

With ATLAS_FAKE=1 every function returns data from atlas/fake.py. Core replaces each
`raise NotImplementedError` with the real call when it works, and says so in notes/core.md.
"""
from __future__ import annotations

import os
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

from atlas.contracts import Answer, Card, Statement, Verdict

load_dotenv()


def _fake() -> bool:
    return os.getenv("ATLAS_FAKE", "1") == "1"


def answer(question: str, as_of: date | None = None) -> Answer:
    """Answer a question with cited steps; stores a Verdict."""
    if _fake():
        from atlas import fake
        return fake.answer(question, as_of)
    raise NotImplementedError("core: answer")


def ingest_document(path: Path, version: str | None = None) -> list[Statement]:
    """Read a document (law extract, manual, procedure) into statements with page citations."""
    if _fake():
        from atlas import fake
        return fake.ingest_document(path, version)
    raise NotImplementedError("core: ingest_document")


def ingest_photo(path: Path, machine_hint: str | None = None) -> list[Statement]:
    """Read a photo (nameplate, inspection label, guards) into observed statements."""
    if _fake():
        from atlas import fake
        return fake.ingest_photo(path, machine_hint)
    raise NotImplementedError("vision: ingest_photo")


def atlas_cards(as_of: date | None = None) -> list[Card]:
    """One card per machine: green, orange, grey or red."""
    if _fake():
        from atlas import fake
        return fake.atlas_cards(as_of)
    raise NotImplementedError("core: atlas_cards")


def history(subject: str) -> list[Statement]:
    """Every statement ever recorded on a subject, closed ones included."""
    if _fake():
        from atlas import fake
        return fake.history(subject)
    raise NotImplementedError("core: history")


def verdicts(as_of: date | None = None) -> list[Verdict]:
    """Stored verdicts, newest first."""
    if _fake():
        from atlas import fake
        return fake.verdicts(as_of)
    raise NotImplementedError("core: verdicts")


def verify_chain() -> bool:
    """True if the event log's hash chain is intact."""
    if _fake():
        return True
    raise NotImplementedError("core: verify_chain")


def reset_context() -> None:
    """Drop the agent's working context; memory stays in the store."""
    if _fake():
        return None
    raise NotImplementedError("core: reset_context")
