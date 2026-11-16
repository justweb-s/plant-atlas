"""Owner: Core. Reading on demand: when the fact store does not hold the answer, the registered documents are
read for this one question, under the same rule as the store ("no quote, no fact").

The passages closest to the question are found by their words (no embedding, so it works with no key), the
corrigendum is applied to the text by code, and a model answers only by pointing at sentences. Code then checks
that every sentence pointed at is really in its passage, and that a date or a number given as the answer is
written in one of those sentences. An answer that fails the check is "unknown".
"""
from __future__ import annotations

import json
import math
import os
import re
import unicodedata
from datetime import date
from functools import lru_cache
from pathlib import Path

from atlas import llm
from atlas.contracts import Answer, Step

PASSAGES = 14
PER_SOURCE = 5                     # no document fills the page: the text of a higher rank must find room
WINDOW, STEP = 2400, 1200          # a long piece (a table, a whole annex) is read through overlapping windows
RANK = {"law": "law", "guidance": "guidance", "manufacturer": "manufacturer's manual",
        "company": "company procedure", "plant": "plant record"}
FOR_READ = re.compile(r"Article\s+(\d+)(?:,\s*(?:paragraph\s+(\d+)|(\w+)\s+paragraph))?.*?"
                      r"for:\s*[‘'\"]\s*(.+?)\s*[’'\"],\s*read:\s*[‘'\"]\s*(.+?)\s*[’'\"]", re.S)
ORDINAL = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5}
STOP = set("the a an of to in on for and or is are be by with from at as that this which what who how does do must "
           "can may it its their there than then when where into not no if under any all each per "
           "il lo la i gli le un una di a da in con su per tra fra e o che chi come quale quali quanto dove quando "
           "del dello della dei degli delle al allo alla ai agli alle dal dalla nel nella nei nelle sul sulla "
           "è sono deve devono può possono non se".split())

SYSTEM = """You answer a question about machines at work (law, guidance, manufacturers' manuals, company and plant
documents) using ONLY the numbered passages given. Each passage is headed by its document, its place and its rank.

Rules:
- Use only the passages. Do not use anything you know from elsewhere.
- Answer only if a passage states the answer for the exact subject asked about (the same device, the same article
  and paragraph, the same kind of verification, the same deadline). A passage about a neighbouring subject does not
  answer the question: then the kind is "unknown" and the value is null. A question about something that happened
  (the date of the last check, whether something is overdue today) is "unknown" unless a passage records that event.
- A passage marked "corrected by the corrigendum" already shows the corrected wording: reason with it. The old
  wording, given in the mark, is no longer valid.
- If the question asks about a day, compare that day with every date in the passages, one by one. A repeal or an
  application "from" a date takes effect on that date, not earlier: an act repealed from a date is still fully in
  force on every earlier day; a rule applying from a date does not yet bind on earlier days.
- When passages of different rank disagree, the higher rank wins: law, then guidance, then manufacturer's manual,
  then company procedure, then plant record. Between two Italian texts, a legislative decree (D.Lgs.) wins over a
  ministerial decree (DM). Say which one wins.
- A row of a table belongs to the thing named in that same row. Read the row of the item asked about, not a
  neighbouring row. When the question itself states a condition ("if it were in regular use", "built in 2017"),
  reason with that condition.
- The kind follows the question: "from which date / by which date / when (a day)" is "date"; "how often / for how
  long / within what time" is "duration"; "can / may / is / does / must" is "boolean"; "which / what (several
  things)" is "set"; who, why, under which condition is "text" (one short sentence naming every element asked for).
- Point at the evidence: for every passage you rely on, copy word for word the sentence, or the table row, that
  states what you use. Copy exactly, without changing a character; do not join text from two places.
- Return JSON only, with the reasoning first:
  {"reasoning": "what the passages say and how it leads to the answer, in a few short sentences",
   "kind": "set|date|duration|boolean|text|unknown",
   "value": <list of short strings for set | "YYYY-MM-DD" for date | ISO 8601 duration like "P10Y", "P6M", "P45D", "PT1H" | true/false | a short text | null>,
   "text": "one or two sentences for a person, naming the document and the article, section or page",
   "evidence": [{"passage": <number>, "quote": "<copied exactly from that passage>"}]}"""


