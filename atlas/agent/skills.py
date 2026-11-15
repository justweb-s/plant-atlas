"""Owner: Core. Procedural graphs: the agent's work as explicit graphs, stored as files and walked by code.

A skill is a file in atlas/skills/: nodes (lookup, script, decision, answer, unknown) and labelled edges.
`route` chooses one skill, or none, from the relation query the agent already builds and the skill's cues.
`run` walks the graph node by node with registered Python functions and returns the value, its kind, a text
composed from the facts, the facts used and a trace of every node and every edge taken. A graph that ends
in `unknown` gives no answer: the caller falls back to the model path.
"""
from __future__ import annotations

import json
import re
import time
from datetime import date
from pathlib import Path

from atlas import llm
from atlas.agent import answer as base
from atlas.contracts import Answer, Step

FOLDER = Path(__file__).resolve().parents[1] / "skills"
PLAIN = {"verificationInterval": "must be verified every", "appliesFrom": "applies from", "repealedFrom": "is repealed from",
         "placingAllowedUntil": "may be placed on the market until", "retentionPeriod": "must be kept for",
         "hasTimeLimit": "has the time limit", "hasReach": "has a reach of", "hasMaxPayload": "has a maximum payload of",
         "requiresPeriodicCheck": "must be checked every", "listedIn": "is listed in", "verifiedBy": "is verified by",
         "hasObligation": "has the obligation", "hasStoppingLimit": "has the stopping limit",
         "protectiveFieldRange": "has a protective field range of"}
NEGATED = re.compile(r"\b(not|no longer|prohibit\w*|forbid\w*|banned|illegal)\b", re.I)
WANTS_DATE = re.compile(r"from which date|from what date|what date|which date|\bwhen\b|until when", re.I)
WANTS_YES_NO = re.compile(r"\b(can|may|is|are|does|do|will)\b", re.I)
QUANTITY = ("hasReach", "hasMaxPayload", "hasStoppingLimit", "protectiveFieldRange")
REGISTRY: dict = {}


def node(fn):
    REGISTRY[fn.__name__] = fn
    return fn


# ---- the files ---------------------------------------------------------------------------------------------
def parse(text: str) -> dict:
    try:
        import yaml
        return yaml.safe_load(text)
    except ImportError:   # the files are JSON-compatible YAML: json reads them once the comment lines are gone
        return json.loads("\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#")))


def load(folder: Path = FOLDER) -> list[dict]:
    """Every skill of the folder, in priority order."""
    skills = [parse(path.read_text(encoding="utf-8")) for path in sorted(folder.glob("*.yaml"))]
    return sorted(skills, key=lambda s: (s.get("priority", 99), s["name"]))


def check(skill: dict) -> list[str]:
    """What is wrong with a skill file; empty when it can be walked."""
    ids = [n["id"] for n in skill.get("nodes", [])]
    problems = [f"edge {e} names a node that does not exist" for e in skill.get("edges", [])
                if e.get("from") not in ids or e.get("to") not in ids]
    problems += [f"node {n['id']} names a function that is not registered" for n in skill.get("nodes", [])
                 if n.get("fn") and n["fn"] not in REGISTRY]
    problems += [f"node {n['id']} has no function" for n in skill.get("nodes", [])
                 if n["kind"] in ("lookup", "script", "decision", "answer") and not n.get("fn")]
    if len(set(ids)) != len(ids):
        problems.append("two nodes share an id")
    return problems


# ---- the context: the facts in force and the relation query the agent already builds -----------------------
_CONTEXT: dict = {}


def context(question: str, store, day: date) -> dict:
    key = (question, id(store), day)
    if _CONTEXT.get("key") != key:
        facts = [s for s in store.as_of(day) if s.status == "current"]
        matched, query = base.graph_query(question, facts)   # the one model call of the router
        asked = base._dates(question)
        matched, _ = base.one_regime(question, matched, facts, asked)
        usage = (next(iter(base._QUERY_OUT.values()), {}) or {}).get("usage") or {}
        relations = [r for r in (query.get("relations") or []) if isinstance(r, str)]
        terms = query.get("subject_terms") if isinstance(query.get("subject_terms"), list) else []
        _CONTEXT.clear()
        _CONTEXT.update(key=key, question=question, store=store, day=day, facts=facts, matched=matched, query=query,
                        relations=relations, asked=asked, on=asked[0] if asked else day,
                        wanted=base._words(question) | base._words(" ".join(str(t) for t in terms)),
                        place=base._place(str(query.get("place") or "")),
                        tokens=(usage.get("prompt_tokens") or 0) + (usage.get("completion_tokens") or 0))
    return dict(_CONTEXT)


