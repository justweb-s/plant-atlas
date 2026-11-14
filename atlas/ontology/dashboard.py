"""The demo dashboard: one screen, the ontology on the left, ask / score / changes / scenes on the right.

`python -m atlas.ontology.dashboard` writes ontology/B/dashboard.html. Everything shown is read from files
already produced by the build and the evaluation; nothing is computed by a model here.
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import date
from pathlib import Path

from atlas.ontology import atlas_page
from atlas.strategies import schema_b

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "ontology" / "B" / "dashboard.html"
OTHER = "held" + "out"          # the key of the second split in the results files
DESIGN = "design"

BAND_WORDS = {
    "law": "EU and Italian binding rules",
    "guidance": "Public bodies explain the law",
    "manufacturer": "Manuals of the machines installed",
    "company": "The organisation's own equipment guidelines",
    "plant": "The plant's own equipment list",
}


REL_WORDS = {
    "requiresProcedure": "requires the procedure", "listedIn": "listed in", "appliesFrom": "applies from",
    "repealedFrom": "repealed from", "placingAllowedUntil": "may be placed on the market until",
    "retentionPeriod": "must be kept for", "definedAs": "means", "mustAccompany": "must come with",
    "hasObligation": "must", "becomesManufacturer": "counts as manufacturer when", "addressesRisk": "addresses the risk",
    "requiresMeasure": "requires the measure", "verifiedBy": "verified by", "hasTimeLimit": "within",
    "hasReach": "reach", "hasMaxPayload": "maximum payload", "isPartlyCompletedMachinery": "is partly completed machinery",
    "hasDeclaration": "has the declaration", "conformsToStandard": "conforms to", "putIntoServiceOnlyWhen": "in service only when",
    "integratorResponsibleFor": "integrator is responsible for", "hasSafetyFunction": "safety function",
    "hasStoppingLimit": "stopping limit", "minimumDistanceRule": "minimum distance rule",
    "minimumDistanceParameter": "minimum distance parameter", "protectiveFieldRange": "protective field range",
    "requiresCheckAfter": "must be checked after", "requiresPeriodicCheck": "must be checked",
    "safeguardedSpaceRule": "safeguarded space rule", "mustKeepRegister": "register required",
    "maintenanceRule": "maintenance rule", "verificationInterval": "must be verified", "deviceKind": "kind",
    "capacityKg": "capacity (kg)", "yearBuilt": "built in", "siteSector": "sector",
}
_STOP = set("how often must the which who what does do is are can from a an of be to in for when by on its it that this and or as with at under after one first out carries carried always".split())


def _short(question: str) -> str:
    words = [w.strip("?,.;:()'\"") for w in question.split()]
    keep = [w for w in words if w and w.lower() not in _STOP][:4]
    return " ".join(w if any(c.isupper() or c.isdigit() for c in w) else w.capitalize() for w in keep)


def _whole(vb: dict, verdicts: dict, impact: dict, facts: dict, store) -> tuple[dict, list]:
    """The status of the whole store, layer by layer, counted from the facts themselves."""
    known = {d["source"]: d for d in impact["documents"]}
    flagged = sorted(i for i, v in verdicts.items() if not (v.get("states") == "yes" and v.get("dropped_condition") == "no"))
    fl = set(flagged)
    layers: dict = {}
    docs: dict = {}
    for f in vb["facts"]:
        lay = layers.setdefault(f["l"], {"docs": Counter(), "rels": Counter(), "counts": Counter()})
        lay["counts"][f.get("st")] += 1
        if f["id"] in fl:
            lay["counts"]["flagged"] += 1
        if f.get("st") != "current":
            continue
        lay["docs"][f["d"]] += 1
        doc = docs.setdefault(f["d"], {"layer": f["l"], "title": known.get(f["d"], {}).get("title") or vb["sources"][f["d"]]["noun"],
                                       "if_changed": known.get(f["d"], {}).get("if_changed", ""), "ex": []})
        if f["p"] != "openPoint":
            lay["rels"][f["p"]] += 1
            if len(doc["ex"]) < 3:
                doc["ex"].append(f["id"])
                facts.setdefault(f["id"], dict(f, n=vb["sources"][f["d"]]["noun"]))
    out = {}
    for name, lay in layers.items():
        c = lay["counts"]
        out[name] = {"docs": [{"source": d, "n": n} for d, n in lay["docs"].most_common()],
                     "rels": [{"p": p, "n": n} for p, n in lay["rels"].most_common(4)],
                     "counts": {"in_force": c["current"], "closed": c["closed"], "conflict": c["conflict"],
                                "open": c["open_point"], "flagged": c["flagged"]}}
    reasons = Counter(r["reason"] if isinstance(r, dict) else getattr(r, "reason", "") for r in getattr(store, "rejections", []))
    whole = {"layers": out, "docs": docs,
             "totals": {"in_force": sum(v["counts"]["in_force"] for v in out.values()), "kept": len(vb["facts"]),
                        "documents": len({f["d"] for f in vb["facts"]}), "layers": len(out),
                        "classes": len(schema_b.CLASSES), "relations": len(schema_b.RELATIONS)},
             "reasons": [{"reason": k.replace("_", " "), "n": n} for k, n in reasons.most_common(3) if k],
             "events": [{"date": e["date"], "title": e["title"], "text": e["text"]} for e in vb.get("events", [])
                        if e.get("kind") == "correction" or e["date"] > vb["today"]]}
    return whole, flagged


DEMOS = {
    "crane": "One answer needs facts from every layer. The rule picks the right row of the law from the device's type, sector and age; search finds passages, not this path.",
    "correction": "History is kept. A correction closes the old fact and links it to the new one; nothing is deleted, so the store can be read as of any date.",
    "repeal": "A change at the top reaches the bottom. On 20 January 2027 the regime flips, and the manuals that cite the old law are flagged for review.",
    "conflict": "Sources have an order. Both statements are kept; the legislative decree prevails over the ministerial decree, and the reason is shown.",
    "arm": "A change in the plant is checked against the layers above it: the new arm's reach, from its manual, no longer fits the protected zone a public safety sheet requires.",
    "unknown": "Unknown is an answer. A missing fact is shown as missing, never guessed.",
}


DOC_NAMES = {
    "REG": "Regulation 2023/1230", "DIR": "Directive 2006/42/EC", "CORR": "Corrigendum 2023", "DLGS": "D.Lgs. 81/08 art. 69-73",
    "DLGSALLVII": "Annex VII", "DM2011": "DM 11 April 2011", "inail-guide": "INAIL guide", "robot-cell-sheet": "Robotic-cell sheet",
    "ur5e-manual": "UR5e manual", "ur10e-manual": "UR10e manual", "nanoscan3-manual": "nanoScan3 manual",
    "mastar-manual": "MA STAR manual", "unict-guideline": "Catania guideline", "univpm-guideline": "UNIVPM guideline",
    "igea-equipment": "IGEA equipment list",
}
DOC_ORDER = ["CORR", "REG", "DIR", "DM2011", "DLGS", "DLGSALLVII"]


def doc_key(source: str) -> str:
    from atlas.ontology import impact
    for key, (_, sources, _) in impact.DOCUMENTS.items():
        if source in sources:
            return key
    return source


def _docmap(store, impact_data: dict, questions: list, facts: dict, vb: dict) -> dict:
    """The documents with facts in force and the links between them, counted from the store."""
    import re
    from atlas.ontology import impact
    vbf = {f["id"]: f for f in vb["facts"]}
    known = {d["source"]: d for d in impact_data["documents"]}
    ids = {st.id: st for st in store.statements}
    current = [st for st in store.statements if st.status == "current"]
    count = Counter(doc_key(st.source_doc) for st in current)
    layer = {}
    for st in current:
        layer.setdefault(doc_key(st.source_doc), vbf[st.id]["l"])
    edges: dict = {}

    def add(a, b, kind, st=None):
        if a == b or a not in count or b not in count:
            return
        e = edges.setdefault((a, b, kind), {"a": a, "b": b, "kind": kind, "n": 0, "ex": []})
        e["n"] += 1
        if st is not None and len(e["ex"]) < 3 and st.id in vbf:
            e["ex"].append(st.id)
            facts.setdefault(st.id, dict(vbf[st.id], n=vb["sources"][vbf[st.id]["d"]]["noun"]))

    for key, (_, sources, cites) in impact.DOCUMENTS.items():
        if not cites:
            continue
        pattern = re.compile(cites)
        for st in current:
            if st.source_doc not in sources and pattern.search(f"{st.quote} {st.object_as_written}"):
                add(doc_key(st.source_doc), key, "cites", st)
    for st in store.statements:
        other = ids.get(st.conflicts_with) if st.conflicts_with else None
        if other is None:
            continue
        if st.status in ("closed", "conflict"):
            add(doc_key(other.source_doc), doc_key(st.source_doc), "corrects" if st.status == "closed" else "prevails")
        elif other.status in ("closed", "conflict") and other.conflicts_with != st.id:
            add(doc_key(st.source_doc), doc_key(other.source_doc), "corrects" if other.status == "closed" else "prevails")
    applied = known.get("DLGSALLVII", {}).get("devices_affected", 0)
    if applied and "DLGSALLVII" in count and "igea-equipment" in count:
        edges[("DLGSALLVII", "igea-equipment", "applied")] = {"a": "DLGSALLVII", "b": "igea-equipment", "kind": "applied", "n": applied, "ex": []}
    used: dict = {}
    for q in questions:
        for step in q.get("steps") or []:
            f = facts.get(step.get("f"))
            if f:
                used.setdefault(doc_key(f["d"]), [])
                if q["short"] not in used[doc_key(f["d"])]:
                    used[doc_key(f["d"])].append(q["short"])
    order = {k: i for i, k in enumerate(DOC_ORDER)}
    docs = [{"key": k, "name": DOC_NAMES.get(k, k), "title": known.get(k, {}).get("title", k), "layer": layer[k], "n": n,
             "pieces": known.get(k, {}).get("pieces"), "devices": known.get(k, {}).get("devices_affected", 0),
             "answers": used.get(k, [])}
            for k, n in sorted(count.items(), key=lambda kv: (order.get(kv[0], 99), -kv[1]))]
    group = {src: key for key, (_, sources, _) in impact.DOCUMENTS.items() for src in sources}
    return {"docs": docs, "edges": list(edges.values()), "group": group}


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _design_rows(path: Path) -> dict:
    return {r["id"]: r for r in _load(path)["rows"] if r["split"] == DESIGN}


def _design_questions() -> list[dict]:
    return [{"id": q["id"], "en": q["question_en"], "it": q.get("question_it") or q["question_en"], "short": _short(q["question_en"])}
            for q in _load(ROOT / "data" / "cq" / "cqs.json")["cqs"] if q["split"] == DESIGN]


def _totals() -> dict:
    raw = _load(ROOT / "results" / "board.json")["totals"]
    keep = ("n", "correct", "unknown", "wrong", "mean")
    return {mode: {"design": {k: raw[mode][DESIGN][k] for k in keep}, "held": {k: raw[mode][OTHER][k] for k in keep}}
            for mode in ("B", "rag")}


def _sentence(group: str, b: dict, r: dict) -> str:
    def part(name, t):
        return f"{name} is right on {t['correct']} of {t['n']}, says unknown on {t['unknown']} and is wrong on {t['wrong']}"
    first, second = (part("Plant Atlas", b), part("plain search", r))
    if r["correct"] > b["correct"]:
        first, second = part("plain search", r), part("Plant Atlas", b)
    elif r["correct"] == b["correct"]:
        return f"On {group} questions the two are level on right answers: {first}; {second}."
    return f"On {group} questions {first}; {second}."


def _row(r: dict | None) -> dict | None:
    if not r:
        return None
    return {"value": r.get("value"), "text": r.get("text") or "", "score": r.get("score")}


def build(store=None, today: date | None = None) -> dict:
    store = store or atlas_page.viewer._store()
    today = today or atlas_page.TODAY
    base = atlas_page.build_data(store, today, True)
    b_rows = _design_rows(ROOT / "results" / "B.json")
    r_rows = _design_rows(ROOT / "results" / "rag.json")
    steps = {a["id"]: a["steps"] for a in base["asks"]}
    questions = []
    for q in _design_questions():
        questions.append(dict(q, B=_row(b_rows.get(q["id"])), rag=_row(r_rows.get(q["id"])), steps=steps.get(q["id"])))
    totals = _totals()
    impact = _load(ROOT / "ontology" / "B" / "impact.json")
    verify = _load(ROOT / "ontology" / "B" / "verify_report.json")
    numbers = base["numbers"]
    vb = atlas_page.viewer.build_data(store, today)
    whole, flagged = _whole(vb, verify["verdicts"], impact, base["facts"], store)
    dmap = _docmap(store, impact, questions, base["facts"], vb)
    index = {}
    for f in vb["facts"]:
        if f.get("st") == "current" and f["id"] not in base["facts"]:
            index[f["id"]] = [f.get("s", ""), f.get("p", ""), f.get("w") or f.get("o", ""), f.get("d", ""), f.get("a", ""), f.get("l", "")]
    return {
        "facts": base["facts"], "scenes": [dict(sc, demo=DEMOS.get(sc["id"], "")) for sc in base["scenes"]], "index": index, "whole": whole, "flagged": flagged, "dmap": dmap,
        "rel": {k: REL_WORDS[k] for k in schema_b.RELATIONS},
        "layers": [dict(l, words=BAND_WORDS[l["name"]]) for l in base["layers"]],
        "scenario_label": base["scenario_label"], "today": base["today"], "today_plain": base["today_plain"],
        "questions": questions, "totals": totals,
        "sentences": {"design": _sentence("design", totals["B"]["design"], totals["rag"]["design"]),
                      "held": _sentence("held-out", totals["B"]["held"], totals["rag"]["held"])},
        "not_run": _load(ROOT / "results" / "board.json").get("not_run", []),
        "rule": {"proposed": numbers["proposed"], "accepted": numbers["accepted"], "rejected": numbers["rejected"],
                 "total": numbers["total"], "open_points": numbers["open_points"], "corrections": numbers["corrections"]},
        "health": impact["health"],
        "reader": {"checked": verify["checked"], "passed": verify["passed"], "back": verify["checked"] - verify["passed"],
                   "dropped": verify.get("dropped_condition", 0), "not_stated": verify.get("not_stated", 0),
                   "unclear": verify.get("unclear", 0)},
        "documents": [d for d in impact["documents"] if d["facts_anchored"] or d["referred_by"]],
        "what_if": [{"title": w["title"], "result": w["result"]} for w in impact["what_if"]],
    }


def embedded(data: dict) -> str:
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return text.replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


def render(data: dict) -> str:
    page = PAGE.replace("__DATA__", embedded(data))
    if len(page.encode("utf-8")) > 1_900_000:      # keep the file small: drop the index used only by live answers
        page = PAGE.replace("__DATA__", embedded(dict(data, index={})))
    return page


def write(path: Path | None = None, store=None, today: date | None = None) -> Path:
    path = Path(path or OUT)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render(build(store, today)), encoding="utf-8")
    return path


PAGE = r"""<title>Plant Atlas Demo</title>
<meta charset="utf-8">
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Space+Grotesk:wght@500;600;700&display=swap">
<style>
:root {
  --bg: #f2f4f7; --surface: #ffffff; --surface-2: #e8ecf1; --ink: #111a2a; --muted: #56627a; --line: #d2d9e3;
  --accent: #14213d; --accent-ink: #ffffff; --focus: #d9480f; --link: #5b6880;
  --law: #2c48b5; --guidance: #0c7767; --manufacturer: #a8530c; --company: #7440ad; --plant: #b12c4c;
  --law-bg: #e9edfb; --guidance-bg: #e2f3ef; --manufacturer-bg: #f8ecdf; --company-bg: #f0e8f8; --plant-bg: #f9e6eb;
  --right: #1f7a3a; --right-bg: #dff1e4; --unknown: #8a6100; --unknown-bg: #f6ecc9; --wrong: #b3261e; --wrong-bg: #f9dedb;
  --inforce: #1f7a3a; --notinforce: #6b7385; --notinforce-bg: #e4e7ec; --flag: #a04a00; --flag-bg: #fbe8d2;
  --shadow: 0 1px 2px rgba(16, 26, 43, .08);
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    color-scheme: dark;
    --bg: #0f141c; --surface: #18202c; --surface-2: #222c3a; --ink: #e8edf5; --muted: #9daabd; --line: #303c4e;
    --accent: #dfe7f5; --accent-ink: #101826; --focus: #ffa94d; --link: #93a1b8;
    --law: #8fa6ff; --guidance: #4fd1b8; --manufacturer: #f0a45c; --company: #c79bf2; --plant: #f58aa5;
    --law-bg: #1b2440; --guidance-bg: #12302b; --manufacturer-bg: #33261a; --company-bg: #2a2038; --plant-bg: #361c25;
    --right: #5fd083; --right-bg: #173a24; --unknown: #e6c05a; --unknown-bg: #3a3013; --wrong: #ff8a80; --wrong-bg: #45201d;
    --inforce: #5fd083; --notinforce: #9aa5b8; --notinforce-bg: #2a3342; --flag: #f5b06a; --flag-bg: #3d2a14;
    --shadow: 0 1px 2px rgba(0, 0, 0, .4);
  }
}
:root[data-theme="dark"] {
  color-scheme: dark;
  --bg: #0f141c; --surface: #18202c; --surface-2: #222c3a; --ink: #e8edf5; --muted: #9daabd; --line: #303c4e;
  --accent: #dfe7f5; --accent-ink: #101826; --focus: #ffa94d; --link: #93a1b8;
  --law: #8fa6ff; --guidance: #4fd1b8; --manufacturer: #f0a45c; --company: #c79bf2; --plant: #f58aa5;
  --law-bg: #1b2440; --guidance-bg: #12302b; --manufacturer-bg: #33261a; --company-bg: #2a2038; --plant-bg: #361c25;
  --right: #5fd083; --right-bg: #173a24; --unknown: #e6c05a; --unknown-bg: #3a3013; --wrong: #ff8a80; --wrong-bg: #45201d;
  --inforce: #5fd083; --notinforce: #9aa5b8; --notinforce-bg: #2a3342; --flag: #f5b06a; --flag-bg: #3d2a14;
  --shadow: 0 1px 2px rgba(0, 0, 0, .4);
}
* { box-sizing: border-box; }
html, body { height: 100%; }
body { margin: 0; background: var(--bg); color: var(--ink); font: 14px/1.4 Inter, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
h1, h2, h3, .disp { font-family: "Space Grotesk", Inter, system-ui, sans-serif; }
button, input, select { font: inherit; color: inherit; }
button { cursor: pointer; }
:focus-visible { outline: 2px solid var(--focus); outline-offset: 2px; }
.app { height: 100%; display: flex; flex-direction: column; padding: 0 max(16px, env(safe-area-inset-right, 0px)) 10px max(16px, env(safe-area-inset-left, 0px)); }
.top { display: flex; align-items: baseline; gap: 14px; padding: 9px 0 8px; flex: none; }
.top h1 { font-size: 20px; margin: 0; letter-spacing: -.01em; }
.top p { margin: 0; color: var(--muted); font-size: 13px; flex: 1; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.badge { font-size: 12px; font-weight: 600; padding: 3px 10px; border-radius: 999px; background: var(--surface-2); color: var(--muted); border: 1px solid var(--line); white-space: nowrap; }
.badge.live { background: var(--right-bg); color: var(--right); border-color: transparent; }
.grid { flex: 1; min-height: 0; display: grid; grid-template-columns: 58fr 42fr; gap: 14px; }
.left, .right { min-height: 0; min-width: 0; display: flex; flex-direction: column; background: var(--surface); border: 1px solid var(--line); border-radius: 12px; box-shadow: var(--shadow); }
.left { padding: 10px 12px 8px; }
.lhead { display: flex; align-items: baseline; gap: 12px; flex: none; margin-bottom: 6px; }
.lhead h2 { font-size: 16px; margin: 0; white-space: nowrap; }
.showing { font-size: 13px; color: var(--muted); min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.showing b { color: var(--ink); font-weight: 600; }
.bands { position: relative; flex: 1; min-height: 0; display: flex; flex-direction: column; gap: 6px; }
.band { flex: 1 1 0; min-height: 0; display: flex; gap: 10px; border-radius: 9px; padding: 7px 8px 7px 0; background: var(--lbg); overflow: hidden; }
.band[data-l="law"] { --lc: var(--law); --lbg: var(--law-bg); }
.band[data-l="guidance"] { --lc: var(--guidance); --lbg: var(--guidance-bg); }
.band[data-l="manufacturer"] { --lc: var(--manufacturer); --lbg: var(--manufacturer-bg); }
.band[data-l="company"] { --lc: var(--company); --lbg: var(--company-bg); }
.band[data-l="plant"] { --lc: var(--plant); --lbg: var(--plant-bg); }
.bname { flex: none; width: 158px; border-left: 5px solid var(--lc); padding-left: 9px; display: flex; flex-direction: column; justify-content: center; }
.bname strong { font-family: "Space Grotesk", Inter, sans-serif; font-size: 16px; color: var(--lc); }
.bname span { font-size: 12px; color: var(--muted); line-height: 1.3; }
.bname em { font-style: normal; font-size: 12px; font-weight: 600; margin-top: 3px; }
.cards { flex: 1; min-width: 0; display: flex; gap: 14px; align-items: center; }
.empty { font-size: 12.5px; color: var(--muted); opacity: .8; }
.card { position: relative; z-index: 2; flex: 1 1 0; min-width: 0; max-width: 250px; max-height: 100%; text-align: left; background: var(--surface); border: 1px solid var(--line); border-left: 3px solid var(--lc); border-radius: 8px; padding: 6px 9px; display: flex; flex-direction: column; gap: 1px; box-shadow: var(--shadow); overflow: hidden; }
.card:hover { border-color: var(--lc); }
.card { transition: opacity .35s ease-out, transform .35s ease-out; }
.card.pend { opacity: 0; transform: translateY(10px); }
svg.links .pend { opacity: 0; }
svg.links.fadein path, svg.links.fadein text { animation: fade .3s ease-out; }
.bands.fadein .card, .bands.fadein .whole { animation: rise .28s ease-out; }
.panel.fadein { animation: fade .2s ease-out; }
.val.pulse { animation: pulse .7s ease-out; transform-origin: left center; }
@keyframes fade { from { opacity: 0; } }
@keyframes rise { from { opacity: 0; transform: translateY(6px); } }
@keyframes pulse { 40% { transform: scale(1.14); color: var(--right); } }
@media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation: none !important; transition: none !important; } }
.nodes { flex: 1; min-width: 0; display: flex; flex-wrap: wrap; gap: 14px 26px; align-items: center; align-content: center; padding-left: 6px; }
.node { position: relative; z-index: 2; background: var(--surface); border: 1.5px solid var(--lc); border-radius: 999px; padding: 5px 12px; font-size: 13px; font-weight: 600; box-shadow: var(--shadow); transition: opacity .35s ease-out, transform .35s ease-out, background-color .35s ease-out; }
.node b { margin-left: 6px; color: var(--lc); }
.node.sel { background: var(--lc); color: var(--surface); } .node.sel b { color: var(--surface); }
.node.gone { opacity: .5; border-style: dashed; background: transparent; color: var(--muted); box-shadow: none; transform: scale(.94); }
.node.gone b { color: var(--muted); }
svg.links path, svg.links text { transition: opacity .35s ease-out; }
svg.links .dim { opacity: .22; }
svg.links text.dim { opacity: 0; }
svg.links .pend { opacity: 0; }
.cnt { display: grid; gap: 3px; margin: 4px 0 0; padding: 0; list-style: none; font-size: 13px; }
.cnt b { font-family: "Space Grotesk", Inter, sans-serif; font-size: 16px; }
.duo { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; align-items: stretch; }
.demo { font-size: 13px; margin: 0 0 6px !important; font-weight: 400 !important; }
.demo b { font-weight: 700; }
.card .s { font-size: 13px; color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.card .r { font-size: 13px; font-weight: 400; line-height: 1.3; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.card .src { font-size: 11px; color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.card .r b { font-weight: 600; } .card .rel { color: var(--muted); }
.chips { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 3px; min-width: 0; }
.chips .chip { margin-top: 0; }
.chip.srcc { background: var(--surface-2); color: var(--muted); font-weight: 500; }
.chip.ok { background: var(--right-bg); color: var(--inforce); }
.whole { flex: 1; min-width: 0; display: flex; flex-direction: column; justify-content: center; gap: 6px; overflow: hidden; }
.docs { display: flex; flex-wrap: wrap; gap: 5px; align-items: center; }
.doc { background: var(--surface); border: 1px solid var(--line); border-left: 3px solid var(--lc); border-radius: 6px; padding: 2px 8px; font-size: 12.5px; }
.doc:hover, .doc[aria-pressed="true"] { border-color: var(--lc); }
.doc b { font-weight: 700; margin-left: 3px; }
.rels { display: flex; flex-wrap: wrap; gap: 2px 14px; font-size: 13px; }
.rels b { font-weight: 700; }
.cnts { font-size: 12px; color: var(--muted); line-height: 1.35; }
.cnts b { color: var(--ink); }
.tl { list-style: none; margin: 4px 0 10px; padding: 0; display: grid; gap: 5px; font-size: 12.5px; color: var(--muted); }
.tl b { color: var(--ink); }
.card.off { border-left-color: var(--notinforce); background: var(--notinforce-bg); }
.card.off .r { text-decoration: line-through; text-decoration-color: var(--notinforce); color: var(--muted); }
.card.flagged { border-left-color: var(--flag); }
.chip { align-self: flex-start; max-width: 100%; font-size: 11px; font-weight: 600; padding: 1px 7px; border-radius: 999px; background: var(--notinforce-bg); color: var(--notinforce); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-top: 2px; }
.card.off .chip { background: var(--surface); }
.chip.flag { background: var(--flag-bg); color: var(--flag); }
.num { position: absolute; top: 4px; right: 5px; width: 19px; height: 19px; border-radius: 50%; background: var(--lc); color: var(--surface); font-size: 11px; font-weight: 700; display: grid; place-items: center; }
.card.numbered .s { padding-right: 22px; }
.more { position: relative; z-index: 2; flex: none; border: 1px dashed var(--lc); background: var(--surface); color: var(--lc); font-weight: 600; font-size: 12px; border-radius: 999px; padding: 4px 10px; white-space: nowrap; }
svg.links { position: absolute; inset: 0; width: 100%; height: 100%; pointer-events: none; z-index: 1; overflow: visible; }
svg.links path { fill: none; stroke: var(--link); stroke-width: 1.6; }
svg.links path.derived { stroke-dasharray: 5 4; }
svg.links text { font-size: 10.5px; fill: var(--muted); paint-order: stroke; stroke: var(--surface); stroke-width: 3px; font-family: Inter, sans-serif; }
.legend { flex: none; display: flex; gap: 16px; align-items: center; font-size: 12px; color: var(--muted); padding-top: 6px; white-space: nowrap; overflow: hidden; }
.legend i { display: inline-block; width: 26px; border-top: 2px solid var(--link); vertical-align: middle; margin-right: 6px; }
.legend i.d { border-top-style: dashed; }
.legend .k { display: inline-block; width: 10px; height: 10px; border-radius: 2px; background: var(--notinforce-bg); border: 1px solid var(--notinforce); margin-right: 5px; vertical-align: -1px; }

.tabs { flex: none; display: flex; gap: 2px; padding: 8px 10px 0; border-bottom: 1px solid var(--line); }
.tabs button { background: none; border: 0; border-bottom: 3px solid transparent; padding: 6px 14px 7px; font-family: "Space Grotesk", Inter, sans-serif; font-size: 15px; font-weight: 600; color: var(--muted); border-radius: 6px 6px 0 0; }
.tabs button[aria-selected="true"] { color: var(--ink); border-bottom-color: var(--accent); }
.panel { flex: 1; min-height: 0; overflow: auto; padding: 12px 14px; }
.panel h3 { font-size: 14px; margin: 0 0 6px; }
.lead { font-size: 13.5px; color: var(--muted); margin: 0 0 10px; }
.row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.askbox { display: flex; gap: 8px; }
.askbox input[type=text] { flex: 1; min-width: 0; padding: 8px 10px; border: 1px solid var(--line); border-radius: 8px; background: var(--bg); font-size: 14px; }
.btn { background: var(--accent); color: var(--accent-ink); border: 0; border-radius: 8px; padding: 8px 16px; font-weight: 600; }
.btn.ghost { background: var(--surface-2); color: var(--ink); padding: 5px 11px; font-size: 13px; }
.seg { display: inline-flex; border: 1px solid var(--line); border-radius: 8px; overflow: hidden; }
.seg button { background: var(--surface); border: 0; padding: 5px 11px; font-size: 13px; font-weight: 600; color: var(--muted); }
.seg button[aria-pressed="true"] { background: var(--accent); color: var(--accent-ink); }
.opts { margin: 8px 0 6px; font-size: 12.5px; color: var(--muted); }
.opts input[type=date] { padding: 4px 6px; border: 1px solid var(--line); border-radius: 6px; background: var(--bg); font-size: 12.5px; }
.qs { display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 10px; max-height: 106px; overflow: auto; }
.qs small { font-weight: 500; opacity: .65; font-size: 10.5px; }
.qs button { background: var(--surface-2); border: 1px solid transparent; border-radius: 6px; padding: 2px 7px; font-size: 11.5px; font-weight: 600; }
.qs button.has { border-color: var(--accent); }
.qs button[aria-pressed="true"] { background: var(--accent); color: var(--accent-ink); }
.ans { border: 1px solid var(--line); border-radius: 10px; padding: 10px 12px; margin-bottom: 10px; background: var(--bg); }
.ans.atlas { border-left: 4px solid var(--accent); }
.ans header { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.ans header { flex-wrap: wrap; }
.ans header h3 { margin: 0; flex: 1; font-size: 13px; color: var(--muted); font-family: Inter, sans-serif; font-weight: 600; text-transform: none; }
.val { font-family: "Space Grotesk", Inter, sans-serif; font-weight: 700; font-size: 24px; line-height: 1.2; margin: 2px 0 4px; overflow-wrap: anywhere; }
.val.long { font-size: 14px; font-weight: 600; }
.val small { font-size: 13px; font-weight: 500; color: var(--muted); font-family: Inter, sans-serif; }
.txt { font-size: 13px; margin: 0; }
.mark { font-size: 12px; font-weight: 700; padding: 2px 9px; border-radius: 999px; white-space: nowrap; }
.mark.right { background: var(--right-bg); color: var(--right); }
.mark.unknown { background: var(--unknown-bg); color: var(--unknown); }
.mark.wrong, .mark.partly { background: var(--wrong-bg); color: var(--wrong); }
.steps { margin: 8px 0 0; padding: 0 4px 0 0; list-style: none; display: grid; gap: 5px; max-height: 300px; overflow: auto; }
.txt.clip { display: -webkit-box; -webkit-line-clamp: 5; -webkit-box-orient: vertical; overflow: hidden; }
.steps button { width: 100%; text-align: left; background: var(--surface); border: 1px solid var(--line); border-radius: 7px; padding: 5px 8px 5px 32px; position: relative; font-size: 12.5px; }
.steps .n { position: absolute; left: 7px; top: 6px; width: 18px; height: 18px; border-radius: 50%; background: var(--accent); color: var(--accent-ink); font-size: 11px; font-weight: 700; display: grid; place-items: center; }
.steps q { display: block; color: var(--muted); font-style: italic; quotes: "\201C" "\201D"; display: -webkit-box; -webkit-line-clamp: 1; -webkit-box-orient: vertical; overflow: hidden; }
.steps .loc { font-size: 11px; color: var(--muted); }
.note { font-size: 12.5px; color: var(--muted); margin: 6px 0 0; }
.err { color: var(--wrong); font-weight: 600; font-size: 13px; }

.group { margin-bottom: 14px; }
.group h3 { display: flex; gap: 8px; align-items: baseline; }
.group h3 small { font-family: Inter, sans-serif; font-weight: 500; color: var(--muted); font-size: 12.5px; }
.bar { display: grid; grid-template-columns: 96px 1fr; gap: 8px; align-items: center; margin: 4px 0; font-size: 13px; }
.stack { display: flex; gap: 2px; height: 26px; }
.stack div { display: grid; place-items: center; font-size: 12.5px; font-weight: 700; border-radius: 4px; min-width: 22px; }
.stack .right { background: var(--right); color: var(--surface); }
.stack .unknown { background: var(--unknown-bg); color: var(--unknown); border: 1px solid var(--unknown); }
.stack .wrong { background: var(--wrong); color: var(--surface); }
.keys { display: flex; gap: 14px; font-size: 12px; color: var(--muted); margin-bottom: 8px; }
.keys i { display: inline-block; width: 11px; height: 11px; border-radius: 3px; margin-right: 5px; vertical-align: -1px; }
.say { font-size: 13.5px; margin: 6px 0 0; font-weight: 500; }
.strip { display: grid; grid-template-columns: repeat(11, 1fr); gap: 3px; margin-top: 8px; }
.strip div { font-size: 10.5px; text-align: center; background: var(--bg); border: 1px solid var(--line); border-radius: 5px; padding: 2px 0 3px; color: var(--muted); }
.strip span { display: flex; justify-content: center; gap: 2px; margin-top: 1px; }
.strip b { width: 15px; height: 15px; border-radius: 3px; font-size: 10px; display: grid; place-items: center; }
.strip b.right { background: var(--right); color: var(--surface); }
.strip b.unknown { background: var(--unknown-bg); color: var(--unknown); }
.strip b.wrong, .strip b.partly { background: var(--wrong); color: var(--surface); }
.facts { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin: 6px 0; }
.facts div { background: var(--bg); border: 1px solid var(--line); border-radius: 8px; padding: 6px 9px; font-size: 12px; color: var(--muted); }
.facts b { display: block; font-family: "Space Grotesk", Inter, sans-serif; font-size: 19px; color: var(--ink); }
.box { border: 1px solid var(--line); border-radius: 10px; padding: 10px 12px; background: var(--bg); margin: 8px 0; }
.box.ok { border-left: 4px solid var(--right); } .box.warn { border-left: 4px solid var(--flag); } .box.unknown { border-left: 4px solid var(--unknown); }
.box .lab { font-size: 11px; font-weight: 700; letter-spacing: .06em; color: var(--muted); }
.box p { margin: 2px 0 0; font-size: 14px; font-weight: 500; }
.box p.sub { font-size: 12.5px; font-weight: 400; color: var(--muted); margin-top: 4px; }
select { padding: 6px 8px; border: 1px solid var(--line); border-radius: 8px; background: var(--bg); max-width: 100%; }
.scenes { list-style: none; margin: 0 0 8px; padding: 0; display: grid; gap: 5px; }
.scenes button { width: 100%; text-align: left; background: var(--bg); border: 1px solid var(--line); border-radius: 8px; padding: 6px 10px; display: grid; grid-template-columns: 22px 1fr; column-gap: 6px; }
.scenes button[aria-pressed="true"] { border-color: var(--accent); box-shadow: inset 3px 0 0 var(--accent); background: var(--surface-2); }
.scenes .i { font-family: "Space Grotesk", sans-serif; font-weight: 700; color: var(--muted); grid-row: span 2; }
.scenes strong { font-size: 13.5px; }
.scenes span.c { font-size: 12.5px; color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.scenes button { min-width: 0; } .scenes button[aria-pressed="true"] span.c { white-space: normal; }
.whatif { margin: 6px 0 0; padding-left: 18px; font-size: 12.5px; color: var(--muted); }
.whatif b { color: var(--ink); font-weight: 600; }

.drawer { position: fixed; top: 0; right: 0; bottom: 0; width: min(440px, 92vw); background: var(--surface); border-left: 1px solid var(--line); box-shadow: -8px 0 30px rgba(0, 0, 0, .18); z-index: 20; padding: 14px 16px; overflow: auto; }
.drawer h3 { margin: 0 34px 2px 0; font-size: 17px; }
.drawer .x { position: absolute; top: 10px; right: 12px; background: var(--surface-2); border: 0; border-radius: 6px; padding: 4px 10px; font-weight: 700; }
.drawer blockquote { margin: 10px 0; padding: 9px 12px; background: var(--bg); border-left: 3px solid var(--lc, var(--accent)); border-radius: 0 8px 8px 0; font-size: 13.5px; overflow-wrap: anywhere; }
.drawer dl { display: grid; grid-template-columns: 92px 1fr; gap: 5px 10px; font-size: 13px; margin: 8px 0; }
.drawer dt { color: var(--muted); } .drawer dd { margin: 0; overflow-wrap: anywhere; }
.drawer .list { display: grid; gap: 6px; margin-top: 10px; }
.drawer .list .card { max-width: none; flex: none; }
[hidden] { display: none !important; }
body { font-variant-numeric: tabular-nums; }
button, a, input, select { transition: background-color .2s, border-color .2s, color .2s, box-shadow .2s, opacity .2s; }
.band { background: color-mix(in srgb, var(--lc) 7%, var(--surface)); border-left: 3px solid var(--lc); border-radius: 10px; }
.bname { border-left: 0; padding-left: 12px; }
.card, .node, .more, .doc { box-shadow: none; }
.btn { border-radius: 10px; border: 1px solid var(--accent); }
.btn.ghost { background: transparent; border: 1px solid var(--line); }
.btn.ghost:hover { border-color: var(--accent); }
.left { position: relative; padding: 12px 14px 10px; }
.lhead { align-items: center; }
.lhead .seg { margin-left: auto; flex: none; border-radius: 999px; }
.lhead .seg button { padding: 4px 12px; font-size: 12.5px; }
.tabs { margin: 10px 12px 0; padding: 3px; gap: 2px; border-bottom: 0; background: var(--surface-2); border-radius: 999px; align-self: flex-start; max-width: calc(100% - 24px); }
.tabs button { border-bottom: 0; border-radius: 999px; padding: 5px 13px; font-size: 13.5px; }
.tabs button[aria-selected="true"] { background: var(--surface); color: var(--ink); }
.nodes { flex-wrap: nowrap; justify-content: space-evenly; gap: 12px 18px; }
.band[data-l="law"] .nodes, .band[data-l="manufacturer"] .nodes { flex-wrap: wrap; justify-content: flex-start; gap: 12px 30px; }
.node { background: var(--surface); white-space: nowrap; }
.band[data-l="law"] .nodes { gap: 10px 10px; padding-left: 0; }
.band[data-l="law"] .node { padding: 4px 9px; font-size: 12.5px; }
.node.gone { opacity: 1; background: var(--surface-2); }
.node.hl { box-shadow: 0 0 0 3px color-mix(in srgb, var(--lc) 30%, transparent); }
.node .num { top: -9px; right: -7px; }
svg.links .dim { opacity: .12; }
svg.links .pend { opacity: 0; }
#dover { position: absolute; left: 14px; right: 14px; bottom: 12px; z-index: 5; background: var(--surface); border: 1px solid var(--line); border-radius: 12px; padding: 10px 12px; display: flex; gap: 10px; align-items: center; box-shadow: 0 6px 24px rgba(0, 0, 0, .16); }
#dover div { flex: 1; min-width: 0; display: grid; gap: 2px; font-size: 12px; color: var(--muted); }
#dover strong { font-size: 14px; color: var(--ink); }
#dover .w { color: var(--flag); font-weight: 600; }
.why { flex: none; display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; font-size: 12px; line-height: 1.35; color: var(--muted); padding: 0 2px 9px; }
.why b { color: var(--ink); font-weight: 600; }
.why a { color: inherit; }
.app.embed { padding: 0; }
.app.embed .top, .app.embed .why { display: none; }
@media (max-width: 900px) {
  .why { display: none; }
  html, body { height: auto; }
  .app { height: auto; }
  .grid { grid-template-columns: 1fr; }
  .band { flex: none; min-height: 110px; }
  .bname { width: 110px; }
  .top p { white-space: normal; }
  .cards { flex-wrap: wrap; }
  .card { flex: 1 1 150px; }
  svg.links { display: none; }
  .panel { overflow: visible; }
}
@media (max-height: 800px) and (min-width: 901px) {
  .card .r { -webkit-line-clamp: 1; }
  .bname span { display: none; }
  .band { padding-top: 4px; padding-bottom: 4px; }
  .card { padding: 3px 9px; }
  .docs, .rels { flex-wrap: nowrap; overflow: hidden; white-space: nowrap; }
  .doc, .docs .more { flex: none; }
  .cnts { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .whole { gap: 4px; }
}
</style>
<div class="app">
  <header class="top">
    <h1>Plant Atlas</h1>
    <p>The documents around a plant's machines, read into checked facts that keep their quote, source and layer. Answers come only from those facts.</p>
    <span class="badge" id="badge">recorded answers</span>
  </header>
  <div class="why" id="why"></div>
  <div class="grid">
    <section class="left" aria-label="The ontology">
      <div class="lhead"><h2>The ontology</h2><div class="showing" id="showing"></div><span class="seg" id="lefttoggle" aria-label="What the left panel shows"><button data-left="facts" aria-pressed="true">Facts</button><button data-left="docs" aria-pressed="false">Documents</button></span></div>
      <div class="bands" id="bands"><svg class="links" id="links" aria-hidden="true"></svg></div>
      <div class="legend"><span><i></i>link stored in the ontology</span><span><i class="d"></i>link derived by a rule or by the selection</span><span><span class="k"></span>kept, not in force</span></div>
      <div id="dover" hidden></div>
    </section>
    <section class="right">
      <div class="tabs" role="tablist" id="tabs">
        <button role="tab" data-tab="ask">Ask</button><button role="tab" data-tab="documents">Documents</button><button role="tab" data-tab="ontology">Ontology</button><button role="tab" data-tab="score">Score</button><button role="tab" data-tab="changes">Changes</button><button role="tab" data-tab="scenes">Scenes</button>
      </div>
      <div class="panel" id="panel" role="tabpanel"></div>
    </section>
  </div>
</div>
<aside class="drawer" id="drawer" hidden aria-label="Details"></aside>
<script>
const D = __DATA__;
const $ = (s, r) => (r || document).querySelector(s);
const esc = v => String(v == null ? "" : v).replace(/[&<>"']/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
const num = n => Number(n).toLocaleString("en-GB");
const LAYER = Object.fromEntries(D.layers.map(l => [l.name, l]));
const DOCLAYER = Object.fromEntries(D.documents.map(d => [d.source, d.layer]));
const DEFAULT_TAB = "ask";
const REL = D.rel; const FLAG = new Set(D.flagged);
const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
const ST_WORDS = {current: "in force", closed: "corrected", conflict: "lost to a stronger source", open_point: "open point"};
function relWords(p) { return REL[p] || String(p || "").replace(/([a-z])([A-Z])/g, "$1 $2").toLowerCase(); }
function isoLike(v) { return typeof v === "string" && /^(\d{4}-\d{2}-\d{2}|P\d+[YMD])$/.test(v); }
function plainDate(v) { const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(v); return m ? (+m[3]) + " " + MONTHS[+m[2] - 1] + " " + m[1] : v; }
function human(v, p) {
  if (v == null) return "";
  if (typeof v !== "string") return String(v);
  const m = /^P(\d+)([YMD])$/.exec(v);
  if (m) { const u = {Y: "year", M: "month", D: "day"}[m[2]]; const every = p === "verificationInterval" || p === "requiresPeriodicCheck"; return every ? (m[1] === "1" ? "every " + u : "every " + m[1] + " " + u + "s") : m[1] + " " + u + (m[1] === "1" ? "" : "s"); }
  return plainDate(v);
}
const S = {tab: "ask", left: "facts", odoc: "", timers: [], live: false, lang: "en", q: null, answer: null, scene: 0, variant: {}, change: "after", doc: "", playing: null, view: null};

/* ---------- left column ---------- */
function factCard(id, extra) {
  const f0 = D.facts[id]; const x = D.index[id];
  if (!f0 && !x) return null;
  const f = f0 || {id: id, s: x[0], p: x[1], o: x[2], d: x[3], a: x[4], l: x[5], st: "current"};
  const c = {id: id, band: f.l, s: f.s, rel: relWords(f.p), val: human(isoLike(f.o) ? f.o : (f.w || f.o), f.p), src: f.d + " \u00b7 " + f.a, fact: f, status: ST_WORDS[f.st] || "in force"};
  if (f.st && f.st !== "current") c.state = f.st === "open_point" ? "open" : "out";
  Object.assign(c, extra || {});
  if (c.chip) c.status = c.chip;
  return c;
}
const STATE_CHIP = {out: "not in force", flag: "flagged for review", undecided: "undecided", open: "open point"};
function sceneView(si, vi) {
  const sc = D.scenes[si]; const v = sc.variants[vi];
  let cards = v.cards.map(c => {
    if (!c.f) return {id: c.k, band: c.band, s: c.title, rel: "", val: c.text, src: "", state: "scenario", status: D.scenario_label, step: c.step, note: c.note, pair: c.pair};
    return factCard(c.f, {id: c.k, step: c.step, state: c.state, chip: c.tag || (c.state !== "in" ? STATE_CHIP[c.state] : ""), note: c.note, pair: c.pair});
  }).filter(Boolean);
  if (cards.some(c => c.pair != null)) {
    const inLink = new Set(); v.links.forEach(l => { inLink.add(l.a); inLink.add(l.b); });
    cards = cards.map((c, i) => [c, i]).sort((a, b) => (inLink.has(b[0].id) - inLink.has(a[0].id)) || String(a[0].pair).localeCompare(String(b[0].pair), "en", {numeric: true}) || ((a[0].state === "out" ? 0 : 1) - (b[0].state === "out" ? 0 : 1)) || a[1] - b[1]).map(p => p[0]);
  }
  return {title: "Scene: <b>" + esc(sc.title) + "</b>" + (v.label ? " \u00b7 " + esc(v.label) : ""), cards: cards, links: v.links, cap: cards.some(c => c.pair != null) ? 2 : 3};
}
function answerView(ans) {
  const cards = []; const seen = {};
  (ans.steps || []).forEach((st, i) => {
    const id = st.f || st.statement_id || ("step" + i);
    if (seen[id]) return;
    let c = factCard(id, {num: i + 1});
    if (!c) {
      const src = String(st.locator || "").split(",")[0].trim();
      c = {id: id, band: DOCLAYER[src] || "law", s: st.text || "", rel: "", val: st.quote || "", src: st.locator || "", status: "used by the answer", num: i + 1, fact: {id: id, q: st.quote, d: src, a: st.locator}};
    }
    if (st.quote && !c.fact.q) c.fact = Object.assign({}, c.fact, {q: st.quote});
    seen[id] = 1; cards.push(c);
  });
  const links = []; for (let i = 1; i < cards.length; i++) links.push({a: cards[i - 1].id, b: cards[i].id, kind: "derived"});
  return {title: "<b>How Plant Atlas reached this answer</b>: " + cards.length + " facts across " + new Set(cards.map(c => c.band)).size + " layers", cards: cards, links: links, cap: 3, reveal: true, pulse: true, answer: true};
}
function docView(doc) {
  const cards = [{id: "doc", band: doc.layer, s: doc.source, rel: "", val: doc.title, src: num(doc.pieces) + " passages", status: num(doc.facts_anchored) + " facts anchored", fact: null, plain: doc.if_changed}];
  const links = []; const extra = {};
  doc.referred_by.forEach(g => {
    g.examples.forEach(e => { cards.push({id: e.id, band: g.layer, s: e.subject, rel: relWords(e.predicate), val: human(e.value, e.predicate), src: e.source_doc + " \u00b7 " + e.anchor, status: "cites this document", flag: true, fact: {id: e.id, s: e.subject, p: e.predicate, o: e.value, q: e.quote, d: e.source_doc, a: e.anchor, l: g.layer, st: "current"}}); links.push({a: e.id, b: "doc", kind: "derived", label: "cites"}); });
    extra[g.layer] = Math.max(0, g.count - g.examples.length);
  });
  return {title: "<b>What changes if this document changes</b>: " + esc(doc.title), cards: cards, links: links, cap: 3, extra: extra};
}
function cardHtml(c, tag) {
  const off = c.state === "out"; const warn = c.state === "flag" || c.state === "scenario" || c.state === "undecided" || c.state === "open" || c.flag;
  const cls = "card" + (off ? " off" : "") + (warn ? " flagged" : "") + (c.num ? " numbered" : "");
  return "<button class='" + cls + "' data-card='" + esc(c.id) + "'" + (tag || "") + ">" + (c.num ? "<span class='num'>" + c.num + "</span>" : "") +
    "<span class='s'>" + esc(c.s) + "</span><span class='r'>" + (c.rel ? "<span class='rel'>" + esc(c.rel) + "</span> " : "") + "<b>" + esc(c.val) + "</b></span><span class='chips'>" +
    (c.src ? "<span class='chip srcc'>" + esc(c.src) + "</span>" : "") + "<span class='chip" + (off ? "" : warn ? " flag" : " ok") + "'>" + esc(c.status || "in force") + "</span>" +
    (c.fact && FLAG.has(c.fact.id) ? "<span class='chip flag'>flagged by second reader</span>" : "") + "</span></button>";
}
function wholeHtml(layer) {
  const W = D.whole.layers[layer]; if (!W) return "<div class='cards'><span class='empty'>No fact in this layer.</span></div>";
  const c = W.counts; const more = W.docs.length - 6;
  return "<div class='whole'><div class='docs'>" + W.docs.slice(0, 6).map(d => "<button class='doc' data-doc=\"" + esc(d.source) + "\" title=\"" + esc(D.whole.docs[d.source].title) + "\">" + esc(d.source) + "<b>" + num(d.n) + "</b></button>").join("") + (more > 0 ? "<button class='more' data-moredocs='" + layer + "'>+" + more + " more</button>" : "") + "</div>" +
    "<div class='rels'>" + W.rels.map(r => "<span>" + esc(relWords(r.p)) + " <b>" + num(r.n) + "</b></span>").join("") + "</div>" +
    "<div class='cnts'><b>" + num(c.in_force) + "</b> in force \u00b7 <b>" + num(c.closed) + "</b> corrected and kept \u00b7 <b>" + num(c.conflict) + "</b> lost to a stronger source \u00b7 <b>" + num(c.open) + "</b> open points \u00b7 <b>" + num(c.flagged) + "</b> flagged by second reader</div></div>";
}
function wholeView() {
  const doc = D.whole.docs[S.odoc];
  if (!doc) return {title: "<b>The whole ontology</b>: each layer's documents, most used relations and status", whole: true, cards: [], links: []};
  return {title: "Document <b>" + esc(S.odoc) + "</b>: " + esc(doc.title) + " \u00b7 example facts in force", whole: true, cards: doc.ex.map(i => factCard(i)).filter(Boolean), links: []};
}
function leftMode() { return S.tab === "documents" ? "docs" : S.left; }
function setToggle() { document.querySelectorAll("#lefttoggle button").forEach(b => b.setAttribute("aria-pressed", b.dataset.left === leftMode())); }
function showLeft(view) {
  S.factView = view; setToggle();
  if (leftMode() === "docs") { showDocMap(); return; }
  $("#dover").hidden = true;
  S.view = view; $("#showing").innerHTML = view.title;
  const bands = $("#bands"); bands.querySelectorAll(".band").forEach(b => b.remove());
  D.layers.forEach(l => {
    const mine = view.cards.filter(c => c.band === l.name); const shown = mine.slice(0, view.cap || 3);
    const hidden = mine.length - shown.length + ((view.extra || {})[l.name] || 0);
    const el = document.createElement("div"); el.className = "band"; el.dataset.l = l.name;
    el.innerHTML = "<div class='bname'><strong>" + esc(l.label) + "</strong><span>" + esc(l.words) + "</span><em>" + num(l.count) + " facts in force</em></div>" + (view.whole && !mine.length ? wholeHtml(l.name) : "<div class='cards'>" +
      (shown.length ? shown.map(c => cardHtml(c)).join("") : "<span class='empty'>No fact of this layer in play here.</span>") +
      (hidden > 0 ? "<button class='more' data-more='" + l.name + "'>+" + hidden + " more</button>" : "") + "</div>");
    bands.appendChild(el);
  });
  S.timers.forEach(clearTimeout); S.timers = [];
  const reduce = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
  const reveal = !!view.reveal && !reduce;
  bands.classList.toggle("fadein", !reveal); $("#links").classList.toggle("fadein", !reveal);
  if (reveal) bands.querySelectorAll(".card").forEach(c => c.classList.add("pend"));
  requestAnimationFrame(() => { drawLinks(reveal); if (reveal) runReveal(view); });
}
function drawIn(p) {
  p.classList.remove("pend"); if (p.tagName.toLowerCase() !== "path") return;
  const L = p.getTotalLength(); p.style.strokeDasharray = L; p.style.strokeDashoffset = L; p.getBoundingClientRect();
  p.style.transition = "stroke-dashoffset .45s ease-out"; p.style.strokeDashoffset = 0;
  S.timers.push(setTimeout(() => { p.style.transition = ""; p.style.strokeDasharray = ""; p.style.strokeDashoffset = ""; }, 480));
}
function runReveal(view) {
  const els = Array.from(document.querySelectorAll("#bands .card"));
  const key = el => { const c = view.cards.find(c => c.id === el.dataset.card); return c ? (c.num != null ? c.num : (c.step || 0)) : 0; };
  els.sort((a, b) => key(a) - key(b));
  const gap = view.gap || 600; const done = new Set();
  els.forEach((el, i) => S.timers.push(setTimeout(() => {
    el.classList.remove("pend"); done.add(el.dataset.card);
    document.querySelectorAll("#links .pend").forEach(p => { if (done.has(p.dataset.a) && done.has(p.dataset.b)) drawIn(p); });
  }, 120 + i * gap)));
  if (view.pulse) S.timers.push(setTimeout(() => { const v = document.querySelector(".ans.atlas .val"); if (v) { v.classList.remove("pulse"); v.getBoundingClientRect(); v.classList.add("pulse"); } }, 120 + els.length * gap));
}
function drawLinks(hide) {
  const svg = $("#links"); const view = S.view; if (!view) return;
  const box = $("#bands").getBoundingClientRect(); let out = "";
  const pos = id => { const el = document.querySelector("#bands [data-card='" + CSS.escape(id) + "']"); if (!el) return null; const r = el.getBoundingClientRect(); return {l: r.left - box.left, r: r.right - box.left, t: r.top - box.top, b: r.bottom - box.top, x: (r.left + r.right) / 2 - box.left, y: (r.top + r.bottom) / 2 - box.top}; };
  (view.links || []).forEach(k => {
    const a = pos(k.a), b = pos(k.b); if (!a || !b) return;
    let d, lx, ly;
    if (Math.abs(a.y - b.y) < 20) { const p = a.x < b.x ? [a, b] : [b, a]; d = "M" + p[0].r + " " + p[0].y + " L" + p[1].l + " " + p[1].y; lx = (p[0].r + p[1].l) / 2; ly = p[0].y - 5; }
    else { const up = a.y > b.y ? [b, a] : [a, b]; const y1 = up[0].b, y2 = up[1].t, m = (y1 + y2) / 2; d = "M" + up[0].x + " " + y1 + " C" + up[0].x + " " + m + " " + up[1].x + " " + m + " " + up[1].x + " " + y2; lx = (up[0].x + up[1].x) / 2; ly = m - 3; }
    const tag = (hide === true || k.hidden ? " pend" : "") + (k.dim ? " dim" : "") + "' data-a='" + esc(k.a) + "' data-b='" + esc(k.b) + "'";
    out += "<path class='" + (k.kind === "stored" ? "stored" : "derived") + tag + (k.w ? " style='stroke-width:" + k.w + "px'" : "") + " d='" + d + "'/>";
    if (k.text || (k.label && k.kind === "stored")) out += "<text class='" + tag + " text-anchor='middle' x='" + lx + "' y='" + ly + "'>" + esc(k.text || k.label) + "</text>";
  });
  svg.innerHTML = out;
}
window.addEventListener("resize", () => drawLinks(false));

/* ---------- drawer ---------- */
function openCard(c) {
  const f = c.fact || {}; const l = LAYER[c.band] || {};
  const status = c.status || "in force";
  const rows = [["Layer", l.label], ["Status", status], ["Second reader", f.id && FLAG.has(f.id) ? "sent back; not applied to the answers" : ""], ["Relation", f.p], ["As written", f.w], ["Value stored", f.o && f.o !== f.w ? f.o : ""], ["Source", f.d ? f.d + (f.n ? " (" + f.n + ")" : "") : ""], ["Locator", f.a], ["Condition", f.c], ["Why here", c.note], ["Replaced by", f.x && D.facts[f.x] ? (D.facts[f.x].w || D.facts[f.x].o) + " (" + f.x + ")" : ""], ["Fact id", f.id]];
  $("#drawer").innerHTML = "<button class='x' data-close>Close</button><h3>" + esc(c.s) + "</h3><div>" + esc(c.rel ? c.rel + " " : "") + "<b>" + esc(c.val) + "</b></div>" +
    (f.q ? "<blockquote>" + esc(f.q) + "</blockquote>" : (c.plain ? "<blockquote>" + esc(c.plain) + "</blockquote>" : "<p class='note'>" + esc(c.state === "scenario" ? "This value is a " + D.scenario_label + "." : "The quote of this fact is not embedded in the page; the live view has it.") + "</p>")) +
    "<dl>" + rows.filter(r => r[1]).map(r => "<dt>" + r[0] + "</dt><dd>" + esc(r[1]) + "</dd>").join("") + "</dl>";
  $("#drawer").style.setProperty("--lc", "var(--" + (c.band || "law") + ")"); $("#drawer").hidden = false;
}
function openMore(layer) {
  const mine = S.view.cards.filter(c => c.band === layer); const extra = (S.view.extra || {})[layer] || 0;
  $("#drawer").innerHTML = "<button class='x' data-close>Close</button><h3>" + esc(LAYER[layer].label) + ": " + mine.length + " facts in play</h3>" +
    (extra ? "<p class='note'>" + extra + " more facts of this layer cite the document; these are the examples kept in the impact file.</p>" : "") +
    "<div class='list' style='--lc:var(--" + layer + ")'>" + mine.map(c => cardHtml(c, " data-indrawer='1'")).join("") + "</div>";
  $("#drawer").hidden = false;
}
document.addEventListener("click", e => {
  const dmo = e.target.closest("[data-dmo]"); if (dmo) { const k = S.dm.pick; if (dmo.dataset.dmo === "close") S.dm.pick = null; else if (S.dm.off.has(k)) S.dm.off.delete(k); else S.dm.off.add(k); showDocMap(); return; }
  const lt = e.target.closest("[data-left]"); if (lt) { S.left = lt.dataset.left; setToggle(); if (S.tab !== "documents") { if (S.left === "docs") showDocMap(); else showLeft(S.factView || sceneView(0, 0)); } return; }
  const nd = e.target.closest("[data-node]"); if (nd) { S.dm.sel = nd.dataset.node; if (S.tab === "documents") renderDocuments(); else { S.dm.pick = S.dm.sel; showDocMap(); } return; }
  const t = e.target.closest("[data-card],[data-more],[data-close],[data-doc],[data-moredocs]");
  if (!t) { if (!$("#drawer").hidden && !e.target.closest("#drawer") && !e.target.closest("[data-step]")) $("#drawer").hidden = true; return; }
  if (t.dataset.close != null) { $("#drawer").hidden = true; return; }
  if (t.dataset.more) { openMore(t.dataset.more); return; }
  if (t.dataset.doc) { $("#drawer").hidden = true; S.odoc = t.dataset.doc; setTab("ontology"); return; }
  if (t.dataset.moredocs) { const L = t.dataset.moredocs; $("#drawer").innerHTML = "<button class='x' data-close>Close</button><h3>" + esc(LAYER[L].label) + ": documents with facts in force</h3><div class='docs' style='--lc:var(--" + L + ");margin-top:10px'>" + D.whole.layers[L].docs.map(d => "<button class='doc' data-doc=\"" + esc(d.source) + "\">" + esc(d.source) + "<b>" + num(d.n) + "</b> " + esc(D.whole.docs[d.source].title) + "</button>").join("") + "</div>"; $("#drawer").hidden = false; return; }
  const c = S.view.cards.find(c => c.id === t.dataset.card); if (c) openCard(c);
});
document.addEventListener("keydown", e => { if (e.key === "Escape") $("#drawer").hidden = true; });

/* ---------- ask ---------- */
function mark(score, value) {
  if (score == null) return null;
  if (score >= 0.999) return {k: "right", t: "right"};
  if (score === 0 && (value == null || value === "" || value === "unknown")) return {k: "unknown", t: "unknown"};
  if (score > 0) return {k: "partly", t: "partly right (" + score.toFixed(2) + ")"};
  return {k: "wrong", t: "wrong"};
}
function words(v) {
  const m = /^P(\d+)([YMD])$/.exec(v); if (!m) return "";
  const u = {Y: "year", M: "month", D: "day"}[m[2]]; return m[1] === "1" ? "every " + u : "every " + m[1] + " " + u + "s";
}
function valHtml(v) {
  if (v == null || v === "") return "<div class='val'>unknown</div>";
  if (v === true || v === false) return "<div class='val'>" + (v ? "Yes" : "No") + "</div>";
  const s = Array.isArray(v) ? v.join("; ") : (typeof v === "object" ? JSON.stringify(v) : String(v));
  const w = words(s);
  return "<div class='val" + (s.length > 48 ? " long" : "") + "'>" + esc(s) + (w ? " <small>" + w + "</small>" : "") + "</div>";
}
function ansPanel(kind, title, a) {
  let h = "<div class='ans " + kind + "'><header><h3>" + title + "</h3>";
  if (!a) return h + "</header><p class='note'>Waiting for the answer.</p></div>";
  if (a.error) return h + "</header><p class='err'>" + esc(a.error) + "</p></div>";
  const m = mark(a.score, a.value); if (m) h += "<span class='mark " + m.k + "'>" + m.t + "</span>";
  h += "</header>" + valHtml(a.value) + "<p class='txt clip' title=\"" + esc(a.text) + "\">" + esc(a.text) + "</p>";
  if (kind === "rag") h += "<p class='note'>plain search read passages; it has no path to show</p>";
  else if (!(a.steps && a.steps.length) && !S.live) h += "<p class='note'>No recorded steps for this question: open live to see the facts used.</p>";
  return h + "</div>";
}
function stepsHtml(a) {
  if (!a || !a.steps || !a.steps.length) return "";
  return "<div class='row' style='justify-content:space-between'><h3 style='margin:0'>The path: " + a.steps.length + " steps through the ontology</h3><button class='btn ghost' id='showfacts'>Replay path</button></div><ol class='steps'>" +
    a.steps.map((s, i) => "<li><button data-step='" + i + "'><span class='n'>" + (i + 1) + "</span>" + esc(s.text || "") + (s.quote ? "<q>" + esc(s.quote) + "</q>" : "") + "<span class='loc'>" + esc(s.locator || "") + "</span></button></li>").join("") + "</ol>";
}
function renderAsk() {
  const q = S.q; const text = S.text != null ? S.text : (q ? q[S.lang] : "");
  let h = "<form class='askbox' id='askform'><input type='text' id='qtext' aria-label='Question' placeholder='Ask a question about the plant, its machines or the rules' value=\"" + esc(text) + "\"><button class='btn'>Ask</button></form>" +
    "<div class='row opts'><span class='seg' aria-label='Question language'><button type='button' data-lang='en' aria-pressed='" + (S.lang === "en") + "'>EN</button><button type='button' data-lang='it' aria-pressed='" + (S.lang === "it") + "'>IT</button></span>" +
    "<label>as of <input type='date' id='asof' value='" + esc(S.asof || "") + "'></label><span>" + (S.live ? "answers computed now" : "the date is used by live answers only") + "</span></div>" +
    "<div class='qs' aria-label='Design questions'>" + D.questions.map(x => "<button data-q='" + x.id + "' title=\"" + esc(x[S.lang]) + "\" class='" + (x.steps ? "has" : "") + "' aria-pressed='" + (q && q.id === x.id) + "'><small>" + x.id.replace("CQ", "Q") + "</small> " + esc(x.short) + "</button>").join("") + "</div>";
  if (S.answer) h += "<div class='duo'>" + ansPanel("atlas", "Plant Atlas, from checked facts", S.answer.B) + ansPanel("rag", "Plain search (RAG)", S.answer.rag) + "</div>" + stepsHtml(S.answer.B);
  else if (S.miss) h += "<p class='note'>" + esc(S.miss) + "</p>";
  $("#panel").innerHTML = h;
}
function recorded(q) { return {B: q.B ? Object.assign({steps: q.steps}, q.B) : {error: "no recorded answer"}, rag: q.rag || {error: "no recorded answer"}}; }
async function call(mode, question, cq) {
  try {
    const r = await fetch("/api/answer", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({mode: mode, question: question, as_of: S.asof || null, lang: S.lang, cq: cq})});
    const j = await r.json();
    if (j.error) return {error: (j.error.state || "error").replace(/_/g, " ") + (j.error.detail ? ": " + j.error.detail : "")};
    if (!j.answer) return {error: "no answer (" + r.status + ")"};
    return {value: j.answer.value, text: j.answer.text, steps: j.answer.steps, score: j.score == null ? null : j.score};
  } catch (err) { return {error: "the server did not answer"}; }
}
async function ask(text, q, light) {
  S.text = text; S.q = q; S.miss = null;
  if (S.live) {
    S.answer = {B: null, rag: null}; renderAsk();
    const cq = q ? q.id : null; const mine = S.answer;
    call("B", text, cq).then(a => { mine.B = a; if (S.answer === mine && S.tab === "ask") { renderAsk(); if (a.steps && a.steps.length) showLeft(answerView(a)); } });
    call("rag", text, cq).then(a => { mine.rag = a; if (S.answer === mine && S.tab === "ask") renderAsk(); });
    return;
  }
  if (!q) { S.answer = null; S.miss = "No recorded answer for this question. This page is showing recorded answers: pick one of the questions above, or open it from the live server to ask anything."; renderAsk(); return; }
  S.answer = recorded(q); renderAsk();
  if (light && q.steps) showLeft(answerView(S.answer.B));
}
function findQ(text) { const t = text.trim().toLowerCase(); return D.questions.find(x => x.en.toLowerCase() === t || x.it.toLowerCase() === t) || null; }

/* ---------- ontology ---------- */
function renderOntology() {
  const T = D.whole.totals, H = D.health, R = D.rule; const doc = D.whole.docs[S.odoc];
  let h = "<p class='lead'>The whole store: every fact read from the documents, with its quote, source and layer.</p>" +
    "<div class='facts'><div><b>" + num(T.in_force) + "</b>facts in force</div><div><b>" + num(T.kept) + "</b>facts kept in all</div><div><b>" + num(T.documents) + "</b>documents with facts</div><div><b>" + T.layers + "</b>layers</div><div><b>" + T.classes + "</b>classes in the schema</div><div><b>" + T.relations + "</b>relations in the schema</div></div>";
  if (doc) h += "<div class='box warn'><div class='lab'>DOCUMENT " + esc(S.odoc) + "</div><p>" + esc(doc.title) + "</p>" + (doc.if_changed ? "<p class='sub'>" + esc(doc.if_changed) + "</p>" : "") + "<div class='row' style='margin-top:6px'><button class='btn ghost' id='odback'>Back to the whole store</button></div></div>";
  h += "<p class='note'><b style='color:var(--ink)'>Health check:</b> " + num(H.checked) + " facts checked, " + num(H.quote_found) + " still found word for word in their documents.</p>" +
    "<h3 style='margin-top:12px'>The rule in numbers: no quote, no fact</h3><p class='note' style='margin-top:0'><b style='color:var(--ink)'>" + num(R.proposed) + "</b> proposed, <b style='color:var(--ink)'>" + num(R.accepted) + "</b> accepted with their quote, <b style='color:var(--ink)'>" + num(R.rejected) + "</b> refused" + (D.whole.reasons.length ? " (" + D.whole.reasons.map(r => r.reason + " " + r.n).join(", ") + ")" : "") + ".</p>" +
    "<h3 style='margin-top:12px'>What happened, and what will</h3><ul class='tl'>" + D.whole.events.map(e => "<li><b>" + esc(plainDate(e.date)) + "</b> \u00b7 " + esc(e.title) + ". " + esc(e.text) + "</li>").join("") + "</ul>" +
    "<div class='row'><button class='btn' data-go='scenes'>See the six scenes</button><button class='btn ghost' data-go='changes'>What changes</button><button class='btn ghost' data-go='score'>The score</button></div>" +
    "<p class='note'>Click a document on the left to see three of its facts.</p>";
  $("#panel").innerHTML = h; showLeft(wholeView());
}

/* ---------- documents ---------- */
const DM = D.dmap; const DOC = Object.fromEntries(DM.docs.map(d => [d.key, d]));
S.dm = {sel: DOC.DIR ? "DIR" : DM.docs[0].key, off: new Set(), prev: new Set(), msg: "", anim: false};
const EDGE_WORD = {cites: "cites", corrects: "corrects", prevails: "prevails over", applied: "is applied to"};
function reduced() { return !!(window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches); }
function showDocMap() {
  S.timers.forEach(clearTimeout); S.timers = [];
  setToggle(); const inTab = S.tab === "documents";
  const prev = S.dm.prev, off = S.dm.off, sel = inTab ? S.dm.sel : (S.dm.pick || null); const hl = inTab ? [] : pathDocs();
  const bands = $("#bands"); bands.querySelectorAll(".band").forEach(b => b.remove()); bands.classList.remove("fadein"); $("#links").classList.remove("fadein");
  D.layers.forEach(l => {
    const el = document.createElement("div"); el.className = "band"; el.dataset.l = l.name;
    el.innerHTML = "<div class='bname'><strong>" + esc(l.label) + "</strong><span>" + esc(l.words) + "</span><em>" + num(DM.docs.filter(d => d.layer === l.name && !off.has(d.key)).reduce((n, d) => n + d.n, 0)) + " facts in force</em></div><div class='nodes'>" +
      DM.docs.filter(d => d.layer === l.name).map(d => "<button class='node" + (prev.has(d.key) ? " gone" : "") + (d.key === sel ? " sel" : "") + (hl.indexOf(d.key) >= 0 ? " hl" : "") + "' data-node=\"" + esc(d.key) + "\" data-card=\"" + esc(d.key) + "\" title=\"" + esc(d.title) + "\">" + esc(d.name) + "<b>" + num(d.n) + "</b>" + (hl.indexOf(d.key) >= 0 ? "<span class='num'>" + (hl.indexOf(d.key) + 1) + "</span>" : "") + "</button>").join("") + "</div>";
    bands.appendChild(el);
  });
  S.view = {cards: [], links: DM.edges.map(e => ({a: e.a, b: e.b, kind: e.kind === "cites" || e.kind === "applied" ? "derived" : "stored", w: (1.2 + Math.min(3.6, Math.sqrt(e.n) * .7)).toFixed(1), text: e.a === sel || e.b === sel ? EDGE_WORD[e.kind] + " \u00b7 " + e.n : "", hidden: prev.has(e.a) || prev.has(e.b), dim: (sel || hl.length) ? (e.a !== sel && e.b !== sel) : false}))};
  for (let i = 1; i < hl.length; i++) S.view.links.push({a: hl[i - 1], b: hl[i], kind: "derived", w: 2.4, hidden: prev.has(hl[i - 1]) || prev.has(hl[i])});
  const on = DM.docs.filter(d => !off.has(d.key));
  renderOver();
  $("#showing").innerHTML = hl.length ? "<b>The agent's path through the documents</b>: " + hl.length + " documents, numbered in the order the agent used them" : "<b>The document map</b>: " + on.length + " documents, " + num(on.reduce((n, d) => n + d.n, 0)) + " facts in force" + (off.size ? " \u00b7 " + off.size + " withdrawn and kept" : "");
  requestAnimationFrame(() => { drawLinks(false); requestAnimationFrame(() => {
    document.querySelectorAll("#bands .node").forEach(n => n.classList.toggle("gone", off.has(n.dataset.node)));
    document.querySelectorAll("#links [data-a]").forEach(p => { const was = p.classList.contains("pend"); const now = off.has(p.dataset.a) || off.has(p.dataset.b); if (now) p.classList.add("pend"); else if (was) { if (reduced()) p.classList.remove("pend"); else S.timers.push(setTimeout(() => drawIn(p), 350)); } });
    S.view.links.forEach(k => { k.hidden = off.has(k.a) || off.has(k.b); });
    S.dm.prev = new Set(off);
  }); });
}
function pathDocs() {
  const v = S.factView; if (!v || !v.answer) return []; const out = [];
  v.cards.slice().sort((a, b) => a.num - b.num).forEach(c => { const src = c.fact && c.fact.d; const k = DM.group[src] || src; if (DOC[k] && out.indexOf(k) < 0) out.push(k); });
  return out;
}
function renderOver() {
  const o = $("#dover"); const d = S.tab !== "documents" && S.dm.pick ? DOC[S.dm.pick] : null;
  if (!d) { o.hidden = true; return; }
  const off = S.dm.off.has(d.key); const inc = DM.edges.filter(e => e.b === d.key), out = DM.edges.filter(e => e.a === d.key);
  const M = inc.filter(e => e.kind === "cites" && !S.dm.off.has(e.a)).reduce((n, e) => n + e.n, 0);
  const links = out.map(e => EDGE_WORD[e.kind] + " " + DOC[e.b].name + " (" + e.n + ")").concat(inc.map(e => DOC[e.a].name + " " + EDGE_WORD[e.kind] + " it (" + e.n + ")"));
  o.innerHTML = "<div><strong>" + esc(d.title) + "</strong><span>" + esc(LAYER[d.layer].label) + " \u00b7 " + num(d.n) + " facts in force" + (off ? " when present" : "") + (links.length ? " \u00b7 " + esc(links.join(", ")) : "") + "</span>" +
    (off ? "<span class='w'>Without it: " + num(d.n) + " facts leave the ontology (kept as withdrawn, not deleted), " + num(M) + " facts that cite it are flagged for review, " + num(d.devices) + " lifting devices lose their result.</span>" : "") +
    "</div><button class='btn' data-dmo='toggle'>" + (off ? "Put it back" : "Remove") + "</button><button class='btn ghost' data-dmo='close'>Close</button>";
  o.hidden = false;
}
function countUp() {
  const go = S.dm.anim && !reduced(); S.dm.anim = false;
  document.querySelectorAll("#panel [data-count]").forEach(el => {
    const to = +el.dataset.count; if (!go) { el.textContent = num(to); return; }
    const t0 = performance.now(); const tick = t => { const k = Math.min(1, (t - t0) / 800); el.textContent = num(Math.round(to * (1 - Math.pow(1 - k, 3)))); if (k < 1) requestAnimationFrame(tick); }; el.textContent = "0"; requestAnimationFrame(tick);
  });
}
function renderDocuments() {
  const d = DOC[S.dm.sel]; const off = S.dm.off.has(d.key);
  const out = DM.edges.filter(e => e.a === d.key), inc = DM.edges.filter(e => e.b === d.key);
  const citing = inc.filter(e => e.kind === "cites" && !S.dm.off.has(e.a)); const M = citing.reduce((n, e) => n + e.n, 0);
  const corr = out.filter(e => e.kind === "corrects");
  const kinds = {}; DM.edges.forEach(e => { const k = kinds[e.kind] = kinds[e.kind] || [0, 0]; k[0]++; k[1] += e.n; });
  const c = n => "<b data-count='" + n + "'>" + num(n) + "</b>";
  let h = "<p class='lead' style='margin-bottom:6px'>The ontology is built from documents that relate to each other. It changes when one is added or removed.</p>" +
    "<div class='row'><button class='btn ghost' data-preset='corr'>Add the corrigendum</button><button class='btn ghost' data-preset='ur10e'>Add the UR10e manual</button><button class='btn ghost' data-preset='dir'>Remove the Directive</button></div>" +
    "<div class='box' style='border-left:4px solid var(--" + d.layer + ")'><div class='lab'>" + esc(LAYER[d.layer].label.toUpperCase()) + " DOCUMENT" + (off ? " \u00b7 WITHDRAWN" : "") + "</div><p>" + esc(d.title) + "</p>" +
    "<p class='sub'>" + (d.pieces ? num(d.pieces) + " passages \u00b7 " : "") + num(d.n) + " facts in force" + (off ? " when present" : "") + "</p>" +
    "<p class='sub'><b>It</b> " + (out.length ? out.map(e => EDGE_WORD[e.kind] + " " + esc(DOC[e.b].name) + " (" + e.n + ")").join(", ") : "has no link to another document") + ".</p>" +
    "<p class='sub'><b>Others:</b> " + (inc.length ? inc.map(e => esc(DOC[e.a].name) + " " + EDGE_WORD[e.kind] + " it (" + e.n + ")").join(", ") : "no other document links to it") + ".</p>" +
    "<div class='row' style='margin-top:8px'><button class='btn' data-dm='toggle'>" + (off ? "Put it back" : "Remove this document") + "</button></div></div>";
  if (off) {
    h += "<div class='box warn'><div class='lab'>WITHOUT IT</div><ul class='cnt'><li>" + c(d.n) + " facts leave the ontology (kept as withdrawn, not deleted)</li>" +
      corr.map(e => "<li>" + c(e.n) + " values of " + esc(DOC[e.b].name) + " go back to how they were first printed</li>").join("") +
      "<li>" + c(M) + " facts in other documents that cite it are flagged for review</li><li>" + c(d.devices) + " lifting devices lose their result</li></ul>" +
      "<p class='sub'>Recorded answers that used it: " + (d.answers.length ? esc(d.answers.join("; ")) : "no recorded answer used it") + ".</p></div>";
    const ex = []; citing.forEach(e => e.ex.forEach(i => { if (ex.length < 3 && D.facts[i]) ex.push(D.facts[i]); }));
    if (ex.length) h += "<ol class='steps' style='max-height:150px'>" + ex.map(f => "<li><button data-fact=\"" + esc(f.id) + "\" style='padding-left:8px'>" + esc(f.s) + " \u00b7 flagged for review<q>" + esc(f.q || "") + "</q><span class='loc'>" + esc(f.d + " \u00b7 " + f.a) + "</span></button></li>").join("") + "</ol>";
  } else if (S.dm.msg === d.key) {
    h += "<div class='box ok'><div class='lab'>WITH IT</div><ul class='cnt'><li>" + c(d.n) + " checked facts arrive, each with its quote</li>" +
      corr.map(e => "<li>" + c(e.n) + " facts of " + esc(DOC[e.b].name) + " change; the old ones are closed and kept</li>").join("") +
      "<li>" + c(out.filter(e => e.kind === "cites").reduce((n, e) => n + e.n, 0)) + " of its facts cite another document</li></ul></div>";
  }
  h += "<p class='note'>Lines: " + Object.keys(kinds).map(k => EDGE_WORD[k] + " " + kinds[k][1] + " (" + kinds[k][0] + (kinds[k][0] === 1 ? " line" : " lines") + ")").join(" \u00b7 ") + ". Solid: stored in the facts. Dashed: computed.</p>" +
    "<p class='note'>This replays what the store already holds for each document: adding a document here shows its checked facts arriving. Reading a brand-new document runs the extraction first.</p>";
  $("#panel").innerHTML = h; countUp(); showDocMap();
}
function preset(which) {
  const key = {corr: "CORR", ur10e: "ur10e-manual", dir: "DIR"}[which]; if (!DOC[key]) return;
  const adding = which !== "dir"; S.dm.sel = key; S.dm.msg = "";
  S.dm.off = new Set(adding ? [key] : []); if (adding) S.dm.prev = new Set([key]);
  renderDocuments();
  S.timers.push(setTimeout(() => { if (S.tab !== "documents") return; if (adding) { S.dm.off.delete(key); S.dm.msg = key; } else S.dm.off.add(key); S.dm.anim = true; renderDocuments(); }, reduced() ? 0 : 900));
}

/* ---------- score ---------- */
function stack(t) {
  return "<div class='stack' role='img' aria-label='" + t.correct + " right, " + t.unknown + " unknown, " + t.wrong + " wrong'>" + [["right", t.correct], ["unknown", t.unknown], ["wrong", t.wrong]].filter(p => p[1] > 0).map(p => "<div class='" + p[0] + "' style='flex:" + p[1] + "'>" + p[1] + "</div>").join("") + "</div>";
}
function renderScore() {
  const T = D.totals; const grp = (key, name) => "<div class='group'><h3>" + name + " <small>" + T.B[key].n + " questions</small></h3><div class='bar'><span>Plant Atlas</span>" + stack(T.B[key]) + "</div><div class='bar'><span>Plain search</span>" + stack(T.rag[key]) + "</div><p class='say'>" + esc(D.sentences[key]) + "</p>";
  const m = a => { const k = mark(a && a.score, a && a.value); return k ? "<b class='" + k.k + "' title='" + k.t + "'>" + ({right: "\u2713", unknown: "?", partly: "~", wrong: "\u00d7"}[k.k]) + "</b>" : "<b>-</b>"; };
  const R = D.rule, H = D.health, V = D.reader;
  $("#panel").innerHTML = "<p class='lead'>Plant Atlas against plain search, on questions written before building.</p>" +
    "<div class='keys'><span><i style='background:var(--right)'></i>right</span><span><i style='background:var(--unknown-bg);border:1px solid var(--unknown)'></i>says unknown</span><span><i style='background:var(--wrong)'></i>wrong or partly right</span></div>" +
    grp("design", "Design questions") + "<div class='strip' aria-label='Design questions one by one: Plant Atlas, then plain search'>" + D.questions.map(q => "<div title=\"" + esc(q.en) + "\">" + q.id.replace("CQ", "Q") + "<span>" + m(q.B) + m(q.rag) + "</span></div>").join("") + "</div><p class='note'>Each box: Plant Atlas, then plain search.</p></div>" +
    grp("held", "Held-out questions") + "</div>" +
    (D.not_run.length ? "<p class='note' style='margin:-6px 0 12px'>Strategy " + esc(D.not_run.join(", ")) + ": not run.</p>" : "") +
    "<h3>The rule in numbers: no quote, no fact</h3><div class='facts'><div><b>" + num(R.proposed) + "</b>facts proposed</div><div><b>" + num(R.accepted) + "</b>accepted with their quote</div><div><b>" + num(R.rejected) + "</b>refused</div></div>" +
    "<p class='note'><b style='color:var(--ink)'>" + num(H.quote_found) + " of " + num(H.checked) + "</b> checked facts are still found word for word in their documents today. Second reader: " + num(V.checked) + " facts re-read, " + num(V.passed) + " passed, " + num(V.back) + " sent back; not applied to the answers.</p>";
}

/* ---------- changes ---------- */
function renderChanges() {
  const sc = D.scenes[1]; const vi = S.change === "before" ? 0 : 1; const v = sc.variants[vi]; const H = D.health;
  const doc = D.documents.find(d => d.source === S.doc);
  let h = "<h3>A correction arrives: the corrigendum</h3><p class='lead'>" + esc(sc.look) + "</p><div class='row'><span class='seg'><button data-change='before' aria-pressed='" + (vi === 0 && !doc) + "'>" + esc(sc.variants[0].label) + "</button><button data-change='after' aria-pressed='" + (vi === 1 && !doc) + "'>" + esc(sc.variants[1].label) + "</button></span></div>" +
    "<div class='box " + v.result.tone + "'><div class='lab'>RESULT</div><p class='demo'><b>What this demonstrates:</b> " + esc(sc.demo) + "</p><p>" + esc(v.result.text) + "</p>" + (v.result.note ? "<p class='sub'>" + esc(v.result.note) + "</p>" : "") + "</div>" +
    "<h3 style='margin-top:14px'>What if a document changes?</h3><div class='row'><select id='docpick' aria-label='Document'><option value=''>Choose a document</option>" + D.documents.map(d => "<option value=\"" + esc(d.source) + "\"" + (d.source === S.doc ? " selected" : "") + ">" + esc(LAYER[d.layer].label + ": " + d.title) + "</option>").join("") + "</select></div>";
  if (doc) { const cites = doc.referred_by.reduce((n, g) => n + g.count, 0); h += "<div class='box warn'><div class='lab'>IF IT CHANGED</div><p>" + esc(doc.if_changed) + "</p><p class='sub'>" + num(doc.facts_anchored) + " facts anchored in it. " + (cites ? num(cites) + " facts in other documents cite it; examples are on the left." : "No fact in another document cites it.") + (doc.devices_affected ? " " + doc.devices_affected + " devices of the plant depend on it." : "") + "</p></div>"; }
  h += "<p class='note'><b style='color:var(--ink)'>Health check:</b> " + num(H.quote_found) + " of " + num(H.checked) + " checked facts still found word for word in their documents; " + num(H.quote_missing) + " quotes missing, " + num(H.piece_missing) + " passages missing.</p>" +
    "<h3 style='margin-top:12px'>Three worked changes</h3><ul class='whatif'>" + D.what_if.map(w => "<li><b>" + esc(w.title) + "</b>: " + esc(w.result) + "</li>").join("") + "</ul>";
  $("#panel").innerHTML = h;
  showLeft(doc ? docView(doc) : Object.assign(sceneView(1, vi), {title: "<b>The corrigendum</b> \u00b7 " + esc(v.label) + ": old facts are closed and kept, new ones are in force"}));
}

/* ---------- scenes ---------- */
function renderScenes() {
  const si = S.scene; const sc = D.scenes[si]; const vi = S.variant[si] || 0; const v = sc.variants[vi];
  let h = "<div class='row' style='justify-content:space-between;margin-bottom:8px'><p class='lead' style='margin:0'>Six things the ontology can show, on real data.</p><button class='btn ghost' id='play'>" + (S.playing ? "Stop" : "Play") + "</button></div><ol class='scenes'>" +
    D.scenes.map((s, i) => "<li><button data-scene='" + i + "' aria-pressed='" + (i === si) + "'><span class='i'>" + (i + 1) + "</span><strong>" + esc(s.title) + "</strong><span class='c'>" + esc(s.look) + "</span></button></li>").join("") + "</ol>";
  if (sc.variants.length > 1) h += "<div class='row'><span style='font-size:13px;color:var(--muted)'>" + esc(sc.toggle || "Switch") + "</span><span class='seg'>" + sc.variants.map((x, i) => "<button data-variant='" + i + "' aria-pressed='" + (i === vi) + "'>" + esc(x.label) + "</button>").join("") + "</span></div>";
  h += "<div class='box " + v.result.tone + "'><div class='lab'>RESULT</div><p class='demo'><b>What this demonstrates:</b> " + esc(sc.demo) + "</p><p>" + esc(v.result.text) + "</p>" + (v.result.note ? "<p class='sub'>" + esc(v.result.note) + "</p>" : "") + "</div>";
  $("#panel").innerHTML = h; const sv = sceneView(si, vi); if (S.playing) { sv.reveal = true; sv.gap = 280; } showLeft(sv);
}
function play() {
  if (S.playing) { clearInterval(S.playing); S.playing = null; renderScenes(); return; }
  S.scene = 0; S.playing = setInterval(() => { if (S.tab !== "scenes" || S.scene >= D.scenes.length - 1) { clearInterval(S.playing); S.playing = null; if (S.tab === "scenes") renderScenes(); return; } S.scene++; renderScenes(); }, 5000);
  renderScenes();
}

/* ---------- tabs and events ---------- */
function setTab(tab, keepLeft) {
  S.tab = tab; document.querySelectorAll("#tabs button").forEach(b => b.setAttribute("aria-selected", b.dataset.tab === tab));
  if (history.replaceState) history.replaceState(null, "", "#" + tab + (S.left === "docs" && tab !== "documents" ? "&docs" : "") + (S.embed ? "&embed" : ""));
  const P = $("#panel"); P.scrollTop = 0; P.classList.remove("fadein"); P.getBoundingClientRect(); P.classList.add("fadein");
  if (tab === "ontology") renderOntology();
  else if (tab === "documents") renderDocuments();
  else if (tab === "ask") { renderAsk(); if (!keepLeft) { if (S.answer && S.answer.B && S.answer.B.steps && S.answer.B.steps.length && S.asked) showLeft(answerView(S.answer.B)); else showLeft(sceneView(0, 0)); } }
  else if (tab === "score") { renderScore(); showLeft(S.factView || sceneView(0, 0)); }
  else if (tab === "changes") renderChanges();
  else renderScenes();
}
$("#tabs").addEventListener("click", e => { const b = e.target.closest("button"); if (b) setTab(b.dataset.tab); });
$("#panel").addEventListener("click", e => {
  const b = e.target.closest("button"); if (!b) return;
  if (b.dataset.go) setTab(b.dataset.go);
  else if (b.dataset.preset) preset(b.dataset.preset);
  else if (b.dataset.dm) { const k = S.dm.sel; if (S.dm.off.has(k)) { S.dm.off.delete(k); S.dm.msg = k; } else { S.dm.off.add(k); S.dm.msg = ""; } S.dm.anim = true; renderDocuments(); }
  else if (b.dataset.fact) { const c = factCard(b.dataset.fact, {status: "flagged for review", flag: true}); if (c) openCard(c); }
  else if (b.id === "odback") { S.odoc = ""; renderOntology(); }
  else if (b.dataset.q) { const q = D.questions.find(x => x.id === b.dataset.q); S.asked = true; ask(q[S.lang], q, true); }
  else if (b.dataset.lang) { S.lang = b.dataset.lang; if (S.q) S.text = S.q[S.lang]; renderAsk(); }
  else if (b.id === "showfacts") { S.asked = true; showLeft(answerView(S.answer.B)); }
  else if (b.dataset.step != null) { const st = S.answer.B.steps[+b.dataset.step]; const v = answerView(S.answer.B); const id = st.f || st.statement_id || ("step" + b.dataset.step); const c = v.cards.find(c => c.id === id); S.asked = true; showLeft(v); if (c) openCard(c); }
  else if (b.dataset.change) { S.change = b.dataset.change; S.doc = ""; renderChanges(); }
  else if (b.dataset.scene != null) { S.scene = +b.dataset.scene; renderScenes(); }
  else if (b.dataset.variant != null) { S.variant[S.scene] = +b.dataset.variant; renderScenes(); }
  else if (b.id === "play") play();
});
$("#panel").addEventListener("submit", e => { e.preventDefault(); const text = $("#qtext").value.trim(); if (!text) return; S.asof = $("#asof").value; S.asked = true; ask(text, findQ(text), true); });
$("#panel").addEventListener("change", e => { if (e.target.id === "docpick") { S.doc = e.target.value; renderChanges(); } else if (e.target.id === "asof") S.asof = e.target.value; });

(function start() {
  const first = D.questions.find(q => q.steps && q.steps.length >= 3 && q.B && q.B.score >= 0.999) || D.questions.find(q => q.steps) || D.questions[0];
  S.q = first; S.text = first.en; S.answer = recorded(first); S.asked = true;
  const tokens = new Set(((location.hash || "") + "&" + (location.search || "")).split(/[#&?=,]/).filter(Boolean));
  if (tokens.has("docs")) S.left = "docs";
  if (tokens.has("embed")) { S.embed = true; document.querySelector(".app").classList.add("embed"); }
  const W = D.whole.totals, H = D.health;
  $("#why").innerHTML = "<span><b>Predictable:</b> the agent follows typed relations between checked facts (<b>" + W.relations + "</b> relations in the schema, <b>" + num(W.in_force) + "</b> facts in force)</span>" +
    "<span><b>Auditable:</b> every step of an answer shows the sentence it rests on (<b>" + num(H.quote_found) + " of " + num(H.checked) + "</b> facts still found word for word in their documents)</span>" +
    "<span><b>Portable:</b> the ontology is a standard file any agent can read (Turtle with SHACL shapes: <a href='ontology.ttl'>ontology.ttl</a>)</span>";
  const tab = ["documents", "ontology", "ask", "score", "changes", "scenes"].find(t => tokens.has(t));
  setTab(tab || DEFAULT_TAB);
  if (/^https?:$/.test(location.protocol)) {
    const ctl = new AbortController(); setTimeout(() => ctl.abort(), 2500);
    fetch("/api/status", {signal: ctl.signal}).then(r => r.ok ? r.json() : Promise.reject()).then(j => {
      if (!j || typeof j !== "object" || !("today" in j)) return;
      S.live = true; const b = $("#badge"); b.textContent = j.fake ? "live (cached answers)" : "live"; b.classList.add("live"); if (S.tab === "ask") renderAsk();
    }).catch(() => {});
  }
})();
</script>
"""


def main() -> None:
    path = write()
    print(f"wrote {path} ({path.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
