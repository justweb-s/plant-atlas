"""Owner: Core. One page to look at the ontology: its relations, and how it changes with time and events.

`python -m atlas.ontology.viewer` writes ontology/B/view.html. The page is self-contained (only d3 and the
fonts come from outside), holds every fact of the store with the fields it shows, and derives what is in
force on a chosen date in the browser. Nothing is stored back and no model is called.
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime
from pathlib import Path

from atlas.ontology.rules import verification_interval
from atlas.ontology.statements import LAYER_NOUN, LAYERS, law_tier, layer_of_statement, settle

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "ontology" / "B" / "view.html"
TODAY = date(2026, 11, 14)
RANGE = (date(2023, 6, 1), date(2027, 6, 30))
DATED = {"appliesFrom": "applies from", "repealedFrom": "repealed from",
         "placingAllowedUntil": "may be placed on the market until"}
ISO = re.compile(r"\d{4}-\d{2}-\d{2}")
OLD_REGIME, NEW_REGIME = ("DIR",), ("REG", "CORR")
DEVICE_YEARS = range(2019, RANGE[1].year + 1)
MONTHS = "January February March April May June July August September October November December".split()


def _store():
    from atlas.ontology import build

    try:
        return build.raw_store("B")
    except AttributeError:
        return build.store_for("B")


def _plain_day(day: date) -> str:
    return f"{day.day} {MONTHS[day.month - 1]} {day.year}"


def _source_noun(source_doc: str, layer: str) -> str:
    if layer == "law":
        tier = law_tier(source_doc)
        return "the law" if tier == "law" else ("an " if tier[0] in "AEIOU" else "a ") + tier
    return LAYER_NOUN.get(layer, "a source of unknown layer")


def annex_facts(statements) -> list:
    return [s for s in statements if s.predicate == "verificationInterval"]


def device_table(statements, on: date) -> list[dict]:
    """The lifting devices with what rules.verification_interval returns for each on `on`."""
    from atlas.strategies.plant import device_records

    annex = annex_facts(statements)
    rows = []
    for d in device_records(statements):
        result = verification_interval(d, annex, on)
        rows.append({"position": d["position"], "kind": d.get("kind"), "capacity_kg": d.get("capacity_kg"),
                     "year_built": d.get("year_built"), "sector": d.get("sector"),
                     "interval": result.get("interval"), "row_id": result.get("row_id") or "",
                     "why": result.get("why") or ""})
    return rows


def _devices(statements) -> list[dict]:
    """One record per device with the rule's result for every year the page can ask for.

    The rule looks at the year of the date only, so one result per year is exact for every day of that year.
    The day written inside a reason is replaced by {date}; the page writes the chosen day back.
    """
    from atlas.strategies.plant import device_records

    out = {d["position"]: {"position": d["position"], "kind": d.get("kind"), "capacity_kg": d.get("capacity_kg"),
                           "year_built": d.get("year_built"), "sector": d.get("sector"), "facts": d.get("facts", {}),
                           "by_year": {}} for d in device_records(statements)}
    for year in DEVICE_YEARS:
        day = date(year, 1, 1)
        for row in device_table(statements, day):
            out[row["position"]]["by_year"][str(year)] = {
                "interval": row["interval"], "row_id": row["row_id"], "why": row["why"].replace(str(day), "{date}")}
    return [out[k] for k in sorted(out)]


def _events(statements, devices, regime, today: date) -> list[dict]:
    events = []
    # Corrections: facts that replace another one from a given day.
    by_day: dict[str, list] = {}
    ids = {s.id: s for s in statements}
    for s in statements:
        old = ids.get(s.conflicts_with)
        if s.status == "current" and old is not None and old.status == "closed" and s.in_force_from:
            by_day.setdefault(s.in_force_from.isoformat(), []).append((old, s))
    for day, pairs in by_day.items():
        kinds = sorted({law_tier(new.source_doc) for _, new in pairs})
        events.append({"date": day, "kind": "correction", "title": f"A {' / '.join(kinds)} was published",
                       "text": f"It corrected {len(pairs)} values of source {', '.join(sorted({o.source_doc for o, _ in pairs}))}. "
                               "The old values are closed and kept. The new ones replace them.",
                       "touched": 2 * len(pairs), "ids": [x.id for pair in pairs for x in pair]})
    # Dates written in the facts themselves (only the values not closed by a correction).
    dated: dict[str, list] = {}
    for s in statements:
        if s.predicate in DATED and s.status == "current" and ISO.fullmatch(s.object) \
                and RANGE[0].isoformat() <= s.object <= RANGE[1].isoformat():
            dated.setdefault(s.object, []).append(s)
    regime_ids = set(regime["applies"]) | set(regime["repealed"])
    for day, facts in dated.items():
        text = " ".join(f"{s.subject}: {DATED[s.predicate]} {s.object_as_written}." for s in facts)
        touched = {s.id for s in facts}
        if any(s.id in regime_ids for s in facts):
            old = [s.id for s in statements if s.source_doc in OLD_REGIME and s.status != "open_point"]
            new = [s.id for s in statements if s.source_doc in NEW_REGIME and s.status == "current"
                   and s.predicate not in DATED]
            text += (f" From this day {len(new)} facts of the Regulation become applicable and "
                     f"{len(old)} facts of the Directive stop being in force.")
            touched |= set(old) | set(new)
        events.append({"date": day, "kind": "dated", "title": "A date written in the law arrives", "text": text,
                       "touched": len(touched), "ids": [s.id for s in facts]})
    # Year boundaries where the age of a device changes what the rule returns.
    for year in range(RANGE[0].year + 1, RANGE[1].year + 1):
        changed = [d["position"] for d in devices
                   if d["by_year"][str(year)] != d["by_year"][str(year - 1)]]
        if changed:
            touched = sorted({fid for d in devices if d["position"] in changed
                              for fid in (d["by_year"][str(year)]["row_id"], d["by_year"][str(year - 1)]["row_id"],
                                          d["facts"].get("year_built", "")) if fid})
            events.append({"date": f"{year}-01-01", "kind": "age", "title": "Lifting devices get one year older",
                           "text": f"The verification rule gives a different result for {len(changed)} of the "
                                   f"{len(devices)} devices (position {', '.join(map(str, changed))}). "
                                   "Derived by the rule from the year of construction, not stored.",
                           "touched": len(touched), "ids": touched})
    events.append({"date": today.isoformat(), "kind": "today", "title": "Today",
                   "text": "The day this page was built for. No fact changes on this day.", "touched": 0, "ids": []})
    return sorted(events, key=lambda e: (e["date"], e["kind"]))


def _focuses(statements, devices) -> list[dict]:
    """Ready starting points, each one a set of fact ids found in the data. Empty ones are dropped."""
    def having(text: str) -> list[str]:
        t = text.lower()
        return [s.id for s in statements if t in s.subject.lower() or t in s.object.lower()]

    ids = {s.id: s for s in statements}
    out = []
    repealed = next((s for s in statements if s.predicate == "repealedFrom" and s.source_doc in NEW_REGIME), None)
    if repealed:
        out.append({"label": repealed.subject, "hint": "what the law says will happen to it, and when",
                    "ids": having(repealed.subject)})
    conflicts = [s for s in statements if s.status == "conflict" and s.conflicts_with in ids]
    if conflicts:
        first = {s.id for s in conflicts} | {s.conflicts_with for s in conflicts}
        words = ("prima verifica", "first periodic verification", "prima delle verifiche")
        first |= {s.id for s in statements if s.predicate == "hasTimeLimit"
                  and any(w in s.subject.lower() for w in words)}
        out.append({"label": "First verification: time limit", "hint": "two sources in force disagree",
                    "ids": [s.id for s in statements if s.id in first]})
    if devices:
        pick = next((d for d in devices if len({json.dumps(v, sort_keys=True) for y, v in d["by_year"].items()
                                                 if int(y) >= RANGE[0].year}) > 1), devices[0])
        subject = f"IGEA device {pick['position']}"
        rows = {v["row_id"] for v in pick["by_year"].values() if v["row_id"]}
        wanted = {s.id for s in statements if s.subject == subject} | rows | set(pick["facts"].values())
        out.append({"label": f"Lifting device {pick['position']}", "hint": "a plant record and the Annex VII rows the rule picks for it",
                    "ids": [s.id for s in statements if s.id in wanted]})
    for label, hint in (("Substantial modification", "a defined term"), ("Annex I, Part A", "a category of Annex I")):
        out.append({"label": label, "hint": hint, "ids": having(label)})
    for layer, hint in (("manufacturer", "a product in a manufacturer's manual"), ("guidance", "a subject in public guidance"),
                        ("company", "a subject in company procedures")):
        count: dict[str, int] = {}
        for s in statements:
            if s.layer == layer and s.status != "open_point":
                count[s.subject] = count.get(s.subject, 0) + 1
        if count:
            top = max(count, key=count.get)
            out.append({"label": top, "hint": hint,
                        "ids": [s.id for s in statements if s.subject == top and s.layer == layer]})
    return [f for f in out if f["ids"]]


def build_data(store=None, today: date = TODAY) -> dict:
    store = store or _store()
    corpus = getattr(store, "corpus", None)
    statements = [s.model_copy(update={"layer": layer_of_statement(s, corpus)}) for s in store.statements]
    ids = {s.id: s for s in statements}
    facts = []
    for s in statements:
        fact = {"id": s.id, "s": s.subject, "p": s.predicate, "o": s.object_normalised or s.object, "w": s.object_as_written,
                "c": s.condition, "q": s.quote, "d": s.source_doc, "a": s.anchor, "l": s.layer, "st": s.status,
                "f": s.in_force_from.isoformat() if s.in_force_from else "",
                "t": s.in_force_to.isoformat() if s.in_force_to else "", "x": s.conflicts_with}
        if s.status == "conflict" and s.conflicts_with in ids:
            fact["y"] = settle(ids[s.conflicts_with], s, corpus)[1]   # why it lost, in the store's own words
        facts.append({k: v for k, v in fact.items() if v or k in ("id", "s", "p", "o")})
    sources: dict[str, dict] = {}
    for s in statements:
        entry = sources.setdefault(s.source_doc, {"noun": _source_noun(s.source_doc, s.layer), "version": s.source_version,
                                                  "layer": s.layer, "count": 0})
        entry["count"] += 1
    regime = {
        "applies": [s.id for s in statements if s.predicate == "appliesFrom" and s.source_doc in NEW_REGIME
                    and s.subject == "Regulation" and ISO.fullmatch(s.object)],
        "repealed": [s.id for s in statements if s.predicate == "repealedFrom" and s.source_doc in NEW_REGIME
                     and ISO.fullmatch(s.object)],
        "old": list(OLD_REGIME), "new": list(NEW_REGIME), "timetable": sorted(DATED)}
    devices = _devices(statements)
    return {
        "facts": facts, "sources": sources, "regime": regime, "devices": devices,
        "layers": [{"name": name, "count": sum(1 for s in statements if s.layer == name)} for name in LAYERS],
        "no_layer": sum(1 for s in statements if s.layer not in LAYERS),
        "events": _events(statements, devices, regime, today), "focuses": _focuses(statements, devices),
        "dated_words": DATED, "range": [RANGE[0].isoformat(), RANGE[1].isoformat()], "today": today.isoformat(),
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M"), "total": len(statements),
    }


def embedded_json(data: dict) -> str:
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return text.replace("</", "<\\/").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


def extract_data(html: str) -> dict:
    """The data embedded in a generated page (used by the tests)."""
    start = html.index("const DATA = ") + len("const DATA = ")
    end = html.index(";\n/*END-DATA*/", start)
    return json.loads(html[start:end].replace("<\\/", "</"))


def render(data: dict) -> str:
    return PAGE.replace("__DATA__", embedded_json(data))


def write(path: Path | None = None, store=None, today: date = TODAY) -> Path:
    path = Path(path or OUT)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render(build_data(store, today)), encoding="utf-8")
    return path


PAGE = r"""<title>Plant Atlas Ontology</title>
<meta charset="utf-8">
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Space+Grotesk:wght@500;600&display=swap">
<style>
:root {
  --bg: #f4f2ec; --surface: #fffdf8; --surface-2: #ebe8df; --ink: #1c2226; --muted: #5a646b; --line: #d5d0c2;
  --accent: #14323f; --accent-ink: #ffffff; --focus: #c2410c;
  --layer-law: #2a5db0; --layer-guidance: #7d47a8; --layer-manufacturer: #b25a12; --layer-company: #0b7f8c; --layer-plant: #b02f5a;
  --in-force: #2c7a36; --in-force-bg: #e3f1e2; --not-in-force: #7b6a55; --not-in-force-bg: #efe9df;
  --not-yet: #8a6d00; --mark: #fff1c2;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    color-scheme: dark;
    --bg: #14181b; --surface: #1c2226; --surface-2: #262d32; --ink: #e9e6de; --muted: #a2abb1; --line: #39424a;
    --accent: #d9e6ea; --accent-ink: #14181b; --focus: #ffa25e;
    --layer-law: #7fa8f0; --layer-guidance: #c79bea; --layer-manufacturer: #f0a560; --layer-company: #58cdd8; --layer-plant: #f287a8;
    --in-force: #7fd18a; --in-force-bg: #1d3221; --not-in-force: #bfae98; --not-in-force-bg: #332d25;
    --not-yet: #e4c75a; --mark: #4a3f14;
  }
}
:root[data-theme="dark"] {
  color-scheme: dark;
  --bg: #14181b; --surface: #1c2226; --surface-2: #262d32; --ink: #e9e6de; --muted: #a2abb1; --line: #39424a;
  --accent: #d9e6ea; --accent-ink: #14181b; --focus: #ffa25e;
  --layer-law: #7fa8f0; --layer-guidance: #c79bea; --layer-manufacturer: #f0a560; --layer-company: #58cdd8; --layer-plant: #f287a8;
  --in-force: #7fd18a; --in-force-bg: #1d3221; --not-in-force: #bfae98; --not-in-force-bg: #332d25;
  --not-yet: #e4c75a; --mark: #4a3f14;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--ink); font: 400 14px/1.5 Inter, "Helvetica Neue", Arial, sans-serif; }
.wrap { max-width: 1240px; margin: 0 auto; padding-block: 20px 40px;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); }
h1, h2, h3 { font-family: "Space Grotesk", "Trebuchet MS", Verdana, sans-serif; font-weight: 600; margin: 0; letter-spacing: -0.01em; }
h1 { font-size: 26px; } h2 { font-size: 17px; } h3 { font-size: 14px; }
p { margin: 0; }
.lead { color: var(--muted); max-width: 70ch; margin-top: 4px; }
.card { background: var(--surface); border: 1px solid var(--line); border-radius: 6px; padding: 14px; margin-top: 16px; }
.card > h2 { margin-bottom: 8px; }
.num { font-family: "Space Grotesk", "Trebuchet MS", sans-serif; font-weight: 600; }
button, input { font: inherit; color: inherit; }
button { cursor: pointer; }
:focus-visible { outline: 3px solid var(--focus); outline-offset: 2px; }
.legend { display: flex; flex-wrap: wrap; gap: 6px 16px; margin-top: 12px; font-size: 13px; }
.legend span { display: inline-flex; align-items: center; gap: 6px; }
.sw { width: 18px; height: 4px; border-radius: 2px; display: inline-block; }
.lay-law { --lc: var(--layer-law); } .lay-guidance { --lc: var(--layer-guidance); } .lay-manufacturer { --lc: var(--layer-manufacturer); }
.lay-company { --lc: var(--layer-company); } .lay-plant { --lc: var(--layer-plant); } .lay- { --lc: var(--muted); }
.sw { background: var(--lc); }

