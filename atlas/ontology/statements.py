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
# The ontology works in layers, from the general to the specific. A higher layer constrains a lower one.
LAYERS = ("law", "guidance", "manufacturer", "company", "plant")
LAYER_ORDER = {name: number for number, name in enumerate(LAYERS, start=1)}
# Higher number wins when two sources disagree: ten points per layer, so there is room for a finer
# order inside a layer (a ministerial decree sits below the other laws and above the guidance).
LAYER_RANK = {name: 10 * (len(LAYERS) + 1 - number) for name, number in LAYER_ORDER.items()}
MINISTERIAL_RANK = LAYER_RANK["law"] - 5
PERSON_RANK = 5
# The document kinds of the registry, and the layer each one belongs to.
KIND_LAYER = {"law": "law", "guidance": "guidance", "manual": "manufacturer", "procedure": "company",
              "log": "plant", "layout": "plant"}
# Kept for older callers: the flat order by document kind. The store itself now ranks with rank_of().
AUTHORITY = {"law": 4, "manual": 3, "procedure": 2, "log": 2, "person": 1}
LAYER_NOUN = {"law": "the law", "guidance": "a public body's guidance", "manufacturer": "the manufacturer's manual",
              "company": "a company procedure", "plant": "a plant record"}
# Words that announce a condition or an exception in the quoted text (English and Italian).
CONDITION_MARKERS = re.compile(
    r"\b(if|unless|except|provided that|older than|only for|for the sector|"
    r"se|salvo|eccetto|tranne|qualora|purch[eé]|ad eccezione)\b",
    re.IGNORECASE,
)


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def law_tier(source_doc: str) -> str:
    """What kind of law a source key names: 'DM2011' is a ministerial decree, 'DLGS71' a legislative decree."""
    key = source_doc.lower()
    if re.match(r"dm[\d_-]", key):
        return "ministerial decree"
    if key.startswith("dlgs"):
        return "legislative decree"
    if key.startswith("corr"):
        return "corrigendum"
    if key.startswith(("reg", "eu-reg")):
        return "EU regulation"
    if key.startswith(("dir", "eu-dir")):
        return "EU directive"
    return "law"


def _article(noun: str) -> str:
    return f"an {noun}" if noun[0] in "AEIOUaeiou" else f"a {noun}"


def layer_of_statement(s: "Statement", corpus=None) -> str:
    """The layer written on the fact, or the layer of its source in the corpus; '' when neither knows."""
    if s.layer:
        return s.layer
    lookup = getattr(corpus, "layer", None)
    return (lookup(s.source_doc) if lookup else "") or ""


def rank_of(s: "Statement", corpus=None) -> int:
    """How much a fact weighs when two disagree: its layer first, then the finer order inside the law."""
    if s.asserted_by.startswith("person:"):
        return PERSON_RANK
    layer = layer_of_statement(s, corpus)
    if layer == "law" and law_tier(s.source_doc) == "ministerial decree":
        return MINISTERIAL_RANK
    return LAYER_RANK.get(layer, 0)


def _describe(s: "Statement", corpus=None) -> str:
    if s.asserted_by.startswith("person:"):
        return "a person's statement"
    layer = layer_of_statement(s, corpus)
    if layer == "law":
        tier = law_tier(s.source_doc)
        return "the law" if tier == "law" else _article(tier)
    return LAYER_NOUN.get(layer, "a source of unknown layer")


def settle(a: "Statement", b: "Statement", corpus=None) -> tuple["Statement", str]:
    """Which of two disagreeing facts prevails, and why in one short sentence. On equal rank `a` prevails
    (the store passes the newer fact first)."""
    rank_a, rank_b = rank_of(a, corpus), rank_of(b, corpus)
    if rank_a == rank_b:
        return a, f"both come from {_describe(a, corpus)}: the more recent one prevails"
    winner, loser = (a, b) if rank_a > rank_b else (b, a)
    return winner, f"{_describe(winner, corpus)} outranks {_describe(loser, corpus)}"


_DURATION = re.compile(r"P(?:(\d+(?:\.\d+)?)Y)?(?:(\d+(?:\.\d+)?)M)?(?:(\d+(?:\.\d+)?)W)?(?:(\d+(?:\.\d+)?)D)?"
                       r"(?:T(?:(\d+(?:\.\d+)?)H)?(?:(\d+(?:\.\d+)?)M)?(?:(\d+(?:\.\d+)?)S)?)?")
