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
- A fact noted as "filed under a place the question names" belongs to the answer of a "which / what" question
  about that place whenever its relation fits the question: list all of them, not one.
- Lines under "Computed by rule" are results worked out in code from the numbered facts they name: trust them,
  give their result as the answer for the device asked about, and put the fact numbers they name in "used".
- Include only what the question asks for: no neighbouring item, no other regime that the question did not ask
  about. An option that combines several things in sequence is one item, not several.
- A fact about a neighbouring subject (another paragraph, another device, another kind of verification, another
  product, another deadline) does not answer the question. When the exact subject asked about is absent from the
  facts, "unknown" is the correct answer: do not answer from the nearest fact.
- For a "who" question, when one fact, or several facts with the same subject and relation, name several bodies,
  all of them are the answer together: name each one.
- For "which categories / which items listed in a place", the answer is the members filed under that place, each
  in the words of its fact, without adding the place to the item.
- For "which risks / which hazards does a numbered point address", use every fact filed under that point whatever
  its relation: a measure is required against a risk, and its subject and condition name that risk.
- Never return a list for a "text" answer: a question that one sentence answers (who, why, how, under which
  condition, which one thing and why) gets one short sentence. "Which / what / list all" of several things is "set".
- Facts marked "matched by relation" were found by querying the facts by their relation, subject and place:
  prefer them. When the question asks for all of something, the answer is the list of their subjects or values,
  one item per fact, nothing merged and nothing dropped. If the matched facts answer the question, do not add
  items from the other facts, which are context.
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


STOP = set("""the a an of to in on for and or is are be by with at from as it its that this which what who whom how
when must may can does do shall will than not all any each per into under about there their they them have has had
il lo la i gli le un una di del della dei delle degli da dal dalla in con su per tra fra e o che chi come quando
deve devono essere sono non ogni quale quali cosa nel nella nei nelle al alla ai alle si ha hanno""".split())
LEXICAL = 15         # facts added because they share the question's words
SHARE = 4            # facts every layer gets, nearest first, whatever the crowd in the other layers
VERIFY = re.compile(r"verif|inspect|check|controll|ispezion", re.I)
POSITION = re.compile(r"\b(?:position|posizione|pos\.?|device|dispositivo|apparecchio|item|n\.|no\.|nr\.?)\s*(\d{1,3})\b", re.I)
ASSUMPTIONS = {
    "en": "Assumptions of the rule: truck cranes and mobile cranes are treated as mobile, overhead and gantry cranes "
          "and hoists as fixed, and the site's sector applies to every device.",
    "it": "Ipotesi della regola: le gru su autocarro e le autogru sono trattate come mobili, le gru a ponte e a "
          "cavalletto e i paranchi come fissi, e il settore del sito vale per ogni apparecchio."}


FREQUENCY = re.compile(r"how often|every how many|how frequent|periodicit|interval|frequen|ogni quant|cadenz", re.I)
VERIFIED_ON = re.compile(r"(last|next|latest|previous|ultim|prossim|date|data|due|scaden).*verif|"
                         r"verif.*(date|data|due|scaden|last|next|ultim|prossim)", re.I)
NO_DATES = "no fact in the store gives a last or next verification date for these devices"


def _words(text: str) -> set[str]:
    """Content words of a text, lower case, camelCase split, crude singular (English and Italian)."""
    spaced = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", text or "")
    out = set()
    for w in _key(spaced).split():
        if w in STOP or (len(w) < 3 and not w.isdigit()):
            continue
        out.add(w[:-1] if len(w) > 4 and w[-1] in "sei" else w)
    return out


def lexical(question: str, facts: list[Statement], top: int = LEXICAL) -> list[Statement]:
    """Facts sharing the question's words (in both languages) in subject, relation, value or condition.
    Rare words weigh more, so an exact match is not pushed out by a crowded store."""
    wanted = _words(question) | _words(_other_language(question))
    if not wanted:
        return []
    bags = [_words(f"{s.subject} {s.predicate} {s.object_as_written} {s.object} {s.condition}") for s in facts]
    seen: dict[str, int] = {}
    for bag in bags:
        for w in bag & wanted:
            seen[w] = seen.get(w, 0) + 1
    total = len(facts) or 1
    scored = sorted(((sum(math.log(1 + total / seen[w]) for w in bag & wanted), -i) for i, bag in enumerate(bags)),
                    reverse=True)
    return [facts[-i] for value, i in scored[:top] if value > 0]


