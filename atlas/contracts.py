"""Shared types between the brain (Core) and the app and evaluation (Product).

SHARED FILE: change it only as AGENTS.md §4 says (a `contract:` commit, atlas/fake.py updated,
the other side told). Adding a field with a default is always fine.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Union

Strategy = Literal["A", "B"]        # A = free extraction, B = guided by the CQs and the structure
Mode = Literal["rag", "A", "B"]     # how a question was answered
AnswerValue = Union[list[str], str, bool, None]   # comparable with the gold in data/cq/cqs.json
ChangeKind = Literal["add", "remove", "modify"]
ChangeStatus = Literal["proposed", "accepted", "rejected"]


@dataclass
class Chunk:
    """A piece of the corpus, cut along the document's own structure."""
    id: str                    # e.g. "REG:Art.25(2)", or "REG:w0042" for a fixed window
    source: str                # a key of "sources" in data/cq/cqs.json, or a plant document id
    locator: str               # e.g. "Art. 25(2)", "Annex III, 1.3.7", "Corrigendum, point 10"
    text: str
    version: str = ""          # e.g. "OJ L 165, 29.6.2023"
    sha256: str = ""           # fingerprint of the text: a changed piece has a different one
    layer: str = ""            # "law" | "manufacturer" | "company" | "plant"


@dataclass
class Step:
    """One step of an answer, with what proves it."""
    text: str
    sparql: str | None = None
    triples: list[tuple[str, str, str]] = field(default_factory=list)
    quote: str | None = None
    locator: str | None = None
    statement_id: str | None = None   # the fact of the store this step used


@dataclass
class Answer:
    question: str
    mode: Mode
    value: AnswerValue         # list for "set", ISO string for "date"/"duration", bool for "boolean", text for "text"
    text: str                  # written for a person, from the steps only
    steps: list[Step] = field(default_factory=list)
    tokens: int = 0
    cost_usd: float = 0.0
    basis: str = ""            # which path answered: "rule", "facts", "text" (read on demand), "both", "" (not said)


@dataclass
class BuildResult:
    strategy: Strategy
    ontology_path: Path
    shapes_path: Path | None   # SHACL shapes; None for strategy A
    n_classes: int
    n_properties: int
    n_triples: int
    human_decisions: int = 0   # how many times a person had to decide (the "expert minutes")
    tokens: int = 0
    cost_usd: float = 0.0
    seconds: float = 0.0
    proposed: int = 0          # facts the strategy proposed
    anchored: int = 0          # facts that passed the checks (quote in the text, value in the quote, condition kept)
    rejected: int = 0          # facts refused by the checks


@dataclass
class ValidationReport:
    strategy: Strategy
    conforms: bool
    violations: list[str] = field(default_factory=list)


@dataclass
class Change:
    """One proposed change to the ontology, with the passage that caused it."""
    id: str
    kind: ChangeKind
    target: str                # class, property or individual (label or IRI)
    before: str | None
    after: str | None
    locator: str
    quote: str
    status: ChangeStatus = "proposed"


@dataclass
class ChangeSet:
    id: str
    document: str              # the new or changed document
    changes: list[Change]
