"""Owner: Core. The second reader: an independent check of every fact against its quoted text.

The extractor points at sentences and fills a relation; code checks that the quote is in the text and the
value is in the quote. That does not prove that the quote *states* the fact, nor that the fact kept every
exception. Here a second, blind call reads the quoted sentences with one sentence before and one after,
and the proposed fact, and answers:
  (1) does the text state this fact?                        yes / no / unclear
  (2) does the text add an exception or condition that the fact drops?   yes / no
"yes" with no dropped condition keeps the fact current. Anything else sends it back to "proposed" and is
counted. Nothing is deleted. The decision sits behind decide(), so a cheaper decision model can replace it.

Run once (results are cached and written to ontology/B/verify_report.json):
    python -m atlas.ontology.verify
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from atlas import llm
from atlas.ontology.statements import Statement, Store, norm
from atlas.strategies.schema_b import RELATIONS

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "ontology" / "B" / "verify_report.json"
# The second reader is a different model from the extractor (anthropic/claude-haiku-5.5).
MODEL = os.getenv("ATLAS_STRONG_MODEL", "anthropic/claude-sonnet-5.5")
PRICE_IN, PRICE_OUT = 2.0 / 1_000_000, 10.0 / 1_000_000   # anthropic/claude-sonnet-5.5 on the gateway
# Facts about dates, time limits, who verifies and which procedure applies are checked first.
PRIORITY = ("appliesFrom", "repealedFrom", "placingAllowedUntil", "retentionPeriod", "hasTimeLimit", "verifiedBy",
            "requiresProcedure", "becomesManufacturer", "listedIn", "mustAccompany")

STATED, DROPPED, NOT_STATED, UNCLEAR = "stated", "stated_but_condition_dropped", "not_stated", "unclear"
LABELS = [STATED, DROPPED, NOT_STATED, UNCLEAR]
QUESTION = f"""Does the passage state the claim, and does the claim keep every condition the passage attaches to it?

Choose one label:
- {STATED}: the passage says what the claim says, and every exception, condition or restriction of scope
  that the passage attaches to it (except, unless, where, if, provided that, only for, an "or" list of
  alternatives, salvo, qualora, a proviso in the sentence before or after) is present in the claim's condition.
- {DROPPED}: the passage says it, but attaches an exception, condition, alternative or restriction
  of scope that the claim leaves out, so the claim as written is broader than the passage.
- {NOT_STATED}: the passage does not say this: wrong subject, wrong value, wrong relation, or a value that
  is only a fragment and does not carry the meaning (for example "means:" or "the following").
- {UNCLEAR}: the passage is not enough to tell (for example the value depends on text that is not shown).

