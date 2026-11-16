"""Owner: Core. The fact store grows from the questions it is asked, and every fact that enters is examined first.

When an answer was found by searching the documents, the sentences it rests on are already verified: they are in
a registered piece. Each of them is turned into a candidate fact, and the candidate is examined on four points
before it may enter the store:

  1. gate (code)        the quote is in the piece, the value is in the quote, a condition is not lost;
  2. faithful (model)   a second reader, a different model that does not see the question, says the passage
                        states the fact, and that no condition was dropped;
  3. complete (model)   the store, holding ONLY the candidates of this answer, answers the question again with
                        the same value: the facts carry the answer, not the search;
  4. new (code)         it is not already in the store (then it counts as a confirmation of the fact it repeats).

A candidate that fails 1, 2 or 3 is written again once, with the reason it failed. If it fails again it does not
enter, and the reason is kept. Everything is logged in ontology/B/learned_log.json; the facts that entered are in
ontology/B/parts/learned.json, loaded with the rest of the store. Nothing is learned from questions kept aside
or blind: learning runs only on the questions named to it.

    python -m atlas.ontology.learn            learn from the design and development questions
    python -m atlas.ontology.learn report     the quality of what was learned, from the log
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

from atlas import llm
from atlas.contracts import Answer
from atlas.ontology.statements import ChunkCorpus, Statement, Store, norm

ROOT = Path(__file__).resolve().parents[2]
PART = ROOT / "ontology" / "B" / "parts" / "learned.json"
LOG = ROOT / "ontology" / "B" / "learned_log.json"
MAX_QUOTES = 6          # sentences of one answer that may become facts
PROPOSE = """You record one fact in a fact store about machines at work. You are given a question, the answer
that was verified, one sentence (or table row) taken word for word from a document, and the place it comes from.
Write the fact that this sentence states and that the answer relies on.

Return JSON only:
{"subject": "...", "predicate": "...", "value_as_written": "...", "value_normalised": "...", "condition": "..."}

- subject: what the fact is about, named so that a reader who has NOT seen the question recognises it: the
  machine and its model, the device and its position, the article and what it rules, the kind of verification.
- predicate: one of the relations listed below, exactly as written. Choose the one whose meaning fits; if none
  fits, use "hasObligation" for a duty, "hasTimeLimit" for a period or deadline, "definedAs" for what something
  is or is declared to be.
- value_as_written: the words of the sentence that carry the value, copied exactly, as short as they can be
  while still carrying it (a number with its unit, a name, a date, the thing required).
- value_normalised: the value in a standard form: a date as YYYY-MM-DD, a period as an ISO 8601 duration
  (P1Y, P6M, P45D, PT1H), otherwise the value in a few plain words, or "true"/"false" for a yes/no fact.
- condition: the condition under which the fact holds ("if ...", "where ...", "for ...", "before ...", a sector,
  an age, a kind of use), copied exactly from the sentence; "" if the sentence states none.
- Do not add anything the sentence does not say. Do not answer the question: record what the sentence states."""


def _reply(text: str) -> dict:
    match = re.search(r"\{.*\}", text or "", re.DOTALL)
    try:
        data = json.loads(match.group(0)) if match else {}
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _key(question: str) -> str:
    return hashlib.sha256(question.encode("utf-8")).hexdigest()[:12]


def propose(question: str, value, chunk, quote: str, feedback: str = "") -> Statement | None:
    """One candidate fact from one verified sentence. `feedback`: why the previous attempt was not accepted."""
    from atlas.strategies.schema_b import RELATIONS

    relations = "\n".join(f"- {name}: {meaning}" for name, (_, _, meaning) in RELATIONS.items())
    prompt = (f"Question: {question}\nVerified answer: {json.dumps(value, ensure_ascii=False)}\n"
              f"Place: {chunk.source}, {chunk.locator}\nSentence: {quote}")
    if feedback:
        prompt += f"\n\nA first attempt at this fact was not accepted: {feedback}\nWrite it again so that this is fixed."
    out = llm.chat([{"role": "system", "content": PROPOSE + "\n\nRelations:\n" + relations},
                    {"role": "user", "content": prompt}], temperature=0, max_tokens=700)
    data = _reply(out.get("text") or "")
    if not data.get("subject") or not data.get("value_as_written"):
        return None
    condition = str(data.get("condition") or "").strip()
    return Statement(subject=str(data["subject"]).strip(), predicate=str(data.get("predicate") or "hasObligation").strip(),
                     object=str(data.get("value_normalised") or data["value_as_written"]).strip(),
                     object_as_written=str(data["value_as_written"]).strip(),
                     object_normalised=str(data.get("value_normalised") or "").strip(),
                     condition=condition, condition_quote=condition, quote=quote.strip(),
                     source_doc=chunk.source, anchor=chunk.locator, asserted_by="learned")


GATE = {"no_anchor": "the sentence is not in the registered piece as written (for instance a wording the corrigendum changed)",
        "value_not_in_quote": "value_as_written is not a part of the sentence, copied exactly",
        "missing_condition": "the sentence carries a condition and the fact has none",
        "condition_no_anchor": "the condition is not copied exactly from the passage",
        "unknown_relation": "the predicate is not one of the relations listed",
        "long_normal_form": "value_normalised is a sentence: it must be a date, a duration, true/false or a few plain words"}


def gate(candidate: Statement, corpus: ChunkCorpus) -> str:
    """"" when the candidate passes the store's own gate, else the reason."""
    from atlas.strategies.schema_b import RELATIONS

    if candidate.predicate not in RELATIONS:
        return "unknown_relation"
    if len(candidate.object_normalised) > 80:
        return "long_normal_form"
    scratch = Store(corpus)
    if scratch.write_statement(candidate.model_copy()) is None:
        return scratch.rejections[-1].get("reason", "rejected") if scratch.rejections else "rejected"
    return ""


