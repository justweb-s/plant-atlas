"""Owner: Core. One kind of record (Statement), one way in (write_statement), one way out (as_of).

Nothing is ever deleted: a fact that stops holding is closed, a fact that loses to a higher
authority is kept as `conflict`, a fact that fails a check is counted in `rejections`.
"""
from __future__ import annotations

import csv
import json
import re
from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[2]
# Higher number wins when two sources disagree.
AUTHORITY = {"law": 4, "manual": 3, "procedure": 2, "log": 2, "person": 1}
# Words that announce a condition or an exception in the quoted text (English and Italian).
CONDITION_MARKERS = re.compile(
    r"\b(if|unless|except|provided that|older than|only for|for the sector|"
    r"se|salvo|eccetto|tranne|qualora|purch[eé]|ad eccezione)\b",
    re.IGNORECASE,
)


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


class Statement(BaseModel):
    id: str = ""
    subject: str
    predicate: str
    object: str
    object_as_written: str
    object_normalised: str = ""
    condition: str = ""
    condition_quote: str = ""
    quote: str
    source_doc: str
    anchor: str
    source_version: str = ""
    kind: Literal["persistent", "dated", "observed"] = "persistent"
    in_force_from: date | None = None
    in_force_to: date | None = None
    status: Literal["proposed", "current", "closed", "conflict", "open_point"] = "proposed"
    asserted_by: str
    conflicts_with: str = ""
    confirmations: int = 0


class Corpus:
    """Reads the registered sections; the only place facts are checked against."""

    def __init__(self, folder: Path = ROOT / "atlas" / "corpus" / "incoming") -> None:
        self.folder = folder
        with (folder / "registry.csv").open() as handle:
            self.rows = {row["id"]: row for row in csv.DictReader(handle)}

    def section(self, doc_id: str, anchor: str) -> str | None:
        row = self.rows.get(f"{doc_id}#{anchor}")
        return (self.folder / row["path"]).read_text(encoding="utf-8") if row else None

    def meta(self, doc_id: str) -> dict:
        return self.rows.get(doc_id, {})


class Store:
    def __init__(self, corpus: Corpus, path: Path | None = None) -> None:
        self.corpus = corpus
        self.path = path
        self.statements: list[Statement] = []
        self.rejections: list[dict] = []

    # ---- one way in -------------------------------------------------------
    def write_statement(self, s: Statement) -> Statement | None:
        """Check the fact against its source. Returns the stored statement, or None if rejected."""
        text = self.corpus.section(s.source_doc, s.anchor)
        if text is None or norm(s.quote) not in norm(text) or not norm(s.quote):
            return self._reject(s, "no_anchor")
        if s.status != "open_point":
            if norm(s.object_as_written) not in norm(s.quote) or not norm(s.object_as_written):
                return self._reject(s, "value_not_in_quote")
            if CONDITION_MARKERS.search(s.quote) and not s.condition.strip():
                return self._reject(s, "missing_condition")
            if s.condition_quote and norm(s.condition_quote) not in norm(text):
                return self._reject(s, "condition_no_anchor")
        meta = self.corpus.meta(s.source_doc)
        s.source_version = s.source_version or meta.get("version", "")
        if s.in_force_from is None and meta.get("in_force_from"):
            s.in_force_from = date.fromisoformat(meta["in_force_from"])
        s.id = s.id or f"st-{len(self.statements) + 1:04d}"
        if s.status != "open_point":
            s.status = "proposed"
        self.statements.append(s)
        return s

    def make_current(self, statement_id: str) -> Statement:
        """A proposed fact passed the second reader: settle it against what is already current."""
        new = self.get(statement_id)
        key = (new.subject, new.predicate, norm(new.condition).lower())
        rivals = [o for o in self.statements if o.status == "current" and o.id != new.id
                  and (o.subject, o.predicate, norm(o.condition).lower()) == key]
        new.status = "current"
        for old in rivals:
            if norm(old.object_normalised or old.object) == norm(new.object_normalised or new.object):
                old.confirmations += 1
                new.status, new.conflicts_with = "closed", old.id  # same fact, kept as a confirmation
                new.in_force_to = new.in_force_from or date.min
            elif old.source_doc == new.source_doc and new.source_version != old.source_version:
                old.status = "closed"  # a newer version of the same document
                old.in_force_to = new.in_force_from or date.today()
            else:
                winner, loser = (new, old) if self._rank(new) >= self._rank(old) else (old, new)
                winner.status, loser.status = "current", "conflict"
                loser.conflicts_with = winner.id
        return new

    # ---- one way out ------------------------------------------------------
    def as_of(self, day: date) -> list[Statement]:
        """Statements that were in force on `day` (current ones, and closed ones before they closed)."""
        result = []
        for s in self.statements:
            if s.status not in ("current", "closed"):
                continue
            if s.in_force_from and s.in_force_from > day:
                continue
            if s.in_force_to and s.in_force_to <= day:
                continue
            result.append(s)
        return result

    # ---- helpers ----------------------------------------------------------
    def get(self, statement_id: str) -> Statement:
        return next(s for s in self.statements if s.id == statement_id)

    def counts(self) -> dict:
        out: dict = {"proposed_total": len(self.statements) + len(self.rejections),
                     "anchored": len(self.statements), "rejected": len(self.rejections)}
        for r in self.rejections:
            out[f"rejected_{r['reason']}"] = out.get(f"rejected_{r['reason']}", 0) + 1
        for s in self.statements:
            out[f"status_{s.status}"] = out.get(f"status_{s.status}", 0) + 1
        return out

    def save(self) -> None:
        if self.path:
            self.path.parent.mkdir(exist_ok=True)
            payload = {"statements": [s.model_dump(mode="json") for s in self.statements],
                       "rejections": self.rejections}
            self.path.write_text(json.dumps(payload, indent=1, ensure_ascii=False))

    def _rank(self, s: Statement) -> int:
        if s.asserted_by.startswith("person:"):
            return AUTHORITY["person"]
        return AUTHORITY.get(self.corpus.meta(s.source_doc).get("kind", ""), 0)

    def _reject(self, s: Statement, reason: str) -> None:
        self.rejections.append({"reason": reason, "statement": s.model_dump(mode="json")})
        return None