def route(question: str, store, day: date) -> dict | None:
    """One decision: the first enabled skill, in priority order, whose relations hold the first relation of
    the query and whose cues the question carries. None when no skill fits."""
    ctx = context(question, store, day)
    first = ctx["relations"][0] if ctx["relations"] else ""
    for skill in load():
        when = skill.get("when", {})
        if not skill.get("enabled", True) or first not in when.get("relations", []):
            continue
        if not re.search(when.get("cues", ""), question, re.I):
            continue
        if when.get("not_cues") and re.search(when["not_cues"], question, re.I):
            continue
        if when.get("needs") == "position" and not base.POSITION.search(question):
            continue
        if when.get("needs") == "place" and not (ctx["place"] and str(ctx["query"].get("wants")) == "all"):
            continue
        return skill
    return None


# ---- the executor ------------------------------------------------------------------------------------------
def run(skill: dict, question: str, store, day: date):
    """Walks the graph. Returns (value, kind, text, used facts, trace); value None when it ends in `unknown`."""
    started = time.perf_counter()
    ctx = context(question, store, day)
    ctx.update(value=None, kind="unknown", text="", used=[], why="", model_calls=0)
    nodes = {n["id"]: n for n in skill["nodes"]}
    seen: dict[str, dict] = {}
    taken: list[list[str]] = []
    current = skill["nodes"][0]["id"]
    for _ in range(len(nodes) + 1):
        spec = nodes[current]
        t0 = time.perf_counter()
        label, output, fact_ids = "", spec["does"], []
        if spec.get("fn"):
            label, output, fact_ids = REGISTRY[spec["fn"]](ctx)
        elif spec["kind"] == "unknown":
            output = ctx["why"] or spec["does"]
        seen[current] = {"id": current, "kind": spec["kind"], "does": spec["does"], "status": "run",
                         "output": str(output)[:240], "fact_ids": [i for i in fact_ids if i],
                         "ms": round((time.perf_counter() - t0) * 1000, 2)}
        if spec["kind"] in ("answer", "unknown"):
            break
        out = [e for e in skill["edges"] if e["from"] == current]
        edge = next((e for e in out if e.get("when") == label), None) or next((e for e in out if not e.get("when")), None)
        if edge is None:   # a label the file does not draw: the graph stops without an answer
            ctx["why"] = f"node {current} returned '{label}', which no edge carries"
            break
        taken.append([current, edge["to"], edge.get("when", "")])
        current = edge["to"]
    if nodes[current]["kind"] != "answer":
        ctx.update(value=None, kind="unknown", used=[], text=ctx["why"] or "This graph ended without an answer.")
    trace = {"skill": skill["name"],
             "nodes": [seen.get(n["id"]) or {"id": n["id"], "kind": n["kind"], "does": n["does"], "status": "skipped",
                                              "output": "", "fact_ids": [], "ms": 0.0} for n in skill["nodes"]],
             "edges_taken": taken, "model_calls": ctx["model_calls"],
             "ms": round((time.perf_counter() - started) * 1000, 2)}
    return ctx["value"], ctx["kind"], ctx["text"], ctx["used"], trace


def as_text(trace: dict) -> str:
    """A trace on a few lines, for a person."""
    lines = [f"skill {trace['skill']} ({trace['ms']} ms, {trace['model_calls']} model calls inside the graph)"]
    labels = {a: (b, label) for a, b, label in trace["edges_taken"]}
    for n in trace["nodes"]:
        arrow = f" --[{labels[n['id']][1] or 'next'}]--> {labels[n['id']][0]}" if n["id"] in labels else ""
        lines.append(f"  {n['id']} ({n['kind']}, {n['status']}): {n['output']}"
                     + (f" facts {n['fact_ids']}" if n["fact_ids"] else "") + arrow)
    return "\n".join(lines)