def faithful(candidate: Statement, chunk_text: str) -> dict:
    from atlas.ontology.verify import verify

    return verify(candidate, chunk_text)


def complete(question: str, expected, candidates: list[Statement], corpus: ChunkCorpus, day: date) -> tuple[str, str, set[int]]:
    """The round trip: a store holding only these candidates is asked the question again.
    Returns "yes" (same answer), "partial" (a list: every item given is right, some are missing) or "no"; the
    reason when not "yes"; and which candidates the answer used."""
    from atlas.agent.answer import _same_value, from_facts

    mini = Store(corpus)
    for i, c in enumerate(candidates):
        fact = c.model_copy()
        fact.id, fact.status = f"cand-{i}", "current"
        mini.statements.append(fact)
    try:
        again = from_facts(question, mini, day)
    except Exception as problem:   # a failed call is not a verdict on the fact
        return "no", f"the round trip could not run ({type(problem).__name__})", set()
    used = {int(s.statement_id.split("-")[1]) for s in again.steps if (s.statement_id or "").startswith("cand-")}
    if again.value is None:
        return "no", ("with these facts alone the question is not answered: the fact does not carry the answer "
                      "(subject too vague, value cut short, or part of the answer missing)"), used
    same = _same_value(again.value, expected)
    plain = lambda x: norm(str(x)).lower()
    close = lambda a, b: plain(a) in plain(b) or plain(b) in plain(a)
    if not same and isinstance(expected, list) and isinstance(again.value, list):
        if all(any(close(e, g) for g in again.value) for e in expected):
            same = True
        elif again.value and all(any(close(g, e) for e in expected) for g in again.value):
            return "partial", f"{len(again.value)} of the {len(expected)} items of the answer", used
    if not same and isinstance(expected, str) and isinstance(again.value, str):
        a, b = set(re.findall(r"\w+", again.value.lower())), set(re.findall(r"\w+", expected.lower()))
        same = bool(a and b) and len(a & b) / len(b) >= 0.6   # free text: the same content in other words
    if same:
        return "yes", "", used or set(range(len(candidates)))
    return "no", (f"with these facts alone the answer comes out as {json.dumps(again.value, ensure_ascii=False)[:120]}, "
                  f"not {json.dumps(expected, ensure_ascii=False)[:120]}"), used


def anchor(quote: str, text: str) -> str | None:
    """The sentence as it is written in the piece: the search may hand it back with other spacing, quotation marks
    or dashes. The letters and digits must be the same, in the same order; None when they are not there."""
    def letters(s: str) -> tuple[str, list[int]]:
        kept, at = [], []
        for i, ch in enumerate(s):
            if ch.isalnum():
                kept.append(ch.lower())
                at.append(i)
        return "".join(kept), at

    wanted, _ = letters(quote)
    plain, positions = letters(text)
    start = plain.find(wanted) if len(wanted) >= 8 else -1
    if start < 0:
        return None
    return text[positions[start]:positions[start + len(wanted) - 1] + 1]