/* date */
.datebar { position: sticky; top: env(safe-area-inset-top, 0px); z-index: 5; background: var(--surface); border: 1px solid var(--line);
  border-radius: 6px; padding: 10px 14px; margin-top: 16px; box-shadow: 0 2px 0 var(--line); }
.daterow { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 14px; }
.daterow .big { font-size: 20px; min-width: 11ch; }
.daterow input[type=date] { background: var(--bg); border: 1px solid var(--line); border-radius: 4px; padding: 4px 6px; }
.btn { background: var(--surface-2); border: 1px solid var(--line); border-radius: 4px; padding: 4px 10px; }
.btn:hover { border-color: var(--ink); }
.btn.on { background: var(--accent); color: var(--accent-ink); border-color: var(--accent); }
.btn.on .small { color: inherit; opacity: .85; }
.slider { position: relative; margin-top: 6px; }
.slider input[type=range] { width: 100%; margin: 0; accent-color: var(--accent); display: block; }
.ticks { position: relative; height: 18px; }
.tick { position: absolute; top: 0; width: 12px; height: 16px; margin-left: -6px; padding: 0; border: 0; background: none; }
.tick::before { content: ""; position: absolute; left: 4px; top: 0; width: 4px; height: 14px; border-radius: 2px; background: var(--not-yet); }
.tick.k-correction::before { background: var(--layer-plant); } .tick.k-today::before { background: var(--in-force); }
.tick.k-age::before { background: var(--muted); height: 9px; }
.ends { display: flex; justify-content: space-between; color: var(--muted); font-size: 12px; }
.chips { display: flex; flex-wrap: wrap; gap: 6px; margin-left: auto; }
.chip { border-radius: 3px; padding: 2px 8px; font-size: 12px; font-weight: 500; border: 1px solid transparent; white-space: nowrap; }
.chip.in { background: var(--in-force-bg); color: var(--in-force); }
.chip.out { background: var(--not-in-force-bg); color: var(--not-in-force); }
.chip.notyet { background: var(--mark); color: var(--not-yet); }
.chip.open { border-color: var(--line); color: var(--muted); }
.chip.lay { border-color: var(--lc); color: var(--lc); }