def shares(ranked: list[Statement], share: int = SHARE) -> list[Statement]:
    """The nearest facts of every layer, so that a large layer does not crowd out a small one."""
    out, count = [], {}
    for s in ranked:
        layer = getattr(s, "layer", "") or ""
        if layer and count.get(layer, 0) < share:
            count[layer] = count.get(layer, 0) + 1
            out.append(s)
    return out


def _named_places(question: str, facts: list[Statement]) -> set[str]:
    """Ids of the facts filed under a place the question names."""
    out: set[str] = set()
    for place in dict.fromkeys(_place(m.group(0)) for m in PLACE.finditer(question)):
        number = re.fullmatch(r"\d+(?: \d+)+", place)
        for s in facts:
            a = _place(s.anchor)
            if (f" {place} " in f" {a} ") if number else _under(a, place):
                out.add(s.id)
    return out if len(out) <= FAMILY else set()


def device_rule(question: str, facts: list[Statement], near: list[Statement], on: date) -> list[dict]:
    """The verification rule applied to the plant's lifting devices the question is about, on the day asked.
    A question is about them when it concerns verification and either names a position of the device list or
    has device facts among its nearest facts. Each result names the facts it rests on."""
    if not VERIFY.search(question):
        return []
    from atlas.ontology.rules import verification_interval
    from atlas.strategies.plant import device_records

    records = device_records(facts)
    if not records:
        return []
    by_id = {s.id: s for s in facts}
    named = {int(n) for n in POSITION.findall(question)}
    targets = [d for d in records if d["position"] in named]
    if not targets:
        owners = {fact_id: d["position"] for d in records for fact_id in d["facts"].values() if fact_id}
        close = list(dict.fromkeys(owners[s.id] for s in near if s.id in owners and s.predicate != "siteSector"))
        targets = [d for d in records if d["position"] in close[:3]]
    annex = [s for s in facts if s.predicate == "verificationInterval"]
    results = []
    for d in targets:
        result = verification_interval(d, annex, on)
        ids = [i for i, _ in result.get("because", [])] or list(d["facts"].values())
        ids = list(dict.fromkeys(ids + list(d["facts"].values())))
        results.append({"device": d, "interval": result.get("interval"), "why": result.get("why", ""),
                        "because": "; ".join(reason for _, reason in result.get("because", [])),
                        "facts": [by_id[i] for i in ids if i in by_id]})
    return results


def _canon(duration: str) -> str:
    match = re.fullmatch(r"P(\d+)M", duration or "")
    return f"P{int(match.group(1)) // 12}Y" if match and int(match.group(1)) % 12 == 0 else (duration or "")


def _all_durations(text: str) -> set[str]:
    found = {m.group(0).upper() for m in ISO_DURATION.finditer(text or "") if len(m.group(0)) > 1}
    found |= {f"P{int(m.group(1))}{UNITS[m.group(2).lower()]}" for m in WRITTEN_DURATION.finditer(text or "")}
    return {_canon(d) for d in found}