_LENGTH = re.compile(r"(\d+(?:[.,]\d+)?)\s*(mm|cm|m)?", re.IGNORECASE)
SMALLER_IS_STRICTER, LARGER_IS_STRICTER = "smaller_is_stricter", "larger_is_stricter"


def measure(value) -> tuple[str, float]:
    """('duration', days) for an ISO duration such as 'P45D' or 'P2Y'; ('length', millimetres) for a number
    or a text such as '850', '850 mm', '1.3 m'. A year counts 365 days and a month 30. Raises ValueError otherwise."""
    text = str(value).strip()
    match = _DURATION.fullmatch(text)
    if match and text not in ("P", "PT") and not text.endswith("T"):
        years, months, weeks, days, hours, minutes, seconds = (float(x or 0) for x in match.groups())
        return "duration", years * 365 + months * 30 + weeks * 7 + days + hours / 24 + minutes / 1440 + seconds / 86400
    match = _LENGTH.fullmatch(text)
    if match:
        factor = {"mm": 1.0, "cm": 10.0, "m": 1000.0}[(match.group(2) or "mm").lower()]
        return "length", float(match.group(1).replace(",", ".")) * factor
    raise ValueError(f"not an ISO duration nor a length in mm: {value!r}")


def compare_strictness(upper_value, lower_value, sense: str) -> str:
    """Is the rule of the lower layer 'stricter', the 'same' or 'looser' than the rule of the higher layer?
    A stricter lower rule is allowed, a looser one is flagged. `sense` is SMALLER_IS_STRICTER for an interval
    or a time limit (inspect every 90 days) and LARGER_IS_STRICTER for a protected distance (a fence radius)."""
    if sense not in (SMALLER_IS_STRICTER, LARGER_IS_STRICTER):
        raise ValueError(f"sense must be {SMALLER_IS_STRICTER!r} or {LARGER_IS_STRICTER!r}, not {sense!r}")
    (upper_unit, upper), (lower_unit, lower) = measure(upper_value), measure(lower_value)
    if upper_unit != lower_unit:
        raise ValueError(f"cannot compare a {upper_unit} with a {lower_unit}")
    if abs(upper - lower) < 1e-9:
        return "same"
    return "stricter" if (lower < upper) == (sense == SMALLER_IS_STRICTER) else "looser"


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
    layer: str = ""            # one of LAYERS; filled from the source when the fact is written


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

    def layer(self, doc_id: str) -> str:
        """The layer of a registered document: its own 'layer' column, or the layer of its kind."""
        row = self.meta(doc_id)
        return row.get("layer") or KIND_LAYER.get(row.get("kind", ""), "")


class ChunkCorpus:
    """The same two questions the store asks, answered from the chunks of atlas.corpus.chunker."""

    KINDS = {"REG": "law", "DIR": "law", "CORR": "law"}

    def __init__(self, chunks) -> None:
        self.chunks = {(c.source, c.locator): c for c in chunks}
        self.versions = {c.source: c.version for c in chunks}
        self.layers = {c.source: c.layer for c in chunks if getattr(c, "layer", "")}

    def section(self, doc_id: str, anchor: str) -> str | None:
        chunk = self.chunks.get((doc_id, anchor))
        return chunk.text if chunk else None

    def meta(self, doc_id: str) -> dict:
        return {"kind": self.KINDS.get(doc_id, "law"), "version": self.versions.get(doc_id, "")}

    def layer(self, doc_id: str) -> str:
        """The layer of the chunks of a source; '' for a source the corpus does not hold."""
        return self.layers.get(doc_id, "")


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
        s.layer = s.layer or self.layer_of(s)
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
                winner, _ = self.settle(new, old)
                loser = old if winner is new else new
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

    @classmethod
    def load(cls, corpus, path: Path) -> "Store":
        store = cls(corpus, path)
        payload = json.loads(path.read_text())
        store.statements = [Statement(**item) for item in payload["statements"]]
        store.rejections = payload["rejections"]
        return store

    def layer_of(self, s: Statement) -> str:
        return layer_of_statement(s, self.corpus)

    def rank_of(self, s: Statement) -> int:
        return rank_of(s, self.corpus)

    def settle(self, a: Statement, b: Statement) -> tuple[Statement, str]:
        """Which of two disagreeing facts prevails and why; pass the newer one first."""
        return settle(a, b, self.corpus)

    def _rank(self, s: Statement) -> int:
        return self.rank_of(s)

    def _reject(self, s: Statement, reason: str) -> None:
        self.rejections.append({"reason": reason, "statement": s.model_dump(mode="json")})
        return None
