"""Owner: Core. One round of "extract -> check -> learn -> extract again".

The evidence comes only from the documents and from the two checks that already exist: the gate of
write_statement() (its recorded rejections) and the second reader (its verdicts and their "why").
The evaluation questions are never read here.

  collect   the facts the second reader did not pass and the gate's rejections, per passage
  learn     group them by relation and failure kind; one model call per group writes one general lesson
  extract   only the passages that failed, with the lessons added to the extractor's instructions
  judge     the second reader reads every candidate; a new fact replaces an old failed one only if it passes
  log       one entry per round in ontology/B/improve_log.json

Nothing is deleted: a replaced fact is closed, the new one points at it with `conflicts_with`.

    python -m atlas.strategies.improve          one round
    python -m atlas.strategies.improve --dry    what it would do, no model call, nothing written
"""
from __future__ import annotations

import json
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from difflib import SequenceMatcher
from pathlib import Path

from atlas import llm
from atlas.ontology import verify as second_reader
from atlas.ontology.statements import CONDITION_MARKERS, ChunkCorpus, Statement, Store, norm
from atlas.strategies import b
from atlas.strategies.schema_b import RELATIONS, describe, describe_layers

ROOT = Path(__file__).resolve().parents[2]
FOLDER = ROOT / "ontology" / "B"
PART = "reextracted"
CLOSE_DAY = date(2026, 11, 14)
MAX_GROUPS, MAX_EXAMPLES, MAX_WORDS = 8, 10, 30
MAX_PASSAGES, MAX_CALLS = 120, 220
SAME_FACT = 0.5          # how alike two facts of one passage must be to count as the same fact, re-read
EXTRACT_IN, EXTRACT_OUT = 0.10 / 1_000_000, 0.50 / 1_000_000   # the extractor's model, list price
GATE_REASONS = {
    "no_anchor": "the quoted spans were missing or not in the passage",
    "value_not_in_quote": "the value was not copied character by character from the quoted spans",
    "missing_condition": "the quoted spans announce a condition or exception and the fact's condition was empty",
    "condition_no_anchor": "the condition was not copied from the passage",
    "not_in_schema": "the relation is not one of the schema",
}
LESSON_SYSTEM = """You improve the instructions of an extractor that fills a fixed schema from passages of law and of
technical documents by pointing at sentences. You are shown facts it extracted that a checker refused, each with
the checker's reason. Write ONE general instruction for the extractor, at most 30 words, that would have avoided
these failures. It must be general: no article or annex numbers, no names of documents, products, organisations
or persons. Answer with the instruction only, on one line."""


class Calls:
    """Every model call of the round is counted here; take() says no once the cap is reached."""

    def __init__(self, cap: int) -> None:
        self.cap, self.used, self.cost = cap, 0, 0.0
        self._lock = threading.Lock()

    def take(self) -> bool:
        with self._lock:
            if self.used >= self.cap:
                return False
            self.used += 1
            return True

    def pay(self, usage: dict | None, price_in: float, price_out: float) -> None:
        usage = usage or {}
        with self._lock:
            self.cost += (usage.get("prompt_tokens", 0) or 0) * price_in + (usage.get("completion_tokens", 0) or 0) * price_out


# ---- collect ------------------------------------------------------------------
def load_files(folder: Path) -> dict[Path, dict]:
    """statements.json and every parts file of the usual shape, as plain JSON (so that only two fields change)."""
    files = {}
    for path in [folder / "statements.json", *sorted((folder / "parts").glob("*.json"))]:
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict) and "statements" in payload:
                files[path] = payload
    return files


def _facts(folder: Path, files: dict[Path, dict]):
    """(id as the store shows it, the fact as written in its file, the file)."""
    for path, payload in files.items():
        prefix = "" if path.parent == folder else path.stem
        for item in payload["statements"]:
            sid = item.get("id", "")
            yield (sid if sid.startswith(prefix) else f"{prefix}-{sid}"), item, path


def _kind(verdict: dict) -> str:
    if verdict.get("states") == "no":
        return "not_stated"
    return "dropped_condition" if verdict.get("states") == "yes" else "unclear"


