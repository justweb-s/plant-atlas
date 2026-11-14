"""Owner: Core. The atlas page: five layers as bands, facts as cards, and six scenes read from the store.

`python -m atlas.ontology.atlas_page` writes ontology/B/atlas.html. The page is self-contained (only the fonts
come from outside) and embeds only the facts its scenes and answers use. Every card is a fact of the store with
its quote, except the cards the page marks as "scenario input" or "not in any document". Links are of two kinds:
stored (conflicts_with of a fact) and derived (put together by a rule or by the scene), and are drawn differently.
"""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

from atlas.ontology import viewer
from atlas.ontology.rules import read_row, verification_interval
from atlas.ontology.viewer import _plain_day, embedded_json, extract_data  # noqa: F401  (extract_data: for the tests)

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "ontology" / "B" / "atlas.html"
TODAY = date(2026, 11, 14)
SCENARIO_LABEL = "scenario input, not from a document"
SCENARIO_ZONE_MM = 1000          # the one declared scenario input of the page
DEVICE, UNKNOWN_DEVICE = 13, 24
ASK_IDS = ("CQ09", "CQ22", "CQ25", "CQ26", "CQ23", "CQ21")
LAYER_TEXT = {
    "law": ("Law", "EU regulation and directive, Italian decrees, a corrigendum"),
    "guidance": ("Guidance", "Guides of public bodies"),
    "manufacturer": ("Manufacturer", "Manuals of two robot arms, a safety scanner, a vehicle lift"),
    "company": ("Company", "Equipment guidelines of two organisations"),
    "plant": ("Plant", "A real list of 24 lifting devices"),
}


def _interval_words(iso: str | None) -> str:
    m = re.fullmatch(r"P(\d+)([YMD])", iso or "")
    if not m:
        return "unknown"
    n, unit = int(m.group(1)), {"Y": "year", "M": "month", "D": "day"}[m.group(2)]
    return f"every {n} {unit}{'s' if n > 1 else ''}"


class _Scene:
    """Collects the cards and links of one variant of a scene and the fact ids it uses."""

    def __init__(self, used: set, label: str, day: str = ""):
        self.used, self.v = used, {"label": label, "date": day, "cards": [], "links": [], "result": {}}

    def fact(self, fid: str, step: int = 0, **kw) -> str:
        self.used.add(fid)
        self.v["cards"].append({"k": fid, "f": fid, "step": step, "state": "in", **kw})
        return fid

    def other(self, key: str, band: str, kind: str, title: str, text: str, step: int = 0, **kw) -> str:
        self.v["cards"].append({"k": key, "band": band, "state": kind, "title": title, "text": text, "step": step, **kw})
        return key

    def link(self, a: str, b: str, kind: str, label: str = "", step: int = 0) -> None:
        self.v["links"].append({"a": a, "b": b, "kind": kind, "label": label, "step": step})

    def result(self, text: str, tone: str = "ok", note: str = "") -> dict:
        self.v["result"] = {"text": text, "tone": tone, "note": note}
        return self.v


def _scene_crane(st, ids, used) -> dict:
    from atlas.strategies.plant import device_records

    device = next(d for d in device_records(st) if d["position"] == DEVICE)
    annex = viewer.annex_facts(st)
    rows = {r["id"]: r for r in map(read_row, annex) if r}
    first = verification_interval(device, annex, TODAY)
    variants = []
    for day in (TODAY, TODAY.replace(year=TODAY.year + 1)):
        res = verification_interval(device, annex, day)
        sc = _Scene(used, str(day.year), _plain_day(day))
        cols = {"kind": 1, "capacity_kg": 2, "year_built": 3, "sector": 4}
        notes = dict((fid, why) for fid, why in res.get("because", []))
        for name, fid in device["facts"].items():
            if fid in ids:
                sc.fact(fid, 0, col=cols.get(name), note=notes.get(fid, ""))
        if res.get("interval"):
            row = sc.fact(res["row_id"], 1, col=1, note=notes.get(res["row_id"], ""))
            for fid in device["facts"].values():
                if fid in ids:
                    sc.link(fid, row, "derived", "", 1)
            text = f"Device {DEVICE}: verification {_interval_words(res['interval'])}."
            tone, note = "ok", "Returned by the verification rule from four plant facts and one row of Annex VII."
        else:
            picked = rows.get(first.get("row_id", ""))
            cands = [r for r in rows.values() if picked and r["type"] == picked["type"] and r["use"] == picked["use"]]
            for i, r in enumerate(cands[:2]):
                sc.fact(r["id"], 1, col=1 + i, state="undecided", tag="candidate row: the rule cannot choose")
                sc.link(device["facts"]["year_built"], r["id"], "derived", "", 1)
            text = f"Device {DEVICE}: unknown. The rule says: {res.get('why', '')}."
            tone, note = "unknown", "The rule does not guess the month of construction."
        if res.get("interval"):
            who = sc.fact("st-1567", 2, col=2)
            days = sc.fact("st-1568", 2, col=3)
            keep = sc.fact("st-1572", 2, col=4)
            sc.link(res["row_id"], who, "derived", "", 2)
            sc.fact("guidance-st-0079", 3, col=2)
            guide = sc.fact("guidance-st-0080", 3, col=3)
            sc.link(days, guide, "derived", "same time limit", 3)
            reg = sc.fact("company-st-0115", 4, col=4)
            sc.link(keep, reg, "derived", "records to keep", 4)
        v = sc.result(text, tone, note)
        v["rule"] = {"interval": res.get("interval"), "row_id": res.get("row_id", ""), "why": res.get("why", ""),
                     "date": day.isoformat()}
        variants.append(v)
    return {"id": "crane", "title": "One crane, five layers",
            "look": f"Follow lifting device {DEVICE} from the plant's own list up to the law and back down to what must be kept.",
            "toggle": "Date", "variants": variants}


def _scene_correction(st, ids, used) -> dict:
    pairs = [(ids[s.conflicts_with], s) for s in st
             if s.status == "current" and s.conflicts_with in ids and ids[s.conflicts_with].status == "closed"]
    day = pairs[0][1].in_force_from
    cites = next((s for s in st if store_layer(s) == "manufacturer" and s.status == "current"
                  and s.predicate == "hasDeclaration" and "2006/42" in (s.object + s.quote)), None)
    repeal = next((new for old, new in pairs if new.predicate == "repealedFrom"), None)
    variants = []
    for after in (False, True):
        sc = _Scene(used, f"After {_plain_day(day)}" if after else f"Before {_plain_day(day)}",
                    _plain_day(day) if after else "before " + _plain_day(day))
        for i, (old, new) in enumerate(pairs):
            if after:
                sc.fact(old.id, 0, pair=f"p{i}", state="out", tag=f"corrected {_plain_day(day)}", compact=True)
                sc.fact(new.id, 1, pair=f"p{i}", compact=True)
                sc.link(old.id, new.id, "stored", "", 1)
            else:
                sc.fact(old.id, 0, pair=f"p{i}", compact=True)
        if cites is not None and repeal is not None:
            sc.fact(cites.id, 2, col=2)
            target = repeal.id if after else repeal.conflicts_with
            sc.link(cites.id, target, "derived", "", 2)
        n = len(pairs)
        text = (f"{n} dates corrected on {_plain_day(day)}. The old values are closed and kept, each linked to the one that replaced it."
                if after else f"{n} dates as the Regulation first printed them.")
        variants.append(sc.result(text, "ok", "The link old to new is stored in the fact (conflicts_with)." if after else ""))
    return {"id": "correction", "title": "The law corrects itself", "cols": {"law": 5},
            "look": "A corrigendum changed nine dates of the Regulation: switch the date and watch the old facts close.",
            "toggle": "Date", "variants": variants}


def store_layer(s) -> str:
    return getattr(s, "layer", "")