def duplicate(candidate: Statement, store: Store) -> Statement | None:
    """A current fact of the store that already says this (same source and place, same relation, same value)."""
    value = norm(candidate.object_normalised or candidate.object).lower()
    for s in store.statements:
        if s.status == "current" and s.source_doc == candidate.source_doc and s.anchor == candidate.anchor \
                and s.predicate == candidate.predicate and norm(s.object_normalised or s.object).lower() == value:
            return s
    return None


def learn_from(question: str, answer: Answer, store: Store, chunks: dict, corpus: ChunkCorpus, day: date) -> dict:
    """Examine what one answered question can add to the store. Returns the log entry (with the accepted facts)."""
    entry = {"question": _key(question), "value": answer.value, "basis": answer.basis, "candidates": [], "accepted": []}
    sentences = [(chunks.get(tuple(p.strip() for p in s.locator.split(",", 1))), s.quote) for s in answer.steps
                 if s.statement_id is None and s.quote and s.locator]
    exact = []
    for chunk, quote in [(c, q) for c, q in sentences if c is not None][:MAX_QUOTES]:
        written = anchor(quote, chunk.text)
        if written is None:   # typically the Regulation's wording as corrected: the corrigendum's own facts hold it
            entry["candidates"].append({"place": f"{chunk.source}, {chunk.locator}", "attempt": 1, "decision": "skipped",
                                        "reason": "the sentence is not in the piece as registered (a wording the corrigendum corrected)"})
        else:
            exact.append((chunk, written))
    sentences = exact
    entry["_text"] = question
    if answer.value is None or not sentences:
        entry["skipped"] = "no answer" if answer.value is None else "the answer rests on facts already in the store"
        return entry
    for attempt in (1, 2):
        records, passed = [], []
        feedbacks = entry.pop("_feedback", {})
        for index, (chunk, quote) in enumerate(sentences):
            record = {"place": f"{chunk.source}, {chunk.locator}", "attempt": attempt}
            candidate = propose(question, answer.value, chunk, quote, feedbacks.get(index, ""))
            if candidate is None:
                record.update(decision="rejected", reason="no fact could be written from the sentence")
                records.append(record)
                continue
            record.update(subject=candidate.subject, predicate=candidate.predicate, value=candidate.object_as_written,
                          normalised=candidate.object_normalised, condition=candidate.condition)
            why = gate(candidate, corpus)
            record["gate"] = why or "ok"
            if why:
                record.update(decision="rejected", reason=GATE.get(why, why))
                records.append(record)
                continue
            verdict = faithful(candidate, chunk.text)
            record["faithful"] = verdict.get("states")
            record["dropped_condition"] = verdict.get("dropped_condition")
            if verdict.get("states") != "yes" or verdict.get("dropped_condition") == "yes":
                record.update(decision="rejected", reason="the second reader: " + (
                    "a condition of the sentence was dropped" if verdict.get("dropped_condition") == "yes"
                    else f"the passage does not clearly state this fact ({verdict.get('why') or verdict.get('states')})"))
                records.append(record)
                continue
            record["_candidate"] = candidate
            records.append(record)
            passed.append((index, record))
        if passed:
            status, why, used = complete(question, answer.value, [r["_candidate"] for _, r in passed], corpus, day)
            for place, (_, record) in enumerate(passed):
                if status == "no":
                    record.update(complete="no", decision="rejected", reason=why)
                elif place in used:
                    record["complete"] = status if status == "yes" else f"partial: {why}"
                else:   # the answer came out right without this fact: it adds nothing to this answer
                    record.update(complete="not used", decision="rejected",
                                  reason="the answer comes out without this fact: it does not carry a part of the answer")
        retry = {}
        for index, record in enumerate(records):
            if record.get("decision") == "rejected" and record.get("gate") != "no_anchor":
                retry[index] = record["reason"]
        if not retry or attempt == 2:
            entry["candidates"] += records
            break
        # one more attempt, with the reasons; the candidates that passed everything are kept as they are
        entry["candidates"] += [r for i, r in enumerate(records) if i in retry]
        entry["_feedback"] = retry
        if all(r.get("decision") != "rejected" for r in records):
            break
    entry.pop("_feedback", None)
    for record in entry["candidates"]:
        candidate = record.pop("_candidate", None)
        if candidate is None or record.get("decision") == "rejected":
            continue
        twin = duplicate(candidate, store)
        if twin is not None:
            record.update(decision="confirmation", confirms=twin.id)
            continue
        record["decision"] = "accepted"
        candidate.asserted_by, candidate.status = f"learned:{entry['question']}", "current"
        candidate.layer = corpus.layer(candidate.source_doc) or ""
        candidate.source_version = corpus.meta(candidate.source_doc).get("version", "")
        entry["accepted"].append(candidate.model_dump(mode="json"))
    return entry