.regime { border-left: 4px solid var(--accent); }
.regime .say { font-size: 16px; font-weight: 500; }
.reasons { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 8px; margin-top: 10px; }
.reason { text-align: left; background: var(--bg); border: 1px solid var(--line); border-radius: 4px; padding: 8px 10px; }
.reason:hover { border-color: var(--ink); }
.reason q, .quote { font-style: italic; }
.small { font-size: 12px; color: var(--muted); }

.events { list-style: none; margin: 0; padding: 0; display: grid; gap: 6px; }
.events li { display: grid; grid-template-columns: 9.5em 1fr auto; gap: 4px 12px; align-items: start; padding: 6px 8px; border-radius: 4px; border: 1px solid transparent; }
.events li.past { background: var(--bg); }
.events li.now { border-color: var(--accent); }
.events .when { background: none; border: 0; padding: 0; text-align: left; font-weight: 600; text-decoration: underline; text-underline-offset: 3px; }
.events .cnt { white-space: nowrap; color: var(--muted); font-size: 12px; }

/* focus + graph */
.focusrow { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
.focusrow .btn { text-align: left; max-width: 100%; }
.search { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
.search input { flex: 1 1 220px; min-width: 0; background: var(--bg); border: 1px solid var(--line); border-radius: 4px; padding: 6px 8px; }
.graphgrid { display: grid; grid-template-columns: minmax(0, 1.7fr) minmax(0, 1fr); gap: 14px; margin-top: 12px; }
.graphbox { border: 1px solid var(--line); border-radius: 4px; background: var(--bg); min-height: 200px; overflow: hidden; }
svg#graph { display: block; width: 100%; height: 480px; }
.edge { fill: none; stroke: var(--lc); stroke-width: 2; }
.edge.s-out, .edge.s-notyet { stroke-dasharray: 6 5; opacity: .5; }
.edge.s-open { stroke-dasharray: 1.5 5; stroke-linecap: round; opacity: .55; }
.hit { fill: none; stroke: transparent; stroke-width: 14; cursor: pointer; }
.elabel { font-size: 10px; fill: var(--muted); text-anchor: middle; pointer-events: none; paint-order: stroke; stroke: var(--bg); stroke-width: 3px; }
.elabel.s-out, .elabel.s-notyet, .elabel.s-open { opacity: .7; }
.node { cursor: pointer; }
.node circle { fill: var(--ink); stroke: var(--bg); stroke-width: 2; }
.node rect { fill: var(--bg); stroke: var(--ink); stroke-width: 1.5; }
.node.dim circle { fill: var(--muted); } .node.dim rect { stroke: var(--muted); stroke-dasharray: 3 2; }
.node text { font-size: 11px; fill: var(--ink); text-anchor: middle; paint-order: stroke; stroke: var(--bg); stroke-width: 3px; }
.node.dim text { fill: var(--muted); }
.gsel .edge { stroke-width: 4; opacity: 1; }
.node.sel circle, .node.sel rect { stroke: var(--focus); stroke-width: 3; }
.gnote { padding: 6px 10px; border-top: 1px solid var(--line); font-size: 12px; color: var(--muted); display: flex; flex-wrap: wrap; gap: 4px 14px; }
.panel { border: 1px solid var(--line); border-radius: 4px; padding: 12px; background: var(--surface); min-width: 0; overflow-wrap: anywhere; }
.panel dl { margin: 8px 0 0; display: grid; grid-template-columns: 7.5em 1fr; gap: 4px 10px; }
.panel dt { color: var(--muted); font-size: 12px; padding-top: 2px; }
.panel dd { margin: 0; }
.panel .quote { border-left: 3px solid var(--lc, var(--line)); padding-left: 8px; }
.linkish { background: none; border: 0; padding: 0; text-decoration: underline; text-underline-offset: 3px; text-align: left; }

/* lists */
.cols { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }
.col h3 { padding: 6px 8px; border-radius: 4px; }
.col.in h3 { background: var(--in-force-bg); color: var(--in-force); }
.col.out h3 { background: var(--not-in-force-bg); color: var(--not-in-force); }
.rows { list-style: none; margin: 8px 0 0; padding: 0; display: grid; gap: 6px; max-height: 560px; overflow: auto; }
.row { display: block; width: 100%; text-align: left; background: var(--bg); border: 1px solid var(--line); border-left: 4px solid var(--lc); border-radius: 4px; padding: 6px 8px; overflow-wrap: anywhere; }
.row:hover { border-color: var(--ink); border-left-color: var(--lc); }
.row .rel { color: var(--muted); }
.row .meta { display: block; font-size: 12px; color: var(--muted); margin-top: 2px; }
.row .why { display: block; font-size: 12px; margin-top: 2px; font-weight: 500; }
.col.in .why { color: var(--in-force); } .col.out .why { color: var(--not-in-force); }
.empty { color: var(--muted); padding: 8px; }

.scroll { overflow-x: auto; }
table { border-collapse: collapse; width: 100%; min-width: 760px; }
th, td { text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--line); vertical-align: top; }
th { font-size: 12px; color: var(--muted); font-weight: 500; }
td.n { font-variant-numeric: tabular-nums; }
tr.changed td { background: var(--mark); }
.tag { font-size: 11px; border: 1px solid var(--not-yet); color: var(--not-yet); border-radius: 3px; padding: 0 5px; margin-left: 6px; white-space: nowrap; }
footer { margin-top: 18px; color: var(--muted); font-size: 12px; }
@media (max-width: 820px) {
  .graphgrid, .cols { grid-template-columns: minmax(0, 1fr); }
  .events li { grid-template-columns: 1fr; }
  svg#graph { height: 400px; }
  .chips { margin-left: 0; }
}
</style>

<div class="wrap">
  <header>
    <h1>Plant Atlas Ontology</h1>
    <p class="lead">Every line here is one fact read from a real document, with the sentence it comes from. Pick a date. The page shows which facts hold on that day, which ones were corrected or lost to a stronger source, and why.</p>
    <div class="legend" id="legend" aria-label="Layers and number of facts in each"></div>
  </header>

  <section class="datebar" aria-label="Date">
    <div class="daterow">
      <span class="num big" id="dayBig"></span>
      <label class="small" for="dayField">Date</label>
      <input type="date" id="dayField">
      <button class="btn" id="todayBtn" type="button">Today</button>
      <div class="chips" id="dayChips" aria-live="polite"></div>
    </div>
    <div class="slider">
      <input type="range" id="daySlider" min="0" step="1" aria-label="Date, from 1 June 2023 to 30 June 2027">
      <div class="ticks" id="ticks"></div>
      <div class="ends"><span id="endA"></span><span>Marks are events found in the facts. Select a mark to jump to it.</span><span id="endB"></span></div>
    </div>
  </section>

  <section class="card regime" aria-live="polite">
    <h2>Which machinery law applies on this date</h2>
    <p class="say" id="regimeSay"></p>
    <p class="small" id="regimeNote"></p>
    <div class="reasons" id="regimeReasons"></div>
  </section>

  <section class="card">
    <h2>Events</h2>
    <ol class="events" id="events"></ol>
  </section>

  <section class="card">
    <h2>Relations</h2>
    <div class="search">
      <label for="q">Search a subject or a value</label>
      <input id="q" type="search" placeholder="for example: declaration of conformity" autocomplete="off">
      <button class="btn" id="qBtn" type="button">Show</button>
      <button class="btn" id="allBtn" type="button">Whole store</button>
    </div>
    <div class="focusrow" id="focuses" aria-label="Ready starting points"></div>
    <div class="graphgrid">
      <div class="graphbox">
        <svg id="graph" role="group" aria-label="Graph of the facts of the current focus"></svg>
        <div class="gnote" id="gnote"></div>
      </div>
      <aside class="panel" id="panel" aria-live="polite"></aside>
    </div>
  </section>

  <section class="card">
    <h2 id="listsTitle">Facts</h2>
    <div class="cols">
      <div class="col in"><h3 id="inTitle"></h3><ul class="rows" id="inRows"></ul></div>
      <div class="col out"><h3 id="outTitle"></h3><ul class="rows" id="outRows"></ul></div>
    </div>
  </section>

  <section class="card">
    <h2 id="devTitle">Lifting devices</h2>
    <p class="small" id="devNote"></p>
    <div class="scroll"><table>
      <thead><tr><th>No.</th><th>Kind</th><th>Capacity</th><th>Built</th><th id="ageHead">Age</th><th>Verification required</th><th>Why</th></tr></thead>
      <tbody id="devRows"></tbody>
    </table></div>
  </section>

  <footer id="footer"></footer>
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js"></script>
<script>
const DATA = __DATA__;
/*END-DATA*/
(function () {
  "use strict";
  const F = DATA.facts, byId = new Map(F.map(f => [f.id, f]));
  const replacedBy = new Map(), beats = new Map();
  F.forEach(f => { if (!f.x) return; if (f.st === "conflict") { if (!beats.has(f.x)) beats.set(f.x, []); beats.get(f.x).push(f); } else replacedBy.set(f.x, f); });
  const MONTHS = ["January","February","March","April","May","June","July","August","September","October","November","December"];
  const ISO = /^\d{4}-\d{2}-\d{2}$/;
  const DAY = 86400000, T0 = Date.parse(DATA.range[0] + "T00:00:00Z"), T1 = Date.parse(DATA.range[1] + "T00:00:00Z");
  const SPAN = Math.round((T1 - T0) / DAY);
  const TIMETABLE = new Set(DATA.regime.timetable), OLD = new Set(DATA.regime.old), NEW = new Set(DATA.regime.new);
  const LIST_CAP = 100, EDGE_CAP = 40;
  const state = { day: DATA.today, focus: null, sel: null };

  const $ = id => document.getElementById(id);
  function h(tag, attrs, ...kids) {
    const el = document.createElement(tag);
    for (const k in (attrs || {})) { if (k === "class") el.className = attrs[k]; else if (k.startsWith("on")) el.addEventListener(k.slice(2), attrs[k]); else el.setAttribute(k, attrs[k]); }
    kids.flat().forEach(k => { if (k != null && k !== false) el.append(k); });
    return el;
  }
  const fmt = iso => { const [y, m, d] = iso.split("-").map(Number); return d + " " + MONTHS[m - 1] + " " + y; };
  const idx2iso = i => new Date(T0 + i * DAY).toISOString().slice(0, 10);
  const iso2idx = iso => Math.round((Date.parse(iso + "T00:00:00Z") - T0) / DAY);
  const words = p => DATA.dated_words[p] || p.replace(/([a-z])([A-Z])/g, "$1 $2").toLowerCase();
  const val = f => f.w || f.o;
  const cut = (t, n) => t.length > n ? t.slice(0, n - 1) + "\u2026" : t;
  const src = f => f.d + ", " + (f.a || "no locator");
  const noun = f => (DATA.sources[f.d] || {}).noun || "a source";
  const layerName = f => f.l || "no layer";

  // ---- what holds on a day ------------------------------------------------
  const live = (f, day) => (f.st === "current" || f.st === "closed") && !(f.f && f.f > day) && !(f.t && f.t <= day);
  function pick(ids, day) { for (const id of ids) { const f = byId.get(id); if (f && live(f, day) && ISO.test(f.o)) return f; } return null; }
  function regime(day) { return { applies: pick(DATA.regime.applies, day), repealed: pick(DATA.regime.repealed, day) }; }
  // k: in = in force; out = closed, repealed or lost; notyet = not yet applicable; open = an open point, not a fact
  function stateOf(f, day, rg) {
    if (f.st === "open_point") return { k: "open", why: "Open point: the passage was read, but no value was fixed as a fact." };
    if (f.st === "conflict") { const w = byId.get(f.x); return { k: "out", why: w ? "Lost to " + noun(w) + ": " + val(w) + " (" + src(w) + ")." + (f.y ? " Rule: " + f.y + "." : "") : "Lost to a stronger source." }; }
    if (f.st === "proposed") return { k: "out", why: "Proposed only: not yet confirmed." };
    if (f.f && f.f > day) return { k: "notyet", why: "Not yet published on this date: " + noun(f) + " brings it on " + fmt(f.f) + "." };
    if (f.t && f.t <= day) { const r = replacedBy.get(f.id); return { k: "out", why: r ? "Corrected by " + noun(r) + " on " + fmt(f.t) + ": now " + val(r) + " (" + src(r) + ")." : "Closed on " + fmt(f.t) + "." }; }
    rg = rg || regime(day);
    if (OLD.has(f.d) && rg.repealed && day >= rg.repealed.o) return { k: "out", why: "Repealed from " + fmt(rg.repealed.o) + " (" + src(rg.repealed) + ")." };
    if (NEW.has(f.d) && !TIMETABLE.has(f.p) && rg.applies && day < rg.applies.o) return { k: "notyet", why: "Published, not yet applicable until " + fmt(rg.applies.o) + " (" + src(rg.applies) + ")." };
    let why = "In force.";
    const old = f.x && f.st !== "conflict" ? byId.get(f.x) : null;
    if (old) why = "In force. It replaced " + val(old) + " (" + src(old) + ") on " + fmt(f.f || old.t || "") + ".";
    else if (beats.has(f.id)) why = "In force. It prevails over " + beats.get(f.id).map(b => val(b) + " (" + src(b) + ")").join(", ") + ".";
    else if (OLD.has(f.d) && rg.repealed) why = "In force until it is repealed from " + fmt(rg.repealed.o) + ".";
    else if (TIMETABLE.has(f.p) && NEW.has(f.d)) why = "In force: part of the timetable of the new law.";
    return { k: "in", why };
  }
  const KLABEL = { in: "In force", out: "Not in force", notyet: "Not yet applicable", open: "Open point" };

  // ---- header -------------------------------------------------------------
  DATA.layers.forEach(l => $("legend").append(h("span", { class: "lay-" + l.name }, h("i", { class: "sw" }), l.name + " ", h("b", { class: "num" }, String(l.count)))));
  if (DATA.no_layer) $("legend").append(h("span", { class: "lay-" }, h("i", { class: "sw" }), "no layer ", h("b", { class: "num" }, String(DATA.no_layer))));
  $("footer").textContent = "Generated " + DATA.generated + " from " + DATA.total + " facts. Every value shown comes from the store; what holds on a date is derived on this page and not stored.";
  $("endA").textContent = fmt(DATA.range[0]); $("endB").textContent = fmt(DATA.range[1]);

  // ---- date control -------------------------------------------------------
  const slider = $("daySlider"), field = $("dayField");
  slider.max = SPAN; field.min = DATA.range[0]; field.max = DATA.range[1];
  DATA.events.forEach(e => {
    const b = h("button", { class: "tick k-" + e.kind, type: "button", title: fmt(e.date) + ": " + e.title, "aria-label": "Go to " + fmt(e.date) + ": " + e.title, onclick: () => setDay(e.date) });
    b.style.left = "calc(8px + (100% - 16px) * " + (iso2idx(e.date) / SPAN).toFixed(5) + ")";
    $("ticks").append(b);
  });
  slider.addEventListener("input", () => setDay(idx2iso(+slider.value)));
  field.addEventListener("change", () => { if (ISO.test(field.value)) setDay(field.value); });
  $("todayBtn").addEventListener("click", () => setDay(DATA.today));
  function setDay(iso) {
    if (iso < DATA.range[0]) iso = DATA.range[0]; if (iso > DATA.range[1]) iso = DATA.range[1];
    state.day = iso; renderDay();
  }

  // ---- focus --------------------------------------------------------------
  function focusFromQuery(q) {
    const t = q.trim().toLowerCase(); if (!t) return null;
    const ids = F.filter(f => f.s.toLowerCase().includes(t) || f.o.toLowerCase().includes(t) || (f.w || "").toLowerCase().includes(t)).map(f => f.id);
    return { label: q.trim(), hint: "search", ids, query: true };
  }
  DATA.focuses.forEach((fo, i) => $("focuses").append(h("button", { class: "btn", type: "button", "data-i": i, title: fo.hint, onclick: () => setFocus(fo) },
    h("b", null, cut(fo.label, 44)), h("span", { class: "small" }, "  " + fo.hint + " \u00b7 " + fo.ids.length))));
  function runSearch() { const fo = focusFromQuery($("q").value); if (fo) setFocus(fo); }
  $("qBtn").addEventListener("click", runSearch);
  $("q").addEventListener("keydown", e => { if (e.key === "Enter") runSearch(); });
  $("allBtn").addEventListener("click", () => setFocus(null));
  function setFocus(fo) {
    state.focus = fo; state.sel = null;
    document.querySelectorAll("#focuses .btn").forEach(b => b.classList.toggle("on", !!fo && DATA.focuses[+b.dataset.i] === fo));
    $("allBtn").classList.toggle("on", !fo);
    buildGraph(); renderDay();
  }
  const focusFacts = () => state.focus ? state.focus.ids.map(id => byId.get(id)).filter(Boolean) : F;

  // ---- graph --------------------------------------------------------------
  const svg = d3.select("#graph");
  let G = null, sim = null;
  function buildGraph() {
    if (sim) sim.stop();
    svg.selectAll("*").remove(); G = null;
    const note = $("gnote"); note.textContent = "";
    if (!state.focus) { note.textContent = "No focus chosen. The whole store has " + F.length + " facts: too many to draw. Choose a starting point or search. The two lists below cover the whole store."; svg.style("display", "none"); return; }
    svg.style("display", null);
    const all = focusFacts();
    if (!all.length) { note.textContent = "Nothing in the store matches \u201c" + state.focus.label + "\u201d."; svg.style("display", "none"); return; }
    const weight = f => (f.x || replacedBy.has(f.id) || beats.has(f.id) || f.t || f.f ? 0 : f.st === "open_point" ? 2 : 1);
    const shown = all.map((f, i) => [weight(f), i, f]).sort((a, b) => a[0] - b[0] || a[1] - b[1]).slice(0, EDGE_CAP).map(x => x[2]);
    const box = svg.node().getBoundingClientRect(), W = Math.max(300, box.width || 700), H = box.height || 480;
    svg.attr("viewBox", "0 0 " + W + " " + H);
    const nodes = new Map(), pairN = new Map();
    const node = (text, label, isSubject) => {
      const key = text.trim().toLowerCase();
      if (!nodes.has(key)) nodes.set(key, { key, label, full: text, subject: false, facts: [] });
      const n = nodes.get(key); if (isSubject) { n.subject = true; n.label = label; } return n;
    };
    const links = shown.map(f => {
      const s = node(f.s, f.s, true), t = node(f.o || "(no value)", val(f) || "(no value)", false);
      s.facts.push(f); if (t !== s) t.facts.push(f);
      const pk = s.key < t.key ? s.key + "|" + t.key : t.key + "|" + s.key, n = pairN.get(pk) || 0; pairN.set(pk, n + 1);
      return { f, source: s, target: t, bend: n ? Math.ceil(n / 2) * 22 * (n % 2 ? 1 : -1) : 0 };
    });
    const ns = [...nodes.values()];
    const PADX = Math.min(84, W / 5), PADT = 16, PADB = 26;
    const gl = svg.append("g"), gn = svg.append("g");
    const le = gl.selectAll("g").data(links).join("g").attr("class", d => "lk lay-" + (d.f.l || ""));
    le.append("path").attr("class", "edge");
    le.append("text").attr("class", "elabel").text(d => words(d.f.p));
    le.append("path").attr("class", "hit").attr("tabindex", 0).attr("role", "button")
      .attr("aria-label", d => d.f.s + " " + words(d.f.p) + " " + val(d.f))
      .on("click", (e, d) => select({ fact: d.f.id })).on("keydown", (e, d) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); select({ fact: d.f.id }); } });
    le.append("title").text(d => d.f.s + " \u2014 " + words(d.f.p) + " \u2014 " + val(d.f));
    const ne = gn.selectAll("g").data(ns).join("g").attr("class", "node").attr("tabindex", 0).attr("role", "button")
      .attr("aria-label", d => (d.subject ? "Subject: " : "Value: ") + d.full)
      .on("click", (e, d) => select({ node: d.key })).on("keydown", (e, d) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); select({ node: d.key }); } });
    ne.filter(d => d.subject).append("circle").attr("r", 7);
    ne.filter(d => !d.subject).append("rect").attr("x", -6).attr("y", -6).attr("width", 12).attr("height", 12).attr("rx", 2);
    ne.append("text").attr("dy", 20).text(d => cut(d.label, 24));
    ne.append("title").text(d => d.full === d.label ? d.full : d.label + " (" + d.full + ")");
    const tick = () => {
      ns.forEach(n => { n.x = Math.max(PADX, Math.min(W - PADX, n.x)); n.y = Math.max(PADT, Math.min(H - PADB, n.y)); });
      const path = d => { const mx = (d.source.x + d.target.x) / 2, my = (d.source.y + d.target.y) / 2, dx = d.target.x - d.source.x, dy = d.target.y - d.source.y, L = Math.hypot(dx, dy) || 1;
        d.cx = mx - dy / L * d.bend * 2; d.cy = my + dx / L * d.bend * 2;
        return "M" + d.source.x + "," + d.source.y + "Q" + d.cx + "," + d.cy + " " + d.target.x + "," + d.target.y; };
      le.select(".edge").attr("d", path); le.select(".hit").attr("d", path);
      le.select(".elabel").attr("x", d => (d.source.x + 2 * d.cx + d.target.x) / 4).attr("y", d => (d.source.y + 2 * d.cy + d.target.y) / 4 - 3);
      ne.attr("transform", d => "translate(" + d.x + "," + d.y + ")");
    };
    sim = d3.forceSimulation(ns)
      .force("link", d3.forceLink(links).distance(Math.max(90, Math.min(170, W / 4.5))).strength(0.5))
      .force("charge", d3.forceManyBody().strength(ns.length > 25 ? -420 : -900))
      .force("collide", d3.forceCollide(46))
      .force("x", d3.forceX(W / 2).strength(0.035)).force("y", d3.forceY(H / 2).strength(0.06))
      .on("tick", tick);
    sim.tick(260); tick();
    G = { le, ne, links, ns, shown };
    note.append(h("span", null, shown.length < all.length
      ? "Capped: showing " + shown.length + " of " + all.length + " facts for this focus. The lists below show them all."
      : "Showing all " + all.length + " facts of this focus."),
      h("span", null, "Round = subject. Square = value. Line colour = layer. Dashed = not in force on the date. Dotted = open point."));
  }
  function paintGraph(rg) {
    if (!G) return;
    const st = new Map(G.shown.map(f => [f.id, stateOf(f, state.day, rg).k]));
    G.le.attr("class", d => "lk lay-" + (d.f.l || "") + (state.sel && state.sel.fact === d.f.id ? " gsel" : ""));
    G.le.select(".edge").attr("class", d => "edge s-" + st.get(d.f.id));
    G.le.select(".elabel").attr("class", d => "elabel s-" + st.get(d.f.id));
    G.ne.attr("class", d => "node" + (d.facts.some(f => st.get(f.id) === "in") ? "" : " dim") + (state.sel && state.sel.node === d.key ? " sel" : ""));
  }

  // ---- side panel ---------------------------------------------------------
  function select(sel, scroll) { state.sel = sel; renderPanel(); paintGraph(regime(state.day)); if (scroll) $("panel").scrollIntoView({ behavior: "smooth", block: "nearest" }); }
  function factLink(f) { return h("button", { class: "linkish", type: "button", onclick: () => select({ fact: f.id }) }, val(f) + " (" + src(f) + ")"); }
  function renderPanel() {
    const p = $("panel"); p.textContent = ""; p.className = "panel";
    const sel = state.sel, rg = regime(state.day);
    if (!sel) { p.append(h("h3", null, "Select a line or a point"), h("p", { class: "small" }, "A line is one fact. Select it to read the sentence it comes from, where it is in the source, and what it replaced or lost to.")); return; }
    if (sel.node) {
      const n = G && G.ns.find(x => x.key === sel.node); if (!n) return;
      p.append(h("h3", null, n.full), h("p", { class: "small" }, (n.subject ? "Subject" : "Value") + " in " + n.facts.length + " drawn fact" + (n.facts.length === 1 ? "" : "s") + "."),
        h("p", null, h("button", { class: "btn", type: "button", onclick: () => { $("q").value = n.full; setFocus(focusFromQuery(n.full)); } }, "Make this the focus")));
      const ul = h("ul", { class: "rows" }); n.facts.forEach(f => ul.append(h("li", null, rowButton(f, stateOf(f, state.day, rg))))); p.append(ul); return;
    }
    const f = byId.get(sel.fact); if (!f) return;
    const s = stateOf(f, state.day, rg);
    p.classList.add("lay-" + (f.l || ""));
    const dl = h("dl");
    const add = (k, v) => dl.append(h("dt", null, k), h("dd", null, v));
    add("Subject", f.s); add("Relation", words(f.p) + " (" + f.p + ")");
    add("Value as written", f.w || "Not in the data.");
    if (f.o && f.o !== f.w) add("Normalised", f.o);
    add("Condition", f.c || "None recorded.");
    add("Quote", h("div", { class: "quote" }, "\u201c" + (f.q || "") + "\u201d"));
    add("Source", src(f) + ((DATA.sources[f.d] || {}).version ? " \u2014 " + DATA.sources[f.d].version : ""));
    add("Layer", h("span", { class: "chip lay lay-" + (f.l || "") }, layerName(f)));
    add("Status in store", f.st + (f.f ? ", from " + fmt(f.f) : "") + (f.t ? ", until " + fmt(f.t) : ""));
    const old = f.x && f.st !== "conflict" ? byId.get(f.x) : null, by = replacedBy.get(f.id), win = f.st === "conflict" ? byId.get(f.x) : null, lost = beats.get(f.id);
    if (old) add("Replaced", factLink(old));
    if (by) add("Replaced by", factLink(by));
    if (win) add("Lost to", h("span", null, factLink(win), f.y ? " \u2014 " + f.y : ""));
    if (lost) add("Prevails over", h("span", null, lost.map(factLink)));
    if (!old && !by && !win && !lost) add("Replaced or lost to", "Nothing recorded.");
    p.append(h("h3", null, cut(f.s, 90)), h("p", null, h("span", { class: "chip " + s.k }, KLABEL[s.k] + " on " + fmt(state.day)), " ", h("span", { class: "small" }, f.id)),
      h("p", { class: "small" }, s.why), dl);
  }

  // ---- lists --------------------------------------------------------------
  function rowButton(f, s) {
    return h("button", { class: "row lay-" + (f.l || ""), type: "button", onclick: () => select({ fact: f.id }, true) },
      h("span", null, h("b", null, cut(f.s, 110)), " ", h("span", { class: "rel" }, words(f.p)), " ", cut(val(f), 160), f.c ? h("span", { class: "rel" }, " (if: " + cut(f.c, 100) + ")") : null),
      h("span", { class: "meta" }, layerName(f) + " \u00b7 " + src(f)),
      h("span", { class: "why" }, s.why));
  }
  function fill(ul, items, total, emptyText) {
    ul.textContent = "";
    if (!items.length) { ul.append(h("li", { class: "empty" }, emptyText)); return; }
    items.forEach(([f, s]) => ul.append(h("li", null, rowButton(f, s))));
    if (total > items.length) ul.append(h("li", { class: "empty" }, "Capped: " + items.length + " of " + total + " shown. Choose a focus or search to narrow it."));
  }

  // ---- devices ------------------------------------------------------------
  const every = iv => { const m = /^P(\d+)Y$/.exec(iv || ""); return m ? (m[1] === "1" ? "every year" : "every " + m[1] + " years") + " (" + iv + ")" : iv; };
  const rowNo = id => { const m = /r(\d+)/.exec(id || ""); return m ? String(+m[1]) : id; };
  function renderDevices() {
    const y = state.day.slice(0, 4), tb = $("devRows"); tb.textContent = "";
    $("devTitle").textContent = "The " + DATA.devices.length + " lifting devices on " + fmt(state.day);
    $("ageHead").textContent = "Age in " + y;
    let changed = 0;
    DATA.devices.forEach(d => {
      const r = d.by_year[y] || {}, prev = d.by_year[String(+y - 1)], diff = prev && (prev.interval !== r.interval || prev.row_id !== r.row_id || prev.why !== r.why);
      if (diff) changed++;
      const need = r.interval ? h("span", null, h("b", null, every(r.interval))) : h("span", null, "unknown");
      if (diff) need.append(h("span", { class: "tag" }, "changed since " + (+y - 1)));
      const why = r.interval
        ? h("button", { class: "linkish", type: "button", onclick: () => select({ fact: r.row_id }, true) }, "Annex VII row " + rowNo(r.row_id))
        : (r.why || "No result for this year in the page.").replace("{date}", state.day);
      tb.append(h("tr", { class: diff ? "changed" : "" },
        h("td", { class: "n" }, String(d.position)),
        h("td", null, d.facts && d.facts.kind ? h("button", { class: "linkish", type: "button", onclick: () => select({ fact: d.facts.kind }, true) }, d.kind || "not in the data") : (d.kind || "not in the data")),
        h("td", { class: "n" }, d.capacity_kg != null ? d.capacity_kg + " kg" : "not in the data"),
        h("td", { class: "n" }, d.year_built != null ? String(d.year_built) : "not in the data"),
        h("td", { class: "n" }, d.year_built != null ? (+y - d.year_built) + " years" : "unknown"),
        h("td", null, need), h("td", null, why)));
    });
    const sector = DATA.devices.length && DATA.devices[0].sector;
    $("devNote").textContent = "From the plant's own list" + (sector ? " (sector of use in the data: " + sector + ")" : "") + ". The interval comes from Annex VII by type, sector and age. Age counts calendar years, as the rule does. "
      + (changed ? changed + " device" + (changed === 1 ? "" : "s") + " changed since the year before (highlighted)." : "No device changed since the year before.");
  }

  // ---- everything that depends on the date --------------------------------
  function renderDay() {
    const day = state.day, rg = regime(day);
    slider.value = iso2idx(day); field.value = day; $("dayBig").textContent = fmt(day);
    slider.setAttribute("aria-valuetext", fmt(day));
    const c = { in: 0, out: 0, notyet: 0, open: 0 };
    F.forEach(f => c[stateOf(f, day, rg).k]++);
    const chips = $("dayChips"); chips.textContent = "";
    chips.append(h("span", { class: "chip in" }, c.in + " in force"), h("span", { class: "chip notyet" }, c.notyet + " not yet applicable"),
      h("span", { class: "chip out" }, c.out + " not in force"), h("span", { class: "chip open" }, c.open + " open points"));

    // regime
    const rr = $("regimeReasons"); rr.textContent = "";
    if (rg.applies && rg.repealed) {
      const before = day < rg.applies.o;
      $("regimeSay").textContent = before
        ? "The Directive (source DIR) is the law in force. The Regulation (source REG) is published, not yet applicable until " + fmt(rg.applies.o) + "."
        : "The Regulation (source REG) applies. The Directive (source DIR) is repealed from " + fmt(rg.repealed.o) + ".";
      $("regimeNote").textContent = "Derived on this page from the two facts below, as they stood on " + fmt(day) + ". Some articles of the Regulation apply earlier: see the timetable under Events. This page does not apply those exceptions article by article.";
      [rg.applies, rg.repealed].forEach(f => rr.append(h("button", { class: "reason", type: "button", onclick: () => select({ fact: f.id }, true) },
        h("b", null, f.s + " " + words(f.p) + " " + val(f)), h("br"), h("q", null, f.q), h("br"), h("span", { class: "small" }, src(f) + " \u00b7 " + f.id))));
    } else {
      $("regimeSay").textContent = "The store has no dated fact, valid on this date, that says when the Regulation applies or when the Directive is repealed.";
      $("regimeNote").textContent = "";
    }

    // events
    const ev = $("events"); ev.textContent = "";
    DATA.events.forEach(e => {
      const li = h("li", { class: e.date < day ? "past" : e.date === day ? "now past" : "" },
        h("button", { class: "when", type: "button", onclick: () => setDay(e.date) }, fmt(e.date)),
        h("span", null, h("b", null, e.title + ". "), e.text, " ", h("span", { class: "small" }, e.date <= day ? "(happened)" : "(still ahead)")),
        h("span", { class: "cnt" }, e.touched + " fact" + (e.touched === 1 ? "" : "s") + " touched"));
      ev.append(li);
    });

    // lists
    const all = focusFacts(), ins = [], outs = [], opens = [];
    all.forEach(f => { const s = stateOf(f, day, rg); (s.k === "in" ? ins : s.k === "open" ? opens : outs).push([f, s]); });
    const cap = state.focus ? 400 : LIST_CAP;
    $("listsTitle").textContent = state.focus ? "Facts for \u201c" + state.focus.label + "\u201d" : "Facts of the whole store";
    $("inTitle").textContent = "In force on " + fmt(day) + " \u00b7 " + ins.length;
    $("outTitle").textContent = "No longer in force, or lost to a stronger source \u00b7 " + outs.length + (opens.length ? " \u00b7 plus " + opens.length + " open points" : "");
    fill($("inRows"), ins.slice(0, cap), ins.length, "No fact of this focus is in force on this date.");
    const right = outs.concat(opens);
    fill($("outRows"), right.slice(0, cap), right.length, "Nothing here: no fact of this focus was closed, corrected, not yet applicable or lost on this date.");

    paintGraph(rg); renderPanel(); renderDevices();
  }

  let rz = null;
  window.addEventListener("resize", () => { clearTimeout(rz); rz = setTimeout(() => { buildGraph(); paintGraph(regime(state.day)); }, 200); });
  setFocus(DATA.focuses[0] || null);
})();
</script>
"""


def main() -> None:
    path = write()
    data = extract_data(path.read_text(encoding="utf-8"))
    print(f"wrote {path} ({path.stat().st_size / 1e6:.2f} MB) from {data['total']} facts")
    for event in data["events"]:
        print("event", event["date"], event["kind"], event["touched"], "-", event["title"])
    for focus in data["focuses"]:
        print("focus", focus["label"], "-", focus["hint"], f"({len(focus['ids'])} facts)")


if __name__ == "__main__":
    main()
