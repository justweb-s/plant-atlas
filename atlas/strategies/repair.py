"""Owner: Core. Two repairs of the law facts, written by code and checked by the store like every other fact.

1. Risks named in the sentences of Annex III, points 1.x, of Regulation (EU) 2023/1230 become `addressesRisk`
   facts (the extraction kept only the heading as a risk and stored the rest as measures).
2. A lettered list "(a) ...; (b) ...; (c) ..." of procedures becomes one `requiresProcedure` fact per item, so a
   sequence inside an item ("module B ..., followed by ... module C") stays whole and in the order of the text.
   The facts it replaces are closed in statements.json (status and in_force_to only); nothing is deleted.

Run: python -m atlas.strategies.repair   (no model call; writes ontology/B/parts/law_repairs.json)
"""
from __future__ import annotations

import json
import re
from collections import Counter
from datetime import date
from pathlib import Path

from atlas.corpus.chunker import load
from atlas.ontology.statements import CONDITION_MARKERS, ChunkCorpus, Statement, Store, norm

ROOT = Path(__file__).resolve().parents[2]
STATEMENTS = ROOT / "ontology" / "B" / "statements.json"
PART = ROOT / "ontology" / "B" / "parts" / "law_repairs.json"
PREFIX = "law_repairs-"
REPAIR_DAY = date(2026, 11, 14)
SOURCE = "REG"
MAX_WORDS = 14

CONDITION_WORD = re.compile(r"\b(if|where|unless|except|provided that|only for)\b", re.IGNORECASE)
SENTENCE_END = re.compile(r"(?<=[a-z)])\.\s+(?=[A-Z])")
# Each pattern gives the phrase to keep as its group "p".
RISK_PATTERNS = [re.compile(p, re.IGNORECASE) for p in (
    r"(?P<p>risks? of [^.;,:]+)",
    r"(?P<p>risks? (?:related to|due to|arising from|caused by|resulting from) [^.;,:]+)",
    r"to prevent (?:any |all )?(?P<p>[^.;,:]+)",
    r"(?P<p>accidental [a-z ]+? of [^.;,:]+)",
    r"(?:the )?(?P<p>\b(?:psychological |physical |mental )?(?:stress|fatigue|strain|discomfort)[^.;,:]*)",
)]
# Where a risk phrase stops inside its clause: at the verb of the sentence, or at the next thing listed.
PHRASE_STOP = re.compile(r"\s+(?:or shall|and shall|shall|must|is to be|are to be|and the|and to|or to|in order to|"
                         r"so that|so as to|where|if|unless|when|while|remains?|(?<!that )(?<!which )(?:is|are|has|have))\b")
TRAILING = re.compile(r"(?:\s+(?:or|and|a|an|the|to|by|of|with|from|in))+$")
HEADING_STOP = re.compile(r"(?<=[a-z])\s+(?=[A-Z][a-z])")   # a heading run into its first sentence


def sentence_at(text: str, start: int, end: int) -> str:
    """The sentence of `text` that holds text[start:end], as a contiguous substring (without the point number)."""
    cuts = [0] + [m.end() for m in SENTENCE_END.finditer(text)] + [len(text)]
    left = max(c for c in cuts if c <= start)
    right = min(c for c in cuts if c >= end)
    sentence = text[left:right].strip()
    return re.sub(r"^\d+(?:\.\d+)*\.\s+", "", sentence)


def trim(phrase: str) -> str:
    """Cut a matched phrase to the risk itself: still a contiguous piece of the text, at most MAX_WORDS words."""
    for stop in (HEADING_STOP, PHRASE_STOP):
        found = stop.search(phrase)
        if found:
            phrase = phrase[:found.start()]
    words = phrase.split(" ")
    if len(words) > MAX_WORDS:
        phrase = " ".join(words[:MAX_WORDS])
    return TRAILING.sub("", phrase).strip(" ()")


def condition_of(quote: str) -> str:
    """The clause that starts at the first condition word of the quote, up to its comma; '' when there is none."""
    first = min((m for m in (CONDITION_WORD.search(quote), CONDITION_MARKERS.search(quote)) if m),
                key=lambda m: m.start(), default=None)
    if first is None:
        return ""
    return re.split(r",(?!\s+(?:Part|Section|Chapter|point)\b)|[;:.]", quote[first.start():], maxsplit=1)[0].strip()


