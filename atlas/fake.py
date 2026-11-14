"""Fake data so the app works before the core. Owner: Product. Same signatures as atlas/api.py."""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from atlas.contracts import Answer, Card, Source, Statement, Step, Verdict

_NOW = datetime(2026, 11, 14, 11, 0)

_MANUAL = Source(type="page", doc_id="manual-P3", page=23, version="v1")
_REGISTER = Source(type="page", doc_id="register", page=1, version="v1")
_LABEL = Source(type="photo", doc_id="label-P3.jpg", taken_at=_NOW)

_STATEMENTS = [
    Statement("s1", "machine:P-3", "inspection_interval_days", "60",
              "Inspect the guard interlocks every 60 days.", _MANUAL, "persistent", _NOW),
    Statement("s2", "machine:P-3", "last_inspection", "2026-09-10",
              "P-3 | 10/09/2026 | OK", _REGISTER, "dated", _NOW),
    Statement("s3", "machine:P-3", "last_inspection", "2026-06-12",
              "VERIFICA 12/06/2026", _LABEL, "observed", _NOW, status="conflict"),
]


def answer(question: str, as_of: date | None = None) -> Answer:
    return Answer(
        question=question,
        label="blocked",
        text="No. The label on P-3 shows its last inspection on 12 June, older than the register "
             "says, and the manual requires one every 60 days.",
        steps=[
            Step("The manual requires an inspection every 60 days.", ["s1"], _STATEMENTS[0].quote, _MANUAL),
            Step("The register says the last inspection was on 10 September.", ["s2"], _STATEMENTS[1].quote, _REGISTER),
            Step("The photo of the label says 12 June: paper and floor disagree.", ["s3"], _STATEMENTS[2].quote, _LABEL),
        ],
        verdict_id="v1",
    )


def ingest_document(path: Path, version: str | None = None) -> list[Statement]:
    return _STATEMENTS[:2]


def ingest_photo(path: Path, machine_hint: str | None = None) -> list[Statement]:
    return _STATEMENTS[2:]


def atlas_cards(as_of: date | None = None) -> list[Card]:
    return [
        Card("P-3", "red", "Blocked: inspection label older than the register",
             ["label photo 12/06/2026 vs register 10/09/2026"]),
        Card("L-1", "green", "In order"),
        Card("S-2", "orange", "Re-read: procedure changed", changed_sources=["procedure v2"]),
        Card("C-4", "grey", "Photo older than 30 days: take a new one"),
    ]


def history(subject: str) -> list[Statement]:
    return [s for s in _STATEMENTS if s.subject == subject]


def verdicts(as_of: date | None = None) -> list[Verdict]:
    return [Verdict("v1", "Can a line operator run press P-3 today?", "blocked",
                    ["s1", "s2", "s3"], ["inspection_overdue", "paper_floor_conflict"],
                    "fake", _NOW, prev_hash=None, hash="0000")]
