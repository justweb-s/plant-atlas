"""Owner: Core. The router: which reader to ask first, and when one answer is enough.

Nothing here is decided by hand. A table (ontology/B/router.json) records, for each kind of question and each
reader, how often the reader answered and how often its answer was right, on questions whose right answer is
known. For a new question the readers are tried from the most often right to the least; one answer is enough
when that reader, on that kind of question, has almost always been right when it answered; otherwise a second
reader is asked and the two must agree, or a judge decides on the evidence.

The kind of a question is read from its words by code (no model): what sort of answer it asks for and what it
is about. learn() rebuilds the table from logged outcomes; evaluation/router_eval.py measures it.
"""
from __future__ import annotations

import json
import os
import re
from datetime import date
from pathlib import Path

from atlas.contracts import Answer

ROOT = Path(__file__).resolve().parents[2]
TABLE = ROOT / "ontology" / "B" / "router.json"
LOG = ROOT / "runtime" / "router_log.jsonl"
ENOUGH = float(os.getenv("ATLAS_ROUTER_ENOUGH", "0.9"))        # one answer is enough when the reader was right at least this often when it answered
PRIOR = 2.0         # weight of the broader evidence when a kind of question has few logged outcomes

ASKS = (("duration", r"\b(how often|how long|for how long|within (what|how many)|how much (time|notice)|ogni quanto|per quanto|entro quant\w+)\b"),
        ("date", r"\b(from which date|by which date|on what date|what date|which day|last day|when\b|da quale data|entro quale data|in che data|quando)\b"),
        ("set", r"\b(which|what|quali)\b[^?]*\b(positions?|devices?|categories|procedures|risks|steps|documents|situations|models|items|bodies|posizion\w+|categorie|procedure|rischi|documenti)\b|\blist\b"),
        ("boolean", r"^\s*(?:[^?]{0,160}?[,:.]\s+)?(can|may|must|is|are|does|do|did|has|have|will|would|should|pu[oò]|deve|devono|[eè]|sono|ha|hanno)\b"),
        ("text", r"\b(who|why|whom|in what capacity|under which condition|chi|perch[eé])\b"))


def asks_for(question: str) -> str:
    """The sort of answer a question asks for, from its words."""
    for kind, pattern in ASKS:
        if re.search(pattern, question, re.I):
            return kind
    return "text"


def about(question: str) -> str:
    """What a question is about: the device list, a machine's manual, a day (which text is in force), or the law."""
    from atlas.agent.answer import LIST_QUESTION, POSITION, TEMPORAL, _dates
    from atlas.agent.text import named_sources

    named = named_sources(question)
    if re.search(r"\b(which|how many|quali|quant[ei])\s+(positions?|devices?|posizion\w+|apparecch\w+)\b", question, re.I):
        return "whole list"
    if POSITION.search(question) or "igea-equipment" in named:
        return "whole list" if LIST_QUESTION.search(question) and len(POSITION.findall(question)) != 1 else "device"
    if named & {"ur5e-manual", "ur10e-manual", "nanoscan3-manual", "mastar-manual", "robot-cell-sheet"}:
        return "machine"
    if _dates(question) or TEMPORAL.search(question):
        return "day"
    return "law"


def kind_of(question: str) -> tuple[str, str]:
    return about(question), asks_for(question)


def learn(outcomes: list[dict]) -> dict:
    """The table from logged outcomes. Each outcome: {"question", "reader", "answered": bool, "right": bool}.
    Counts are kept at three levels (what it is about + what it asks for; what it is about; everything), so a
    kind of question with few outcomes leans on the broader counts."""
    table: dict = {"levels": {}, "n": len(outcomes)}
    for o in outcomes:
        topic, asks = kind_of(o["question"])
        for key in (f"{topic}|{asks}", f"{topic}|*", "*|*"):
            cell = table["levels"].setdefault(key, {}).setdefault(o["reader"], {"n": 0, "answered": 0, "right": 0,
                                                                                 "right_answered": 0})
            cell["n"] += 1
            cell["answered"] += bool(o["answered"])
            cell["right"] += bool(o["right"])
            cell["right_answered"] += bool(o["right"] and o["answered"])
    return table


def load() -> dict:
    return json.loads(TABLE.read_text(encoding="utf-8")) if TABLE.exists() else {"levels": {}, "n": 0}