The value is a few words copied from the passage: a shortened but faithful excerpt is fine, do not ask for the
whole sentence. Words of manner or purpose ("without risk to persons", "immediately") are not conditions; only
what changes when, where or to whom the claim applies counts. Judge only from the passage."""

SYSTEM = """You check one claim against one passage of law. Use only the passage; do not use what you know of the law.
Answer with JSON: "why" (at most 20 words), then "label", then "confidence" (0 to 1)."""


def _answer_format(labels: list[str]) -> dict:
    """The answer is constrained to this shape: the reader cannot drift into prose and run out of tokens."""
    return {"type": "json_schema", "json_schema": {"name": "verdict", "strict": True, "schema": {
        "type": "object", "additionalProperties": False,
        "properties": {"why": {"type": "string"}, "label": {"type": "string", "enum": labels},
                       "confidence": {"type": "number"}},
        "required": ["why", "label", "confidence"]}}}


_SPLIT = re.compile(r"(?<=[.;:])\s+(?=[\(A-Z0-9‘'“a-z])")   # the same cut as atlas.strategies.b.spans_of, no cap


def decide(question: str, labels: list[str], text: str) -> tuple[str, float]:
    """Choose one label for `text`. Returns the label and a confidence in [0, 1].

    The only place the second reader's model is called. An answer that cannot be read is "unclear"
    (or the last label) with confidence 0, never a pass.
    """
    label, confidence, _ = _decide(question, labels, text)
    return label, confidence


def _decide(question: str, labels: list[str], text: str) -> tuple[str, float, str]:
    out = llm.chat(
        [{"role": "system", "content": SYSTEM},
         {"role": "user", "content": f"{question}\n\nLabels: {', '.join(labels)}\n\n{text}"}],
        model=MODEL, temperature=0, max_tokens=150, response_format=_answer_format(labels))
    _spend(out.get("usage") or {})
    fallback = UNCLEAR if UNCLEAR in labels else labels[-1]
    data: dict = {}
    for found in re.findall(r"\{[^{}]*\}", out.get("text") or ""):   # the last readable answer wins
        try:
            candidate = json.loads(found)
        except json.JSONDecodeError:
            continue
        if isinstance(candidate, dict) and str(candidate.get("label", "")).strip() in labels:
            data = candidate
    label = str(data.get("label", "")).strip()
    if label not in labels:
        return fallback, 0.0, "answer not readable"
    try:
        confidence = min(1.0, max(0.0, float(data.get("confidence", 0.0))))
    except (TypeError, ValueError):
        confidence = 0.0
    return label, confidence, str(data.get("why", ""))[:200]


def context_of(statement: Statement, chunk_text: str) -> str:
    """The quote with the sentence before it and the sentence after it, as they are in the chunk."""
    before, quote, after = _context_parts(statement, chunk_text)
    return " ".join(part for part in (before, quote, after) if part)


def _context_parts(statement: Statement, chunk_text: str) -> tuple[str, str, str]:
    spans = [p.strip() for p in _SPLIT.split(chunk_text) if p.strip()]
    quote = norm(statement.quote)
    for first in range(len(spans)):
        for last in range(first, min(first + 3, len(spans))):
            if norm(" ".join(spans[first:last + 1])) == quote:
                return (spans[first - 1] if first else "", " ".join(spans[first:last + 1]),
                        spans[last + 1] if last + 1 < len(spans) else "")
    # The quote does not sit on sentence borders (a corrigendum, a quote cut by hand): cut around it.
    text = norm(chunk_text)
    at = text.find(quote)
    if at < 0 or not quote:
        return "", statement.quote, ""
    head = [p for p in _SPLIT.split(text[:at]) if p.strip()]
    tail = [p for p in _SPLIT.split(text[at + len(quote):]) if p.strip()]
    return (head[-1].strip() if head else "", quote, tail[0].strip() if tail else "")


def fingerprint(statement: Statement) -> str:
    """Ties a verdict to the fact it was given for, so a rebuilt store never inherits a stale verdict."""
    blob = "|".join([statement.subject, statement.predicate, statement.object_as_written, statement.condition,
                     norm(statement.quote)])
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12]


def _claim(statement: Statement, chunk_text: str) -> str:
    """What the second reader sees. It is not told where the claim comes from."""
    before, quote, after = _context_parts(statement, chunk_text)
    meaning = RELATIONS.get(statement.predicate, ("", "", ""))[2]
    return "\n".join([
        f"PASSAGE ({statement.source_doc}, {statement.anchor})",
        f"sentence before: {before or '(none)'}",
        f"quoted sentences: {quote}",
        f"sentence after: {after or '(none)'}",
        "",
        "CLAIM",
        f"relation: {statement.predicate}" + (f" ({meaning})" if meaning else ""),
        f"subject: {statement.subject}",
        f"value: {statement.object_as_written}",
        f"condition: {statement.condition or '(none)'}",
    ])


def verify(statement: Statement, chunk_text: str) -> dict:
    """One blind reading of one fact. Returns states / dropped_condition / confidence (and a short reason)."""
    label, confidence, why = _decide(QUESTION, LABELS, _claim(statement, chunk_text))
    states = {STATED: "yes", DROPPED: "yes", NOT_STATED: "no", UNCLEAR: "unclear"}[label]
    return {"states": states, "dropped_condition": "yes" if label == DROPPED else "no",
            "confidence": confidence, "why": why, "fingerprint": fingerprint(statement)}


def passes(verdict: dict) -> bool:
    return verdict.get("states") == "yes" and verdict.get("dropped_condition") == "no"


def _bucket(verdict: dict) -> str:
    if passes(verdict):
        return "passed"
    if verdict.get("states") == "no":
        return "not_stated"
    if verdict.get("states") == "yes":
        return "dropped_condition"
    return "unclear"


def apply_verdicts(store: Store, verdicts: dict) -> dict:
    """Send every current fact that did not pass back to "proposed". Changes the store in memory only.

    A fact with no verdict, or whose verdict was given for a different wording of the fact, is left as it is
    and counted as unchecked. Nothing is deleted.
    """
    counts = {"checked": 0, "passed": 0, "not_stated": 0, "unclear": 0, "dropped_condition": 0,
              "sent_back": 0, "unchecked": 0}
    for statement in store.statements:
        if statement.status != "current":
            continue
        verdict = verdicts.get(statement.id)
        if not verdict or verdict.get("fingerprint", fingerprint(statement)) != fingerprint(statement):
            counts["unchecked"] += 1
            continue
        counts["checked"] += 1
        counts[_bucket(verdict)] += 1
        if not passes(verdict):
            statement.status = "proposed"
            counts["sent_back"] += 1
    return counts


def load_verdicts(path: Path = REPORT) -> dict:
    """The verdicts of the last run, or {} if the second reader has not run."""
    return json.loads(path.read_text(encoding="utf-8"))["verdicts"] if path.exists() else {}


# ---- the run ----------------------------------------------------------------
_lock = threading.Lock()
_spent = {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0}


def _spend(usage: dict) -> None:
    with _lock:
        _spent["calls"] += 1
        _spent["prompt_tokens"] += usage.get("prompt_tokens", 0) or 0
        _spent["completion_tokens"] += usage.get("completion_tokens", 0) or 0


def spent_usd() -> float:
    """Cost of the calls of this process at list price (answers read from the cache are counted too)."""
    return _spent["prompt_tokens"] * PRICE_IN + _spent["completion_tokens"] * PRICE_OUT


def prioritised(store: Store) -> list[Statement]:
    # A fact written by code from a corrigendum quotes only the corrected words: there is nothing to re-read.
    current = [s for s in store.statements if s.status == "current" and not s.asserted_by.endswith(":corrigendum")]
    return ([s for s in current if s.predicate in PRIORITY] + [s for s in current if s.predicate not in PRIORITY])


def run(store: Store, max_calls: int, budget_usd: float, workers: int = 8) -> dict:
    """Verify the current facts in priority order, under a hard cap on calls and on cost."""
    todo = prioritised(store)[:max_calls]
    verdicts: dict = {}

    def one(statement: Statement) -> None:
        if spent_usd() >= budget_usd:   # the cap: facts not reached stay unchecked
            return
        text = store.corpus.section(statement.source_doc, statement.anchor) or statement.quote
        verdicts[statement.id] = verify(statement, text)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(one, todo))
    report = {"model": MODEL, "checked": len(verdicts)}
    for bucket in ("passed", "not_stated", "unclear", "dropped_condition"):
        report[bucket] = sum(1 for v in verdicts.values() if _bucket(v) == bucket)
    by_predicate: dict = {}
    for statement in todo:
        if statement.id in verdicts:
            row = by_predicate.setdefault(statement.predicate, {"checked": 0, "passed": 0})
            row["checked"] += 1
            row["passed"] += int(passes(verdicts[statement.id]))
    report |= {"current_before": len(prioritised(store)), "by_predicate": by_predicate,
               "calls": _spent["calls"], "prompt_tokens": _spent["prompt_tokens"],
               "completion_tokens": _spent["completion_tokens"], "cost_usd": round(spent_usd(), 3),
               "verdicts": dict(sorted(verdicts.items()))}
    return report


def main(max_calls: int = 20, budget_usd: float = 0.05) -> None:
    import sys

    from atlas.corpus.chunker import load
    from atlas.ontology.statements import ChunkCorpus

    if len(sys.argv) > 1:
        max_calls = int(sys.argv[1])
    if len(sys.argv) > 2:
        budget_usd = float(sys.argv[2])
    store = Store.load(ChunkCorpus(list(load())), ROOT / "ontology" / "B" / "statements.json")
    report = run(store, max_calls, budget_usd)
    REPORT.write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "verdicts"}))


if __name__ == "__main__":
    main()