def collect(folder: Path, files: dict[Path, dict], verdicts: dict) -> dict:
    """Per passage (source, locator): the facts the second reader did not pass and what the gate rejected."""
    passages: dict = {}

    def at(item: dict) -> dict:
        key = (item.get("source_doc", ""), item.get("anchor", ""))
        return passages.setdefault(key, {"failed": [], "rejected": [], "facts": []})

    for sid, item, path in _facts(folder, files):
        at(item)["facts"].append((sid, item))
        verdict = verdicts.get(sid)
        if not verdict or second_reader.passes(verdict) or item.get("status") != "current":
            continue
        if verdict.get("fingerprint") and verdict["fingerprint"] != second_reader.fingerprint(Statement(**item)):
            continue   # the verdict was given for another wording of the fact
        at(item)["failed"].append({"id": sid, "item": item, "path": path, "kind": _kind(verdict),
                                   "why": verdict.get("why", "")})
    for payload in files.values():
        for rejection in payload.get("rejections", []):
            at(rejection["statement"])["rejected"].append(rejection)
    return {key: p for key, p in passages.items() if p["failed"] or p["rejected"]}


# ---- learn --------------------------------------------------------------------
def group_failures(passages: dict) -> list[dict]:
    """Failures grouped by relation and failure kind, the largest group first."""
    groups: dict = {}
    for passage in passages.values():
        for f in passage["failed"]:
            key = (f["item"]["predicate"], f["kind"], "second_reader")
            groups.setdefault(key, []).append({"id": f["id"], "fact": f["item"], "why": f["why"]})
        for r in passage["rejected"]:
            relation = r["statement"].get("predicate") or None
            if relation not in RELATIONS and relation != "openPoint":
                relation = None   # a relation the schema does not have: the lesson is for every relation
            groups.setdefault((relation, r["reason"], "gate"), []).append(
                {"id": "", "fact": r["statement"], "why": GATE_REASONS.get(r["reason"], r["reason"])})
    ordered = sorted(groups.items(), key=lambda kv: (-len(kv[1]), str(kv[0])))
    return [{"relation": relation, "kind": kind, "source": source, "examples": examples}
            for (relation, kind, source), examples in ordered]


def _general(text: str) -> str:
    """One line, at most MAX_WORDS words, no article or annex number."""
    line = next((l.strip(" -\"'`") for l in (text or "").splitlines() if l.strip()), "")
    line = re.sub(r"\b(Art(?:icle)?\.?|Annex|art\.)\s*[\dIVXLC]+(\(\d+\))?", "a provision", line)
    return " ".join(line.split()[:MAX_WORDS])


def learn(groups: list[dict], calls: Calls) -> list[dict]:
    """One model call per group, at most MAX_GROUPS: the lesson that would have avoided its failures."""
    lessons = []
    for n, group in enumerate(groups[:MAX_GROUPS], start=1):
        if not calls.take():
            break
        shown = []
        for example in group["examples"][:MAX_EXAMPLES]:
            fact = example["fact"]
            shown.append(f"- relation: {fact.get('predicate')} | subject: {fact.get('subject')} | value: "
                         f"{fact.get('object_as_written')} | condition: {fact.get('condition') or '(none)'}\n"
                         f"  quoted text: {norm(fact.get('quote', ''))[:600] or '(none)'}\n"
                         f"  checker: {example['why']}")
        out = llm.chat(
            [{"role": "system", "content": LESSON_SYSTEM},
             {"role": "user", "content": f"Relation: {group['relation'] or '(any)'}\nFailure: {group['kind']} "
                                         f"({len(group['examples'])} facts)\n\n" + "\n".join(shown)}],
            model=second_reader.MODEL, temperature=0, max_tokens=120)
        calls.pay(out.get("usage"), second_reader.PRICE_IN, second_reader.PRICE_OUT)
        pattern = _general(out.get("text", ""))
        if pattern:
            lessons.append({"id": f"lesson-{n:02d}", "relation": group["relation"], "pattern": pattern,
                            "evidence": {"count": len(group["examples"]), "kind": group["kind"],
                                         "examples": [e["id"] for e in group["examples"] if e["id"]][:3]},
                            "source": group["source"]})
    return lessons


def lessons_for(passage: dict, lessons: list[dict]) -> list[dict]:
    relations = {f["item"]["predicate"] for f in passage["failed"]} | \
                {r["statement"].get("predicate") for r in passage["rejected"]}
    return [l for l in lessons if l["relation"] is None or l["relation"] in relations]