def risk_phrases(text: str) -> list[tuple[str, str]]:
    """(phrase, sentence) for every risk the patterns find in a chunk, in the order of the text, no phrase twice."""
    found: list[tuple[int, int, str]] = []
    for pattern in RISK_PATTERNS:
        for match in pattern.finditer(text):
            phrase = trim(match.group("p"))
            if len(phrase.split()) < 2 or phrase.lower().startswith(("this ", "these ", "it ", "them ", "such ", "or ", "a risk")):
                continue
            start = text.find(phrase, match.start("p"))
            if start >= 0:
                found.append((start, start + len(phrase), phrase))
    found.sort(key=lambda item: (item[0], -(item[1] - item[0])))
    kept: list[tuple[int, int, str]] = []
    for start, end, phrase in found:
        if any(s <= start and end <= e for s, e, _ in kept):   # inside a phrase already kept
            continue
        if any(norm(phrase).lower() == norm(p).lower() for _, _, p in kept):
            continue
        kept.append((start, end, phrase))
    return [(phrase, sentence_at(text, start, end)) for start, end, phrase in kept]


def repair_risks(store: Store, chunks, existing: list[Statement]) -> dict[str, int]:
    """Defect 1. Returns how many facts each point gained."""
    seen = {(s.anchor, norm(s.object_normalised or s.object).lower()) for s in existing
            if s.predicate == "addressesRisk" and s.status == "current" and s.source_doc == SOURCE}
    added: Counter = Counter()
    for chunk in chunks:
        if chunk.source != SOURCE or not chunk.locator.startswith("Annex III, 1."):
            continue
        point = chunk.locator.split(", ", 1)[1]
        for phrase, sentence in risk_phrases(chunk.text):
            key = (chunk.locator, norm(phrase).lower())
            if key in seen:
                continue
            seen.add(key)
            fact = store.write_statement(Statement(
                id=f"{PREFIX}{len(store.statements) + 1:04d}", subject=f"essential requirement {point}",
                predicate="addressesRisk", object=phrase, object_as_written=phrase,
                object_normalised=norm(phrase).lower(), condition=condition_of(sentence), quote=sentence,
                source_doc=SOURCE, anchor=chunk.locator, asserted_by="code:risk_phrases", layer="law"))
            if fact:
                fact.status = "current"
                added[point] += 1
    return dict(added)


ITEM_MARK = re.compile(r"\(([a-z])\)\s+")
MODULE = re.compile(r"\(module ([A-Z][0-9]?)\)|\bmodule ([A-Z][0-9]?)\b")


def list_items(text: str) -> tuple[str, list[tuple[str, str, str]]]:
    """(chapeau, [(letter, value, quote)]) of a paragraph with "(a) ...; (b) ...". The value is the item up to
    its semicolon or final full stop; the quote is the item with its letter. No list: ('', [])."""
    marks = [m for m in ITEM_MARK.finditer(text)]
    letters = [m.group(1) for m in marks]
    if len(marks) < 2 or letters != [chr(ord("a") + i) for i in range(len(marks))]:
        return "", []
    items = []
    for number, mark in enumerate(marks):
        stop = marks[number + 1].start() if number + 1 < len(marks) else len(text)
        body = text[mark.end():stop]
        cut = re.search(r";|\.\s*$|\.\s+(?=[A-Z])", body)
        value = (body[:cut.start()] if cut else body).strip()
        value = re.sub(r"\s+(?:or|and)$", "", value)
        quote = text[mark.start():mark.end() + (cut.end() if cut else len(body))].strip()
        items.append((mark.group(1), value, quote))
    return text[:marks[0].start()].strip(), items


def short_form(value: str) -> str:
    """'module B followed by module C' from the module letters of an item, in the order of the text."""
    letters = [a or b for a, b in MODULE.findall(value)]
    if not letters:
        return norm(value).lower()
    joiner = " followed by " if "followed by" in value else " and "
    return joiner.join(f"module {letter}" for letter in letters)


