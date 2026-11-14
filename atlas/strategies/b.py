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
from atlas.ontology.statements import CONDITION_MARKERS, ChunkCorpus, Statement, Store, norm
from atlas.strategies.schema_b import RELATIONS, describe, describe_layers

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


def extract(chunk: Chunk, system: str | None = None, spans: list[str] | None = None) -> tuple[list[Statement], dict]:
    """One model call for one chunk. Returns the candidate statements and the usage.

    Without `system` and `spans` this is the call used for the law texts, unchanged. The other layers pass
    their own instructions (with their schema) and their own cut of the page."""
    spans = spans_of(chunk.text) if spans is None else spans
    numbered = "\n".join(f"[{i}] {s}" for i, s in enumerate(spans))
    out = llm.chat(
        [{"role": "system", "content": system or (SYSTEM + "\n\n" + describe())},
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
                subject=fact.subject, predicate=fact.predicate,
                condition=fact.condition.replace(old, new),   # the correction applies to the whole sentence
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


# ---- the other layers: manufacturers' manuals, guidance documents, company guidelines ------------------

LAYERS = ("manufacturer", "guidance", "company")
MAX_SPAN_CHARS = 320
SYSTEM_LAYERS = """You fill a fixed schema from one page of a technical document about machines at work: a manufacturer's
manual (robot arm, safety laser scanner, vehicle lift), a guidance document, or an organisation's internal
guideline on work equipment. The page is in English or in Italian. You never write a fact in your own words.

Rules:
- Use only the relations of the schema. If the page states something important that no relation
  can hold, report it under "open_points" instead of forcing it into a relation.
- Point at the spans that state the fact: "first_span" and "last_span" are span numbers, at most 3 adjacent spans.
- "value_as_written" must be copied character by character from those spans, in the language of the page
  (a few words, not the whole span). A value with a unit keeps the unit as written ("850 mm", "5 kg / 11 lb").
- "value_normalised": number and unit ("850 mm", "5 kg"), ISO duration for intervals (P1Y, P6M), ISO date,
  or the same words in lower case. Never translate.
- "subject": the machine, device, check or role the fact is about, in a few words; for a manual, name the
  product as the page names it.
- "condition": if the spans state a condition, exception or scope (if, unless, except, provided that, only for,
  se, salvo, qualora, tranne), copy it from the spans; otherwise "".
- Pages of manuals are flattened tables: a label and its value stand next to each other ("Reach 850 mm / 33.5 in").
  Take a value only when its label is in the same spans.
- Never extract names of persons, signatures, addresses, phone numbers, part numbers, page headers or footers.
- Skip tables of contents, lists of figures, pure operating steps of the software and marketing text.
- Answer with one line per fact, fields separated by " | ", nothing else, no header, no code fence:
  predicate | subject | value_as_written | value_normalised | condition | first_span | last_span
- Technical limits, who is responsible, what must be checked, when and by whom come first. At most 12 facts.
  At most one open point, as: OPEN | a note of at most 12 words | first_span | last_span
- If the page states nothing the schema can hold, answer with the single word NONE."""

# Pages of the manuals worth a model call: the ones that speak of the facts the schema holds.
MANUAL_KEYWORDS = re.compile(
    r"\breach\b|payload|rated load|load capacity|declaration of (incorporation|conformity)|partly completed|"
    r"stopping (time|distance)|response time|minimum distance|protective field range|protective field (size|length)|"
    r"scanning range|resolution|safety function|risk assessment|integrator|put into service|"
    r"\b(every|once a|once per|at least once|annual|yearly|monthly|daily|weekly)\b.{0,80}"
    r"\b(check|checked|inspect|inspection|test|tests|tested|maintenance|service)\b|"
    r"\b(check|checked|inspect|inspection|test|tests|tested|thorough examination)\b.{0,80}"
    r"\b(every|once a|once per|at least once|annual|annually|yearly|monthly|daily|weekly|interval|intervals|after)\b|"
    r"maintenance (interval|schedule|plan)|regular (check|test|inspection)|harmoni[sz]ed standard",
    re.IGNORECASE)
DOT_LEADER = re.compile(r"\.{5,}|(?:\. ){5,}")   # a table of contents is mostly dots; a form has a few lines of them


def spans_for_layer(text: str) -> list[str]:
    """Sentences as in spans_of(); a long one (a flattened table, a list) is cut at word ends, so that a quote
    stays short. Adjacent spans joined by one space give back the text, so the quote is still verbatim."""
    spans: list[str] = []
    for span in re.split(r"(?<=[.;:])\s+(?=[\(A-Z0-9‘'“a-z→•])", text):
        span = span.strip()
        while len(span) > MAX_SPAN_CHARS:
            window = span[:MAX_SPAN_CHARS]
            cut = max(window.rfind(" → "), window.rfind(" • "), window.rfind(", "), window.rfind(") "))
            cut = cut + 1 if cut > MAX_SPAN_CHARS // 2 else window.rfind(" ")
            if cut <= 0:
                break
            spans.append(span[:cut].strip())
            span = span[cut:].strip()
        if span:
            spans.append(span)
    return spans[:2 * MAX_SPANS]


def select_pages(chunks: list[Chunk], layer: str) -> list[Chunk]:
    """Manuals: only the pages that match the keywords, tables of contents left out. Other layers: every page."""
    pages = [c for c in chunks if c.layer == layer]
    if layer != "manufacturer":
        return pages
    return [c for c in pages if MANUAL_KEYWORDS.search(c.text)
            and sum(len(m.group()) for m in DOT_LEADER.finditer(c.text)) < 0.4 * len(c.text)]


def extract_page(chunk: Chunk) -> tuple[list[Statement], dict]:
    """The pointing call of extract(), with the instructions and the schema of the other layers."""
    return extract(chunk, system=SYSTEM_LAYERS + "\n\n" + describe_layers(), spans=spans_for_layer(chunk.text))


def build_layer(chunks: list[Chunk], layer: str, workers: int = 8, store: Store | None = None) -> tuple[Store, dict]:
    """Run the pointing extraction on one layer into its own store. No corrigendum step: these are not acts."""
    store = store or Store(ChunkCorpus(chunks))
    pages = select_pages(chunks, layer)
    usage = {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(extract_page, pages))
    for page, (statements, used) in zip(pages, results):
        usage["calls"] += 1
        usage["prompt_tokens"] += used.get("prompt_tokens", 0) or 0
        usage["completion_tokens"] += used.get("completion_tokens", 0) or 0
        for statement in statements:
            statement.asserted_by = f"strategy_b:{layer}"
            on_page = norm(statement.condition) in norm(page.text)
            if statement.condition and not on_page and not CONDITION_MARKERS.search(statement.quote):
                statement.condition = ""   # a condition in the model's own words, and the quote states none: dropped
            statement.condition_quote = statement.condition   # the store then checks the condition is on the page
            if statement.status != "open_point" and statement.predicate not in RELATIONS:
                store._reject(statement, "not_in_schema")
                continue
            written = store.write_statement(statement)
            if written and written.status == "proposed":
                written.status = "current"
    for n, statement in enumerate(store.statements, start=1):   # ids carry the layer: the parts share one store later
        statement.id = f"{layer}-st-{n:04d}"
    selected: dict[str, int] = {}
    for page in pages:
        selected[page.source] = selected.get(page.source, 0) + 1
    return store, store.counts() | usage | {"pages_selected": selected}


def main_layers(layers: tuple[str, ...] = LAYERS) -> dict:
    """Writes ontology/B/parts/<layer>.json for each layer. Returns the counts per layer."""
    from pathlib import Path

    from atlas.corpus.chunker import load

    chunks = list(load())
    parts = Path(__file__).resolve().parents[2] / "ontology" / "B" / "parts"
    parts.mkdir(parents=True, exist_ok=True)
    report = {}
    for layer in layers:
        store, counts = build_layer(chunks, layer, store=Store(ChunkCorpus(chunks), parts / f"{layer}.json"))
        store.save()
        report[layer] = counts
    print(json.dumps(report, indent=1))
    return report


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
    (out / "build.json").write_text(json.dumps(counts, indent=1), encoding="utf-8")
    print(json.dumps(counts))


if __name__ == "__main__":
    main()