# ---- extract again --------------------------------------------------------------
def reextract(chunk, lessons: list[dict]) -> tuple[list[Statement], dict]:
    """The extractor's own call, its instructions extended by the lessons."""
    law = chunk.layer in ("", "law")
    base = (b.SYSTEM + "\n\n" + describe()) if law else (b.SYSTEM_LAYERS + "\n\n" + describe_layers())
    system = base + "\n\nLessons from earlier checks:\n" + "\n".join(f"- {l['pattern']}" for l in lessons)
    statements, usage = b.extract(chunk, system=system, spans=None if law else b.spans_for_layer(chunk.text))
    if not law:   # the same care build_layer() takes with a condition in the model's own words
        for s in statements:
            if s.condition and norm(s.condition) not in norm(chunk.text) and not CONDITION_MARKERS.search(s.quote):
                s.condition = ""
            s.condition_quote = s.condition
    return statements, usage


def _alike(new: Statement, old: dict) -> float:
    """Is it the same fact, re-read? Same relation, and the quote and the value mostly the same words."""
    if new.predicate != old.get("predicate"):
        return 0.0
    a, c = norm(new.quote), norm(old.get("quote", ""))
    quote = 1.0 if a and c and (a in c or c in a) else SequenceMatcher(None, a, c).ratio()
    if quote < SAME_FACT:
        return 0.0
    value = SequenceMatcher(None, norm(new.object_as_written).lower(), norm(old.get("object_as_written", "")).lower()).ratio()
    return quote + 0.5 * value