def _scene_repeal(st, ids, used, regime) -> dict:
    applies = next(ids[i] for i in regime["applies"] if ids[i].status == "current")
    repealed = next(ids[i] for i in regime["repealed"] if ids[i].status == "current")
    day = date.fromisoformat(repealed.object)
    plain = _plain_day(day)
    old = [s for s in st if s.source_doc in viewer.OLD_REGIME and s.status == "current" and s.predicate == "definedAs"]
    new = [s for s in st if s.source_doc == "REG" and s.status == "current" and s.predicate == "definedAs"]
    pick = lambda xs, words: [next(s for s in xs if w in s.subject.lower()) for w in words   # noqa: E731
                              if any(w in s.subject.lower() for s in xs)]
    old, new = pick(old, ("safety component", "manufacturer"))[:2], pick(new, ("safety component", "machinery"))[:2]
    citing = [s for s in st if s.layer == "manufacturer" and s.status == "current"
              and s.predicate in ("hasDeclaration", "conformsToStandard") and "2006/42" in s.object + s.condition
              and s.source_doc in ("ur5e-manual", "ur10e-manual")][:3]
    variants = []
    for d in (date.fromordinal(day.toordinal() - 1), day):
        after = d >= day
        sc = _Scene(used, _plain_day(d), _plain_day(d))
        sc.fact(repealed.id, 0, col=1, note="the date the Directive is repealed")
        sc.fact(applies.id, 0, col=3, note="the date the Regulation applies")
        for i, s in enumerate(old):
            sc.fact(s.id, 1, col=1 + i, **({"state": "out", "tag": f"repealed from {plain}"} if after else {}))
            sc.link(repealed.id, s.id, "derived", "", 1)
        for i, s in enumerate(new):
            sc.fact(s.id, 1, col=3 + i, **({} if after else {"state": "notyet", "tag": "not yet applicable"}))
            sc.link(applies.id, s.id, "derived", "", 1)
        for i, s in enumerate(citing):
            sc.fact(s.id, 2, col=1 + i, **({"state": "flag", "tag": f"relies on a law repealed from {plain}: review"} if after else {}))
            sc.link(s.id, repealed.id, "derived", "cites the Directive" if i == 0 else "", 2)
        text = (f"From {plain} the Regulation applies and the Directive is repealed. {len(citing)} manufacturer facts that cite the Directive are flagged for review."
                if after else f"One day before: the Directive is in force, the Regulation is published and not yet applicable. Nothing is flagged.")
        variants.append(sc.result(text, "warn" if after else "ok",
                                  "The flag is derived on this page from the two dated facts and from the words of the manufacturer facts. It is not stored."))
    return {"id": "repeal", "title": "The law changes under the machines",
            "look": "Move one day forward: a law is repealed and the manufacturer facts that rely on it are flagged below.",
            "toggle": "Date", "variants": variants}


def _scene_conflict(st, ids, used) -> dict:
    lost = next(s for s in st if s.status == "conflict" and s.conflicts_with in ids)
    won = ids[lost.conflicts_with]
    guides = [s for s in st if s.source_doc == "inail-guide" and s.status == "current" and s.predicate == "hasTimeLimit"
              and s.object_normalised == won.object_normalised and "prima" in s.subject.lower()][:2]
    sc = _Scene(used, "", _plain_day(TODAY))
    sc.fact(lost.id, 0, col=1, state="out", tag="lost to a legislative decree")
    sc.fact(won.id, 1, col=3)
    sc.link(lost.id, won.id, "stored", "lost to", 1)
    for i, g in enumerate(guides):
        sc.fact(g.id, 2, col=3 + i)
        sc.link(g.id, won.id, "derived", "agrees with the winner" if i == 0 else "", 2)
    v = sc.result(f"Two sources in force disagree: {lost.object_as_written} against {won.object_as_written}. "
                  f"The legislative decree outranks the ministerial decree, so the answer is {won.object_as_written}. The losing fact is kept, marked and linked.",
                  "ok", "The link between the two law facts is stored. The agreement of the public guide is put together by the scene.")
    return {"id": "conflict", "title": "Two sources disagree",
            "look": "A ministerial decree and a legislative decree give different time limits for the same verification.",
            "variants": [v]}


def _scene_arm(st, ids, used) -> dict:
    def one(doc, predicate, contains=""):
        return next((s for s in st if s.source_doc == doc and s.predicate == predicate and s.status == "current"
                     and contains in s.quote), None)

    rule = one("robot-cell-sheet", "safeguardedSpaceRule")
    check = one("nanoscan3-manual", "requiresPeriodicCheck", "at least once a year")
    variants = []
    for name, doc in (("UR5e", "ur5e-manual"), ("UR10e", "ur10e-manual")):
        reach = one(doc, "hasReach", "extends") or one(doc, "hasReach")
        partly = one(doc, "isPartlyCompletedMachinery", "Declaration of Incorporation is provided")
        mm = int(re.search(r"(\d+)\s*mm", reach.object_as_written + " " + reach.object).group(1))
        sc = _Scene(used, name, _plain_day(TODAY))
        sc.fact(rule.id, 0, col=2)
        sc.fact(reach.id, 1, col=2, note=f"reach read from the fact: {mm} mm")
        if partly:
            sc.fact(partly.id, 1, col=1)
        if check:
            sc.fact(check.id, 2, col=4)
        zone = sc.other("zone", "plant", "scenario", "Protected zone radius of the robotic cell",
                        f"{SCENARIO_ZONE_MM} mm", 2, col=2)
        sc.link(reach.id, rule.id, "derived", "maximum extension", 1)
        sc.link(zone, reach.id, "derived", f"{SCENARIO_ZONE_MM} mm against {mm} mm", 2)
        covered = mm <= SCENARIO_ZONE_MM
        text = (f"{name} reaches {mm} mm. The {SCENARIO_ZONE_MM} mm zone ({SCENARIO_LABEL}) covers the arm."
                if covered else
                f"{name} reaches {mm} mm, more than the {SCENARIO_ZONE_MM} mm zone ({SCENARIO_LABEL}). The fence does not cover the machine's maximum extension.")
        v = sc.result(text, "ok" if covered else "warn",
                      "Reach and rule are facts with quotes. The comparison is made on this page.")
        v["reach_mm"] = mm
        variants.append(v)
    return {"id": "arm", "title": "The factory changes: a bigger arm",
            "look": "Swap the robot arm for a bigger one and see whether the protected zone still covers its reach.",
            "toggle": "Robot arm", "variants": variants}


def _scene_unknown(store, st, ids, used, counts) -> dict:
    from atlas.strategies.plant import device_records

    devices = device_records(st)
    device = next(d for d in devices if d["position"] == UNKNOWN_DEVICE)
    res = verification_interval(device, viewer.annex_facts(st), TODAY)
    plant_predicates = {s.predicate for s in st if s.layer == "plant"}
    sc = _Scene(used, "", _plain_day(TODAY))
    cols = {"kind": 1, "capacity_kg": 2, "year_built": 3}
    for name, fid in device["facts"].items():
        if fid in ids and name in cols:
            sc.fact(fid, 0, col=cols[name], **({"state": "flag", "tag": "the rule has no mapping for this kind"} if name == "kind" else {}))
    if not any("verif" in p.lower() for p in plant_predicates):
        sc.other("lastcheck", "plant", "gap", "Last verification date", f"not in any document, for any of the {len(devices)} devices", 1, col=4)
    row = next((s for s in viewer.annex_facts(st) if read_row(s)), None)
    if row is not None:
        sc.fact(row.id, 1, col=1, state="undecided", tag="no row picked for device 24")
    opens = [s for s in st if s.status == "open_point"]
    for i, layer in enumerate(("law", "guidance")):
        sample = next((s for s in opens if s.layer == layer and 30 < len(s.object) < 110 and len(s.quote) < 500), None)
        if sample is not None:
            sc.fact(sample.id, 2, col=3, state="open", tag="open point: the document leaves it open")
    v = sc.result("Unknown is an answer. Nothing is guessed.", "unknown",
                  f"Device {UNKNOWN_DEVICE}: {res.get('why', '')}. {len(opens)} open points are kept as open points. "
                  f"{counts['rejected']} proposed facts were rejected by the rule \"no quote, no fact\".")
    v["rule"] = {"interval": res.get("interval"), "why": res.get("why", "")}
    return {"id": "unknown", "title": "What the atlas does not know",
            "look": f"Device {UNKNOWN_DEVICE} gets no interval, no device has a last verification date, and open points stay open.",
            "variants": [v]}


def _numbers(store, st) -> dict:
    from atlas.ontology import build

    b = build.counts("B")
    kept = len(st)
    refused = len(getattr(store, "rejections", []) or [])
    return {"in_force": {name: sum(1 for s in st if s.layer == name and s.status == "current") for name in LAYER_TEXT},
            "total": kept, "proposed": kept + refused, "accepted": kept, "rejected": refused,
            "first_build": {k: b.get(k, 0) for k in ("proposed_total", "anchored", "rejected", "rejected_no_anchor",
                                                     "rejected_missing_condition", "rejected_value_not_in_quote",
                                                     "rejected_not_in_schema")},
            "corrections": sum(1 for s in st if s.status == "closed"),
            "conflicts": sum(1 for s in st if s.status == "conflict"),
            "open_points": sum(1 for s in st if s.status == "open_point")}