def try_answer(question: str, store, day: date, mode: str = "B") -> Answer | None:
    """The hook of answer(): the Answer of the skill that fits, or None (no skill, unknown, or not grounded)."""
    skill = route(question, store, day)
    if skill is None:
        return None
    value, kind, text, used, trace = run(skill, question, store, day)
    if value is None:
        return None
    value, used, _ = base.grounded(kind, value, list(used), question)
    if value is None:
        return None
    path = " > ".join(n["id"] for n in trace["nodes"] if n["status"] == "run")
    steps = [Step(text=f"{s.subject}: {s.predicate} = {s.object_as_written}"
                       + (f" (condition: {s.condition})" if s.condition else ""),
                  triples=[(s.subject, s.predicate, s.object)], quote=s.quote,
                  locator=f"{s.source_doc}, {s.anchor}", statement_id=s.id) for s in used]
    if steps:
        steps[0].text = f"[skill {skill['name']}: {path}] {steps[0].text}"
    found = Answer(question=question, mode=mode, value=value, text=text, steps=steps,
                   tokens=context(question, store, day)["tokens"])
    found.trace = trace   # not a field of the dataclass: a batch run reads it and writes the traces file
    return found


# ---- shared helpers of the nodes ---------------------------------------------------------------------------
def _cover(ctx: dict, s) -> tuple[int, float]:
    """How well a fact's subject matches what the question is about: shared words, and their share of the subject."""
    bag = base._words(s.subject)
    shared = bag & ctx["wanted"]
    return len(shared), (len(shared) / len(bag) if bag else 0.0)


def _cite(s) -> str:
    return f"{s.source_doc}, {s.anchor}"


def _sentence(s, value: str | None = None) -> str:
    condition = f", on the condition: {s.condition}" if s.condition else ""
    return (f"{s.subject} {PLAIN.get(s.predicate, re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', s.predicate).lower())} "
            f"{value or s.object_as_written}{condition} (source: {_cite(s)}).")


def _normal(s) -> str:
    return (s.object_normalised or s.object or "").strip()


def _single(ctx: dict, candidates: list, same) -> tuple[object | None, str]:
    """The best match, unless its subject does not match or another candidate with a different value matches
    as well: then the graph does not choose."""
    top = candidates[0]
    shared, share = _cover(ctx, top)
    if shared < 2 and share < 0.5:
        return None, "no exact subject"
    rivals = [s for s in candidates[1:] if not same(s, top) and _cover(ctx, s) >= (shared, share)]
    if rivals:
        return None, "ambiguous"
    return top, ""


# ---- verification_interval ---------------------------------------------------------------------------------
STAGES = (("kind", "is lifting equipment", ("not mapped",)), ("capacity", "capacity", ("capacity",)),
          ("sector", "sector", ("sector",)), ("age", "built in", ("year of construction", "built in")),
          ("row", "Annex VII row", ()))


@node
def lookup_device(ctx):
    from atlas.strategies.plant import device_records

    named = {int(n) for n in base.POSITION.findall(ctx["question"])}
    device = next((d for d in device_records(ctx["facts"]) if d["position"] in named), None)
    if device is None:
        ctx["why"] = "no device facts for the position asked"
        return "none", ctx["why"], []
    ctx["device"] = device
    shown = ", ".join(f"{k} {device.get(k, '?')}" for k in ("kind", "capacity_kg", "year_built", "sector"))
    return "found", f"device {device['position']}: {shown}", list(device["facts"].values())


@node
def lookup_annex_rows(ctx):
    from atlas.ontology.rules import read_row, verification_interval

    annex = [s for s in ctx["facts"] if s.predicate == "verificationInterval"]
    rows = [s for s in annex if read_row(s)]
    if not rows:
        ctx["why"] = "no Annex VII row for lifting equipment among the facts"
        return "none", ctx["why"], []
    ctx["rule"] = verification_interval(ctx["device"], annex, ctx["on"])   # the rule itself, applied once
    return "found", f"{len(rows)} rows for lifting equipment", [s.id for s in rows]