def _plain(text: str) -> str:
    text = unicodedata.normalize("NFKD", (text or "").lower())
    return "".join(c for c in text if not unicodedata.combining(c))


def _tokens(text: str) -> list[str]:
    """Words for the search: lower case, no accents, no filler words, long words cut to a common stem."""
    out = []
    for word in re.findall(r"[a-z0-9]+", _plain(text)):
        if word in STOP or (len(word) < 3 and not word.isdigit()):
            continue
        out.append(word if word.isdigit() or len(word) <= 6 else word[:6])
    return out


def _squash(text: str) -> str:
    return re.sub(r"\s+", " ", _plain(text)).strip()


def _loose(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", _plain(text)).strip()


@lru_cache(maxsize=1)
def _corrections() -> dict[tuple[int, int | None], list[tuple[str, str, str]]]:
    """(article, paragraph) -> [(old wording, new wording, corrigendum point)], read from the corrigendum itself."""
    from atlas.corpus.chunker import load

    found: dict[tuple[int, int | None], list[tuple[str, str, str]]] = {}
    for chunk in load():
        if chunk.source != "CORR":
            continue
        match = FOR_READ.search(chunk.text)
        if match:
            paragraph = int(match.group(2)) if match.group(2) else ORDINAL.get((match.group(3) or "").lower())
            found.setdefault((int(match.group(1)), paragraph), []).append(
                (match.group(4).strip(), match.group(5).strip(), chunk.locator))
    return found


def corrected(chunk) -> tuple[str, str]:
    """The text of a piece with the corrigendum applied, and the mark that says what was changed ("" if nothing)."""
    if chunk.source != "REG":
        return chunk.text, ""
    place = re.match(r"Art\.\s*(\d+)(?:\((\d+)\))?", chunk.locator or "")
    if not place:
        return chunk.text, ""
    article, paragraph = int(place.group(1)), int(place.group(2)) if place.group(2) else None
    text, marks = chunk.text, []
    for (art, par), changes in _corrections().items():
        if art != article or (par is not None and paragraph is not None and par != paragraph):
            continue
        for old, new, point in changes:
            if old in text and new not in text:
                text = text.replace(old, new)
                marks.append(f"{point}: '{old}' now reads '{new}'")
    return text, ("corrected by the corrigendum (" + "; ".join(marks) + ")") if marks else ""


@lru_cache(maxsize=1)
def _index():
    """Every piece of the registered documents, long ones cut into windows, with the word counts the search uses."""
    from atlas.corpus.chunker import load

    units, counts, seen = [], [], {}
    for chunk in load():
        if chunk.source == "CORR":
            continue   # its content is applied to the Regulation's text, and cited from there
        text, mark = corrected(chunk)
        starts = range(0, max(1, len(text) - WINDOW + STEP), STEP) if len(text) > WINDOW else [0]
        for start in starts:
            piece = text[start:start + WINDOW]
            words: dict[str, int] = {}
            for token in _tokens(f"{chunk.locator} {piece}"):
                words[token] = words.get(token, 0) + 1
            units.append((chunk, piece, mark))
            counts.append(words)
            for token in words:
                seen[token] = seen.get(token, 0) + 1
    average = sum(sum(c.values()) for c in counts) / max(1, len(counts))
    return units, counts, seen, average


def _place(text: str) -> str:
    words = {"article": "art", "articolo": "art", "allegato": "annex", "parte": "part", "punto": "point",
             "riga": "row"}
    return " ".join(words.get(w, w) for w in re.sub(r"[^a-z0-9]+", " ", _plain(text)).split())


NAMES = (("REG", r"2023/1230|machinery regulation|regolamento macchine"),
         ("DIR", r"2006/42|machinery directive|direttiva macchine"),
         ("DLGS71", r"81/2008|81/08|article 71|art\. ?71|articolo 71"), ("DLGSALLVII", r"annex vii|allegato vii"),
         ("DM2011", r"11 april 2011|11 aprile 2011|ministerial decree|decreto ministeriale|\bdm\b"),
         ("inail-guide", r"\binail guid"), ("igea-equipment", r"\bigea\b"),
         ("ur5e-manual", r"\bur5e\b"), ("ur10e-manual", r"\bur10e\b"), ("nanoscan3-manual", r"nanoscan"),
         ("mastar-manual", r"ma ?star"), ("robot-cell-sheet", r"robot cell|cella robot"),
         ("unict-guideline", r"\bunict\b"), ("univpm-guideline", r"\bunivpm\b"))
ACT = re.compile(r"eu-(?:dir|reg)-(\d{4})-(\d+)")


def named_sources(question: str) -> set[str]:
    """The registered documents a question names: by the number of an act, or by the name of a machine or guide."""
    low = _plain(question)
    found = {source for source, pattern in NAMES if re.search(pattern, low)}
    from atlas.corpus.chunker import load

    for source in {c.source for c in load()}:
        match = ACT.fullmatch(source)
        if match and re.search(rf"\b{match.group(1)}/{match.group(2)}\b|\b{match.group(2)}/{match.group(1)}\b", low):
            found.add(source)
    return found


def passages(question: str, top: int = PASSAGES, sources: set[str] | None = None,
             also: list[tuple[str, str]] | None = None, translate: bool = True, named_by: str = "") -> list[tuple]:
    """The pieces closest to the question by their words (BM25), best first. A piece filed under a place the
    question names ("Article 53(1)") moves up. At most three windows of the same piece."""
    from atlas.agent.answer import PLACE, _other_language

    units, counts, seen, average = _index()
    asked = set(_tokens(f"{question} {_other_language(question) if translate else ''}"))
    named = [_place(m.group(0)) for m in PLACE.finditer(question)]
    documents = named_sources(f"{question} {named_by}")
    scored = []
    for i, words in enumerate(counts):
        chunk = units[i][0]
        if sources is not None and chunk.source not in sources:
            continue
        length = sum(words.values())
        score = 0.0
        for token in asked & words.keys():
            idf = math.log(1 + (len(counts) - seen[token] + 0.5) / (seen[token] + 0.5))
            score += idf * words[token] * 2.2 / (words[token] + 1.2 * (0.25 + 0.75 * length / average))
        if score and named:
            place = _place(chunk.locator)
            if any(place == n or place.startswith(n + " ") for n in named):
                score *= 2.0
        if score and documents:   # a document the question names moves up; an act it does not name moves down
            if chunk.source in documents:
                score *= 1.6
            elif ACT.fullmatch(chunk.source):
                score *= 0.5
        if score:
            scored.append((score, i))
    chosen, per_piece = [], {}
    wanted = {(source, _place(locator)) for source, locator in (also or [])[:8]}
    if wanted:   # the pieces the fact store answered from are read too, so the two readings can be compared
        best = {}
        for score, i in scored:
            chunk = units[i][0]
            if (chunk.source, _place(chunk.locator)) in wanted and score > best.get(chunk.id, (0, 0))[0]:
                best[chunk.id] = (score, i)
        for _, i in sorted(best.values(), reverse=True)[:5]:
            chosen.append(units[i])
            per_piece[units[i][0].id] = 3   # one window of each is enough
    top += len(chosen)
    per_source: dict[str, int] = {}
    for _, i in sorted(scored, reverse=True):
        chunk = units[i][0]
        if per_piece.get(chunk.id, 0) >= 3 or per_source.get(chunk.source, 0) >= (PER_SOURCE + 3 if chunk.source in documents else PER_SOURCE):
            continue
        per_piece[chunk.id] = per_piece.get(chunk.id, 0) + 1
        per_source[chunk.source] = per_source.get(chunk.source, 0) + 1
        chosen.append(units[i])
        if len(chosen) >= top:
            break
    return chosen


PLAN = """A question about machines at work (EU machinery law, Italian law on work equipment, guidance, manuals
of specific machines, a company's list of lifting devices) could not be answered from the passages found by its own
words. Break it into the lookups needed to answer it: each lookup is one thing to find in the documents (a
definition, the article that sets a duty, the list an annex gives, the date an article applies from, what a manual
declares about a machine, the row of a table).
Return JSON only: {"lookups": ["<search words for one lookup>", ...]} with 2 to 4 lookups. Write each lookup as
the words the document itself would use, in English and in Italian together, naming the act, the article or annex
and the machine when the question names them. Do not answer the question."""


def lookups(question: str) -> list[str]:
    out = llm.chat([{"role": "system", "content": PLAN}, {"role": "user", "content": question}],
                   temperature=0, max_tokens=500)
    found = _reply(out.get("text") or "").get("lookups")
    return [str(x) for x in found if isinstance(x, str) and x.strip()][:4] if isinstance(found, list) else []


def passages_in_depth(question: str, also: list[tuple[str, str]] | None = None) -> list[tuple]:
    """A second, wider search: the question is broken into lookups, each lookup brings its own passages, and the
    passages found by the question's own words follow. No piece twice."""
    chosen, seen = [], set()

    def add(units: list[tuple]) -> None:
        for unit in units:
            key = (unit[0].id, unit[1][:80])
            if key not in seen:
                seen.add(key)
                chosen.append(unit)

    for lookup in lookups(question):
        add(passages(f"{lookup}", top=5, also=None, translate=False, named_by=question))
    add(passages(question, top=8, also=also))
    return chosen[:26]


def _reply(text: str) -> dict:
    match = re.search(r"\{.*\}", text or "", re.DOTALL)
    if not match:
        return {}
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _numbers(text: str) -> set[str]:
    words = {"one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6", "ten": "10", "twelve": "12",
             "fifteen": "15", "twenty": "20", "thirty": "30", "forty-five": "45", "sixty": "60",
             "un": "1", "uno": "1", "una": "1", "due": "2", "tre": "3", "quattro": "4", "cinque": "5", "sei": "6",
             "dieci": "10", "dodici": "12", "quindici": "15", "venti": "20", "trenta": "30", "quarantacinque": "45",
             "sessanta": "60", "annual": "1", "annuale": "1", "annually": "1", "yearly": "1", "biennale": "2",
             "biennial": "2", "triennale": "3", "triennial": "3", "monthly": "1", "mensile": "1", "daily": "1",
             "semestrale": "6", "half-yearly": "6", "hour": "1", "ora": "1"}
    plain = _plain(text)
    return set(re.findall(r"\d+", plain)) | {n for w, n in words.items() if re.search(rf"\b{w}\b", plain)}


def derivable(value: str, written: list, numbers: set[str]) -> bool:
    """A date given as the answer must be written in the sentences, or be worked out from a written date in one
    plain step: the day before or after it ("until the day before", "from the day after"), or that date moved by
    a whole number of years or months that the sentences state ("every four years", "within 18 months")."""
    from datetime import timedelta

    try:
        day = date.fromisoformat(value)
    except ValueError:
        return False
    for start in written:
        if day == start or abs((day - start).days) == 1:
            return True
        months = (day.year - start.year) * 12 + day.month - start.month
        if day.day == start.day and months and (str(abs(months)) in numbers
                                                or (months % 12 == 0 and str(abs(months) // 12) in numbers)):
            return True
    return False


def check(kind: str, value, evidence: list, shown: list[tuple]) -> tuple[list[tuple], str]:
    """The same gate as the store: every quote is in its passage; a date or a number given as the answer is
    written in a quote. Returns the (piece, quote) pairs that hold and, when the answer falls, why."""
    held = []
    for item in evidence if isinstance(evidence, list) else []:
        if not isinstance(item, dict) or not isinstance(item.get("passage"), int) or isinstance(item.get("passage"), bool):
            continue
        number, quote = item["passage"], str(item.get("quote") or "")
        if not 0 <= number < len(shown) or len(quote.strip()) < 8:
            continue
        chunk, piece, _ = shown[number]
        if _squash(quote) in _squash(piece) or (len(_loose(quote)) >= 20 and _loose(quote) in _loose(piece)):
            held.append((chunk, quote.strip()))
    if not held:
        return [], "no sentence pointed at was found in its passage"
    quoted = " ".join(q for _, q in held)
    if kind == "date":
        from atlas.agent.answer import _dates

        if not derivable(str(value), _dates(quoted), _numbers(quoted)):
            return [], f"the date {value} is neither written in the sentences pointed at nor worked out from them"
    if kind == "duration":
        digits = re.findall(r"\d+", str(value))
        if digits and not set(digits) & _numbers(quoted):
            twelfths = {str(int(d) * 12) for d in digits} | {str(int(d) // 12) for d in digits if int(d) % 12 == 0}
            if not twelfths & _numbers(quoted):
                return [], f"the period {value} is not written in the sentences pointed at"
    return held, ""


def answer(question: str, day: date | None = None, mode: str = "B", lang: str = "en",
           sources: set[str] | None = None, also: list[tuple[str, str]] | None = None,
           deep: bool = False, finder=None) -> Answer:
    from atlas.agent.answer import ITALIAN, UNKNOWN, typed

    if day is None and os.getenv("ATLAS_TODAY"):
        day = date.fromisoformat(os.environ["ATLAS_TODAY"])
    day = day or date.today()
    if finder is not None:   # another way to find the passages (e.g. by similarity); same reading, same gate
        shown = [(chunk, corrected(chunk)[0][:WINDOW * 2], corrected(chunk)[1]) for chunk in finder(question)
                 if chunk.source != "CORR"]
    else:
        shown = passages_in_depth(question, also) if deep else passages(question, sources=sources, also=also)
    numbered = "\n\n".join(
        f"[{i}] {chunk.source}, {chunk.locator} — rank: {RANK.get(chunk.layer, chunk.layer)}"
        + (f" — {mark}" if mark else "") + f"\n{piece}" for i, (chunk, piece, mark) in enumerate(shown))
    out = llm.chat([{"role": "system", "content": SYSTEM + (ITALIAN if lang == "it" else "")},
                    {"role": "user", "content": f"Today is {day.isoformat()}.\nQuestion: {question}\n\nPassages:\n{numbered}"}],
                   temperature=0, max_tokens=3000)
    data = _reply(out.get("text") or "")
    kind = str(data.get("kind") or "")
    if re.match(r"\s*(who|chi)\b", question, re.I) and isinstance(data.get("value"), list):
        kind = "text"   # "who" is answered by one sentence naming every body, not by a list
        data["value"] = "; ".join(str(v) for v in data["value"])
    value = typed(kind, data.get("value"))
    held, why = check(kind, value, data.get("evidence"), shown) if value is not None else ([], "")
    text = data.get("text") or UNKNOWN.get(lang, UNKNOWN["en"])
    if value is not None and not held:
        value, text = None, f"{UNKNOWN.get(lang, UNKNOWN['en'])} ({why})"
    elif value is None:
        text = data.get("text") or UNKNOWN.get(lang, UNKNOWN["en"])
    marks = {chunk.id: mark for chunk, _, mark in shown}
    steps = [Step(text=f"Read on demand: {chunk.source}, {chunk.locator}"
                       + (f" ({marks.get(chunk.id)})" if marks.get(chunk.id) else ""),
                  triples=[], quote=quote, locator=f"{chunk.source}, {chunk.locator}", statement_id=None)
             for chunk, quote in (held if value is not None else [])]
    usage = out.get("usage") or {}
    return Answer(question=question, mode=mode, value=value, text=text, steps=steps,
                  tokens=(usage.get("prompt_tokens") or 0) + (usage.get("completion_tokens") or 0))


# ---- the third reading: a search through the documents, under the same gate ----------------------------------
FOLDER = Path(__file__).resolve().parents[2] / "runtime" / "atlas_search" / "docs"
SEARCH = SYSTEM.replace(
    "using ONLY the numbered passages given. Each passage is headed by its document, its place and its rank.",
    "using ONLY the documents in the current folder, one text file per document; README.md lists them with their "
    "rank. Use your tools (Glob, Grep, Read) to find and read what you need: search in English and in Italian, "
    "follow references from one article or annex to another, and read the whole section before you rely on it."
).replace("- Use only the passages.", "- Use only the files.").replace(
    '"evidence": [{"passage": <number>, "quote": "<copied exactly from that passage>"}]}',
    '"evidence": [{"file": "<file name>", "quote": "<copied exactly from that file, one sentence or one table row>"}]}'
).replace("Return JSON only, with the reasoning first:",
          "When you have the answer, or are sure the files do not state it, reply with JSON only, nothing before or "
          "after, with the reasoning first:")


@lru_cache(maxsize=1)
def _folder() -> str:
    """Every registered document as one text file, the Regulation with the corrigendum already applied and marked.
    Returns a stamp of the content (the search is cached under it)."""
    import hashlib

    from atlas.corpus.chunker import load

    by_source: dict[str, list] = {}
    for chunk in load():
        by_source.setdefault(chunk.source, []).append(chunk)
    FOLDER.mkdir(parents=True, exist_ok=True)
    index = ["# Documents", "", "| File | Rank | Sections |", "|---|---|---|"]
    stamp = hashlib.sha256()
    for source, chunks in sorted(by_source.items()):
        lines = [f"# {source}", "", f"Rank: {RANK.get(chunks[0].layer, chunks[0].layer)}.", ""]
        for chunk in chunks:
            body, mark = corrected(chunk)
            lines += [f"## {chunk.locator}", ""] + ([f"[{mark}]", ""] if mark else []) + [body, ""]
        content = "\n".join(lines)
        stamp.update(content.encode("utf-8"))
        target = FOLDER / f"{source}.md"
        if not target.exists() or target.read_text(encoding="utf-8") != content:
            target.write_text(content, encoding="utf-8")
        index.append(f"| {source}.md | {RANK.get(chunks[0].layer, chunks[0].layer)} | {len(chunks)} |")
    (FOLDER / "README.md").write_text("\n".join(index) + "\n", encoding="utf-8")
    return stamp.hexdigest()[:16]


def search(question: str, day: date | None = None, mode: str = "B", lang: str = "en") -> Answer:
    """The documents are searched freely by a model with read-only tools; what it brings back passes the same
    gate as every other reading: each sentence it points at must be found in a registered piece of that document,
    and a date or a period given as the answer must be written in those sentences."""
    from atlas.agent.answer import UNKNOWN, typed
    from atlas.corpus.chunker import load

    if day is None and os.getenv("ATLAS_TODAY"):
        day = date.fromisoformat(os.environ["ATLAS_TODAY"])
    day = day or date.today()
    out = llm.search_agent(SEARCH, f"Today is {day.isoformat()}.\nQuestion: {question}", FOLDER, stamp=_folder())
    found = re.findall(r"\{.*\}", out.get("text") or "", re.DOTALL)
    data = _reply(found[-1]) if found else {}
    kind = str(data.get("kind") or "")
    if re.match(r"\s*(who|chi)\b", question, re.I) and isinstance(data.get("value"), list):
        kind, data["value"] = "text", "; ".join(str(v) for v in data["value"])
    value = typed(kind, data.get("value"))
    shown, pointed = [], []
    if value is not None:
        pieces: dict[str, list] = {}
        for chunk in load():
            pieces.setdefault(chunk.source, []).append(chunk)
        for item in data.get("evidence") if isinstance(data.get("evidence"), list) else []:
            if not isinstance(item, dict):
                continue
            source, quote = str(item.get("file") or "").removesuffix(".md"), str(item.get("quote") or "")
            wanted = _squash(quote)
            for chunk in pieces.get(source, []) if len(wanted) >= 8 else []:
                body, mark = corrected(chunk)
                if wanted in _squash(body) or (len(_loose(quote)) >= 20 and _loose(quote) in _loose(body)):
                    pointed.append({"passage": len(shown), "quote": quote})
                    shown.append((chunk, body, mark))
                    break
    held, why = check(kind, value, pointed, shown) if value is not None else ([], "")
    text = data.get("text") or UNKNOWN.get(lang, UNKNOWN["en"])
    if value is not None and not held:
        value, text = None, f"{UNKNOWN.get(lang, UNKNOWN['en'])} ({why})"
    marks = {chunk.id: mark for chunk, _, mark in shown}
    steps = [Step(text=f"Found by search: {chunk.source}, {chunk.locator}"
                       + (f" ({marks.get(chunk.id)})" if marks.get(chunk.id) else ""),
                  triples=[], quote=quote, locator=f"{chunk.source}, {chunk.locator}", statement_id=None)
             for chunk, quote in (held if value is not None else [])]
    usage = out.get("usage") or {}
    return Answer(question=question, mode=mode, value=value, text=text, steps=steps, basis="search",
                  tokens=(usage.get("prompt_tokens") or 0) + (usage.get("completion_tokens") or 0))