# ---- the round ------------------------------------------------------------------
def run_round(folder: Path, chunks: list, verdicts: dict, dry: bool = False, max_passages: int = MAX_PASSAGES,
              max_calls: int = MAX_CALLS, workers: int = 8) -> dict:
    files = load_files(folder)
    passages = collect(folder, files, verdicts)
    groups = group_failures(passages)
    by_locator = {}
    for chunk in chunks:
        by_locator.setdefault((chunk.source, chunk.locator), chunk)
    log_path, lessons_path, part_path = folder / "improve_log.json", folder / "lessons.json", folder / "parts" / f"{PART}.json"
    history = json.loads(log_path.read_text(encoding="utf-8")) if log_path.exists() else []
    number = 2 + len(history)
    old_failures = sum(len(p["failed"]) for p in passages.values())
    ordered = sorted((k for k in passages if k in by_locator), key=lambda k: (-len(passages[k]["failed"]), k))
    if dry:
        return {"round": number, "dry": True, "passages_with_failures": len(passages), "old_failures": old_failures,
                "gate_rejections": sum(len(p["rejected"]) for p in passages.values()),
                "groups": [{"relation": g["relation"], "kind": g["kind"], "source": g["source"],
                            "count": len(g["examples"])} for g in groups[:MAX_GROUPS]],
                "would_reextract_at_most": min(max_passages, len(ordered)), "call_cap": max_calls}

    calls = Calls(max_calls)
    read_before = second_reader.spent_usd()
    lessons = learn(groups, calls)

    # extract again: only the passages a lesson speaks to (without one the call would be the old call)
    todo = [(k, lessons_for(passages[k], lessons)) for k in ordered]
    todo = [(k, ls) for k, ls in todo if ls][:max_passages]

    def one(job):
        key, relevant = job
        if not calls.take():
            return key, None
        statements, usage = reextract(by_locator[key], relevant)
        calls.pay(usage, EXTRACT_IN, EXTRACT_OUT)
        return key, statements

    with ThreadPoolExecutor(max_workers=workers) as pool:
        extracted = [(k, s) for k, s in pool.map(one, todo) if s is not None]

    fresh = Store(ChunkCorpus(chunks))
    candidates = []   # (rank, new statement, passage key, the old failed fact it re-reads or None)
    for key, statements in extracted:
        passage = passages[key]
        known = {second_reader.fingerprint(Statement(**item)) for _, item in passage["facts"]}
        failed_ids = {f["id"]: f for f in passage["failed"]}
        for statement in statements:
            if statement.status != "open_point" and statement.predicate not in RELATIONS:
                fresh._reject(statement, "not_in_schema")
                continue
            written = fresh.write_statement(statement)
            if not written or written.status == "open_point" or second_reader.fingerprint(written) in known:
                continue   # rejected by the gate, a note, or word for word a fact we already have
            scored = sorted(((_alike(written, item), sid) for sid, item in passage["facts"]
                             if item.get("status") != "open_point"), reverse=True)
            best, best_id = scored[0] if scored else (0.0, "")
            if best >= SAME_FACT and best_id not in failed_ids:
                continue   # it re-reads a fact that did not fail: the old one stays
            candidates.append((0 if best >= SAME_FACT else 1, -best, written, key,
                               failed_ids.get(best_id) if best >= SAME_FACT else None))

    candidates.sort(key=lambda c: (c[0], c[1], c[2].id))
    judged = {}

    def read(candidate):
        statement = candidate[2]
        if not calls.take():
            return
        judged[statement.id] = second_reader.verify(statement, by_locator[candidate[3]].text)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(read, candidates))

    # judge: the best passing re-reading replaces the failed fact; a passing fact that is new is added
    part = json.loads(part_path.read_text(encoding="utf-8")) if part_path.exists() else {"statements": [], "rejections": []}
    kept, replaced, examples, touched = [], {}, [], set()
    for _, _, statement, key, old in candidates:
        verdict = judged.get(statement.id)
        if not verdict or not second_reader.passes(verdict):
            continue
        if old is not None and old["id"] in replaced:
            continue   # a better re-reading already replaced it
        statement.status, statement.asserted_by = "current", f"strategy_b:round{number}"
        if old is not None:
            old["item"]["status"], old["item"]["in_force_to"] = "closed", CLOSE_DAY.isoformat()
            touched.add(old["path"])
            statement.conflicts_with, statement.in_force_from = old["id"], CLOSE_DAY
            replaced[old["id"]] = statement
        kept.append((statement, verdict))
    for n, (statement, verdict) in enumerate(kept, start=len(part["statements"]) + 1):
        statement.id = f"{PART}-r{number}-{n:04d}"
        part["statements"].append(statement.model_dump(mode="json"))
        part.setdefault("verdicts", {})[statement.id] = verdict
    done = {k for k, _ in extracted}
    part["rejections"] += fresh.rejections
    still = [f["id"] for p in passages.values() for f in p["failed"] if f["id"] not in replaced]
    for old_id, new in replaced.items():
        old = next(f for p in passages.values() for f in p["failed"] if f["id"] == old_id)
        examples.append({"old": {k: old["item"].get(k) for k in ("id", "predicate", "subject", "object_as_written", "condition", "quote")}
                         | {"id": old_id, "why_failed": old["why"]},
                         "new": {k: getattr(new, k) for k in ("id", "predicate", "subject", "object_as_written", "condition", "quote")}})

    entry = {"round": number, "passages_reextracted": len(extracted), "old_failures": old_failures,
             "replaced_by_passing_fact": len(replaced), "still_failing": len(still),
             "new_facts_added": len(kept) - len(replaced),
             "gate_rejections_before": sum(len(passages[k]["rejected"]) for k in done),
             "gate_rejections_after": len(fresh.rejections), "lessons": len(lessons),
             "candidates_read": len(judged), "candidates_not_read_call_cap": len(candidates) - len(judged),
             "calls": calls.used,
             "cost_usd_estimate": round(calls.cost + second_reader.spent_usd() - read_before, 3),
             "still_failing_ids": still, "replacements": examples}

    def dump(payload) -> str:
        return json.dumps(payload, indent=1, ensure_ascii=False)

    for path in touched:   # only `status` and `in_force_to` of the closed facts changed
        path.write_text(dump(files[path]), encoding="utf-8")
    part_path.parent.mkdir(parents=True, exist_ok=True)
    part_path.write_text(dump(part), encoding="utf-8")
    lessons_path.write_text(dump([l | {"round": number} for l in lessons]), encoding="utf-8")
    log_path.write_text(dump(history + [entry]), encoding="utf-8")
    return entry


def main() -> None:
    import sys

    from atlas.corpus.chunker import load

    numbers = [int(a) for a in sys.argv[1:] if a.isdigit()]
    entry = run_round(FOLDER, list(load()), second_reader.load_verdicts(), dry="--dry" in sys.argv,
                      max_passages=numbers[0] if numbers else MAX_PASSAGES)
    print(json.dumps({k: v for k, v in entry.items() if k not in ("still_failing_ids", "replacements")}, indent=1))


if __name__ == "__main__":
    main()