def _stage(ctx, name: str, passed: str, failed: str):
    """What the rule (rules.verification_interval) found at one of its stages: its reason, or why it stopped."""
    rule = ctx["rule"]
    order = [stage for stage, _, _ in STAGES]
    marker = next(m for stage, m, _ in STAGES if stage == name)
    reason = next(((i, text) for i, text in rule.get("because", []) if marker in text), None)
    if rule.get("interval"):
        return passed, (reason[1] if reason else "not needed by the rows that match"), [reason[0]] if reason else []
    why = rule.get("why", "")
    stopped = next((stage for stage, _, words in STAGES if any(w in why for w in words)), "row")
    if order.index(name) < order.index(stopped):
        return passed, "passed", []
    ctx["why"] = f"device {ctx['device']['position']}: {why}"
    return failed, why, []


@node
def rule_kind(ctx):
    return _stage(ctx, "kind", "mapped", "not mapped")


@node
def rule_capacity(ctx):
    return _stage(ctx, "capacity", "above the limit", "missing or below")


@node
def rule_sector(ctx):
    return _stage(ctx, "sector", "known", "missing")


@node
def rule_age(ctx):
    return _stage(ctx, "age", "decided", "missing or on the edge")


@node
def rule_row(ctx):
    return _stage(ctx, "row", "one row", "no single row")


@node
def answer_interval(ctx):
    rule, device = ctx["rule"], ctx["device"]
    by_id = {s.id: s for s in ctx["facts"]}
    ids = list(dict.fromkeys([i for i, _ in rule["because"]] + list(device["facts"].values())))
    ctx["used"] = [by_id[i] for i in ids if i in by_id]
    ctx["kind"], ctx["value"] = "duration", base.typed("duration", rule["interval"])
    row = by_id.get(rule.get("row_id", ""))
    ctx["text"] = (f"IGEA device {device['position']} must be verified every {ctx['value']} on {ctx['on'].isoformat()}: "
                   + "; ".join(reason for _, reason in rule["because"])
                   + (f" (source: {_cite(row)})" if row else "") + f". {base.ASSUMPTIONS['en']}")
    return "", f"{ctx['value']}", [rule.get("row_id", "")]


# ---- value_on_date -----------------------------------------------------------------------------------------
@node
def lookup_dated(ctx):
    dated = ("appliesFrom", "repealedFrom", "placingAllowedUntil")
    relation = ", ".join(r for r in ctx["relations"] if r in dated)
    found = [s for s in ctx["matched"] if s.predicate in dated and s.predicate in ctx["relations"] and base._fact_day(s)]
    if not found:
        ctx["why"] = "no dated fact of the relation asked matches the subject"
        return "none", ctx["why"], []
    ctx["candidates"] = found
    return "found", f"{len(found)} dated facts of {relation}", [s.id for s in found]


@node
def pick_in_force(ctx):
    top, problem = _single(ctx, ctx["candidates"], lambda a, b: base._fact_day(a) == base._fact_day(b))
    if top is None:
        ctx["why"] = f"dated facts: {problem}"
        return "ambiguous", ctx["why"], []
    ctx["fact"] = top
    replaced = [s for s in ctx["store"].statements if s.status == "closed" and (s.subject, s.predicate) == (top.subject, top.predicate)
                and base._fact_day(s) and base._fact_day(s) != base._fact_day(top)]
    note = "".join(f"; it replaced {s.object} ({_cite(s)}), now closed" for s in replaced)
    return "one in force", f"{top.subject} {top.predicate} {top.object} ({_cite(top)}){note}", [top.id] + [s.id for s in replaced]