def repair_lists(store: Store, chunks, existing: list[Statement], only: str | None = None) -> tuple[list, list[str]]:
    """Defect 2. Returns the new facts and the ids of the facts they replace (to be closed)."""
    texts = {c.locator: c.text for c in chunks if c.source == SOURCE}
    by_anchor: dict[str, list[Statement]] = {}
    for s in existing:
        replaced_before = s.status == "closed" and s.in_force_to == REPAIR_DAY   # a second run finds them again
        if (s.source_doc == SOURCE and s.predicate == "requiresProcedure" and not s.asserted_by.startswith("code:")
                and (s.status == "current" or replaced_before) and (only is None or s.anchor == only)):
            by_anchor.setdefault(s.anchor, []).append(s)
    new, closed = [], []
    for anchor, old in by_anchor.items():
        chapeau, items = list_items(texts.get(anchor, ""))
        if not items:
            continue
        owners = {letter: [s for s in old if norm(s.object_as_written) in norm(value)] for letter, value, _ in items}
        placed = {s.id for group in owners.values() for s in group}
        if any(not group for group in owners.values()) or placed != {s.id for s in old}:
            continue   # the old facts are not the items of this list: leave the paragraph alone
        subject = Counter(s.subject for s in old).most_common(1)[0][0]
        sentence = sentence_at(texts[anchor], len(chapeau) - 1, len(chapeau)) if chapeau else ""
        clause = condition_of(sentence)
        for letter, value, quote in items:
            fact = store.write_statement(Statement(
                id=f"{PREFIX}{len(store.statements) + 1:04d}", subject=subject, predicate="requiresProcedure",
                object=value, object_as_written=value, object_normalised=short_form(value),
                condition=clause or condition_of(quote), condition_quote=clause and sentence, quote=quote,
                source_doc=SOURCE, anchor=anchor, asserted_by="code:list_items", layer="law",
                conflicts_with=owners[letter][0].id))
            if fact:
                fact.status = "current"
                new.append(fact)
        if sum(1 for f in new if f.anchor == anchor) == len(items):
            closed += [s.id for s in old]
        else:   # an item was refused: keep the old facts, drop the half-made replacement
            store.statements = [f for f in store.statements if not (f.anchor == anchor and f in new)]
            new = [f for f in new if f.anchor != anchor]
    return new, closed


def close_in_file(ids: list[str]) -> int:
    """Set status 'closed' and in_force_to on the named facts of statements.json; no other field is touched."""
    payload = json.loads(STATEMENTS.read_text(encoding="utf-8"))
    changed = 0
    for item in payload["statements"]:
        if item["id"] in ids and (item["status"] != "closed" or item["in_force_to"] != REPAIR_DAY.isoformat()):
            item["status"], item["in_force_to"] = "closed", REPAIR_DAY.isoformat()
            changed += 1
    if changed:
        STATEMENTS.write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")
    return changed


def run(write: bool = True) -> dict:
    chunks = list(load())
    corpus = ChunkCorpus(chunks)
    existing = Store.load(corpus, STATEMENTS).statements
    store = Store(corpus, PART)
    per_point = repair_risks(store, chunks, existing)
    new_lists, closed = repair_lists(store, chunks, existing)
    if write:
        store.save()
        changed = close_in_file(closed)
    else:
        changed = 0
    return {"risks_added": sum(per_point.values()), "risks_per_point": per_point,
            "list_facts_added": len(new_lists), "list_anchors": sorted({f.anchor for f in new_lists}),
            "closed": closed, "closed_now": changed, "rejected": len(store.rejections), "store": store}


if __name__ == "__main__":
    import sys

    report = run(write="--dry" not in sys.argv)
    store = report.pop("store")
    print(json.dumps(report, indent=1))
    if "--show" in sys.argv:
        for s in store.statements:
            print(f"{s.id} {s.anchor} | {s.predicate} | {s.object_as_written} | {s.object_normalised} | if: {s.condition}")
        for r in store.rejections:
            print("REJECTED", r["reason"], r["statement"]["anchor"], r["statement"]["object_as_written"])