def _asks(ids, used, today: date) -> list[dict]:
    """Up to eight design questions answered by the agent, with the facts each answer used."""
    from atlas.ontology import build

    payload = json.loads((ROOT / "data" / "cq" / "cqs.json").read_text(encoding="utf-8"))
    questions = [q for q in payload["cqs"] if q["split"] == "design" and q["id"] in ASK_IDS]
    out = []
    for q in questions:
        try:
            a = build.answer(q["question_en"], "B", today)
        except Exception:   # an answer that cannot be produced is left out, never invented
            continue
        if not a.steps:
            continue
        steps = []
        for n, s in enumerate(a.steps, 1):
            fid = s.statement_id if s.statement_id in ids else ""
            if fid:
                used.add(fid)
            steps.append({"n": n, "f": fid, "text": s.text, "quote": s.quote or "", "locator": s.locator or ""})
        value = a.value
        out.append({"id": q["id"], "question": q["question_en"],
                    "value": value if isinstance(value, (list, bool)) or value is None else str(value),
                    "text": a.text, "steps": steps})
    return out


def _impact() -> dict | None:
    """What would be flagged if a document changed: read from ontology/B/impact.json when it exists."""
    path = ROOT / "ontology" / "B" / "impact.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    for doc in data.get("documents") or []:
        for ref in doc.get("referred_by") or []:
            ref["examples"] = (ref.get("examples") or [])[:3]
    for w in data.get("what_if") or []:
        w["facts_total"] = len(w.get("facts_affected") or [])
        w["facts_affected"] = (w.get("facts_affected") or [])[:6]
        for k in ("added", "removed", "modified"):
            w[k + "_total"] = len(w.get(k) or [])
            w[k] = (w.get(k) or [])[:6]
    return data


def build_data(store=None, today: date = TODAY, answers: bool = True) -> dict:
    store = store or viewer._store()
    base = viewer.build_data(store, today)
    corpus = getattr(store, "corpus", None)
    st = [s.model_copy(update={"layer": viewer.layer_of_statement(s, corpus)}) for s in store.statements]
    ids = {s.id: s for s in st}
    used: set[str] = set()
    numbers = _numbers(store, st)
    scenes = [_scene_crane(st, ids, used), _scene_correction(st, ids, used), _scene_repeal(st, ids, used, base["regime"]),
              _scene_conflict(st, ids, used), _scene_arm(st, ids, used), _scene_unknown(store, st, ids, used, numbers)]
    asks = _asks(ids, used, today) if answers else []
    for f in base["facts"]:          # what a fact replaced or lost to is shown in the drawer
        if f["id"] in used and f.get("x"):
            used.add(f["x"])
    back = {f["x"]: f["id"] for f in base["facts"] if f.get("x")}
    facts = {}
    for f in base["facts"]:
        if f["id"] in used:
            f = dict(f, n=base["sources"][f["d"]]["noun"])
            if f["id"] in back:
                f["r"] = back[f["id"]]
            facts[f["id"]] = f
    return {"facts": facts, "scenes": scenes, "asks": asks, "numbers": numbers, "impact": _impact(),
            "layers": [{"name": k, "label": v[0], "text": v[1], "count": numbers["in_force"][k]} for k, v in LAYER_TEXT.items()],
            "scenario_label": SCENARIO_LABEL, "today": today.isoformat(), "today_plain": _plain_day(today)}


def render(data: dict) -> str:
    return PAGE.replace("__DATA__", embedded_json(data))


def write(path: Path | None = None, store=None, today: date = TODAY, answers: bool = True) -> Path:
    path = Path(path or OUT)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render(build_data(store, today, answers)), encoding="utf-8")
    return path