@node
def compare_date(ctx):
    fact, question = ctx["fact"], ctx["question"]
    fact_day = base._fact_day(fact)
    if not ctx["asked"]:
        if WANTS_DATE.search(question):
            ctx["kind"], ctx["value"] = "date", fact_day.isoformat()
            return "date asked", f"the date itself: {ctx['value']}", [fact.id]
        ctx["why"] = "the question asks neither for the date nor about a day"
        return "undecided", ctx["why"], []
    asked = ctx["asked"][0]
    if len(ctx["asked"]) > 1 and any(d != fact_day for d in ctx["asked"][1:]) or NEGATED.search(question) \
            or not WANTS_YES_NO.search(question):
        ctx["why"] = "the comparison the question asks for is not one the script decides"
        return "undecided", ctx["why"], []
    # "applies from" holds from its day on; a repeal takes effect on its day; "until" includes its day.
    holds = {"appliesFrom": asked >= fact_day, "repealedFrom": asked < fact_day, "placingAllowedUntil": asked <= fact_day}
    ctx["kind"], ctx["value"] = "boolean", holds[fact.predicate]
    gap = (fact_day - asked).days
    ctx["compared"] = (f"{asked.isoformat()} is the same day as {fact_day.isoformat()}" if gap == 0 else
                       f"{asked.isoformat()} is {abs(gap)} days {'before' if gap > 0 else 'after'} {fact_day.isoformat()}")
    return "day compared", f"{ctx['compared']}: {ctx['value']}", [fact.id]


@node
def answer_dated(ctx):
    fact = ctx["fact"]
    ctx["used"] = [fact]
    if ctx["kind"] == "date":
        ctx["text"] = _sentence(fact, ctx["value"])
    else:
        ctx["text"] = f"{'Yes' if ctx['value'] else 'No'}: {ctx['compared']}. {_sentence(fact, base._fact_day(fact).isoformat())}"
    return "", str(ctx["value"]), [fact.id]


# ---- single_value ------------------------------------------------------------------------------------------
@node
def lookup_relation(ctx):
    relation = ctx["relations"][0] if ctx["relations"] else ""
    found = [s for s in ctx["matched"] if s.predicate == relation]
    if not found:
        ctx["why"] = "no fact of the relation asked matches the subject"
        return "none", ctx["why"], []
    ctx["candidates"] = found
    return "found", f"{len(found)} facts of {relation}", [s.id for s in found]


@node
def choose_subject(ctx):
    top, problem = _single(ctx, ctx["candidates"], lambda a, b: base._canon(_normal(a)) == base._canon(_normal(b)))
    if top is not None and not (base.ISO_DURATION.fullmatch(_normal(top))
                                or (top.predicate in QUANTITY and re.search(r"\d", top.object_as_written))):
        top, problem = None, "no exact subject"   # neither a duration nor a quantity: not this graph's answer
    if top is None:
        ctx["why"] = f"facts of the relation: {problem}"
        return problem, ctx["why"], []
    ctx["fact"] = top
    rank = ctx["store"].rank_of(top) if hasattr(ctx["store"], "rank_of") else 0
    return "one subject", f"{top.subject} = {_normal(top)} ({_cite(top)}, layer {top.layer or '?'}, rank {rank})", [top.id]


@node
def settle_conflict(ctx):
    top, store = ctx["fact"], ctx["store"]
    losers = [s for s in store.statements if s.status == "conflict" and s.conflicts_with == top.id]
    if not losers:
        return "no conflict", "no source in force disagrees", []
    winner, why = store.settle(top, losers[0])
    if winner is not top:   # the store keeps the winner current; anything else is not for this graph to decide
        return "no conflict", "the store's own settlement stands", []
    ctx["settled"] = (f"{_cite(losers[0])} says {losers[0].object_as_written}, but {why}: {_cite(top)} prevails")
    return "settled by authority", ctx["settled"], [s.id for s in losers]


@node
def answer_value(ctx):
    fact = ctx["fact"]
    ctx["used"] = [fact]
    if base.ISO_DURATION.fullmatch(_normal(fact)):
        ctx["kind"], ctx["value"] = "duration", base._canon(_normal(fact).upper())
    else:
        ctx["kind"], ctx["value"] = "text", fact.object_as_written
    ctx["text"] = _sentence(fact, f"{fact.object_as_written} ({ctx['value']})" if ctx["kind"] == "duration" else None)
    if ctx.get("settled"):
        ctx["text"] += f" {ctx['settled'][0].upper()}{ctx['settled'][1:]}."
    return "", str(ctx["value"]), [fact.id]