def grounded(kind: str, value, used: list[Statement], question: str) -> tuple[object, list[Statement], str]:
    """No supporting fact, no answer. Checks a typed value against the facts the model says it used and returns
    (value, used, what was missing). The value comes back None when the facts do not carry it:
    - date, duration: the value must be written, as given or in normal form, in a used fact;
    - set: only the items found in a used fact (containment or half of their words) are kept;
    - boolean: a used fact must be dated, conditioned, or share words with the question;
    - text: a clause naming a number, a duration or an acronym found neither in the used facts nor in the
      question is removed.
    A used fact sharing no word with the question or with another used fact is dropped when one at least stays."""
    if value is None or not used:
        return None, used, ""
    asked = _words(question)
    bags = [_words(f"{s.subject} {s.predicate} {s.object_as_written} {s.object} {s.condition}") for s in used]
    keep = [s for i, s in enumerate(used)
            if bags[i] & asked or any(bags[i] & bag for j, bag in enumerate(bags) if j != i)]
    used = keep or used
    blob = " ".join(f"{s.subject} {s.object_as_written} {s.object} {s.object_normalised} {s.condition} {s.quote} "
                    f"{s.source_doc} {s.anchor}" for s in used)
    if kind == "date":
        ok = any(d.isoformat() == value for d in _dates(blob))
        return (value if ok else None), used, "" if ok else f"no used fact carries the date {value}"
    if kind == "duration":
        ok = _canon(str(value)) in _all_durations(blob)
        return (value if ok else None), used, "" if ok else f"no used fact carries the duration {value}"
    if kind == "set" and isinstance(value, list):
        flat, words = _key(blob), _words(blob)
        def found(item: str) -> bool:
            own = _words(item)
            return (len(_key(item)) >= 4 and _key(item) in flat) or (bool(own) and len(own & words) * 2 >= len(own))
        items = [item for item in value if found(item)]
        return (items or None), used, "" if items else "no used fact names any of the items"
    if kind == "boolean" or isinstance(value, bool):
        ok = any(_dates(f"{s.object} {s.object_as_written} {s.condition}") or s.condition or bag & asked
                 for s, bag in zip(used, bags))
        return (value if ok else None), used, "" if ok else "no used fact is dated or about what the question asks"
    known = _key(blob + " " + question)
    flat = f" {known} "
    def supported(clause: str) -> bool:
        tokens = re.findall(r"\b\d+(?:[.,]\d+)?\b|\b[A-Z]{2,}\b", clause)
        tokens = [tok for tok in tokens if not re.fullmatch(r"P?\d*[YMWD]", tok)]
        return (all(f" {_key(tok)} " in flat for tok in tokens)
                and all(d in _all_durations(blob + " " + question) for d in _all_durations(clause)))
    clauses = [c for c in re.split(r"(?<=[;.])\s+|;\s*", str(value)) if c.strip()]
    kept = [c for c in clauses if supported(c)]
    text = str(value) if len(kept) == len(clauses) else " ".join(kept).strip() or None
    return text, used, "" if text else "the used facts do not carry the names or numbers of the answer"


QUERY = """You turn a question into a query over a store of facts. Each fact has a subject, a relation and a value.
Return JSON only:
{"relations": [up to 3 relation names from the list below, the ones whose facts would answer the question],
 "subject_terms": [2 to 5 words naming what the question is about, in English and in Italian],
 "place": "an article, annex part or numbered point if the question names one, else null",
 "source_hint": "a document or product the question names, else null",
 "wants": "one" or "all"}

Relations:
"""
MATCH_ALL, MATCH_ONE = 12, 5
OLD_ACT, NEW_ACT = ("DIR",), ("REG", "CORR")


