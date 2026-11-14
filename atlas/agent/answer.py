"""Owner: Core. Answers from the facts in force at a date, and only from them.

The agent finds the facts closest to the question, and a model may use nothing else. Every step of
the answer carries the fact's quote and locator. No supporting fact means value None: "unknown",
never a guess.
"""
from __future__ import annotations

import json
import math
import re
import os
from datetime import date

from atlas import llm
from atlas.contracts import Answer, Step
from atlas.ontology.statements import Statement, Store

TOP = 50
SYSTEM = """You answer a question about machinery and work-equipment law using ONLY the numbered facts given.
Each fact has a subject, a relation, a value, sometimes a condition, and the place it comes from.

Rules:
- Use only these facts. Do not use anything you know from elsewhere.
- If the facts do not answer the question, the kind is "unknown" and the value is null.
- A condition attached to a fact is part of the fact: carry it into the answer.
- If the question asks about a day, compare that day with the dates in the facts, step by step: a repeal or a
  limit "from 20 January" does not yet apply on 16 January.
- If the question asks "which" or "what" and several facts answer it, list every one of them, in the words of the facts.
- If the question asks who does something and within what time, the kind is "text" and the value names both.
- Return JSON only:
  {"kind": "set|date|duration|boolean|text|unknown",
   "value": <list of short strings for set | "YYYY-MM-DD" for date | ISO 8601 duration like "P10Y" | true/false | a short text | null>,
   "text": "one or two sentences for a person, naming the article or annex point",
   "used": [fact numbers you relied on]}"""


def _line(s: Statement) -> str:
    condition = f" [condition: {s.condition}]" if s.condition else ""
    return f"{s.subject} — {s.predicate} — {s.object_as_written} ({s.object}){condition} [{s.source_doc}, {s.anchor}]"


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    return dot / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)) or 1.0)


def _vectors(texts: list[str]) -> list[list[float]]:
    vectors: list[list[float]] = []
    for start in range(0, len(texts), 200):   # batches: each one is cached by atlas.llm
        vectors += llm.embed(texts[start:start + 200])
    return vectors


def nearest(question: str, facts: list[Statement], top: int = TOP) -> list[Statement]:
    if len(facts) <= top:
        return facts
    lines = [_line(s) for s in facts]
    question_vector = llm.embed([question])[0]
    scored = sorted(zip((_cosine(question_vector, v) for v in _vectors(lines)), range(len(facts))), reverse=True)
    return [facts[i] for _, i in scored[:top]]


def answer(question: str, store: Store, day: date | None = None, mode: str = "B") -> Answer:
    day = day or date.today()
    facts = [s for s in store.as_of(day) if s.status == "current"]
    chosen = nearest(question, facts)
    numbered = "\n".join(f"[{i}] {_line(s)}" for i, s in enumerate(chosen))
    out = llm.chat([{"role": "system", "content": SYSTEM},
                    {"role": "user", "content": f"Today is {day.isoformat()}.\nQuestion: {question}\n\nFacts:\n{numbered}"}],
                   model=os.getenv("ATLAS_STRONG_MODEL", "anthropic/claude-sonnet-5.5"), temperature=0, max_tokens=3000)
    match = re.search(r"\{.*\}", out["text"] or "", re.DOTALL)
    try:
        data = json.loads(match.group(0)) if match else {}
    except json.JSONDecodeError:
        data = {}
    used = [chosen[i] for i in data.get("used", []) if isinstance(i, int) and 0 <= i < len(chosen)]
    value = data.get("value")
    if data.get("kind") == "unknown" or not used:
        value = None   # no fact, no answer
    usage = out.get("usage") or {}
    steps = [Step(text=f"{s.subject}: {s.predicate} = {s.object_as_written}"
                       + (f" (condition: {s.condition})" if s.condition else ""),
                  triples=[(s.subject, s.predicate, s.object)], quote=s.quote,
                  locator=f"{s.source_doc}, {s.anchor}") for s in used]
    return Answer(question=question, mode=mode, value=value,
                  text=data.get("text") or "The facts in force do not answer this question.",
                  steps=steps, tokens=(usage.get("prompt_tokens") or 0) + (usage.get("completion_tokens") or 0))