def save(entries: list[dict]) -> int:
    """Append the accepted facts to the learned part and the entries to the log. Returns how many facts entered."""
    part = json.loads(PART.read_text(encoding="utf-8")) if PART.exists() else {"statements": [], "rejections": []}
    log = json.loads(LOG.read_text(encoding="utf-8")) if LOG.exists() else []
    done = {e["question"] for e in log}
    added = 0
    for entry in entries:
        if entry["question"] in done:
            continue
        entry.setdefault("_text", "")
        text = entry.pop("_text", "")
        for fact in entry.pop("accepted"):
            fact["id"] = f"learned-{len(part['statements']) + 1:04d}"
            part["statements"].append(fact)
            part.setdefault("questions", {})[entry["question"]] = text   # to find the fact when a like question comes
            added += 1
        log.append(entry)
    PART.write_text(json.dumps(part, ensure_ascii=False, indent=1), encoding="utf-8")
    LOG.write_text(json.dumps(log, ensure_ascii=False, indent=1), encoding="utf-8")
    return added


def report() -> dict:
    log = json.loads(LOG.read_text(encoding="utf-8")) if LOG.exists() else []
    candidates = [c for e in log for c in e["candidates"]]
    final = {}
    for e in log:
        for c in e["candidates"]:
            final[(e["question"], c["place"], c.get("value") if c["attempt"] == 2 else None, c["attempt"])] = c
    last = [c for e in log for c in e["candidates"] if c["attempt"] == max(x["attempt"] for x in e["candidates"] if x["place"] == c["place"])]
    reasons: dict[str, int] = {}
    for c in last:
        if c.get("decision") == "rejected":
            kind = ("gate: " + c["gate"]) if c.get("gate") not in (None, "ok") else "second reader" if "second reader" in c["reason"] \
                else "not complete" if c.get("complete") == "no" else "not needed for the answer" if c.get("complete") == "not used" \
                else "no fact written"
            reasons[kind] = reasons.get(kind, 0) + 1
    out = {"questions": len(log), "questions_with_new_sentences": sum(1 for e in log if e["candidates"]),
           "questions_that_added_facts": sum(1 for e in log if any(c.get("decision") == "accepted" for c in e["candidates"])),
           "sentences_examined": len(last), "accepted": sum(c.get("decision") == "accepted" for c in last),
           "confirmations": sum(c.get("decision") == "confirmation" for c in last),
           "rejected": sum(c.get("decision") == "rejected" for c in last), "rejected_why": reasons,
           "skipped_corrected_wording": sum(c.get("decision") == "skipped" for c in last),
           "accepted_as_part_of_a_list": sum(c.get("decision") == "accepted" and str(c.get("complete", "")).startswith("partial") for c in last),
           "first_attempts_rejected": sum(1 for c in candidates if c["attempt"] == 1 and c.get("decision") == "rejected"),
           "recovered_by_second_attempt": sum(1 for c in last if c["attempt"] == 2 and c.get("decision") in ("accepted", "confirmation"))}
    return out


def main(argv: list[str]) -> None:
    if argv[:1] == ["report"]:
        print(json.dumps(report(), ensure_ascii=False, indent=1))
        return
    from concurrent.futures import ThreadPoolExecutor

    from atlas import api
    from atlas.corpus.chunker import load
    from atlas.ontology.build import store_for

    day = date.fromisoformat(os.environ["ATLAS_TODAY"]) if os.getenv("ATLAS_TODAY") else date.today()
    pieces = list(load())
    chunks, corpus, store = {(c.source, c.locator): c for c in pieces}, ChunkCorpus(pieces), store_for("B")
    asked = [c["question_en"] for c in json.loads((ROOT / "data/cq/cqs.json").read_text(encoding="utf-8"))["cqs"]
             if c.get("split", "design") == "design"]
    for path in sorted((ROOT / "data/cq/dev").glob("*.json")):
        asked += [c["question_en"] for c in json.loads(path.read_text(encoding="utf-8"))["cqs"]]
    if argv:
        asked = asked[:int(argv[0])]

    def one(question: str) -> dict:
        return learn_from(question, api.answer(question, "B"), store, chunks, corpus, day)

    with ThreadPoolExecutor(int(os.getenv("ATLAS_DEV_PARALLEL", "5"))) as pool:
        entries = list(pool.map(one, asked))
    print("facts added:", save(entries))
    print(json.dumps(report(), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main(sys.argv[1:])