def graph_query(question: str, facts: list[Statement]) -> tuple[list[Statement], dict]:
    """Queries the facts by their structure. One cached model call names the relations, the subject words, the
    place and the source the question is about; the code then filters the facts by relation and ranks them by
    rare shared words, by place and by source. Returns the matches, best first, and the query."""
    from atlas.strategies.schema_b import RELATIONS

    present = {s.predicate for s in facts}
    described = "\n".join(f"- {name}: {RELATIONS[name][2] if name in RELATIONS else ''}" for name in sorted(present))
    out = llm.chat([{"role": "system", "content": QUERY + described}, {"role": "user", "content": question}],
                   temperature=0, max_tokens=400)
    found = re.search(r"\{.*\}", out.get("text") or "", re.DOTALL)
    try:
        query = json.loads(found.group(0)) if found else {}
    except json.JSONDecodeError:
        query = {}
    if not isinstance(query, dict) or not isinstance(query.get("relations"), list):
        return [], {}
    relations = [r for r in query["relations"] if r in present][:3]
    pool = [s for s in facts if s.predicate in relations]
    if not pool:
        return [], query
    terms = query.get("subject_terms") if isinstance(query.get("subject_terms"), list) else []
    wanted = _words(" ".join(str(term) for term in terms))
    place = _place(str(query.get("place") or ""))
    number = re.fullmatch(r"\d+(?: \d+)+", place)
    hint = _words(str(query.get("source_hint") or ""))
    bags = [_words(f"{s.subject} {s.object_as_written} {s.object} {s.condition}") for s in pool]
    seen: dict[str, int] = {}
    for bag in bags:
        for w in bag & wanted:
            seen[w] = seen.get(w, 0) + 1

    def placed(s: Statement) -> bool:
        anchor = _place(s.anchor)
        return bool(place) and ((f" {place} " in f" {anchor} ") if number else _under(anchor, place))

    everything = str(query.get("wants") or "") == "all"
    under = [s for s in pool if placed(s)]
    if everything and under and len(under) <= FAMILY:
        return under, query   # all of a place: every fact of those relations filed there
    scored = []
    for i, (s, bag) in enumerate(zip(pool, bags)):
        value = sum(math.log(1 + len(pool) / seen[w]) for w in bag & wanted)
        value += 5.0 * placed(s) + 3.0 * bool(hint & (_words(s.source_doc) | _words(s.subject)))
        if value > 0:
            scored.append((value, -i))
    return [pool[-i] for _, i in sorted(scored, reverse=True)[:MATCH_ALL if everything else MATCH_ONE]], query


def one_regime(question: str, matched: list[Statement], facts: list[Statement], asked: list[date]) -> tuple[list[Statement], str]:
    """When facts of one relation come from both the Directive and the Regulation, keeps one regime: the
    Regulation, unless the question names the Directive or a day before the Regulation applies (a date read
    from the store). Returns the facts kept and a line saying which regime was kept, or ''."""
    both = {s.predicate for s in matched if s.source_doc in OLD_ACT} & {s.predicate for s in matched if s.source_doc in NEW_ACT}
    if not both:
        return matched, ""
    start = next((_fact_day(s) for s in facts if s.predicate == "appliesFrom" and _fact_day(s) and s.source_doc in NEW_ACT
                  and re.fullmatch(r"(this |the |il presente |il )?(regulation|regolamento)", _key(s.subject))), None)
    old = (bool(re.search(r"directive|direttiva", question, re.I)) and not re.search(r"regulation|regolamento", question, re.I)) \
        or bool(start and any(d < start for d in asked))
    drop = NEW_ACT if old else OLD_ACT
    kept = [s for s in matched if not (s.predicate in both and s.source_doc in drop)]
    return kept, ("The matched facts come from both the Directive and the Regulation: use the "
                  + ("Directive's" if old else "Regulation's") + " and name that act in the sentence.")


LEAD = re.compile(r"^\s*(?:(?:option|opzione)\s*\(?[a-z0-9]{1,2}\)?\s*[:.\-]|\(?[a-z0-9]{1,2}\)|\d{1,2}\.)\s+", re.I)
TAIL = re.compile(r"\s*\(([^()]*)\)\s*$")
LOCATOR = re.compile(r"\b(annex|allegato|art|article|articolo|point|punto|part|parte|riga|comma)\b|\b[pc]\.", re.I)
CLAUSE = re.compile(r"^\s*(before|where|if|in a language|as determined|or alternatively)\b", re.I)
ALTERNATIVE = re.compile(r"alternativ|does not allow|non consent", re.I)
SEQUENCE = re.compile(r",?\s+(followed by|seguit[oa] da)\s+", re.I)
JOINED = re.compile(r"\b(or|o|oppure|ovvero)\b", re.I)


