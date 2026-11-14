"""Owner: Core. Answers from the facts in force at a date, and only from them.

The agent finds the facts closest to the question, and a model may use nothing else. Every step of
the answer carries the fact's quote and locator. No supporting fact means value None: "unknown",
never a guess.
"""
from __future__ import annotations

import json
import math
import re
from datetime import date

from atlas import llm
from atlas.contracts import Answer, Step
from atlas.ontology.statements import Statement, Store

TOP = 50
EXTRA = 40           # facts added by relation, by locator and by family, on top of the nearest ones
FAMILY = 30          # a family (same source, same article or annex part) larger than this is not pulled in whole
SEEDS = 10           # how many of the nearest facts may bring their family along
SYSTEM = """You answer a question about machinery and work-equipment law using ONLY the numbered facts given.
Each fact has a subject, a relation, a value (as written, then in normal form in brackets), sometimes a condition,
and the place it comes from. Some facts carry a note computed from the dates: trust the notes.

Rules:
- Use only these facts. Do not use anything you know from elsewhere.
- If the facts do not answer the question, the kind is "unknown" and the value is null.
- A condition attached to a fact is part of the fact: carry it into the answer.
- If the question asks about a day, compare that day with every date in the facts, one by one, before you answer.
  A repeal, a limit or an application "from" a date takes effect on that date, not earlier: an act repealed from a
  date is still fully in force, with everything it permits, on every earlier day; a rule applying from a date does
  not yet bind on earlier days.
- If a note says that a date quoted in a condition was corrected, reason with the corrected date.
- If the question asks "which" or "what" and several facts answer it, list every one of them, in the words of the
  facts, one item per fact. Facts filed under the same article, annex part or numbered point belong together.
  When the answer is a group named by an article or an annex part and the facts list the members of that group,
  give the members, not the name of the group.
- The kind follows the question: "from which date / when (a day)" is "date"; "for how long" alone is "duration";
  "can / may / is / does" is "boolean"; "which / what (several things)" is "set"; who, why, under which condition,
  or who does something and within what time is "text", and the text names every element asked for.
- Return JSON only, with the reasoning first:
  {"reasoning": "the facts and dates compared, step by step, in a few short sentences",
   "kind": "set|date|duration|boolean|text|unknown",
   "value": <list of short strings for set | "YYYY-MM-DD" for date | ISO 8601 duration like "P10Y" | true/false | a short text | null>,
   "text": "one or two sentences for a person, naming the article or annex point",
   "used": [fact numbers you relied on]}"""
ITALIAN = '\n- Write the "text" field in Italian. The "value" stays exactly as specified above.'
UNKNOWN = {"en": "The facts in force do not answer this question.",
           "it": "I fatti in vigore non rispondono a questa domanda."}

ISO_DATE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
ISO_DURATION = re.compile(r"\bP(?=\d|T\d)(?:\d+Y)?(?:\d+M)?(?:\d+W)?(?:\d+D)?(?:T(?:\d+H)?(?:\d+M)?(?:\d+S)?)?\b", re.I)
MONTHS = {name: i % 12 + 1 for i, name in enumerate(
    "january february march april may june july august september october november december "
    "gennaio febbraio marzo aprile maggio giugno luglio agosto settembre ottobre novembre dicembre".split())}
WRITTEN_DATE = re.compile(r"\b(\d{1,2})(?:st|nd|rd|th|°|º)?\s+(" + "|".join(MONTHS) + r")\s+(\d{4})\b", re.I)
UNITS = {"year": "Y", "years": "Y", "anno": "Y", "anni": "Y", "month": "M", "months": "M", "mese": "M", "mesi": "M",
         "week": "W", "weeks": "W", "settimana": "W", "settimane": "W", "day": "D", "days": "D", "giorno": "D",
         "giorni": "D"}
WRITTEN_DURATION = re.compile(r"\b(\d+)\s+(" + "|".join(UNITS) + r")\b", re.I)
TEMPORAL = re.compile(r"\b(when|date|until|still|already|yet|deadline|from which|as of|in force|repeal\w*|"
                      r"quando|data|fino|ancora|gi[aà]|scadenza|in vigore|abrog\w*)\b", re.I)
LASTING = re.compile(r"\b(how long|within|period|time limit|deadline|keep|retain\w*|"
                     r"quanto tempo|entro|periodo|termine|scadenza|conserv\w*)\b", re.I)
# Places a question or a fact may name: "Article 25(2)", "art. 71", "Annex I, Part A", "1.3.7".
PLACE = re.compile(r"\b(?:art(?:icle|icolo)?\.?\s*\d+(?:\(\d+\))?|"
                   r"(?:annex|allegato)\s+[IVXL]+(?:,?\s+(?:part|parte)\s+[A-Z])?(?:,?\s+(?:point|punto)\s+\d+)?|"
                   r"\d+(?:\.\d+)+)", re.I)