PAGE = r"""<title>Plant Atlas</title>
<meta charset="utf-8">
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Space+Grotesk:wght@500;600;700&display=swap">
<style>
:root {
  --bg: #f3f5f8; --surface: #ffffff; --surface-2: #e9edf2; --ink: #101a2b; --muted: #55627a; --line: #d3dae4;
  --accent: #101a2b; --accent-ink: #ffffff; --focus: #d9480f;
  --layer-law: #2c48b5; --layer-guidance: #0c7767; --layer-manufacturer: #a8530c; --layer-company: #7440ad; --layer-plant: #b12c4c;
  --in-force: #1f7a3a; --in-force-bg: #e2f3e6; --not-in-force: #6f7684; --not-in-force-bg: #e8eaee;
  --warn: #a14a00; --warn-bg: #fdeeda; --scenario: #8a5a00; --scenario-bg: #fff6d6; --derived: #c2410c; --stored: #101a2b;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    color-scheme: dark;
    --bg: #0d131d; --surface: #151d2a; --surface-2: #1f2937; --ink: #e8edf5; --muted: #9aa7bb; --line: #2d394b;
    --accent: #e8edf5; --accent-ink: #0d131d; --focus: #ffa25e;
    --layer-law: #8ea5ff; --layer-guidance: #4fd1b8; --layer-manufacturer: #f2a55c; --layer-company: #c79bf2; --layer-plant: #f58aa3;
    --in-force: #7fd695; --in-force-bg: #17301f; --not-in-force: #a0a8b6; --not-in-force-bg: #252d3a;
    --warn: #ffb469; --warn-bg: #3a2812; --scenario: #f0cf6a; --scenario-bg: #352c10; --derived: #ff9a62; --stored: #e8edf5;
  }
}
:root[data-theme="dark"] {
  color-scheme: dark;
  --bg: #0d131d; --surface: #151d2a; --surface-2: #1f2937; --ink: #e8edf5; --muted: #9aa7bb; --line: #2d394b;
  --accent: #e8edf5; --accent-ink: #0d131d; --focus: #ffa25e;
  --layer-law: #8ea5ff; --layer-guidance: #4fd1b8; --layer-manufacturer: #f2a55c; --layer-company: #c79bf2; --layer-plant: #f58aa3;
  --in-force: #7fd695; --in-force-bg: #17301f; --not-in-force: #a0a8b6; --not-in-force-bg: #252d3a;
  --warn: #ffb469; --warn-bg: #3a2812; --scenario: #f0cf6a; --scenario-bg: #352c10; --derived: #ff9a62; --stored: #e8edf5;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--ink); font: 400 15px/1.5 Inter, "Helvetica Neue", Arial, sans-serif; }
.wrap { max-width: 1320px; margin: 0 auto; padding-block: 28px 56px;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); }
h1, h2, h3, .disp { font-family: "Space Grotesk", "Trebuchet MS", Verdana, sans-serif; font-weight: 600; margin: 0; letter-spacing: -0.015em; }
p { margin: 0; }
button { font: inherit; color: inherit; cursor: pointer; }
:focus-visible { outline: 3px solid var(--focus); outline-offset: 2px; }
.top { display: flex; flex-wrap: wrap; align-items: end; justify-content: space-between; gap: 8px 24px; }
.brand { font-size: 13px; font-weight: 600; letter-spacing: .14em; text-transform: uppercase; color: var(--muted); }
h1 { font-size: clamp(28px, 4vw, 44px); line-height: 1.05; font-weight: 700; }
.lead { color: var(--muted); max-width: 62ch; font-size: 16px; margin-top: 8px; }
.lay-law { --lc: var(--layer-law); } .lay-guidance { --lc: var(--layer-guidance); } .lay-manufacturer { --lc: var(--layer-manufacturer); }
.lay-company { --lc: var(--layer-company); } .lay-plant { --lc: var(--layer-plant); }

/* scenes */
.stage { margin-top: 24px; background: var(--surface); border: 1px solid var(--line); border-radius: 10px; overflow: hidden; }
.tabs { display: flex; flex-wrap: wrap; gap: 6px; padding: 10px; border-bottom: 1px solid var(--line); align-items: center; }
.tab { background: none; border: 1px solid transparent; border-radius: 6px; padding: 7px 12px; font-weight: 500; font-size: 14px; color: var(--muted);
  display: inline-flex; gap: 8px; align-items: baseline; transition: background .2s, color .2s; }
.tab b { font-family: "Space Grotesk", "Trebuchet MS", sans-serif; font-weight: 600; font-size: 12px; opacity: .7; }
.tab:hover { background: var(--surface-2); color: var(--ink); }
.tab[aria-selected="true"] { background: var(--accent); color: var(--accent-ink); }
.play { margin-left: auto; background: var(--surface); border: 1px solid var(--ink); border-radius: 6px; padding: 7px 14px; font-weight: 600; min-width: 92px; }
.play:hover { background: var(--surface-2); }
.progress { height: 3px; background: var(--surface-2); }
.progress i { display: block; height: 100%; width: 0; background: var(--derived); }
.progress.run i { width: 100%; transition: width var(--dur, 9s) linear; }
.head { display: grid; grid-template-columns: 1fr auto; gap: 12px 28px; padding: 20px 20px 8px; align-items: end; }
.head h2 { font-size: clamp(22px, 2.6vw, 30px); line-height: 1.15; }
.look { font-size: 17px; color: var(--muted); margin-top: 6px; max-width: 70ch; }
.when { text-align: right; }
.when .lbl { font-size: 11px; font-weight: 600; letter-spacing: .1em; text-transform: uppercase; color: var(--muted); }
.when .date { font-family: "Space Grotesk", "Trebuchet MS", sans-serif; font-weight: 600; font-size: 20px; white-space: nowrap; }
.seg { display: inline-flex; border: 1px solid var(--ink); border-radius: 6px; overflow: hidden; margin-top: 6px; }
.seg button { background: var(--surface); border: 0; padding: 6px 12px; font-weight: 500; font-size: 14px; }
.seg button + button { border-left: 1px solid var(--ink); }
.seg button[aria-pressed="true"] { background: var(--accent); color: var(--accent-ink); }
.legend { display: flex; flex-wrap: wrap; gap: 6px 20px; padding: 6px 20px 14px; font-size: 13px; color: var(--muted); }
.legend span { display: inline-flex; align-items: center; gap: 7px; }
.legend svg { flex: none; }
.dot { width: 10px; height: 10px; border-radius: 2px; display: inline-block; }

/* atlas */
.atlas { position: relative; isolation: isolate; border-top: 1px solid var(--line); }
.band { display: grid; grid-template-columns: 190px 1fr; border-bottom: 1px solid var(--line);
  background: color-mix(in srgb, var(--lc) 6%, var(--surface)); }
.band:last-of-type { border-bottom: 0; }
.bandlabel { padding: 14px 14px 14px 20px; border-left: 5px solid var(--lc); }
.bandlabel .name { font-family: "Space Grotesk", "Trebuchet MS", sans-serif; font-weight: 700; font-size: 17px; color: var(--lc); }
.bandlabel .txt { font-size: 12px; color: var(--muted); line-height: 1.35; margin-top: 2px; }
.bandlabel .cnt { font-size: 12px; margin-top: 6px; font-weight: 500; }
.bandlabel .cnt b { font-family: "Space Grotesk", "Trebuchet MS", sans-serif; font-size: 15px; }
.cards { display: grid; grid-template-columns: repeat(var(--cols, 4), minmax(0, 1fr)); gap: 30px 18px; padding: 18px 20px 18px 6px; align-content: start; min-height: 64px; }
.cards:empty::after { content: "no fact of this layer in this scene"; font-size: 12px; color: var(--muted); align-self: center; opacity: .7; }
.stack { display: grid; gap: 22px; align-content: start; }
.fc { position: relative; z-index: 2; text-align: left; background: var(--surface); border: 1px solid var(--line); border-top: 3px solid var(--lc);
  border-radius: 6px; padding: 8px 10px 9px; min-width: 0; width: 100%; display: block;
  transition: opacity .28s ease, transform .28s ease, border-color .2s, background .2s; }
.fc:hover { border-color: var(--lc); }
@media (min-width: 900px) { .cards > .fc, .cards > .stack { grid-column: var(--col, auto); } }
.fc .subj { font-size: 12px; color: var(--muted); display: block; overflow-wrap: anywhere; }
.fc .rel { font-size: 12px; color: var(--lc); font-weight: 600; }
.fc .val { display: block; font-family: "Space Grotesk", "Trebuchet MS", sans-serif; font-weight: 600; font-size: 16px; line-height: 1.25; overflow-wrap: anywhere; margin-top: 1px; }
.fc .val.long { font-size: 13.5px; font-family: Inter, "Helvetica Neue", Arial, sans-serif; font-weight: 500; }
.fc .src { display: block; font-size: 11px; color: var(--muted); margin-top: 5px; }
.fc .note { display: block; font-size: 11.5px; color: var(--derived); margin-top: 5px; border-top: 1px dashed var(--line); padding-top: 4px; }
.fc .tag { display: inline-block; font-size: 11px; font-weight: 600; border-radius: 3px; padding: 1px 6px; margin-top: 6px; background: var(--not-in-force-bg); color: var(--not-in-force); }
.fc .num { position: absolute; top: -11px; left: -9px; width: 22px; height: 22px; border-radius: 50%; background: var(--accent); color: var(--accent-ink);
  font: 600 12px/22px "Space Grotesk", "Trebuchet MS", sans-serif; text-align: center; }
.fc.s-out, .fc.s-notyet { background: var(--not-in-force-bg); border-top-color: var(--not-in-force); border-style: dashed; border-top-style: solid; }
.fc.s-out .val { text-decoration: line-through; text-decoration-thickness: 1px; color: var(--not-in-force); }
.fc.s-out .rel, .fc.s-notyet .rel, .fc.s-notyet .val { color: var(--not-in-force); }
.fc.s-flag { border-color: var(--warn); border-top-color: var(--warn); }
.fc.s-flag .tag { background: var(--warn-bg); color: var(--warn); }
.fc.s-undecided .tag, .fc.s-open .tag { background: var(--surface-2); color: var(--muted); }
.fc.s-undecided, .fc.s-open { border-style: dashed; border-top-style: solid; }
.fc.s-scenario { background: var(--scenario-bg); border: 2px dashed var(--scenario); }
.fc.s-scenario .tag { background: var(--scenario); color: var(--surface); text-transform: uppercase; letter-spacing: .04em; margin: 0 0 4px; }
.fc.s-gap { background: transparent; border: 2px dashed var(--muted); }
.fc.s-gap .val { color: var(--muted); font-size: 14px; }
.fc.compact .val { font-size: 14.5px; }
.fc.hid { opacity: 0; transform: translateY(8px); pointer-events: none; }
#wires { position: absolute; left: 0; top: 0; z-index: 1; pointer-events: none; overflow: visible; }
#wires path { fill: none; stroke-width: 1.8; transition: opacity .3s ease, stroke-dashoffset .5s ease; }
#wires path.stored { stroke: var(--stored); stroke-width: 2.4; }
#wires path.derived { stroke: var(--derived); stroke-dasharray: 5 5; }
#wires path.hid { opacity: 0; }
#wires .m-stored { fill: var(--stored); } #wires .m-derived { fill: var(--derived); }
#wlabels { position: absolute; inset: 0; z-index: 3; pointer-events: none; }
#wlabels span { position: absolute; transform: translate(-50%, -50%); font-size: 11px; font-weight: 600; padding: 1px 7px; border-radius: 9px; white-space: nowrap;
  background: var(--surface); border: 1px solid var(--derived); color: var(--derived); transition: opacity .3s ease; }
#wlabels span.stored { border-color: var(--stored); color: var(--stored); }
#wlabels span.hid { opacity: 0; }
.result { margin: 0; padding: 18px 20px 20px; border-top: 1px solid var(--line); display: grid; grid-template-columns: auto 1fr; gap: 4px 16px; align-items: baseline; }
.result .lbl { font-size: 11px; font-weight: 600; letter-spacing: .1em; text-transform: uppercase; color: var(--muted); }
.result .txt { font-family: "Space Grotesk", "Trebuchet MS", sans-serif; font-weight: 600; font-size: clamp(18px, 2.2vw, 24px); line-height: 1.25; }
.result .note { grid-column: 2; color: var(--muted); font-size: 14px; }
.result.t-ok { box-shadow: inset 5px 0 0 var(--in-force); } .result.t-warn { box-shadow: inset 5px 0 0 var(--warn); background: var(--warn-bg); }
.result.t-unknown { box-shadow: inset 5px 0 0 var(--muted); }

/* ask */
.sect { margin-top: 44px; }
.sect > h2 { font-size: 26px; }
.sect > .lead { margin-bottom: 14px; }
.qs { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 8px; }
.q { text-align: left; background: var(--surface); border: 1px solid var(--line); border-radius: 6px; padding: 10px 12px; font-size: 14px; line-height: 1.35; transition: border-color .2s, background .2s; }
.q:hover { border-color: var(--ink); }
.q[aria-pressed="true"] { background: var(--accent); color: var(--accent-ink); border-color: var(--accent); }
.ans { margin-top: 14px; background: var(--surface); border: 1px solid var(--line); border-radius: 10px; overflow: hidden; }
.anshead { padding: 18px 20px; display: grid; gap: 6px; }
.anshead .typed { font-family: "Space Grotesk", "Trebuchet MS", sans-serif; font-weight: 700; font-size: clamp(20px, 2.4vw, 28px); overflow-wrap: anywhere; }
.anshead .say { font-size: 16px; max-width: 80ch; }
.anshead .lbl { font-size: 11px; font-weight: 600; letter-spacing: .1em; text-transform: uppercase; color: var(--muted); }
.ans .band { border-top: 1px solid var(--line); border-bottom: 0; }
.ans .fc q { display: block; font-size: 12px; font-style: italic; color: var(--muted); margin-top: 5px; }
.ans .band:has(.cards:empty) { display: none; }
.loose { padding: 12px 20px; border-top: 1px solid var(--line); font-size: 13px; color: var(--muted); }

/* impact */
.health { font-size: 15px; font-weight: 500; margin-bottom: 12px; padding: 8px 12px; background: var(--surface); border: 1px solid var(--line); border-left: 5px solid var(--in-force); border-radius: 6px; }
.docgroup { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; margin-top: 6px; }
.docgroup .g { width: 110px; font: 700 14px "Space Grotesk", "Trebuchet MS", sans-serif; color: var(--lc); }
.doc { background: var(--surface); border: 1px solid var(--line); border-left: 4px solid var(--lc); border-radius: 6px; padding: 5px 10px; font-size: 13px; text-align: left; }
.doc small { color: var(--muted); display: block; font-size: 11px; }
.doc[aria-pressed="true"] { background: var(--accent); color: var(--accent-ink); border-color: var(--accent); } .doc[aria-pressed="true"] small { color: inherit; opacity: .8; }
.cards .cnt2 { grid-column: 1 / -1; font-size: 14px; } .cards .cnt2 b { font: 700 22px "Space Grotesk", "Trebuchet MS", sans-serif; color: var(--warn); margin-right: 6px; }
div.fc { cursor: default; } .fc q { display: block; font-size: 12px; font-style: italic; color: var(--muted); margin-top: 5px; }
.whatifs { display: grid; gap: 12px; margin-top: 14px; }
.whatif { background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: 16px 20px; }
.whatif h3 { font-size: 18px; } .whatif .wnote { color: var(--muted); margin: 4px 0 10px; max-width: 90ch; }
.ba { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 10px; }
.ba > div { border: 1px solid var(--line); border-radius: 6px; padding: 10px 12px; font-size: 13px; overflow-wrap: anywhere; }
.ba h4 { margin: 0 0 4px; font-size: 11px; letter-spacing: .1em; text-transform: uppercase; color: var(--muted); }
.ba ul { margin: 0; padding-left: 18px; } .ba .bef { color: var(--not-in-force); text-decoration: line-through; } .ba .aft { font-weight: 600; }

/* numbers */
.nums { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 1px; background: var(--surface); border: 1px solid var(--line); border-radius: 10px; overflow: hidden; }
.nums div { background: var(--surface); padding: 14px 16px; box-shadow: 0 0 0 1px var(--line); }
.nums b { display: block; font-family: "Space Grotesk", "Trebuchet MS", sans-serif; font-weight: 700; font-size: 28px; line-height: 1.1; font-variant-numeric: tabular-nums; }
.nums span { font-size: 12.5px; color: var(--muted); }
.nums .lay b { color: var(--lc); }
.more { display: inline-block; margin-top: 18px; font-weight: 600; color: var(--ink); text-underline-offset: 4px; }

/* drawer */
.drawer { position: fixed; top: 0; right: 0; bottom: 0; width: min(440px, 100%); background: var(--surface); border-left: 1px solid var(--line); z-index: 20;
  padding: calc(18px + env(safe-area-inset-top, 0px)) 20px 24px; overflow-y: auto; transform: translateX(102%); transition: transform .26s ease; visibility: hidden; }
.drawer.open { transform: none; visibility: visible; }
.drawer h3 { font-size: 20px; line-height: 1.25; margin: 10px 0 2px; overflow-wrap: anywhere; }
.drawer .close { float: right; background: var(--surface-2); border: 1px solid var(--line); border-radius: 6px; padding: 4px 12px; }
.drawer blockquote { margin: 12px 0; padding: 10px 12px; border-left: 4px solid var(--lc); background: var(--surface-2); font-style: italic; overflow-wrap: anywhere; white-space: pre-wrap; }
.drawer dl { display: grid; grid-template-columns: 110px 1fr; gap: 6px 12px; margin: 12px 0 0; font-size: 14px; }
.drawer dt { color: var(--muted); } .drawer dd { margin: 0; overflow-wrap: anywhere; }
.drawer .chip { display: inline-block; font-size: 12px; font-weight: 600; border: 1px solid var(--lc); color: var(--lc); border-radius: 3px; padding: 1px 8px; }
.linkbtn { background: none; border: 0; padding: 0; text-decoration: underline; text-underline-offset: 3px; text-align: left; }

@media (max-width: 900px) {
  .cards { --cols: 2 !important; }
  .head { grid-template-columns: 1fr; } .when { text-align: left; }
}
@media (max-width: 640px) {
  .band { grid-template-columns: 1fr; }
  .bandlabel { padding: 10px 14px 0; display: flex; flex-wrap: wrap; gap: 2px 10px; align-items: baseline; }
  .bandlabel .txt { display: none; } .bandlabel .cnt { margin: 0; }
  .cards { --cols: 1 !important; padding: 14px; }
  .result { grid-template-columns: 1fr; } .result .note { grid-column: 1; }
  .play { margin-left: 0; }
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { transition: none !important; animation: none !important; }
}
</style>

<div class="wrap">
  <header class="top">
    <div>
      <div class="brand">Plant Atlas</div>
      <h1>No quote, no fact.</h1>
      <p class="lead">The documents around a plant's machines, read into five layers of facts. Each card below is one fact with the sentence it was read from. Click any card to see it.</p>
    </div>
  </header>

  <section class="stage" aria-label="The atlas">
    <div class="tabs" role="tablist" id="tabs"></div>
    <div class="progress" id="progress"><i></i></div>
    <div class="head">
      <div><h2 id="stitle"></h2><p class="look" id="slook"></p></div>
      <div class="when"><div class="lbl" id="wlbl">Date</div><div class="date" id="sdate"></div><div class="seg" id="seg" hidden></div></div>
    </div>
    <div class="legend" aria-label="Legend">
      <span><svg width="38" height="10" aria-hidden="true"><line x1="1" y1="5" x2="30" y2="5" stroke="var(--stored)" stroke-width="2.4"/><path d="M29 1 L37 5 L29 9 z" fill="var(--stored)"/></svg>stored link: replaced by, lost to</span>
      <span><svg width="38" height="10" aria-hidden="true"><line x1="1" y1="5" x2="30" y2="5" stroke="var(--derived)" stroke-width="1.8" stroke-dasharray="5 4"/><path d="M29 1 L37 5 L29 9 z" fill="var(--derived)"/></svg>derived link: put together by a rule or by this scene, not stored</span>
      <span><i class="dot" style="background:var(--in-force)"></i>in force</span>
      <span><i class="dot" style="background:var(--not-in-force)"></i>not in force on this date</span>
      <span><i class="dot" style="background:var(--warn)"></i>flagged</span>
      <span><i class="dot" style="background:var(--scenario)"></i>scenario input, not from a document</span>
    </div>
    <div class="atlas" id="atlas"></div>
    <div class="result" id="result" aria-live="polite"></div>
  </section>

  <section class="sect" id="ask" hidden>
    <h2>Ask the atlas</h2>
    <p class="lead">Questions answered by the agent on <span id="asktoday"></span>. Each answer shows the facts it used, in order, in their layers.</p>
    <div class="qs" id="qs"></div>
    <div class="ans" id="ans"></div>
  </section>

  <section class="sect" id="impact" hidden>
    <h2>Change a document</h2>
    <p class="lead">Pick a document: what would be flagged if it changed or were withdrawn. Computed from each fact's stored source and from citations found in the quotes. These are not stored links.</p>
    <p class="health" id="health" hidden></p>
    <div id="docpick"></div>
    <div class="ans" id="docview"></div>
    <div class="whatifs" id="whatifs"></div>
  </section>

  <section class="sect">
    <h2>The numbers</h2>
    <p class="lead">Read from the store and from the build record.</p>
    <div class="nums" id="nums"></div>
    <a class="more" href="view.html">Open the full explorer</a>
  </section>
</div>
<aside class="drawer" id="drawer" aria-label="Fact detail" tabindex="-1"></aside>

<script>
const DATA = __DATA__;
/*END-DATA*/
(function () {
  "use strict";
  const F = DATA.facts, SC = DATA.scenes, LAYERS = DATA.layers;
  const $ = (s, r) => (r || document).querySelector(s);
  const esc = (t) => String(t == null ? "" : t).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const words = (p) => String(p).replace(/([a-z])([A-Z])/g, "$1 $2").toLowerCase();
  const MONTHS = "January February March April May June July August September October November December".split(" ");
  const plainDay = (iso) => { const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso || ""); return m ? (+m[3]) + " " + MONTHS[+m[2] - 1] + " " + m[1] : iso; };
  const DUR = 9000;
  let si = 0, vi = 0, reveal = 99, playing = false, timers = [];
  const reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function valueOf(f) {
    const w = f.w || f.o, o = f.o || "";
    if (/^\d{4}-\d{2}-\d{2}$/.test(o)) return plainDay(o);
    if (o && w && o !== w && o.length <= 12 && w.toLowerCase() !== o.toLowerCase()) return w + " (" + o + ")";
    return w;
  }
  function bandOf(c) { return c.f ? (F[c.f] || {}).l : c.band; }

  function cardEl(c, opts) {
    opts = opts || {};
    const b = document.createElement("button");
    b.type = "button";
    b.className = "fc lay-" + bandOf(c) + " s-" + (c.state || "in") + (c.compact ? " compact" : "");
    b.dataset.k = c.k; b.dataset.step = c.step || 0;
    if (c.col) b.style.setProperty("--col", c.col);
    let h = "";
    if (opts.num) h += '<span class="num">' + opts.num + "</span>";
    if (c.f) {
      const f = F[c.f], v = valueOf(f);
      h += '<span class="subj">' + esc(f.s) + ' <span class="rel">· ' + esc(words(f.p)) + " →</span></span>";
      h += '<span class="val' + (v.length > 46 ? " long" : "") + '">' + esc(v.length > 150 ? v.slice(0, 148) + "…" : v) + "</span>";
      h += '<span class="src">' + esc(f.d) + " · " + esc(f.a || "") + "</span>";
      if (opts.quote) h += "<q>" + esc(opts.quote.length > 220 ? opts.quote.slice(0, 218) + "…" : opts.quote) + "</q>";
      if (c.tag) h += '<span class="tag">' + esc(c.tag) + "</span>";
      if (c.note) h += '<span class="note">rule: ' + esc(c.note) + "</span>";
    } else if (c.state === "scenario") {
      h += '<span class="tag">' + esc(DATA.scenario_label) + "</span>";
      h += '<span class="subj">' + esc(c.title) + "</span>" + '<span class="val">' + esc(c.text) + "</span>";
    } else {
      h += '<span class="subj">' + esc(c.title) + "</span>" + '<span class="val">' + esc(c.text) + "</span>";
    }
    b.innerHTML = h;
    b.addEventListener("click", () => openDrawer(c));
    return b;
  }

  function bandsInto(host, cards, opts) {
    opts = opts || {};
    const by = {};
    LAYERS.forEach((L) => {
      const row = document.createElement("div"); row.className = "band lay-" + L.name;
      row.innerHTML = '<div class="bandlabel"><div class="name">' + esc(L.label) + '</div><div class="txt">' + esc(L.text) +
        '</div><div class="cnt"><b>' + L.count.toLocaleString("en") + "</b> facts in force</div></div>";
      const box = document.createElement("div"); box.className = "cards";
      if (opts.cols && opts.cols[L.name]) box.style.setProperty("--cols", opts.cols[L.name]);
      row.appendChild(box); host.appendChild(row); by[L.name] = box;
    });
    const stacks = {};
    cards.forEach((c, i) => {
      const box = by[bandOf(c)]; if (!box) return;
      const el = cardEl(c, opts.decorate ? opts.decorate(c, i) : null);
      if (c.pair) {
        const key = bandOf(c) + c.pair;
        if (!stacks[key]) { stacks[key] = document.createElement("div"); stacks[key].className = "stack"; box.appendChild(stacks[key]); }
        stacks[key].appendChild(el);
      } else box.appendChild(el);
    });
  }

  function variant() { return SC[si].variants[vi]; }

  function renderScene() {
    const S = SC[si], V = variant();
    document.querySelectorAll("#tabs .tab").forEach((t, i) => { t.setAttribute("aria-selected", i === si ? "true" : "false"); t.tabIndex = i === si ? 0 : -1; });
    $("#stitle").textContent = S.title; $("#slook").textContent = S.look;
    $("#wlbl").textContent = S.toggle && S.toggle !== "Date" ? S.toggle : "Date";
    $("#sdate").textContent = S.toggle && S.toggle !== "Date" ? V.label : V.date;
    const seg = $("#seg"); seg.innerHTML = ""; seg.hidden = S.variants.length < 2;
    if (S.variants.length > 1) S.variants.forEach((v, i) => {
      const b = document.createElement("button"); b.type = "button"; b.textContent = v.label; b.setAttribute("aria-pressed", i === vi ? "true" : "false");
      b.addEventListener("click", () => { stop(); vi = i; reveal = 99; renderScene(); });
      seg.appendChild(b);
    });
    const host = $("#atlas"); host.innerHTML = "";
    bandsInto(host, V.cards, { cols: S.cols });
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg"); svg.id = "wires"; svg.setAttribute("aria-hidden", "true"); host.appendChild(svg);
    const lab = document.createElement("div"); lab.id = "wlabels"; host.appendChild(lab);
    const r = $("#result"); r.className = "result t-" + (V.result.tone || "ok");
    r.innerHTML = '<span class="lbl">Result</span><span class="txt">' + esc(V.result.text) + "</span>" + (V.result.note ? '<span class="note">' + esc(V.result.note) + "</span>" : "");
    applyReveal(); draw();
  }

  function applyReveal() {
    document.querySelectorAll("#atlas .fc").forEach((e) => e.classList.toggle("hid", +e.dataset.step > reveal));
    document.querySelectorAll("#wires path, #wlabels span").forEach((e) => e.classList.toggle("hid", +e.dataset.step > reveal));
    $("#result").style.opacity = reveal >= maxStep() ? "1" : ".35";
  }
  function maxStep() { return variant().cards.reduce((m, c) => Math.max(m, c.step || 0), 0); }

  function draw() {
    const host = $("#atlas"), svg = $("#wires"), lab = $("#wlabels"); if (!svg) return;
    const hr = host.getBoundingClientRect();
    svg.setAttribute("width", hr.width); svg.setAttribute("height", hr.height); svg.setAttribute("viewBox", "0 0 " + hr.width + " " + hr.height);
    let out = '<defs><marker id="ah-stored" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path class="m-stored" d="M0 0 L10 5 L0 10 z"/></marker>' +
      '<marker id="ah-derived" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path class="m-derived" d="M0 0 L10 5 L0 10 z"/></marker></defs>';
    lab.innerHTML = "";
    const els = {}; host.querySelectorAll("[data-k]").forEach((e) => { els[e.dataset.k] = e.getBoundingClientRect(); });
    const geo = [], tot = {}, seen = {};
    variant().links.forEach((l) => {
      const a = els[l.a], b = els[l.b]; if (!a || !b) return;
      const mode = a.bottom <= b.top + 2 ? "down" : b.bottom <= a.top + 2 ? "up" : "side";
      const sa = mode === "down" ? "b" : mode === "up" ? "t" : "s", sb = mode === "down" ? "t" : mode === "up" ? "b" : "s";
      tot[l.a + sa] = (tot[l.a + sa] || 0) + 1; tot[l.b + sb] = (tot[l.b + sb] || 0) + 1;
      geo.push({ l: l, a: a, b: b, mode: mode, sa: sa, sb: sb });
    });
    const slot = (k, side, r) => { const id = k + side; seen[id] = (seen[id] || 0) + 1; return r.left - hr.left + r.width * seen[id] / (tot[id] + 1); };
    geo.forEach((g) => {
      const l = g.l; let x1, y1, x2, y2, d;
      if (g.mode === "side") {
        const right = g.a.right <= g.b.left;
        x1 = (right ? g.a.right : g.a.left) - hr.left; x2 = (right ? g.b.left - 3 : g.b.right + 3) - hr.left;
        y1 = g.a.top - hr.top + Math.min(g.a.height, g.b.height) / 2; y2 = g.b.top - hr.top + Math.min(g.a.height, g.b.height) / 2;
        const k = (x2 - x1) / 2; d = "M" + x1 + " " + y1 + " C" + (x1 + k) + " " + y1 + "," + (x2 - k) + " " + y2 + "," + x2 + " " + y2;
      } else {
        const down = g.mode === "down";
        x1 = slot(l.a, g.sa, g.a); x2 = slot(l.b, g.sb, g.b);
        y1 = (down ? g.a.bottom : g.a.top) - hr.top; y2 = (down ? g.b.top - 3 : g.b.bottom + 3) - hr.top;
        const k = Math.max(14, Math.abs(y2 - y1) / 2) * (down ? 1 : -1);
        d = "M" + x1 + " " + y1 + " C" + x1 + " " + (y1 + k) + "," + x2 + " " + (y2 - k) + "," + x2 + " " + y2;
      }
      out += '<path class="' + l.kind + '" data-step="' + (l.step || 0) + '" d="' + d + '" marker-end="url(#ah-' + l.kind + ')"/>';
      if (l.label) {
        const s = document.createElement("span"); s.className = l.kind; s.dataset.step = l.step || 0; s.textContent = l.label;
        s.style.left = (x1 + x2) / 2 + "px"; s.style.top = (y1 + y2) / 2 + "px"; lab.appendChild(s);
      }
    });
    svg.innerHTML = out;
    document.querySelectorAll("#wires path, #wlabels span").forEach((e) => e.classList.toggle("hid", +e.dataset.step > reveal));
  }

  /* play */
  function stop() {
    playing = false; timers.forEach(clearTimeout); timers = [];
    const p = $("#progress"); p.classList.remove("run");
    const b = $("#play"); if (b) { b.textContent = "Play"; b.setAttribute("aria-pressed", "false"); }
  }
  function runScene() {
    timers.forEach(clearTimeout); timers = [];
    const S = SC[si], two = S.variants.length > 1, half = two ? DUR / 2 : DUR;
    const p = $("#progress"); p.classList.remove("run"); void p.offsetWidth; p.style.setProperty("--dur", DUR + "ms"); p.classList.add("run");
    const seq = (offset, span) => {
      const n = maxStep(), gap = Math.min(900, span * 0.6 / Math.max(1, n));
      for (let k = 0; k <= n; k++) timers.push(setTimeout(() => { reveal = k; applyReveal(); }, offset + k * gap));
    };
    vi = 0; reveal = 0; renderScene(); seq(0, half);
    if (two) timers.push(setTimeout(() => { vi = 1; reveal = 0; renderScene(); seq(0, half); }, half));
    timers.push(setTimeout(() => { si = (si + 1) % SC.length; runScene(); }, DUR));
  }
  function start() { playing = true; const b = $("#play"); b.textContent = "Pause"; b.setAttribute("aria-pressed", "true"); runScene(); }

  /* drawer */
  function factBtn(id, label) { return F[id] ? '<button type="button" class="linkbtn" data-open="' + esc(id) + '">' + esc(label) + "</button>" : esc(label); }
  function openDrawer(c) {
    const d = $("#drawer"); let h = '<button type="button" class="close">Close</button>';
    if (c.f) {
      const f = F[c.f];
      d.className = "drawer open lay-" + f.l;
      const status = { current: "current: in force in the store", closed: "closed: replaced by a correction, kept", conflict: "conflict: lost to a higher source, kept", open_point: "open point: left open by the document" }[f.st] || f.st;
      h += '<span class="chip">' + esc(f.l) + " layer</span>";
      h += "<h3>" + esc(f.s) + "</h3><p>" + esc(words(f.p)) + " → <b>" + esc(f.w || f.o) + "</b>" + (f.o && f.w && f.o !== f.w ? " (normalised: " + esc(f.o) + ")" : "") + "</p>";
      h += "<blockquote>" + esc(f.q) + "</blockquote><dl>";
      if (f.c) h += "<dt>Condition</dt><dd>" + esc(f.c) + "</dd>";
      h += "<dt>Source</dt><dd>" + esc(f.d) + " (" + esc(f.n || "") + ")</dd><dt>Locator</dt><dd>" + esc(f.a || "") + "</dd>";
      h += "<dt>Layer</dt><dd>" + esc(f.l) + "</dd><dt>Status</dt><dd>" + esc(status) + "</dd>";
      if (f.f) h += "<dt>Valid from</dt><dd>" + esc(plainDay(f.f)) + "</dd>";
      if (f.t) h += "<dt>Valid until</dt><dd>" + esc(plainDay(f.t)) + "</dd>";
      if (f.x && f.st === "conflict") h += "<dt>Lost to</dt><dd>" + factBtn(f.x, f.x) + (f.y ? ": " + esc(f.y) : "") + " (stored link)</dd>";
      else if (f.x) h += "<dt>Replaced</dt><dd>" + factBtn(f.x, f.x) + " (stored link)</dd>";
      if (f.r) h += "<dt>" + (f.st === "closed" ? "Replaced by" : "Won over") + "</dt><dd>" + factBtn(f.r, f.r) + " (stored link)</dd>";
      if (c.tag) h += "<dt>In this scene</dt><dd>" + esc(c.tag) + " (derived on this page)</dd>";
      if (c.note) h += "<dt>Rule says</dt><dd>" + esc(c.note) + "</dd>";
      h += "<dt>Fact id</dt><dd>" + esc(f.id) + "</dd></dl>";
    } else {
      d.className = "drawer open lay-" + c.band;
      h += '<span class="chip">' + (c.state === "scenario" ? esc(DATA.scenario_label) : "not a fact") + "</span><h3>" + esc(c.title) + "</h3><p><b>" + esc(c.text) + "</b></p>";
      h += "<p style=\"margin-top:12px\">" + (c.state === "scenario"
        ? "This value is the one scenario input of the page. It is not in any document and has no quote. It is here to show what the atlas does when the factory changes."
        : "No document in the store states this. The atlas does not fill it in.") + "</p>";
    }
    d.innerHTML = h; d.focus();
  }
  $("#drawer").addEventListener("click", (e) => {
    const t = e.target.closest("button"); if (!t) return;
    if (t.classList.contains("close")) $("#drawer").classList.remove("open");
    else if (t.dataset.open) openDrawer({ f: t.dataset.open });
  });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") $("#drawer").classList.remove("open"); });

  /* tabs */
  const tabs = $("#tabs");
  SC.forEach((S, i) => {
    const b = document.createElement("button"); b.type = "button"; b.className = "tab"; b.setAttribute("role", "tab");
    b.innerHTML = "<b>" + (i + 1) + "</b>" + esc(S.title);
    b.addEventListener("click", () => { stop(); si = i; vi = 0; reveal = 99; renderScene(); });
    tabs.appendChild(b);
  });
  tabs.addEventListener("keydown", (e) => {
    if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
    stop(); si = (si + (e.key === "ArrowRight" ? 1 : SC.length - 1)) % SC.length; vi = 0; reveal = 99; renderScene();
    tabs.querySelectorAll(".tab")[si].focus();
  });
  const play = document.createElement("button"); play.type = "button"; play.className = "play"; play.id = "play"; play.textContent = "Play"; play.setAttribute("aria-pressed", "false");
  play.addEventListener("click", () => (playing ? (stop(), reveal = 99, applyReveal()) : start()));
  tabs.appendChild(play);

  /* ask */
  function typed(v) {
    if (v === true) return "Yes"; if (v === false) return "No";
    if (v == null || v === "" || (Array.isArray(v) && !v.length)) return "unknown";
    if (Array.isArray(v)) return v.join(" · ");
    if (/^\d{4}-\d{2}-\d{2}$/.test(v)) return plainDay(v);
    const m = /^P(\d+)([YMD])$/.exec(v); if (m) { const u = { Y: "year", M: "month", D: "day" }[m[2]]; return m[1] + " " + u + (+m[1] > 1 ? "s" : "") + " (" + v + ")"; }
    return v;
  }
  function renderAsk(i) {
    const A = DATA.asks[i];
    document.querySelectorAll("#qs .q").forEach((b, j) => b.setAttribute("aria-pressed", j === i ? "true" : "false"));
    const host = $("#ans"); host.innerHTML = "";
    const withFact = A.steps.filter((s) => s.f);
    const head = document.createElement("div"); head.className = "anshead";
    head.innerHTML = '<span class="lbl">Typed answer</span><span class="typed">' + esc(withFact.length ? typed(A.value) : "unknown") + "</span>" +
      '<span class="lbl">For a person</span><p class="say">' + esc(A.text) + "</p>";
    host.appendChild(head);
    const seenF = {}, cards = [];
    withFact.forEach((s) => { if (seenF[s.f]) { seenF[s.f].nums.push(s.n); return; } const c = { k: "a" + s.n, f: s.f, nums: [s.n], quote: s.quote || F[s.f].q }; seenF[s.f] = c; cards.push(c); });
    bandsInto(host, cards, { decorate: (c) => ({ num: c.nums[0], quote: c.quote }) });
    const loose = A.steps.filter((s) => !s.f);
    if (loose.length) {
      const d = document.createElement("div"); d.className = "loose";
      d.innerHTML = "Steps with no single fact behind them (reasoning of the agent over the facts above): " + loose.map((s) => "<br>" + s.n + ". " + esc(s.text)).join("");
      host.appendChild(d);
    }
  }
  if (DATA.asks.length) {
    $("#ask").hidden = false; $("#asktoday").textContent = DATA.today_plain;
    DATA.asks.forEach((A, i) => {
      const b = document.createElement("button"); b.type = "button"; b.className = "q"; b.textContent = A.question;
      b.addEventListener("click", () => renderAsk(i)); $("#qs").appendChild(b);
    });
    renderAsk(0);
  }

  /* impact */
  const IM = DATA.impact;
  function show(x) { if (x == null) return ""; if (typeof x === "string" || typeof x === "number") return String(x);
    return [x.subject || x.id || x.anchor || "", x.predicate ? words(x.predicate) : "", x.value || x.text || x.quote || ""].filter(Boolean).join(" · ") || JSON.stringify(x).slice(0, 200); }
  function exCard(x, layer) {
    return '<div class="fc lay-' + esc(layer) + '"><span class="subj">' + esc(x.subject || "") + ' <span class="rel">· ' + esc(words(x.predicate || "")) + ' →</span></span><span class="val long">' +
      esc(String(x.value || "").slice(0, 150)) + '</span><span class="src">' + esc(x.source_doc || "") + " · " + esc(x.anchor || "") + "</span>" +
      (x.quote ? "<q>" + esc(String(x.quote).slice(0, 220)) + "</q>" : "") + '<span class="tag" style="background:var(--warn-bg);color:var(--warn)">would be flagged</span></div>';
  }
  function renderDoc(i) {
    const D0 = IM.documents[i]; document.querySelectorAll("#docpick .doc").forEach((b) => b.setAttribute("aria-pressed", +b.dataset.i === i ? "true" : "false"));
    const host = $("#docview"); host.innerHTML = "";
    const head = document.createElement("div"); head.className = "anshead";
    head.innerHTML = '<span class="lbl">If this document changed</span><span class="typed">' + esc(D0.title || D0.source || "") + '</span><p class="say">' + esc(D0.if_changed || "") + "</p>";
    host.appendChild(head);
    const refs = {}; (D0.referred_by || []).forEach((r) => { refs[r.layer] = r; });
    LAYERS.forEach((L) => {
      let h = "";
      if (L.name === D0.layer && D0.facts_anchored != null) h += '<div class="cnt2"><b>' + D0.facts_anchored + "</b>facts anchored in this document" + (D0.pieces != null ? " (" + D0.pieces + " pieces of text)" : "") + "</div>";
      const r = refs[L.name];
      if (r) { h += '<div class="cnt2"><b>' + (r.count || 0) + "</b>facts of this layer refer to it (citation found in the quote)</div>"; (r.examples || []).slice(0, 3).forEach((x) => { h += exCard(x, L.name); }); }
      if (L.name === "plant" && D0.devices_affected != null) h += '<div class="cnt2"><b>' + D0.devices_affected + "</b>lifting devices whose result depends on it</div>";
      const row = document.createElement("div"); row.className = "band lay-" + L.name;
      row.innerHTML = '<div class="bandlabel"><div class="name">' + esc(L.label) + '</div></div><div class="cards" style="--cols:3;gap:12px 14px">' + h + "</div>";
      host.appendChild(row);
    });
  }
  if (IM && typeof IM === "object") {
    let any = false; const H = IM.health;
    if (H && H.checked != null) { any = true; const e = $("#health"); e.hidden = false;
      e.textContent = H.checked + " facts checked against their source today: " + (H.quote_found != null ? H.quote_found : "?") + " still found word for word, " +
        ((H.quote_missing || 0) + (H.piece_missing || 0)) + " not found."; }
    if ((IM.documents || []).length) { any = true; const pick = $("#docpick");
      LAYERS.forEach((L) => {
        const docs = IM.documents.map((d, i) => [d, i]).filter((x) => x[0].layer === L.name); if (!docs.length) return;
        const g = document.createElement("div"); g.className = "docgroup lay-" + L.name; g.innerHTML = '<span class="g">' + esc(L.label) + "</span>";
        docs.forEach((x) => { const b = document.createElement("button"); b.type = "button"; b.className = "doc"; b.dataset.i = x[1]; b.setAttribute("aria-pressed", "false");
          b.innerHTML = esc(x[0].title || x[0].source || "") + "<small>" + (x[0].pieces != null ? x[0].pieces + " pieces · " : "") + (x[0].facts_anchored != null ? x[0].facts_anchored + " facts" : "") + "</small>";
          b.addEventListener("click", () => renderDoc(x[1])); g.appendChild(b); });
        pick.appendChild(g);
      });
      const firstDoc = IM.documents.findIndex((d) => (d.referred_by || []).length); renderDoc(firstDoc < 0 ? 0 : firstDoc);
    } else $("#docview").hidden = true;
    (IM.what_if || []).forEach((w) => { any = true;
      const d = document.createElement("div"); d.className = "whatif"; let h = "<h3>" + esc(w.title || w.id || "What if") + '</h3><p class="wnote">' + esc(w.note || "") + '</p><div class="ba">';
      [["removed", "Before: removed"], ["modified", "Modified"], ["added", "After: added"]].forEach((k) => { const a = w[k[0]] || []; const n = w[k[0] + "_total"] != null ? w[k[0] + "_total"] : a.length; if (!n) return;
        h += "<div><h4>" + k[1] + " (" + n + ")</h4><ul>" + a.map((x) => "<li>" + esc(show(x).slice(0, 260)) + "</li>").join("") + "</ul></div>"; });
      const fa = w.facts_affected || []; const fn = w.facts_total != null ? w.facts_total : fa.length;
      if (fn) h += "<div><h4>Facts that would be flagged (" + fn + ")</h4><ul>" + fa.map((x) => "<li>" + esc(show(x).slice(0, 220)) + "</li>").join("") + "</ul></div>";
      const dv = w.devices_affected || [];
      if (dv.length) h += "<div><h4>Lifting devices (" + dv.length + ")</h4><ul>" + dv.slice(0, 8).map((x) => "<li>device " + esc(x.position) + ': <span class="bef">' + esc(x.before == null ? "unknown" : x.before) + '</span> → <span class="aft">' + esc(x.after == null ? "unknown" : x.after) + "</span></li>").join("") + "</ul></div>";
      d.innerHTML = h + "</div>" + (w.result ? '<p style="margin-top:10px;font-weight:600">' + esc(w.result) + "</p>" : ""); $("#whatifs").appendChild(d); });
    $("#impact").hidden = !any;
  }

  /* numbers */
  const N = DATA.numbers; let nh = "";
  LAYERS.forEach((L) => { nh += '<div class="lay lay-' + L.name + '"><b>' + L.count.toLocaleString("en") + "</b><span>" + esc(L.label) + ": facts in force</span></div>"; });
  [[N.proposed, "facts proposed by the reader"], [N.accepted, "accepted: quote found in the source"], [N.rejected, "rejected by the rule"],
   [N.corrections, "corrections applied (old fact kept)"], [N.conflicts, "conflict settled by rank"], [N.open_points, "open points kept open"]]
    .forEach((x) => { nh += "<div><b>" + Number(x[0]).toLocaleString("en") + "</b><span>" + x[1] + "</span></div>"; });
  $("#nums").innerHTML = nh;

  const hm = /^#s(\d)(?:v(\d))?$/.exec(location.hash || "");
  if (hm && SC[+hm[1] - 1]) { si = +hm[1] - 1; vi = Math.min(SC[si].variants.length - 1, Math.max(0, (+hm[2] || 1) - 1)); }
  renderScene();
  let rt; window.addEventListener("resize", () => { clearTimeout(rt); rt = setTimeout(draw, 80); });
  window.addEventListener("load", draw);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(draw);
  setTimeout(draw, 400);
})();
</script>
"""


if __name__ == "__main__":
    out = write()
    print(f"wrote {out} ({out.stat().st_size / 1000:.0f} kB)")
