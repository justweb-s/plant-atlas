"""Owner: Core. What happens to the ontology when a document changes, is added or is withdrawn.

Nothing here calls a model. Everything is computed from three things the store already keeps:
each fact's source and locator, each fact's quote, and the fingerprint of every piece of every document.

- health(): is every fact still found, word for word, in the piece it points to?
- documents(): for each document, the facts anchored in it, the facts of other documents that cite it,
  and the lifting devices whose result depends on it.
- what_if(): a few real changes worked through: the earlier version of Annex VII, the corrigendum
  withdrawn, one robot arm replaced by another.

`python -m atlas.ontology.impact` writes ontology/B/impact.json for the pages and the app.
Links found here are computed (anchors and citations in the quotes); they are not stored relations.
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path

from atlas.ontology.statements import norm

ROOT = Path(__file__).resolve().parents[2]
TODAY = date(2026, 11, 14)

# Several sources that are one document for a reader, and how other documents cite it.
DOCUMENTS = {
    "REG": ("Regulation (EU) 2023/1230 on machinery", ["REG"], r"2023/1230"),
    "CORR": ("Corrigendum to Regulation (EU) 2023/1230, 4 July 2023", ["CORR"], None),
    "DIR": ("Directive 2006/42/EC on machinery", ["DIR"], r"2006/42"),
    "DLGS": ("D.Lgs. 81/2008, articles 69 to 73", ["DLGS69", "DLGS70", "DLGS71", "DLGS72", "DLGS73"],
             r"81/(?:20)?08|decreto legislativo n\. 81|art(?:icolo|\.)\s*71"),
    "DLGSALLVII": ("D.Lgs. 81/2008, Annex VII", ["DLGSALLVII"], r"[Aa]llegato VII"),
    "DM2011": ("Ministerial decree of 11 April 2011", ["DM2011"], r"11 aprile 2011|11/0?4/2011"),
}


def _example(s) -> dict:
    return {"id": s.id, "subject": s.subject, "predicate": s.predicate, "value": s.object_as_written or s.object,
            "source_doc": s.source_doc, "anchor": s.anchor, "quote": s.quote[:280]}


def health(store, chunks) -> dict:
    """Check every current fact against the piece it points to, as the piece is today."""
    text = {(c.source, c.locator): norm(c.text) for c in chunks}
    result = {"checked": 0, "quote_found": 0, "quote_missing": 0, "piece_missing": 0, "problems": []}
    for s in store.statements:
        if s.status != "current":
            continue
        result["checked"] += 1
        piece = text.get((s.source_doc, s.anchor))
        if piece is None:
            result["piece_missing"] += 1
            result["problems"].append({"id": s.id, "why": "the piece it points to is not in the corpus on this machine"})
        elif norm(s.quote) in piece:
            result["quote_found"] += 1
        else:
            result["quote_missing"] += 1
            result["problems"].append({"id": s.id, "why": "the piece no longer contains the quote"})
    result["problems"] = result["problems"][:50]
    return result


def _catalogue(chunks) -> dict[str, tuple[str, list[str], str | None]]:
    """Every document of the corpus: the grouped law texts above, and one entry per other source."""
    grouped = {source for _, sources, _ in DOCUMENTS.values() for source in sources}
    catalogue = dict(DOCUMENTS)
    titles = {}
    for c in chunks:
        if c.source not in grouped and c.source not in titles:
            titles[c.source] = c.version if c.layer != "law" and c.version else c.source
    for source, title in titles.items():
        catalogue[source] = (title, [source], None)
    return catalogue


def documents(store, chunks, devices=None, annex_rows_used=None) -> list[dict]:
    layer = {c.source: c.layer for c in chunks}
    pieces = Counter(c.source for c in chunks)
    current = [s for s in store.statements if s.status == "current"]
    by_source = defaultdict(list)
    for s in current:
        by_source[s.source_doc].append(s)
    out = []
    for key, (title, sources, cites) in _catalogue(chunks).items():
        anchored = [s for source in sources for s in by_source.get(source, [])]
        referring = defaultdict(list)
        if cites:
            pattern = re.compile(cites)
            for s in current:
                if s.source_doc not in sources and pattern.search(f"{s.quote} {s.object_as_written}"):
                    referring[layer.get(s.source_doc, "law")].append(s)
        affected = 0
        if devices is not None:
            if key == "DLGSALLVII":
                affected = len(annex_rows_used or [])
            elif key == "igea-equipment":
                affected = len(devices)
        n_pieces = sum(pieces.get(source, 0) for source in sources)
        referred = [{"layer": name, "count": len(facts), "examples": [_example(s) for s in facts[:3]]}
                    for name, facts in sorted(referring.items())]
        total_referring = sum(r["count"] for r in referred)
        sentence = (f"If this document changed, {len(anchored)} facts anchored in it would be checked again"
                    + (f", {total_referring} facts in other documents cite it and would be flagged for review" if total_referring else "")
                    + (f", and the result for {affected} lifting devices depends on it" if affected else "") + ".")
        out.append({"source": key, "title": title, "layer": layer.get(sources[0], "law"), "pieces": n_pieces,
                    "facts_anchored": len(anchored), "referred_by": referred, "devices_affected": affected,
                    "if_changed": sentence})
    return sorted(out, key=lambda d: (-d["facts_anchored"] - sum(r["count"] for r in d["referred_by"]), d["source"]))


def _intervals(devices, annex_facts, on: date) -> dict[int, dict]:
    from atlas.ontology.rules import verification_interval

    return {d["position"]: verification_interval(d, annex_facts, on) for d in devices}


def what_if(store, devices) -> list[dict]:
    cases = []
    annex = [s for s in store.statements if s.predicate == "verificationInterval" and s.status == "current"]
    # 1. Annex VII before the row added in 2026. The earlier text is reconstructed by leaving that row out.
    added = [s for s in annex if "frutteto" in s.subject]
    if added and devices:
        before = _intervals(devices, [s for s in annex if s not in added], TODAY)
        after = _intervals(devices, annex, TODAY)
        moved = [{"position": p, "before": before[p].get("interval") or "unknown", "after": after[p].get("interval") or "unknown"}
                 for p in sorted(after) if before[p].get("interval") != after[p].get("interval")]
        cases.append({
            "id": "annex-vii-2026", "title": "Annex VII gains a row (Law 11 March 2026, n. 34)",
            "note": "The earlier version is reconstructed by leaving out the row the archive marks as added in 2026; "
                    "we do not hold the earlier official text. Rows are matched by content, so rows that only moved "
                    "down one place count as unchanged.",
            "added": [s.anchor for s in added], "removed": [], "modified": [],
            "facts_affected": [_example(s) for s in added], "devices_affected": moved,
            "result": (f"{len(added)} fact added, {len(annex) - len(added)} facts untouched, "
                       f"{len(moved)} of {len(devices)} lifting devices get a different interval.")})
    # 2. The corrigendum withdrawn: the nine corrected facts fall back to what the Regulation printed.
    corrected = [s for s in store.statements if s.asserted_by == "strategy_b:corrigendum" and s.status == "current"]
    if corrected:
        by_id = {s.id: s for s in store.statements}
        cases.append({
            "id": "corrigendum-withdrawn", "title": "The corrigendum of 4 July 2023, with and without",
            "note": "Without the corrigendum the Regulation's printed dates stand; with it, each is closed and replaced. "
                    "Both versions stay in the store.",
            "added": [], "removed": [], "modified": [s.anchor for s in corrected],
            "facts_affected": [dict(_example(s), before=by_id[s.conflicts_with].object_as_written
                                    if s.conflicts_with in by_id else "") for s in corrected],
            "devices_affected": [],
            "result": f"{len(corrected)} dates change; the old ones are closed and kept."})
    # 3. One robot arm replaced by another: the facts of the old manual leave, those of the new one arrive.
    reach = {s.source_doc: s for s in store.statements if s.predicate == "hasReach" and s.status == "current"}
    if "ur5e-manual" in reach and "ur10e-manual" in reach:
        old = [s for s in store.statements if s.source_doc == "ur5e-manual" and s.status == "current"]
        new = [s for s in store.statements if s.source_doc == "ur10e-manual" and s.status == "current"]
        cases.append({
            "id": "arm-replaced", "title": "A robot arm is replaced by a larger one",
            "note": "Both manuals are real. Which arm stands in the cell is the plant's choice, not a document.",
            "added": ["ur10e-manual"], "removed": ["ur5e-manual"], "modified": [],
            "facts_affected": [dict(_example(reach["ur10e-manual"]), before=reach["ur5e-manual"].object_as_written)],
            "devices_affected": [],
            "result": (f"{len(old)} facts of the old manual stop applying to the cell and {len(new)} of the new one start; "
                       f"reach goes from {reach['ur5e-manual'].object_as_written} to {reach['ur10e-manual'].object_as_written}.")})
    return cases


def build(strategy: str = "B") -> dict:
    from atlas.corpus.chunker import load
    from atlas.ontology.build import raw_store
    from atlas.strategies.plant import device_records

    store, chunks = raw_store(strategy), list(load())
    devices = device_records(store.statements)
    annex = [s for s in store.statements if s.predicate == "verificationInterval" and s.status == "current"]
    used = [p for p, r in _intervals(devices, annex, TODAY).items() if r.get("interval")] if devices else []
    report = health(store, chunks)
    return {"generated": datetime.now().isoformat(timespec="seconds"),
            "health": {k: v for k, v in report.items() if k != "problems"}, "health_problems": report["problems"],
            "documents": documents(store, chunks, devices, used), "what_if": what_if(store, devices)}


if __name__ == "__main__":
    result = build()
    path = ROOT / "ontology" / "B" / "impact.json"
    path.write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding="utf-8")
    print("health:", result["health"])
    for d in result["documents"][:12]:
        print(f"  {d['source']:18} {d['layer']:12} pieces {d['pieces']:4}  facts {d['facts_anchored']:4}  cited by "
              f"{sum(r['count'] for r in d['referred_by']):3}  devices {d['devices_affected']}")
    for case in result["what_if"]:
        print(" what if:", case["title"], "->", case["result"])
