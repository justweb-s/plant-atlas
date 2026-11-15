"""Owner: Core. Repeated extraction errors turned into rules of code, measured on the extraction itself.

The second reader (atlas.ontology.verify) re-read 345 current facts and did not pass 117. Read one by one,
those failures fall into a few types; each type with enough cases is one small pure function here:

  a FIX   (statement, chunk_text) -> Statement or None   rebuilds the fact from the text, deterministically;
  a CHECK (statement, chunk_text) -> reason or None      flags a fact as wrong by pattern.

No model is called by any rule. A fixed fact goes through Store.write_statement like every other fact, keeps
its subject and relation, is asserted by "code:learned_rules" and names the fact it replaces in conflicts_with.

Nothing is applied by running this module. It writes a proposal and its measurements:
    python -m atlas.strategies.learned_rules --dry     print the numbers only
    python -m atlas.strategies.learned_rules           write ontology/B/rounds/round3-rules.json and rules_log.json
    python -m atlas.strategies.learned_rules --spot    re-read up to 30 fixed facts with the second reader
apply(path) and revert(path) exist for the coordinator; neither is called from here.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

from atlas.ontology.statements import CONDITION_MARKERS, Statement, Store, norm

ROOT = Path(__file__).resolve().parents[2]
FOLDER = ROOT / "ontology" / "B"
PROPOSAL = FOLDER / "rounds" / "round3-rules.json"
LOG = FOLDER / "rules_log.json"
PART_NAME = "learned_rules.json"
PREFIX = "learned_rules-"
ASSERTED_BY = "code:learned_rules"
CLOSE_DAY = "2026-11-14"
MAX_VALUE = 900          # a rebuilt value longer than this is not a value any more: the rule gives up
MAX_QUOTE = 2000

# ---- reading the text ---------------------------------------------------------------------------------------
# Where a sentence or a list item ends: a semicolon, a full stop before a new sentence (or the end), a bullet.
_END = re.compile(r";|\.(?=\s+(?:\d+(?:\.\d+)*\.\s+)?[A-Z(‘“]|\s*$)|\s•\s|”(?=\s|$)")
_ITEM = re.compile(r"^\(([a-z])\)\s+")
_SUBITEM = re.compile(r"^(\d+)\.(\d+)\.\s+")
_POINT = re.compile(r"^(?:\d+(?:\.\d+)*\.|\([a-z]\))\s+")
_LIST_OPEN = re.compile(r":\s+(?=\(a\)\s)")
_TRAIL = " ;.,"


def _locate(quote: str, value: str) -> tuple[str, int, int]:
    """(normalised quote, start, end) of the value inside it; start is -1 when the value is not there."""
    q, v = norm(quote), norm(value)
    at = q.find(v) if v else -1
    return q, at, at + len(v)


def _end_of_clause(q: str, start: int) -> int:
    """Index where the sentence or list item that holds q[start] ends (the terminator is left out)."""
    found = _END.search(q, start)
    return found.start() if found else len(q)


def _start_of_sentence(q: str, at: int) -> int:
    """Index where the sentence that holds q[at] starts."""
    start = 0
    for found in re.finditer(r"[.;:]\s+(?=(?:\d+(?:\.\d+)*\.\s+)?[A-Z(‘“])", q[:at]):
        start = found.end()
    return start


def _list_after(quote: str, chunk_text: str) -> str:
    """The quote, lengthened to the end of the lettered list it opens ("...: (a) ...; (b) ...") when the list goes
    on in the chunk after the quote. The quote itself when there is no such list or it would be too long."""
    q, text = norm(quote), norm(chunk_text)
    at = text.find(q)
    if at < 0:
        return q
    rest = text[at + len(q):]
    opens = q.endswith(":") and re.match(r"\s*\(a\)\s", rest)
    goes_on = _LIST_OPEN.search(q) and re.match(r"\s*(?:or\s+|and\s+)?\([b-z]\)\s", rest)
    if not (opens or goes_on):
        return q
    stop = re.search(r"\.(?=\s+(?:\d+(?:\.\d+)*\.\s+)?[A-Z‘“]|\s*$)", rest)
    longer = q + (rest[:stop.end()] if stop else rest)
    return longer if len(longer) <= MAX_QUOTE else q


def _clause_at_marker(quote: str) -> str:
    """The clause that starts at the first condition word of the quote, up to its comma."""
    found = CONDITION_MARKERS.search(quote)
    if not found:
        return ""
    return re.split(r"[,;:.](?:\s|$)", norm(quote[found.start():]), maxsplit=1)[0].strip()


def _words(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


def _rebuilt(old: Statement, **changes) -> Statement | None:
    """A copy of the fact with the changes, or None when nothing a reader would see has changed."""
    new = old.model_copy(update=changes)
    if new.object_as_written != old.object_as_written:
        new.object = new.object_as_written
        if old.predicate == "requiresProcedure":
            from atlas.strategies.repair import short_form
            new.object_normalised = short_form(new.object_as_written)
        elif old.object_normalised:
            new.object_normalised = norm(new.object_as_written).lower()
    if CONDITION_MARKERS.search(new.quote) and not new.condition.strip():
        new.condition = _clause_at_marker(new.quote)   # a longer quote may bring a condition word with it
    same = (_words(new.object_as_written) == _words(old.object_as_written)
            and _words(new.condition) == _words(old.condition))
    return None if same or len(norm(new.object_as_written)) > MAX_VALUE else new


def _whole_clause(s: Statement, chunk_text: str, drop_lead: re.Pattern | None = None) -> Statement | None:
    """The fact with its value lengthened to the end of the sentence or item it was cut from."""
    q, start, end = _locate(s.quote, s.object_as_written)
    if start < 0:
        return None
    quote = _list_after(q, chunk_text)
    in_list = _LIST_OPEN.search(quote, start) or (quote.endswith(":") and quote is q)
    if _LIST_OPEN.search(quote, start):
        stop = len(quote)                                  # a definition or duty that is a list: all its items
    else:
        stop = max(_end_of_clause(quote, start), end)
    if in_list and quote.rstrip().endswith(":"):
        return None                                        # the list is not in the chunk: nothing to rebuild from
    value = quote[start:stop].strip(_TRAIL)
    if drop_lead:
        value = drop_lead.sub("", value).strip(_TRAIL)
    if not value or norm(value) not in quote:
        return None
    return _rebuilt(s, object_as_written=value, quote=quote if quote != q else s.quote)


# ---- the fixes ----------------------------------------------------------------------------------------------
_MEANS = re.compile(r"^(?:.{0,80}?[’'”\"]\s+)?means:?\s+(?:[—–-]\s+)?")   # "‘term’ means ..." or "means: ..."


def fix_definition_whole(s: Statement, chunk_text: str) -> Statement | None:
    """FIX. Error: a definition stored up to its first comma or its first few words ("means:", "any natural or
    legal person who", "a component or equipment, not attached to the lifting machinery"), so the qualifiers that
    make it a definition are lost. 22 of the 117 failures (17 "dropped a condition", 5 "not stated").
    The value becomes the definition up to the end of its sentence; when the definition is a lettered list the
    quote is lengthened to the end of that list."""
    if s.predicate != "definedAs":
        return None
    return _whole_clause(s, chunk_text, drop_lead=_MEANS)


def fix_obligation_whole(s: Statement, chunk_text: str) -> Statement | None:
    """FIX. Error: an obligation stored as its first words ("shall ensure that", "bears at least a designation",
    "cooperate with that authority"), so what must be done, for whom and within which limits is lost.
    33 of the 117 failures (27 "dropped a condition" whose missing words follow the value in the same sentence,
    6 "not stated" for an empty fragment). The value becomes the duty up to the end of its sentence or item.
    Narrowed after measuring: lengthening every cut duty changed 72 facts the second reader had passed against
    40 it had not, so the rule now fires only when the value stops on a connective (the 6 empty fragments).
    `wide=True` gives the first version, kept for whoever wants to measure it again."""
    return _obligation_whole(s, chunk_text, wide=False)


def fix_obligation_whole_wide(s: Statement, chunk_text: str) -> Statement | None:
    """FIX, not in FIXES. The first version of fix_obligation_whole: every duty cut before the end of its sentence.
    Dropped from the proposal: more facts changed among those the second reader passed than among its failures."""
    return _obligation_whole(s, chunk_text, wide=True)


def _obligation_whole(s: Statement, chunk_text: str, wide: bool) -> Statement | None:
    if s.predicate != "hasObligation" or _ITEM.match(norm(s.quote)):
        return None                                        # a list item is rebuilt by fix_list_item
    if not wide and not _DANGLING.search(norm(s.object_as_written).rstrip(" ,;")):
        return None
    return _whole_clause(s, chunk_text)


_LEAD = (r"for at least|for a period|for a minimum|where|when|before|after|further to|if|upon|within|in the case|"
         r"qualora|quando|prima di|dopo|entro|nel caso|ove")
_LEAD_AT = re.compile(rf"(?:^|,\s+|\b(?:shall|must),?\s+)({_LEAD})\b", re.IGNORECASE)
_MODAL = re.compile(r"\b(?:shall|must|deve|devono)\b")


def fix_condition_whole(s: Statement, chunk_text: str) -> Statement | None:
    """FIX. Error: the clause that says when a duty holds is stored cut at its first comma ("where the machinery
    presents a risk to the health and safety of persons" without "and, where appropriate, domestic animals and
    property, and, where applicable, to the environment") or not at all when it sits between the verb and the
    duty ("Importers shall, for at least 10 years after ..., keep a copy"). 9 of the 117 failures.
    The condition becomes the whole leading clause of the sentence, when the old condition is empty or part of it."""
    if s.predicate != "hasObligation":
        return None
    q, start, _ = _locate(s.quote, s.object_as_written)
    if start <= 0:
        return None
    first = _start_of_sentence(q, start)
    head = q[first:start]
    lead = _LEAD_AT.search(head)
    if not lead:
        return None
    begin = lead.start(1)
    modal = _MODAL.search(q, first + begin)
    if modal and first + modal.start() - first <= len(head) + 12 and "," in head[begin:]:
        modal = None if modal.start() - first > len(head) + 12 else modal
    if modal and _MODAL.search(head[:begin]):
        modal = None                                       # the verb came first: "shall, for at least ..., keep"
    if modal:                    # "Where ..., the importer shall": up to the main clause
        stop = head.rfind(",", begin, max(begin, modal.start() - first))
    else:                                                  # "shall, for at least ..., keep": up to the next comma
        stop = head.find(",", begin)
    if stop <= begin:
        return None
    clause = re.sub(r"\s+(?:and|or)$", "", head[begin:stop].strip(_TRAIL))
    old = norm(s.condition).strip('"').lower()
    if old and old not in clause.lower():
        return None                                        # the fact has another condition: not ours to replace
    if len(clause) > 400 or len(clause.split()) < 3 or re.search(r"[—–;:]", head[begin:]):
        return None
    return _rebuilt(s, condition=clause, condition_quote="")


_TOKEN = re.compile(r"[a-zà-ù]{4,}")
_NUMBER_ONLY = re.compile(r"^(?:\d+(?:\.\d+)*\.?|\([a-z]\))$")


def fix_listed_item_whole(s: Statement, chunk_text: str) -> Statement | None:
    """FIX. Error: an entry of a list of categories stored as its number alone ("3.", "4.1.") or as its first words
    ("Circular saws (single- or multi-blade)"), so the qualifier that limits the category ("for woodworking",
    "with reciprocating motion", "incorporating a compression mechanism", "of the following types") is lost.
    9 of the 117 failures. The value becomes the whole entry, without its number.
    Narrowed after measuring: a number alone passes the second reader when the condition and the subject hold the
    whole entry (21 passed facts), so the rule fires only when a word of the entry is in no field of the fact."""
    if s.predicate != "listedIn":
        return None
    q, start, end = _locate(s.quote, s.object_as_written)
    if start < 0:
        return None
    if not (start == 0 or _POINT.match(q)) or re.match(r"^\s*Annex\b", norm(s.object_as_written)):
        return None                                        # the value is a reference inside a sentence: leave it
    if _NUMBER_ONLY.match(norm(s.object_as_written)):
        start = end
        if _POINT.match(q[start:].lstrip()):
            return None                                    # "17. (a) ...": a point that is itself a list
    body = q[start:]
    lead = len(body) - len(body.lstrip())
    marker = _POINT.match(body.lstrip())
    if marker:
        lead += marker.end()
    if _POINT.match(body[lead:]):
        return None                                        # "17. (a) ...": a point that is itself a list
    start += lead
    stop = _end_of_clause(q, start)
    value = q[start:stop].strip(_TRAIL + ":")
    if not value or len(value.split()) < 2:
        return None
    kept = set(_TOKEN.findall(f"{s.object_as_written} {s.condition} {s.subject}".lower()))
    if not [w for w in _TOKEN.findall(value.lower()) if w not in kept]:
        return None                                        # every word of the entry is already in the fact
    return _rebuilt(s, object_as_written=value)


_FLOOR = re.compile(r"(?:\b(?:at least|not less than|no less than|a minimum of|almeno|non meno di)\s+)$", re.IGNORECASE)
_MORE = re.compile(r"^(?:\s+of\s+[^,.;:]{0,80}?)?\s+and(?:,?\s+in any event,?)?\s+for\s+"
                   r"(?:at least|not less than)\s+\w+\s+(?:years?|months?|weeks?|days?)", re.IGNORECASE)
_FROM = re.compile(r"^\s+((?:after|following|from|starting from|dalla|dallo|dalle|dal|dall['’]|dopo|a decorrere d\w+|"
                   r"a partire d\w+)\b[^,.;:]*(?:,\s+(?:in the case|nel caso)[^,.;:]*,[^,.;:]*)?)", re.IGNORECASE)
_HAS_NUMBER = re.compile(r"\d|\b(?:one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|thirty|"
                         r"un|una|due|tre|quattro|cinque|sei|sette|otto|nove|dieci|dodici|quindici|venti|trenta|"
                         r"quarantacinque|sessanta|novanta|lifetime|durata)\b", re.IGNORECASE)


def fix_period_floor_and_start(s: Statement, chunk_text: str) -> Statement | None:
    """FIX. Error: a retention period or time limit stored without its floor or without the moment it runs from
    ("at least 10 years" without "after they supplied ...", "for the expected lifetime" without "and in any event
    for at least 10 years after the placing on the market", "entro dodici mesi" without "dalla data di ...").
    7 of the 117 failures. The floor words are put back into the value and the starting point, read from the
    words that follow the period in the same sentence, goes into the condition."""
    if s.predicate not in ("retentionPeriod", "hasTimeLimit"):
        return None
    q, start, end = _locate(s.quote, s.object_as_written)
    if start < 0 or not _HAS_NUMBER.search(s.object_as_written):
        return None
    floor = _FLOOR.search(q[:start])
    if floor:
        start = floor.start()
    more = _MORE.match(q[end:])
    if more:
        end += more.end()
    begins = _FROM.match(q[end:])
    point = re.sub(r"\s+(?:or|and|e|o)$", "", begins.group(1).strip(_TRAIL)) if begins else ""
    condition = norm(s.condition).strip('"')
    if point and point.lower() not in condition.lower():
        if len(point.split()) < 3:
            point = ""
        else:
            condition = f"{condition}; {point}" if condition and condition.lower() not in point.lower() else point
    else:
        condition = s.condition
    return _rebuilt(s, object_as_written=q[start:end].strip(_TRAIL), condition=condition)


_FIX_LIST_RELATIONS = ("requiresProcedure", "hasObligation", "listedIn")


def _chapeau(q: str, text: str) -> tuple[str, str]:
    """(the sentence that opens the list an item belongs to, the item without its mark); ('', '') when the quote
    is not an item of a list opened by a sentence ending with a colon."""
    inside = _LIST_OPEN.search(q)
    if inside and not _ITEM.match(q):                      # the quote holds the opening sentence and item (a)
        opening = q[_start_of_sentence(q, inside.start()):inside.start() + 1]
        body = q[inside.end():]
        return opening, _ITEM.sub("", body)[:_end_of_clause(_ITEM.sub("", body), 0)]
    letter, sub = _ITEM.match(q), _SUBITEM.match(q)
    if not (letter or sub):
        return "", ""
    at = text.find(q)
    if at < 0:
        return "", ""
    first = r"\(a\)\s" if letter else rf"{sub.group(1)}\.1\.\s"
    opens = [m for m in re.finditer(rf":\s+(?={first})", text[:at + 8])]
    if not opens:
        return "", ""
    colon = opens[-1].start()
    between = text[colon:at]
    if re.search(r"\.\s+(?:\d+\.\s+)?[A-Z]", between):     # a sentence ended in between: the list was over
        return "", ""
    opening = text[_start_of_sentence(text, colon):colon + 1]
    body = q[(letter or sub).end():]
    return opening, body[:_end_of_clause(body, 0)]


def fix_list_item(s: Statement, chunk_text: str) -> Statement | None:
    """FIX. Error: an item of a list stored cut from the sentence that opens the list and often cut short itself:
    "(b) EU type-examination (module B)" without "followed by ... (module C)" and without "shall apply one of the
    following procedures"; "(a) any refusal, restriction, suspension or withdrawal" without "A notified body shall
    inform the notifying authority of the following"; "4.1." without "Band-saws ... of the following types".
    26 of the 117 failures (14 requiresProcedure, 8 hasObligation, 4 listedIn).
    The value becomes the whole item and the opening sentence becomes the condition (and the condition quote)."""
    if s.predicate not in _FIX_LIST_RELATIONS:
        return None
    if s.predicate == "listedIn" and re.match(r"\s*Annex\b", s.object_as_written):
        return None                                        # the value is the annex that lists it: nothing was cut
    q, text = norm(s.quote), norm(chunk_text)
    opening, item = _chapeau(q, text)
    item = item.strip(_TRAIL)
    if not opening or not item or norm(s.object_as_written).strip(_TRAIL) not in item + "." \
            and not _NUMBER_ONLY.match(norm(s.object_as_written)):
        return None
    opening = re.sub(r"^(?:\d+(?:\.\d+)*\.\s+)+", "", opening).strip()
    if len(opening.split()) < 4 or len(opening) > 700 or opening not in text:
        return None
    old = norm(s.condition).strip('"')
    said = opening.rstrip(":")
    if not old or old.rstrip(":").lower() in said.lower() or old.lower() in item.lower():
        condition = said
    else:
        condition = f"{said}; {old}"
    return _rebuilt(s, object_as_written=item, condition=condition, condition_quote=opening)


# ---- the checks ---------------------------------------------------------------------------------------------
_IN_FORCE = re.compile(r"\benter(?:s|ed)? into force\b|\bentry into force\b|\bentra(?:no)? in vigore\b|"
                       r"\bentrata in vigore\b", re.IGNORECASE)
_APPLIES = re.compile(r"\bappl(?:y|ies|ied|icable|ication)\b|\bsi applica(?:no)?\b|\btrova(?:no)? applicazione\b",
                      re.IGNORECASE)


def check_entry_into_force(s: Statement, chunk_text: str) -> str | None:
    """CHECK. Error: the sentence on the entry into force of an act stored as the date from which it applies
    (they are two different dates in these acts). 1 of the 117 failures; kept because the pattern is exact."""
    if s.predicate != "appliesFrom":
        return None
    if _IN_FORCE.search(s.quote) and not _APPLIES.search(s.quote):
        return "the quote states the entry into force, not the date of application"
    return None


_ACCOMPANY = re.compile(r"accompan|supplied with|provided with|delivered with|come with|comes with|together with|"
                        r"\baffix|\bbear|\bmarked\b|corred|accompagn|allegat|unitamente|fornit|munit", re.IGNORECASE)


def check_accompany_not_stated(s: Statement, chunk_text: str) -> str | None:
    """CHECK. Error: a sentence on what the instructions must contain, or a heading that names them, stored as
    "the instructions must accompany the machinery". 6 of the 117 failures ("not stated").
    The fact is flagged when its quote has no word of accompanying, supplying or affixing."""
    if s.predicate != "mustAccompany":
        return None
    if not _ACCOMPANY.search(s.quote):
        return "the quote says what a document contains or names it; it does not say that it must accompany anything"
    return None


_DANGLING = re.compile(r"(?::|\b(?:that|who|whom|which|whose|of|the|a|an|to|and|or|by|for|with|in|on|from|means|"
                       r"shall|must|shall ensure|shall verify|che|di|il|la|per|con|deve|devono))$")
_TEXT_RELATIONS = ("definedAs", "hasObligation", "becomesManufacturer", "listedIn", "mustAccompany",
                   "requiresProcedure", "requiresMeasure", "addressesRisk", "integratorResponsibleFor",
                   "putIntoServiceOnlyWhen", "maintenanceRule", "safeguardedSpaceRule", "requiresCheckAfter")


def check_empty_value(s: Statement, chunk_text: str) -> str | None:
    """CHECK. Error: a value that carries nothing: punctuation, a list number alone ("3.", "17."), or words that
    stop on a connective ("means:", "shall ensure that", "any natural or legal person who").
    17 of the 117 failures had such a value (6 list numbers, 11 dangling fragments); most are rebuilt by a fix,
    this check flags what is left."""
    if s.predicate not in _TEXT_RELATIONS:
        return None
    value = norm(s.object_as_written)
    if s.predicate == "listedIn" and re.fullmatch(r"\d+(?:\.\d+)*\.?", value):
        return None                                        # the number of the point that lists the category
    if not re.search(r"[^\W\d_]{2}", value) or _NUMBER_ONLY.match(value):
        return "the value is only a number or punctuation"
    if _DANGLING.search(value.rstrip(" ,;")):
        return "the value stops on a connective and does not carry the meaning"
    return None


FIXES = (fix_list_item, fix_definition_whole, fix_obligation_whole, fix_listed_item_whole, fix_condition_whole,
         fix_period_floor_and_start)
CHECKS = (check_entry_into_force, check_accompany_not_stated, check_empty_value)
# A check closes a fact only when the value itself carries nothing; a wrong relation on a true sentence is flagged.
CLOSING_REASONS = ("the value is only a number or punctuation",)


# ---- recovering what the gate refused -----------------------------------------------------------------------
def recover_missing_condition(rejected: dict) -> Statement | None:
    """FIX for refused facts. The gate refused 53 facts for "missing_condition": the quote has a condition word
    ("if" 44 times, "se" 6, "except", "unless", "purché") and the model left the condition empty.
    The condition becomes the clause that starts at that word. Proposed apart, never applied by apply()."""
    s = Statement(**rejected)
    clause = _clause_at_marker(s.quote)
    if len(clause.split()) < 3 or not re.match(r"(?i)(if|unless|except|provided that|se|salvo|qualora|purch[eé])\b", clause):
        return None
    if re.search(r"\bSE\b", s.quote) and clause.startswith("SE"):
        return None                                        # "SE" of a company form, not the Italian "se"
    return s.model_copy(update={"condition": clause, "asserted_by": ASSERTED_BY, "id": "", "status": "proposed"})


# ---- running the rules over the store -----------------------------------------------------------------------
def scratch_store() -> Store:
    from atlas.corpus.chunker import load
    from atlas.ontology.statements import ChunkCorpus

    return Store(ChunkCorpus(list(load())))


def candidates(store: Store) -> list[Statement]:
    """The current facts a model extracted (facts written by code are already whole)."""
    return [s for s in store.statements if s.status == "current" and s.asserted_by.startswith("strategy_b")
            and not s.asserted_by.endswith(":corrigendum")]


def rebuild(s: Statement, chunk_text: str, fixes=FIXES) -> tuple[Statement | None, list[str]]:
    """Run the fixes in order, each on the result of the one before. Returns the rebuilt fact and the rules used."""
    fact, used = s, []
    for fix in fixes:
        try:
            out = fix(fact, chunk_text)
        except (re.error, IndexError, ValueError):
            out = None
        if out is not None:
            fact, used = out, used + [fix.__name__]
    return (fact if used else None), used


def flags(s: Statement, chunk_text: str, checks=CHECKS) -> list[tuple[str, str]]:
    return [(check.__name__, reason) for check in checks if (reason := check(s, chunk_text))]


def files_of(folder: Path = FOLDER) -> dict[str, str]:
    """statement id (as the built store names it) -> the file that holds it."""
    where: dict[str, str] = {}
    main = folder / "statements.json"
    if main.exists():
        for item in json.loads(main.read_text(encoding="utf-8"))["statements"]:
            where[item["id"]] = "statements.json"
    for part in sorted((folder / "parts").glob("*.json")):
        payload = json.loads(part.read_text(encoding="utf-8"))
        for item in payload.get("statements", []) if isinstance(payload, dict) else []:
            name = item["id"] if item["id"].startswith(part.stem) else f"{part.stem}-{item['id']}"
            where[name] = part.name
    return where


def propose(store: Store | None = None, fixes=FIXES, checks=CHECKS) -> dict:
    """Every rule over every candidate fact. Returns the proposal and, per fact, what each rule did."""
    if store is None:
        from atlas.ontology.build import raw_store
        store = raw_store("B")
    gate = Store(store.corpus)
    where = files_of() if store.path is None or store.path.parent == FOLDER else {}
    statements, close, flag_only, trace, refused = [], [], [], {}, []
    seen: dict[tuple, str] = {}
    for old in candidates(store):
        text = store.corpus.section(old.source_doc, old.anchor) or ""
        new, used = rebuild(old, text, fixes)
        written = None
        if new is not None:
            key = (new.subject, new.predicate, norm(new.object_as_written), norm(new.condition), new.anchor)
            if key in seen:                                # two cut facts rebuilt into the same whole fact
                close.append({"id": old.id, "file": where.get(old.id, "statements.json"), "reason": "+".join(used)})
                trace[old.id] = {"fixed_by": used, "new_id": seen[key], "flags": []}
                continue
            draft = new.model_copy(update={"id": f"{PREFIX}{len(gate.statements) + 1:04d}", "status": "proposed",
                                           "asserted_by": ASSERTED_BY, "conflicts_with": old.id, "confirmations": 0})
            written = gate.write_statement(draft)
            if written is None:
                refused.append({"id": old.id, "rules": used, "reason": gate.rejections[-1]["reason"]})
            else:
                written.status = "current"
                seen[key] = written.id
                statements.append(written)
                close.append({"id": old.id, "file": where.get(old.id, "statements.json"), "reason": "+".join(used)})
        found = flags(written or old, text, checks)
        trace[old.id] = {"fixed_by": used if written else [], "new_id": written.id if written else "",
                         "flags": [name for name, _ in found]}
        for name, reason in found:
            if reason in CLOSING_REASONS and not written:
                close.append({"id": old.id, "file": where.get(old.id, "statements.json"), "reason": name})
            else:
                flag_only.append({"id": written.id if written else old.id, "rule": name, "reason": reason})
    recovered = [s.model_dump(mode="json") for r in store.rejections if r.get("reason") == "missing_condition"
                 and (s := recover_missing_condition(r["statement"])) and gate.write_statement(s.model_copy())]
    return {"statements": statements, "close": close, "flag_only": flag_only, "trace": trace, "refused": refused,
            "recovered_not_applied": recovered}


# ---- measuring ----------------------------------------------------------------------------------------------
_WORD = re.compile(r"[a-zà-ù]{4,}")
_STOP = set("passage claim omits omitted omit condition conditions states stated says value that this with from "
            "only also which their there other does scope restriction qualifier fragment lacks lacking carry "
            "meaning requires required though while where when what whom have been being broader narrower "
            "limit limits adds added drops dropped keeps kept definition defines defined relation subject".split())


def asked_for(why: str, old: Statement, new: Statement) -> bool:
    """Does the rebuilt fact now hold words that the second reader's reason names and the old fact lacked?
    A proxy read by code, so the count can be reproduced; the report says how it compares with reading them."""
    before = set(_WORD.findall(f"{old.object_as_written} {old.condition}".lower()))
    after = set(_WORD.findall(f"{new.object_as_written} {new.condition}".lower()))
    named = set(_WORD.findall(why.lower())) - _STOP
    stems = {w[:6] for w in after - before}
    return any(w[:6] in stems for w in named)


def measure(proposal: dict, store: Store, verdicts: dict) -> dict:
    from atlas.ontology.verify import passes

    by_id = {s.id: s for s in store.statements}
    new_by_id = {s.id: s for s in proposal["statements"]}
    failed = {k for k, v in verdicts.items() if not passes(v)}
    passed = set(verdicts) - failed
    rules = {f.__name__: {"kind": "FIX"} for f in FIXES} | {c.__name__: {"kind": "CHECK"} for c in CHECKS}
    for row in rules.values():
        row.update(fired_whole_store=0, on_failures=0, failures_addressed=0, on_passed=0,
                   failure_ids=[], passed_ids=[])
    addressed, alarms, flagged_failures = set(), set(), set()
    for fact_id, did in proposal["trace"].items():
        new = new_by_id.get(did["new_id"])
        for name in did["fixed_by"] + did["flags"]:
            row = rules[name]
            row["fired_whole_store"] += 1
            if fact_id in passed:
                row["on_passed"] += 1
                row["passed_ids"].append(fact_id)
                alarms.add(fact_id)
            if fact_id in failed:
                row["on_failures"] += 1
                row["failure_ids"].append(fact_id)
                if row["kind"] == "CHECK":
                    flagged_failures.add(fact_id)
                    if verdicts[fact_id].get("states") != "yes":
                        row["failures_addressed"] += 1
                        addressed.add(fact_id)
                elif new is not None and asked_for(verdicts[fact_id].get("why", ""), by_id[fact_id], new):
                    row["failures_addressed"] += 1
                    addressed.add(fact_id)
    closing_checks = sum(1 for c in proposal["close"] if c["reason"].startswith("check_"))
    return {"rules": rules,
            "totals": {"second_reader_failures": len(failed), "second_reader_passed": len(passed),
                       "failures_fired_on": len({i for r in rules.values() for i in r["failure_ids"]}),
                       "failures_addressed": len(addressed), "failures_flagged": len(flagged_failures),
                       "false_alarms_on_passed": len(alarms),
                       "facts_changed_whole_store": len(proposal["statements"]),
                       "old_facts_closed_by_a_fix": len(proposal["close"]) - closing_checks,
                       "facts_closed_by_a_check": closing_checks,
                       "facts_flagged_only": len(proposal["flag_only"]),
                       "rebuilt_but_refused_by_the_gate": len(proposal["refused"]),
                       "refused_facts_recovered_not_applied": len(proposal["recovered_not_applied"]),
                       "candidates": len(candidates(store))}}


def write_proposal(proposal: dict, path: Path = PROPOSAL) -> None:
    payload = {"statements": [s.model_dump(mode="json") for s in proposal["statements"]],
               "close": proposal["close"], "flag_only": proposal["flag_only"],
               "recovered_not_applied": proposal["recovered_not_applied"]}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")


def spot_check(proposal: dict, store: Store, verdicts: dict, limit: int = 30) -> dict:
    """Up to `limit` rebuilt facts re-read by the second reader, spread over the rules, half of them outside
    the facts it had already seen. The only place of this module that calls a model; never run by the rules."""
    from atlas.ontology import verify

    by_rule: dict[str, list[Statement]] = {}
    for s in proposal["statements"]:
        rule = proposal["trace"][s.conflicts_with]["fixed_by"][0]
        by_rule.setdefault(rule, []).append(s)
    for facts in by_rule.values():                          # seen and unseen facts in turn
        seen = [s for s in facts if s.conflicts_with in verdicts]
        unseen = [s for s in facts if s.conflicts_with not in verdicts]
        facts[:] = [s for pair in zip(seen, unseen) for s in pair] + seen[len(unseen):] + unseen[len(seen):]
    picked: list[Statement] = []
    while len(picked) < limit and any(by_rule.values()):
        for facts in by_rule.values():
            if facts and len(picked) < limit:
                picked.append(facts.pop(0))
    rows = []
    for s in picked:
        verdict = verify.verify(s, store.corpus.section(s.source_doc, s.anchor) or s.quote)
        before = verdicts.get(s.conflicts_with)
        rows.append({"new_id": s.id, "replaces": s.conflicts_with,
                     "rules": proposal["trace"][s.conflicts_with]["fixed_by"],
                     "before": ("passed" if verify.passes(before) else "failed") if before else "not read",
                     "after": "passed" if verify.passes(verdict) else "failed", "why": verdict.get("why", "")})
    return {"calls": len(rows), "cost_usd": round(verify.spent_usd(), 3),
            "passed": sum(r["after"] == "passed" for r in rows),
            "failed": sum(r["after"] == "failed" for r in rows),
            "of_which_failed_before": sum(r["before"] == "failed" for r in rows),
            "failed_before_now_passed": sum(r["before"] == "failed" and r["after"] == "passed" for r in rows),
            "not_read_before": sum(r["before"] == "not read" for r in rows),
            "not_read_before_now_passed": sum(r["before"] == "not read" and r["after"] == "passed" for r in rows),
            "rows": rows}


# ---- applying and undoing (for the coordinator; not called here) ---------------------------------------------
def _edit_fact(text: str, fact_id: str, changes: dict[str, tuple[str, str]]) -> tuple[str, bool]:
    """Change fields of one fact in the text of a store file without touching anything else (layout included).
    `changes` is field -> (JSON literal expected now, JSON literal to write)."""
    head = re.search(rf'(?<!\\)"id"\s*:\s*"{re.escape(fact_id)}"', text)
    if not head:
        return text, False
    following = re.search(r'(?<!\\)"id"\s*:', text[head.end():])
    stop = head.end() + following.start() if following else len(text)
    body = text[head.end():stop]
    for field, (now, then) in changes.items():
        body, done = re.subn(rf'((?<!\\)"{field}"\s*:\s*){re.escape(now)}(?=\s*[,}}])', lambda m: m.group(1) + then,
                             body, count=1)
        if not done:
            return text, False
    return text[:head.end()] + body + text[stop:], True


def _file_of(folder: Path, name: str) -> Path:
    return folder / name if name == "statements.json" else folder / "parts" / name


def _local_ids(fact_id: str, name: str) -> list[str]:
    stem = Path(name).stem
    return [fact_id] + ([fact_id[len(stem) + 1:]] if fact_id.startswith(stem + "-") else [])


def apply(path: Path = PROPOSAL, folder: Path = FOLDER) -> dict:
    """Apply a proposal: its statements go to parts/learned_rules.json and each fact of "close" gets status
    "closed" and in_force_to 2026-11-14 in its own file. What was there before is written next to the new
    statements (key "undo"), so revert() can put every file back exactly."""
    path, folder = Path(path), Path(folder)
    payload = json.loads(path.read_text(encoding="utf-8"))
    part = folder / "parts" / PART_NAME
    if part.exists():
        raise FileExistsError(f"{part} exists: revert the earlier application first")
    texts: dict[str, str] = {}
    undo, missed = [], []
    for entry in payload["close"]:
        name = entry["file"]
        if name not in texts:
            texts[name] = _file_of(folder, name).read_text(encoding="utf-8")
        for local in _local_ids(entry["id"], name):
            found = re.search(rf'(?<!\\)"id"\s*:\s*"{re.escape(local)}"', texts[name])
            if not found:
                continue
            rest = texts[name][found.end():]
            nxt = re.search(r'(?<!\\)"id"\s*:', rest)
            body = rest[:nxt.start()] if nxt else rest
            status = re.search(r'(?<!\\)"status"\s*:\s*("[a-z_]+")', body)
            until = re.search(r'(?<!\\)"in_force_to"\s*:\s*(null|"[0-9-]+")', body)
            if not status or not until:
                continue
            texts[name], done = _edit_fact(texts[name], local, {"status": (status.group(1), '"closed"'),
                                                                "in_force_to": (until.group(1), f'"{CLOSE_DAY}"')})
            if done:
                undo.append({"id": local, "file": name, "status": status.group(1), "in_force_to": until.group(1)})
                break
        else:
            missed.append(entry["id"])
    if missed:
        raise KeyError(f"facts to close not found, nothing written: {missed[:5]}")
    for name, text in texts.items():
        json.loads(text)                                    # still a readable store before anything is written
    for name, text in texts.items():
        _file_of(folder, name).write_text(text, encoding="utf-8")
    part.parent.mkdir(parents=True, exist_ok=True)
    part.write_text(json.dumps({"statements": payload["statements"], "rejections": [], "undo": undo,
                                "applied_from": path.name}, indent=1, ensure_ascii=False), encoding="utf-8")
    return {"added": len(payload["statements"]), "closed": len(undo), "files": sorted(texts)}


def revert(path: Path = PROPOSAL, folder: Path = FOLDER) -> dict:
    """Undo apply(): every closed fact gets back the status and in_force_to it had, and the part is removed."""
    folder = Path(folder)
    part = folder / "parts" / PART_NAME
    if not part.exists():
        return {"reopened": 0, "removed": False}
    undo = json.loads(part.read_text(encoding="utf-8")).get("undo", [])
    texts: dict[str, str] = {}
    for entry in undo:
        name = entry["file"]
        if name not in texts:
            texts[name] = _file_of(folder, name).read_text(encoding="utf-8")
        texts[name], done = _edit_fact(texts[name], entry["id"], {"status": ('"closed"', entry["status"]),
                                                                   "in_force_to": (f'"{CLOSE_DAY}"', entry["in_force_to"])})
        if not done:
            raise KeyError(f"cannot reopen {entry['id']} in {name}: the file changed since apply()")
    for name, text in texts.items():
        _file_of(folder, name).write_text(text, encoding="utf-8")
    part.unlink()
    return {"reopened": len(undo), "removed": True}


def main(argv: list[str]) -> None:
    from atlas.ontology.build import raw_store
    from atlas.ontology.verify import load_verdicts

    store = raw_store("B")
    verdicts = load_verdicts()
    proposal = propose(store)
    numbers = measure(proposal, store, verdicts)
    short = {name: {k: v for k, v in row.items() if not k.endswith("_ids")} for name, row in numbers["rules"].items()}
    print(json.dumps({"rules": short, "totals": numbers["totals"]}, indent=1))
    if "--dry" in argv:
        return
    log = json.loads(LOG.read_text(encoding="utf-8")) if LOG.exists() else {}
    log.update(numbers)
    log["refused_by_the_gate"] = proposal["refused"]
    if "--spot" in argv:
        log["spot_check"] = spot_check(proposal, store, verdicts)
        print(json.dumps({k: v for k, v in log["spot_check"].items() if k != "rows"}))
    write_proposal(proposal)
    LOG.write_text(json.dumps(log, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    import sys

    main(sys.argv[1:])
