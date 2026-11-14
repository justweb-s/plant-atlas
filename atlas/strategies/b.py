"""Owner: Core. Strategy B: schema first, the model only points.

For each chunk, code cuts the text into numbered spans (sentences). The model sees the schema and the
spans and may only answer with span numbers, a relation of the schema, and values copied from the spans.
The quote of every fact is therefore verbatim by construction, and write_statement() checks it again.
Corrections published in a corrigendum are applied by code, not by the model.
"""
from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import date

from atlas import llm
from atlas.contracts import Chunk
from atlas.ontology.statements import ChunkCorpus, Statement, Store
from atlas.strategies.schema_b import RELATIONS, describe

MAX_SPANS = 60
SYSTEM = """You fill a fixed schema from one passage of law. You never write a fact in your own words.

Rules:
- Use only the relations of the schema. If the passage states something important that no relation
  can hold, report it under "open_points" instead of forcing it into a relation.
- Point at the spans that state the fact: "first_span" and "last_span" are span numbers, at most 3 adjacent spans.
- "value_as_written" must be copied character by character from those spans (a few words, not the whole span).
- "value_normalised": ISO date (2027-01-20), ISO duration (P10Y, P45D), or the same words in lower case.
- "subject": the thing the fact is about, in a few words taken from the passage.
- "condition": if the spans state a condition, exception or scope (if, where, unless, except, provided that,
  only for, salvo, qualora), copy it from the spans; otherwise "".
- Answer with one line per fact, fields separated by " | ", nothing else, no header, no code fence:
  predicate | subject | value_as_written | value_normalised | condition | first_span | last_span
- Dates, time limits and who must do what come first. At most 12 facts. At most one open point, as: OPEN | a note of at most 12 words | first_span | last_span
- If the passage states nothing the schema can hold, answer with the single word NONE."""


def spans_of(text: str) -> list[str]:
    """Sentences and list items, as they are in the text."""
    parts = re.split(r"(?<=[.;:])\s+(?=[\(A-Z0-9‘'“a-z])", text)
    return [p.strip() for p in parts if p.strip()][:MAX_SPANS]


def _parse(text: str) -> dict:
    """One fact per line, fields separated by ' | '. Lines that do not fit are dropped."""
    facts, open_points = [], []
    for line in (text or "").splitlines():
        cells = [c.strip() for c in re.split(r"\s*\|\s*", line.strip().strip("`"))]
        if cells[0] == "OPEN" and len(cells) == 4:
            open_points.append({"note": cells[1], "first_span": cells[2], "last_span": cells[3]})
        elif len(cells) == 7:
            facts.append(dict(zip(["predicate", "subject", "value_as_written", "value_normalised", "condition",
                                   "first_span", "last_span"], cells)))
    return {"facts": facts, "open_points": open_points}


def extract(chunk: Chunk) -> tuple[list[Statement], dict]:
    """One model call for one chunk. Returns the candidate statements and the usage."""
    spans = spans_of(chunk.text)
    numbered = "\n".join(f"[{i}] {s}" for i, s in enumerate(spans))
    out = llm.chat(
        [{"role": "system", "content": SYSTEM + "\n\n" + describe()},
         {"role": "user", "content": f"Passage: {chunk.source}, {chunk.locator}\n\n{numbered}"}],
        temperature=0, max_tokens=4000)
    data = _parse(out["text"])
    statements = []

    def quote(item) -> str | None:
        try:
            first, last = int(item["first_span"]), int(item["last_span"])
        except (KeyError, TypeError, ValueError):
            return None
        if not (0 <= first <= last < len(spans)) or last - first > 2:
            return None
        return " ".join(spans[first:last + 1])

    for item in data.get("facts", []) or []:
        q = quote(item) or ""
        written_date = _iso(str(item.get("value_as_written", "")))
        if written_date:   # a date is normalised by code, never by the model
            item["value_normalised"] = written_date
        statements.append(Statement(
            subject=str(item.get("subject", "")).strip(), predicate=str(item.get("predicate", "")),
            object=str(item.get("value_normalised") or item.get("value_as_written") or ""),
            object_as_written=str(item.get("value_as_written", "")),
            object_normalised=str(item.get("value_normalised", "")),
            condition=str(item.get("condition", "") or ""), quote=q,
            source_doc=chunk.source, anchor=chunk.locator, asserted_by="strategy_b"))
    for item in data.get("open_points", []) or []:
        statements.append(Statement(
            subject=chunk.locator, predicate="openPoint", object=str(item.get("note", "")),
            object_as_written="", quote=quote(item) or "", source_doc=chunk.source, anchor=chunk.locator,
            status="open_point", asserted_by="strategy_b"))
    return statements, out.get("usage") or {}


