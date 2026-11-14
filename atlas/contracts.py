"""Shared types between the core and the app. SHARED FILE: see AGENTS.md §2 before changing it.

Adding a field with a default is always fine. Renaming or removing one needs a `contract:` commit
and the other side told first.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Literal

Kind = Literal["persistent", "dated", "observed"]
Status = Literal["proposed", "current", "closed", "archived", "conflict"]
Label = Literal["allowed", "blocked", "unknown"]
CardColor = Literal["green", "orange", "grey", "red"]
SourceType = Literal["page", "photo"]


@dataclass
class Source:
    """Where a fact comes from: a page of a document or a photo."""
    type: SourceType
    doc_id: str                      # document id or photo file name
    page: int | None = None          # for pages
    taken_at: datetime | None = None  # for photos
    version: str | None = None       # document version, e.g. "v1"


@dataclass
class Statement:
    """The one kind of record. Never deleted: closed or archived."""
    id: str
    subject: str                     # e.g. "machine:P-3"
    property: str                    # e.g. "inspection_interval_days"
    value: str
    quote: str                       # exact text on the page, or text read in the photo
    source: Source
    kind: Kind
    recorded_at: datetime
    in_force_from: date | None = None
    in_force_to: date | None = None
    status: Status = "current"


@dataclass
class Step:
    """One step of an answer's reasoning, with what proves it."""
    text: str
    statement_ids: list[str] = field(default_factory=list)
    quote: str | None = None
    source: Source | None = None


@dataclass
class Answer:
    question: str
    label: Label
    text: str                        # written for a person, from cited steps only
    steps: list[Step]
    verdict_id: str | None = None


@dataclass
class Card:
    """One machine in the Atlas tab."""
    machine: str
    color: CardColor
    headline: str                    # e.g. "Blocked: inspection label older than register"
    reasons: list[str] = field(default_factory=list)
    changed_sources: list[str] = field(default_factory=list)


@dataclass
class Verdict:
    """A stored decision: why, with which facts, rules and model, when."""
    id: str
    question: str
    label: Label
    statement_ids: list[str]
    rules: list[str]
    model: str | None
    decided_at: datetime
    prev_hash: str | None = None
    hash: str | None = None