def rates(table: dict, question: str, reader: str) -> tuple[float, float]:
    """(how often this reader is right on this kind of question, how often it is right when it answers).
    Each level is smoothed toward the broader one."""
    topic, asks = kind_of(question)
    right, precise = 0.5, 0.5
    for key in ("*|*", f"{topic}|*", f"{topic}|{asks}"):
        cell = table["levels"].get(key, {}).get(reader)
        if not cell:
            continue
        right = (cell["right"] + PRIOR * right) / (cell["n"] + PRIOR)
        precise = (cell["right_answered"] + PRIOR * precise) / (cell["answered"] + PRIOR)
    return right, precise


def order(table: dict, question: str, names: list[str]) -> list[str]:
    from atlas.agent.readers import COST

    return sorted(names, key=lambda r: (-round(rates(table, question, r)[0], 2), COST.get(r, 1)))


def route(question: str, ask, names: list[str], table: dict, judge=None, same=None, limit: int = 3,
          ranked: list[str] | None = None) -> tuple[Answer | None, list[dict]]:
    """The policy, apart from how a reader is run: `ask(name)` returns that reader's Answer.
    Returns the answer chosen (None: nobody answered) and the trace of what was tried and why."""
    trace, held = [], None
    for name in (ranked or order(table, question, names))[:limit]:   # `ranked`: an order given by hand, to compare
        right, precise = rates(table, question, name)
        found = ask(name)
        step = {"reader": name, "expected_right": round(right, 2), "right_when_answering": round(precise, 2),
                "answered": found.value is not None}
        trace.append(step)
        if found.basis == "rule":       # computed in code from the facts: final, whether a value or "unknown"
            step["decision"] = "computed by rule: final"
            return found, trace
        if found.value is None:
            step["decision"] = "no answer: next reader"
            continue
        if held is None:
            if precise >= ENOUGH:
                step["decision"] = f"right {precise:.0%} of the times it answered this kind of question: enough"
                return found, trace
            step["decision"] = "not sure enough alone: a second reader is asked"
            held = (name, found)
            continue
        first_name, first = held
        if same(first.value, found.value):
            step["decision"] = f"agrees with {first_name}: answer"
            first.steps = first.steps + found.steps
            first.basis = f"{first_name}+{name}"
            return first, trace
        choice = judge(first, found)
        step["decision"] = f"disagrees with {first_name}: the judge chose {choice}"
        if choice == "a" or choice == "same":
            return first, trace
        if choice == "b":
            return found, trace
        held = None   # neither is supported: the next reader starts afresh
    if held is not None:   # one answer, never confirmed and never contradicted
        trace[-1]["decision"] = trace[-1].get("decision", "") + f"; {held[0]} stands alone"
        return held[1], trace
    return None, trace


def answer(question: str, store, day: date | None = None, mode: str = "B", lang: str = "en") -> Answer:
    from atlas.agent import answer as base, readers

    readers.load_plugins()
    if day is None and os.getenv("ATLAS_TODAY"):
        day = date.fromisoformat(os.environ["ATLAS_TODAY"])
    day = day or date.today()
    names = [n for n in os.getenv("ATLAS_READERS", "facts,words,similar,search").split(",") if n in readers.READERS]
    tokens = [0]

    def ask(name: str) -> Answer:
        found = readers.READERS[name](question, store, day)
        tokens[0] += found.tokens
        if not found.basis or found.basis == "facts":
            found.basis = found.basis or name
        return found

    chosen, trace = route(question, ask, names, load(), same=base._same_value,
                          judge=lambda a, b: base._judge(question, day, a, b))
    if chosen is None:
        chosen = Answer(question=question, mode=mode, value=None, basis="none",
                        text=base.UNKNOWN.get(lang, base.UNKNOWN["en"]) + " (" + ", ".join(t["reader"] for t in trace)
                        + " found no answer that passes the check)")
    chosen.mode, chosen.tokens = mode, tokens[0]
    chosen.trace = trace   # not a field of the dataclass: shown by the app, written to the log
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8") as log:
            log.write(json.dumps({"question": question, "kind": kind_of(question), "trace": trace,
                                  "value": chosen.value, "basis": chosen.basis}, ensure_ascii=False) + "\n")
    except OSError:
        pass
    return chosen


# ---- the panel: every reader answers, agreement wins, one judge settles the rest ------------------------------
PANEL = """Several readers answered the same question about machines at work, each pointing at the sentences it
used. Decide which answer the evidence supports. Use only the evidence shown; do not use what you know.

Rules:
- An answer is supported only if its evidence states it for the exact subject asked about (the same device, the
  same article and paragraph, the same kind of verification, the same deadline, the same condition the question
  states). Evidence about a neighbouring subject does not support an answer.
- When answers rest on texts of different rank, the higher rank wins: law, then guidance, then manufacturer's
  manual, then company procedure, then plant record. Between two Italian texts, a legislative decree (D.Lgs.)
  wins over a ministerial decree (DM). A wording corrected by a corrigendum replaces the original wording.
- For a list, prefer the answer whose items are each stated by the evidence and that leaves none out.
- Readers that found nothing are listed too: when most readers found nothing and the one answer shown rests on
  evidence about a neighbouring subject, choose "none".
Return JSON only: {"reasoning": "two or three short sentences", "choice": <the number of the answer supported, or "none">}"""