def apply_corrigendum(store: Store, chunks: list[Chunk], in_force_from: date) -> int:
    """'On page 38, Article 51, paragraph 2 ...: for: '14 January 2027', read: '20 January 2027'.'

    Code reads the instruction, finds the current facts of that article whose quote holds the old words,
    closes them and writes the corrected fact with the corrigendum as its source. Nothing is deleted.
    """
    corrected = 0
    for chunk in chunks:
        match = re.search(r"Article (\d+)(?:, paragraph (\d+))?.*?for:\s*[‘'\"]\s*(.+?)\s*[’'\"],\s*read:\s*[‘'\"]\s*(.+?)\s*[’'\"]",
                          chunk.text)
        if not match:
            continue
        article, paragraph, old, new = match.groups()
        prefix = f"Art. {article}" + (f"({paragraph})" if paragraph else "")
        read_span = chunk.text[chunk.text.index("read:"):]
        for fact in [s for s in store.statements if s.status == "current" and s.source_doc == "REG"
                     and s.anchor.startswith(prefix) and old in s.quote
                     and (old in s.object_as_written or s.object_as_written in old)]:
            fact.status, fact.in_force_to = "closed", in_force_from
            fixed = store.write_statement(Statement(
                subject=fact.subject, predicate=fact.predicate, condition=fact.condition,
                object=_iso(new) or new, object_as_written=new, object_normalised=_iso(new) or new.lower(),
                quote=read_span, source_doc=chunk.source, anchor=chunk.locator,
                in_force_from=in_force_from, asserted_by="strategy_b:corrigendum"))
            if fixed:
                fixed.status, fixed.conflicts_with = "current", fact.id   # the fact it replaces
                corrected += 1
    return corrected


MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
     "november", "december"], start=1)}


def _iso(text: str) -> str:
    match = re.search(r"(\d{1,2}) ([A-Za-z]+) (\d{4})", text)
    if not match or match.group(2).lower() not in MONTHS:
        return ""
    return f"{int(match.group(3)):04d}-{MONTHS[match.group(2).lower()]:02d}-{int(match.group(1)):02d}"


def build(chunks: list[Chunk], workers: int = 8, store: Store | None = None) -> tuple[Store, dict]:
    """Run strategy B on the chunks. Returns the store and the counts for the scoreboard."""
    store = store or Store(ChunkCorpus(chunks))
    body = [c for c in chunks if c.source != "CORR" and not c.locator.startswith("Recital")]
    usage = {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(extract, body))
    for statements, used in results:
        usage["calls"] += 1
        usage["prompt_tokens"] += used.get("prompt_tokens", 0) or 0
        usage["completion_tokens"] += used.get("completion_tokens", 0) or 0
        for statement in statements:
            if statement.status != "open_point" and statement.predicate not in RELATIONS:
                store._reject(statement, "not_in_schema")
                continue
            written = store.write_statement(statement)
            if written and written.status == "proposed":
                written.status = "current"   # the second reader (verify) is not built yet: see notes/core.md
    corrections = apply_corrigendum(store, [c for c in chunks if c.source == "CORR"], date(2023, 7, 4))
    counts = store.counts() | {"corrections_applied": corrections} | usage
    return store, counts


def main() -> None:
    """Full run on the texts the gold refers to. Writes ontology/B/statements.json and build.json."""
    import time
    from pathlib import Path

    from atlas.corpus.chunker import load

    started = time.time()
    chunks = [c for c in load() if c.source in ("REG", "DIR", "CORR") or c.source.startswith("DLGS")]
    out = Path(__file__).resolve().parents[2] / "ontology" / "B"
    out.mkdir(parents=True, exist_ok=True)
    store = Store(ChunkCorpus(chunks), out / "statements.json")
    store, counts = build(chunks, store=store)
    store.save()
    counts["seconds"] = round(time.time() - started, 1)
    counts["chunks_read"] = len([c for c in chunks if c.source != "CORR" and not c.locator.startswith("Recital")])
    (out / "build.json").write_text(json.dumps(counts, indent=1))
    print(json.dumps(counts))


if __name__ == "__main__":
    main()