def polish_set(items: list[str], used: list[Statement]) -> list[str]:
    """Set items in the facts' own words: no "Option (a):" prefix or numbering, no trailing bracket holding a
    locator or a condition (unless the bracket is written in a used fact), the fact's exact subject (listedIn)
    or value as written when the item matches one, the order of a "followed by" sequence as the fact writes
    it, no repeats, no item that merely extends another, no alternative of an item already there."""
    names = _key(" ".join(f"{s.subject} {s.object_as_written}" for s in used))
    written = _key(" ".join(f"{s.subject} {s.object_as_written} {s.quote}" for s in used))
    out: list[tuple[str, Statement | None]] = []
    for item in items:
        item = LEAD.sub("", str(item)).strip()
        while True:
            tail = TAIL.search(item)
            if not tail or not (LOCATOR.search(tail.group(1)) or CLAUSE.search(tail.group(1))) \
                    or (_key(tail.group(1)) and _key(tail.group(1)) in names) or not item[:tail.start()].strip():
                break
            item = item[:tail.start()].strip()
        parts = SEQUENCE.split(item, maxsplit=1)
        if len(parts) == 3 and f"{_key(parts[2])} {_key(parts[1])} {_key(parts[0])}" in written \
                and f"{_key(parts[0])} {_key(parts[1])} {_key(parts[2])}" not in written:
            item = f"{parts[2]} {parts[1]} {parts[0]}"   # the order the fact writes
        source, own, flat = None, _words(item), _key(item)
        for s in used:
            target = s.subject if s.predicate == "listedIn" else s.object_as_written
            theirs, there = _words(target), _key(target)
            close = (len(flat) >= 4 and len(there) >= 4 and (flat in there or there in flat)) or \
                (bool(own) and bool(theirs) and len(own & theirs) >= 0.6 * max(len(own), len(theirs)))
            if close and len(target) <= 200:
                item, source = target.strip(), s
                break
        if item:
            out.append((item, source))
    kept: list[tuple[str, Statement | None]] = []
    for item, source in out:
        if any(_key(item) == _key(other) for other, _ in kept):
            continue
        twin = source is not None and ALTERNATIVE.search(source.condition or "") and any(
            o is not None and o.id != source.id and o.predicate == source.predicate and o.source_doc == source.source_doc
            and _place(o.anchor).split(" ")[:2] == _place(source.anchor).split(" ")[:2] for _, o in out)
        if not twin:
            kept.append((item, source))
    keys = [f" {_key(item)} " for item, _ in kept]
    return [item for i, (item, _) in enumerate(kept)
            if not any(j != i and other != keys[i] and other in keys[i] for j, other in enumerate(keys))]