def _dates(text: str) -> list[date]:
    """Every calendar day written in a text, ISO or in words (English and Italian)."""
    found = [(m.start(), (int(m.group(1)), int(m.group(2)), int(m.group(3)))) for m in ISO_DATE.finditer(text or "")]
    found += [(m.start(), (int(m.group(3)), MONTHS[m.group(2).lower()], int(m.group(1))))
              for m in WRITTEN_DATE.finditer(text or "")]
    days = []
    for _, parts in sorted(found):
        try:
            days.append(date(*parts))
        except ValueError:
            continue
    return days


def _fact_day(s: Statement) -> date | None:
    match = ISO_DATE.fullmatch((s.object or "").strip())
    days = _dates(match.group(0)) if match else []
    return days[0] if days else None


def _key(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def corrections(store: Store, facts: list[Statement]) -> dict[date, tuple[date, Statement]]:
    """Dates that a later source replaced: a closed dated fact and the current fact on the same subject and relation."""
    current = {(s.subject, s.predicate): s for s in facts if _fact_day(s)}
    out: dict[date, tuple[date, Statement]] = {}
    for old in store.statements:
        new = current.get((old.subject, old.predicate))
        old_day = _fact_day(old) if old.status == "closed" else None
        if new and old_day and _fact_day(new) != old_day:
            out[old_day] = (_fact_day(new), new)
    return out


def _notes(s: Statement, asked: list[date], corrected: dict[date, tuple[date, Statement]]) -> str:
    """What the code can work out from the dates, so that the model does not have to do the arithmetic."""
    notes = []
    for old in _dates(s.condition):
        if old in corrected and corrected[old][1].id != s.id:
            new, by = corrected[old]
            notes.append(f"the date {old.isoformat()} quoted in this condition was corrected to {new.isoformat()} "
                         f"by {by.source_doc}, {by.anchor}")
    fact_day = _fact_day(s)
    for asked_day in asked if fact_day else []:
        gap = (fact_day - asked_day).days
        notes.append(f"{asked_day.isoformat()} is the same day as {fact_day.isoformat()}" if gap == 0 else
                     f"{asked_day.isoformat()} is {abs(gap)} days {'before' if gap > 0 else 'after'} {fact_day.isoformat()}")
    return f" [note: {'; '.join(notes)}]" if notes else ""


def _line(s: Statement) -> str:
    condition = f" [condition: {s.condition}]" if s.condition else ""
    return f"{s.subject} — {s.predicate} — {s.object_as_written} ({s.object}){condition} [{s.source_doc}, {s.anchor}]"


_VECTORS: dict[str, tuple[list[float], float]] = {}   # line -> (vector, length); filled once per process


def _vectors(texts: list[str]) -> list[tuple[list[float], float]]:
    missing = [t for t in dict.fromkeys(texts) if t not in _VECTORS]
    for start in range(0, len(missing), 200):   # batches: each one is cached on disk by atlas.llm
        batch = missing[start:start + 200]
        for text, vector in zip(batch, llm.embed(batch)):
            _VECTORS[text] = (vector, math.sqrt(sum(x * x for x in vector)) or 1.0)
    return [_VECTORS[t] for t in texts]


def _other_language(question: str) -> str:
    """The question in the other language of the sources (English and Italian), so that facts written in
    either language can be found. One short cached call; the question itself if the model returns nothing."""
    out = llm.chat([{"role": "system", "content": "Translate the question into Italian if it is in English, into "
                     "English if it is in Italian. Keep names, numbers and dates. Return only the translation."},
                    {"role": "user", "content": question}], temperature=0, max_tokens=300)
    return (out.get("text") or "").strip() or question


def nearest(question: str, facts: list[Statement], top: int = TOP) -> list[Statement]:
    """The facts closest to the question, closest first; all of them when there are no more than `top`.
    A fact counts as close when it is close to the question in either language."""
    if len(facts) <= top:
        return list(facts)
    queries = []
    for q in llm.embed([question, _other_language(question)]):
        queries.append((q, math.sqrt(sum(x * x for x in q)) or 1.0))
    scored = sorted(((max(sum(x * y for x, y in zip(q, v)) / (q_length * length) for q, q_length in queries), i)
                     for i, (v, length) in enumerate(_vectors([_line(s) for s in facts]))), reverse=True)
    return [facts[i] for _, i in scored[:top]]


def _place(text: str) -> str:
    """A locator in one spelling: "Article 25(2)" and "Art. 25(2)" are the same place."""
    words = {"article": "art", "articolo": "art", "allegato": "annex", "parte": "part", "punto": "point"}
    return " ".join(words.get(w, w) for w in _key(text).split())


def _under(anchor: str, place: str) -> bool:
    """True when a fact's locator is the place or lies inside it ("annex i part a point 3" is under "annex i part a")."""
    return anchor == place or anchor.startswith(place + " ")


def related(question: str, facts: list[Statement], chosen: list[Statement], extra: int = EXTRA) -> list[Statement]:
    """Facts the nearest ones leave out: dated facts for a question about time, the facts filed under a place
    the question names, and the family (same source, same article or annex part) of the nearest facts."""
    have = {s.id for s in chosen}
    added: list[Statement] = []

    def add(group: list[Statement]) -> None:
        for s in group:
            if s.id not in have and len(added) < extra:
                have.add(s.id)
                added.append(s)

    # `facts` come nearest first, so each group keeps the facts closest to the question when the cap cuts it.
    if TEMPORAL.search(question) or _dates(question):
        add([s for s in facts if _fact_day(s)][:EXTRA // 2])
    if LASTING.search(question):
        add([s for s in facts if ISO_DURATION.fullmatch((s.object or "").strip())][:EXTRA // 2])
    anchors = [(s, _place(s.anchor)) for s in facts]
    for place in dict.fromkeys(_place(m.group(0)) for m in PLACE.finditer(question)):
        number = re.fullmatch(r"\d+(?: \d+)+", place)   # a bare point number sits at the end of a locator
        group = [s for s, a in anchors if (a.endswith(" " + place) or a == place if number else _under(a, place))]
        if len(group) <= FAMILY:
            add(group)
    for seed in chosen[:SEEDS]:
        own = _place(seed.anchor)
        named = {_place(m.group(0)) for m in PLACE.finditer(f"{seed.subject} {seed.object_as_written}")} - {own}
        family = [s for s, a in anchors if s.source_doc == seed.source_doc
                  and ((a == own and s.predicate == seed.predicate) or (a != own and _under(a, own))
                       or any(_under(a, place) for place in named if " " in place))]
        if len(family) <= FAMILY:
            add(family)
    return added


def _duration(text: str) -> str | None:
    match = ISO_DURATION.search(text)
    if match and len(match.group(0)) > 1:
        return match.group(0).upper()
    written = WRITTEN_DURATION.search(text)
    return f"P{int(written.group(1))}{UNITS[written.group(2).lower()]}" if written else None


def typed(kind: str, value):
    """The value in the shape its kind promises: list for set, ISO string for date and duration, bool, short text."""
    if value is None or kind == "unknown":
        return None
    if kind not in ("set", "date", "duration", "boolean", "text"):
        kind = "boolean" if isinstance(value, bool) else "set" if isinstance(value, list) else "text"
    if kind == "set":
        items = value if isinstance(value, list) else [value]
        items = [re.sub(r"\s*\[facts?\s*[\d,\s]+\]", "", str(v)).strip() for v in items if v is not None]
        items = list(dict.fromkeys(v for v in items if v))   # no fact numbers inside the items, no repeats
        return items or None
    if isinstance(value, list):
        value = value[0] if len(value) == 1 else "; ".join(str(v) for v in value)
    if kind == "boolean":
        if isinstance(value, bool):
            return value
        word = _key(str(value)).split(" ")[0]
        return True if word in ("true", "yes", "si", "sì") else False if word in ("false", "no") else None
    text = str(value).strip()
    if kind == "date":
        days = _dates(text)
        return days[0].isoformat() if days else text or None
    if kind == "duration":
        return _duration(text) or text or None
    return text or None


def answer(question: str, store: Store, day: date | None = None, mode: str = "B", lang: str = "en") -> Answer:
    day = day or date.today()
    facts = [s for s in store.as_of(day) if s.status == "current"]
    ranked = nearest(question, facts, top=max(TOP, len(facts) - 1)) if len(facts) > TOP else list(facts)
    chosen = ranked[:TOP]
    chosen = chosen + related(question, ranked, chosen)
    asked, corrected = _dates(question), corrections(store, facts)
    numbered = "\n".join(f"[{i}] {_line(s)}{_notes(s, asked, corrected)}" for i, s in enumerate(chosen))
    out = llm.chat([{"role": "system", "content": SYSTEM + (ITALIAN if lang == "it" else "")},
                    {"role": "user", "content": f"Today is {day.isoformat()}.\nQuestion: {question}\n\nFacts:\n{numbered}"}],
                   temperature=0, max_tokens=3000)
    match = re.search(r"\{.*\}", out["text"] or "", re.DOTALL)
    try:
        data = json.loads(match.group(0)) if match else {}
    except json.JSONDecodeError:
        data = {}
    if not isinstance(data, dict):
        data = {}
    numbers = data.get("used") if isinstance(data.get("used"), list) else []
    used = [chosen[i] for i in dict.fromkeys(n for n in numbers if isinstance(n, int) and not isinstance(n, bool))
            if 0 <= i < len(chosen)]
    value = typed(str(data.get("kind") or ""), data.get("value")) if used else None   # no fact, no answer
    usage = out.get("usage") or {}
    steps = [Step(text=f"{s.subject}: {s.predicate} = {s.object_as_written}"
                       + (f" (condition: {s.condition})" if s.condition else ""),
                  triples=[(s.subject, s.predicate, s.object)], quote=s.quote,
                  locator=f"{s.source_doc}, {s.anchor}", statement_id=s.id) for s in used]
    return Answer(question=question, mode=mode, value=value,
                  text=(data.get("text") if value is not None or used else None) or UNKNOWN.get(lang, UNKNOWN["en"]),
                  steps=steps, tokens=(usage.get("prompt_tokens") or 0) + (usage.get("completion_tokens") or 0))