def panel(question: str, found: dict[str, Answer], day: date, same, chat=None) -> tuple[Answer | None, list[dict]]:
    """`found`: each reader's Answer. A result computed by rule is final. Otherwise the answers are grouped by
    value: one group backed by two readers or more is the answer; anything else goes once to a judge, who sees
    every answer with its evidence and may choose one of them or none. The judge never writes a value."""
    from atlas import llm
    from atlas.agent import answer as base

    trace = [{"reader": n, "answered": a.value is not None, "basis": a.basis} for n, a in found.items()]
    for name, a in found.items():
        if a.basis == "rule":
            trace.append({"decision": f"{name}: computed by rule, final"})
            return a, trace
    groups: list[dict] = []
    for name, a in found.items():
        if a.value is None:
            continue
        for g in groups:
            if same(g["answer"].value, a.value):
                g["by"].append(name)
                g["answer"].steps = g["answer"].steps + a.steps
                break
        else:
            groups.append({"answer": a, "by": [name]})
    if not groups:
        trace.append({"decision": "no reader answered"})
        return None, trace
    if len(groups) == 1 and len(groups[0]["by"]) >= 2:
        chosen = groups[0]
        trace.append({"decision": f"{' and '.join(chosen['by'])} agree: answer"})
    else:
        silent = [n for n, a in found.items() if a.value is None]
        body = "\n\n".join(
            f"Answer {i + 1} (given by {len(g['by'])} reader(s): {', '.join(g['by'])}): "
            f"{json.dumps(g['answer'].value, ensure_ascii=False)}\n{g['answer'].text}\nEvidence:\n{base._evidence(g['answer'])}"
            for i, g in enumerate(groups))
        out = (chat or llm.chat)([{"role": "system", "content": PANEL},
                                  {"role": "user", "content": f"Today is {day.isoformat()}.\nQuestion: {question}\n\n{body}"
                                   f"\n\nReaders that found nothing: {', '.join(silent) or 'none'}"}],
                                 model=os.getenv("ATLAS_JUDGE_MODEL", base.JUDGE_MODEL), temperature=0, max_tokens=800)
        choice = base._reply(out.get("text") or "").get("choice")
        if not (isinstance(choice, int) and not isinstance(choice, bool) and 1 <= choice <= len(groups)):
            trace.append({"decision": f"{len(groups)} different answers: the judge found none supported"})
            return None, trace
        chosen = groups[choice - 1]
        trace.append({"decision": f"{len(groups)} different answer(s): the judge chose that of {' and '.join(chosen['by'])}"})
    chosen["answer"].basis = "+".join(chosen["by"])
    return chosen["answer"], trace


def panel_answer(question: str, store, day: date | None = None, mode: str = "B", lang: str = "en") -> Answer:
    """Every reader answers (in parallel), then panel() decides."""
    from concurrent.futures import ThreadPoolExecutor

    from atlas.agent import answer as base, readers

    readers.load_plugins()
    if day is None and os.getenv("ATLAS_TODAY"):
        day = date.fromisoformat(os.environ["ATLAS_TODAY"])
    day = day or date.today()
    names = [n for n in os.getenv("ATLAS_READERS", "facts,words,similar,search").split(",") if n in readers.READERS]
    first = readers.READERS[names[0]](question, store, day)   # the fact store first: a rule result ends it there
    found = {names[0]: first}
    if first.basis != "rule":
        with ThreadPoolExecutor(len(names)) as pool:
            for name, a in zip(names[1:], pool.map(lambda n: readers.READERS[n](question, store, day), names[1:])):
                found[name] = a
    tokens = sum(a.tokens for a in found.values())
    chosen, trace = panel(question, found, day, base._same_value)
    if chosen is None:
        chosen = Answer(question=question, mode=mode, value=None, basis="none",
                        text=base.UNKNOWN.get(lang, base.UNKNOWN["en"]) + " (no answer of the readers is supported by its evidence)")
    chosen.mode, chosen.tokens = mode, tokens
    chosen.trace = trace
    return chosen