def all_bodies(value: str, used: list[Statement]) -> str:
    """For a "who" answer: when the sentence of a used fact's quote that names the answer goes on to name other
    bodies joined by "or", the rest of that sentence is added, so that no body is lost to a shortening."""
    for s in used:
        name = (s.object_as_written or "").strip()
        if len(name) < 3 or _key(name) not in _key(value):
            continue
        for sentence in re.split(r"(?<=[.;])\s+", s.quote or ""):
            at = sentence.lower().find(name.lower())
            rest = sentence[at + len(name):].strip(" .;") if at >= 0 else ""
            if rest and JOINED.search(rest) and _key(rest) not in _key(value):
                return f"{value.rstrip(' .')}; {name} {rest}"
    return value


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
    if len(facts) > TOP:   # a crowded store: exact word matches, named places and every layer keep their seat
        named = _named_places(question, facts)
        for s in [s for s in ranked if s.id in named] + lexical(question, ranked) + shares(ranked):
            if all(s.id != c.id for c in chosen):
                chosen.append(s)
    else:
        named = set()
    matched, regime = [], ""
    if len(facts) > TOP:   # the graph is queried by relation first; the nearest facts follow as context
        matched, _ = graph_query(question, ranked)
        matched, regime = one_regime(question, matched, facts, asked)
        ids = {s.id for s in matched}
        chosen = matched + [s for s in chosen if s.id not in ids]
    by_relation = {s.id for s in matched}
    rule = device_rule(question, facts, ranked[:TOP], asked[0] if asked else day)
    for result in rule:
        chosen += [s for s in result["facts"] if all(s.id != c.id for c in chosen)]
    index = {s.id: i for i, s in enumerate(chosen)}
    on = (asked[0] if asked else day).isoformat()
    computed = "".join(
        f"\n- IGEA device {r['device']['position']} ({r['device'].get('kind', '?')}): verification interval on {on} = "
        + (f"{r['interval']}, because {r['because']}" if r["interval"] else f"unknown, because {r['why']}")
        + f" [rests on facts {', '.join(str(index[s.id]) for s in r['facts'])}]" for r in rule)
    frequency = bool(FREQUENCY.search(question))   # the rule answers only "how often"
    if rule and not frequency:
        # The interval is context only. Whether the plant records a verification date is looked up, not assumed.
        sources = {s.source_doc for r in rule for s in r["facts"] if s.subject.startswith("IGEA device")}
        dated = [s for s in facts if (getattr(s, "layer", "") == "plant" or s.source_doc in sources)
                 and VERIFIED_ON.search(f"{s.predicate} {s.subject}")]
        computed += ("\n- The intervals above say only how often a device must be verified; they do not say when it "
                     "was last verified, when the next verification is due, whether it is overdue or compliant, or "
                     "who verified it.")
        if not dated:
            computed += f"\n- {NO_DATES}: a question about such a date, or about being overdue, is unknown."
    numbered = "\n".join(f"[{i}] {_line(s)}{_notes(s, asked, corrected)}"
                         + (" [matched by relation]" if s.id in by_relation else "")
                         + (" [note: filed under a place the question names]" if s.id in named else "")
                         for i, s in enumerate(chosen))
    if regime:
        numbered += "\n\n" + regime
    elif len(facts) > TOP and not matched and not rule:
        numbered += ("\n\nNo fact matched the question by relation: answer only if a fact above is about the exact "
                     "subject asked; otherwise the answer is unknown.")
    if computed:
        numbered += "\n\nComputed by rule (" + ASSUMPTIONS["en"] + "):" + computed
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
    text = (data.get("text") if value is not None or used else None) or UNKNOWN.get(lang, UNKNOWN["en"])
    if value is not None:   # no supporting fact, no answer
        value, used, missing = grounded(str(data.get("kind") or ""), value, used, question)
        if value is None:
            text = f"{UNKNOWN.get(lang, UNKNOWN['en'])} ({missing})"
    if isinstance(value, list):   # set items in the facts' own words
        value = polish_set(value, used) or None
    elif isinstance(value, str) and re.match(r"\s*(who|chi)\b", question, re.I):
        value = all_bodies(value, used)
    if rule and frequency:   # the rule's facts are always cited and its assumptions always stated
        if len(rule) == 1 and str(data.get("kind") or "") in ("duration", "unknown", ""):
            only = rule[0]   # one device asked about: the rule decides, the model only words it
            value = typed("duration", only["interval"]) if only["interval"] else None
            if value is None:
                text = f"IGEA device {only['device']['position']}: {UNKNOWN.get(lang, UNKNOWN['en'])} ({only['why']})."
            elif not used or data.get("value") is None or typed("duration", data.get("value")) != value:
                text = (f"IGEA device {only['device']['position']} must be verified every {value} on {on}: "
                        f"{only['because']}.")
        for result in rule:
            used += [s for s in result["facts"] if all(s.id != u.id for u in used)]
        text = f"{text} {ASSUMPTIONS.get(lang, ASSUMPTIONS['en'])}"
    steps = [Step(text=f"{s.subject}: {s.predicate} = {s.object_as_written}"
                       + (f" (condition: {s.condition})" if s.condition else ""),
                  triples=[(s.subject, s.predicate, s.object)], quote=s.quote,
                  locator=f"{s.source_doc}, {s.anchor}", statement_id=s.id) for s in used]
    return Answer(question=question, mode=mode, value=value,
                  text=text,
                  steps=steps, tokens=(usage.get("prompt_tokens") or 0) + (usage.get("completion_tokens") or 0))