# ---- members_of --------------------------------------------------------------------------------------------
@node
def lookup_members(ctx):
    relation, place = (ctx["relations"][0] if ctx["relations"] else ""), ctx["place"]
    number = re.fullmatch(r"\d+(?: \d+)+", place)
    found = []
    for s in ctx["facts"] if place else []:
        anchor = base._place(s.anchor)
        if s.predicate == relation and ((f" {place} " in f" {anchor} ") if number else base._under(anchor, place)):
            found.append(s)
    if not found or len(found) > base.FAMILY:
        ctx["why"] = f"{len(found)} facts of {relation} are filed under '{place}'"
        return "none", ctx["why"], []
    ctx["candidates"] = found
    return "found", f"{len(found)} facts of {relation} under {place}", [s.id for s in found]


@node
def dedupe_members(ctx):
    kept: dict[str, object] = {}
    for s in ctx["candidates"]:
        kept.setdefault(base._key(base._item_of(s)), s)
    ctx["members"] = list(kept.values())
    return "", f"{len(ctx['members'])} members after {len(ctx['candidates']) - len(kept)} repeats removed", []


@node
def answer_members(ctx):
    members = ctx["members"]
    ctx["used"] = members
    ctx["kind"], ctx["value"] = "set", [base._item_of(s).strip() for s in members]
    places = ", ".join(dict.fromkeys(_cite(s) for s in members))
    ctx["text"] = (f"{len(members)} items {PLAIN.get(members[0].predicate, 'are filed')} {ctx['query'].get('place')}: "
                   + "; ".join(ctx["value"]) + f" (source: {places}).")
    return "", f"{len(members)} items", [s.id for s in members]


# ---- who_does ----------------------------------------------------------------------------------------------
@node
def lookup_who(ctx):
    """The fact saying who does what the question asks about: the facts of the relation are ranked by how well
    their SUBJECT matches the question's subject, not by their being of the relation. Among equal matches the
    source of higher authority wins; equal matches of equal authority must come from one sentence."""
    relation = ctx["relations"][0] if ctx["relations"] else ""
    scored = sorted(((_cover(ctx, s), -i, s) for i, s in enumerate(ctx["facts"]) if s.predicate == relation),
                    key=lambda row: (row[0], row[1]), reverse=True)
    if not scored or scored[0][0][0] < 2 or scored[0][0][1] < 0.6:
        ctx["why"] = "facts saying who: no fact whose subject is what the question asks about"
        return "none", ctx["why"], []
    best = [s for cover, _, s in scored if cover == scored[0][0]]
    rank = getattr(ctx["store"], "rank_of", None)
    if rank and len(best) > 1:
        top = max(rank(s) for s in best)
        best = [s for s in best if rank(s) == top]
    if len({(s.source_doc, s.quote) for s in best}) > 1:
        ctx["why"] = "facts saying who: several sources of equal authority match the subject equally"
        return "none", ctx["why"], []
    ctx["fact"], ctx["same_sentence"] = best[0], best
    return "found", f"{best[0].subject} {best[0].predicate} {best[0].object_as_written} ({_cite(best[0])})", [s.id for s in best]


@node
def collect_bodies(ctx):
    """Every body the fact's own sentence names: the fact's value, the bodies joined to it by "or" in the quote,
    and the values of the other facts read from the same sentence."""
    fact = ctx["fact"]
    bodies = base.all_bodies(fact.object_as_written, [fact])
    for other in ctx["same_sentence"][1:]:
        if base._key(other.object_as_written) not in base._key(bodies):
            bodies += f"; {other.object_as_written}"
    ctx["bodies"] = bodies
    return "", bodies, [s.id for s in ctx["same_sentence"]]


@node
def answer_who(ctx):
    fact = ctx["fact"]
    ctx["used"] = list(ctx["same_sentence"])
    ctx["kind"], ctx["value"] = "text", ctx["bodies"]
    ctx["text"] = _sentence(fact, ctx["bodies"])
    return "", ctx["value"], [s.id for s in ctx["used"]]


def decide_by_model(ctx, prompt: str, options: list[str]) -> str:
    """For a `decision` node whose script cannot decide: one cached model call, counted and said in the trace."""
    out = llm.chat([{"role": "system", "content": "Choose one of the options. Return only the option.\nOptions: "
                     + " | ".join(options)}, {"role": "user", "content": prompt}], temperature=0, max_tokens=20)
    ctx["model_calls"] += 1
    reply = (out.get("text") or "").strip().lower()
    return next((o for o in options if o.lower() in reply), options[-1])
