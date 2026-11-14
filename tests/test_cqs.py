"""The competency questions are the gold: check them before anything is built.

- every quote is really in its source file (after normalising quotes, dashes and spaces);
- the plant answers (CQ13-CQ15) follow from the plant facts in the same file.
"""
import html
import json
import re
import unicodedata
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "data/cq/cqs.json").read_text(encoding="utf-8"))
CQS = {cq["id"]: cq for cq in DATA["cqs"]}
PLANT = DATA["plant"]

_DROP = dict.fromkeys(map(ord, "‘’‚‛“”„«»\"'`"), None)
_DASH = {ord(c): "-" for c in "‐‑‒–—−"}


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s).translate(_DROP).translate(_DASH)
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"\s+([,.;:)\]])", r"\1", s)
    s = re.sub(r"([(\[])\s+", r"\1", s)
    return s.strip().casefold()


@lru_cache(maxsize=None)
def source_text(key: str) -> str:
    path = ROOT / DATA["sources"][key]
    raw = path.read_text(encoding="utf-8")
    if path.suffix in {".xhtml", ".html"}:
        raw = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", raw)
        raw = html.unescape(re.sub(r"<[^>]+>", " ", raw))
    return norm(raw)


def test_structure():
    assert len(DATA["cqs"]) == 15
    assert len(CQS) == 15, "duplicate ids"
    kinds = set(DATA["about"]["answer_kinds"])
    roles = set(DATA["about"]["evidence_roles"])
    for cq in DATA["cqs"]:
        assert cq["type"] in {"T", "V", "I"}, cq["id"]
        assert cq["question_it"] and cq["question_en"], cq["id"]
        assert cq["answer"]["kind"] in kinds, cq["id"]
        assert cq["evidence"], cq["id"]
        for ev in cq["evidence"]:
            assert ev["source"] in DATA["sources"], (cq["id"], ev["source"])
            assert ev["role"] in roles, (cq["id"], ev["role"])
        for group in ("explicit", "implicit", "derived"):
            assert set(cq["terms"][group]) == {"classes", "properties"}, (cq["id"], group)
        if cq["answer"]["kind"] == "text":
            groups = cq["answer"]["keywords"]
            assert groups and all(isinstance(g, list) and g for g in groups), cq["id"]


def test_quotes_are_in_their_sources():
    missing = []
    for cq in DATA["cqs"]:
        for ev in cq["evidence"]:
            if ev["source"] == "PLANT":
                continue
            if norm(ev["quote"]) not in source_text(ev["source"]):
                missing.append(f'{cq["id"]} {ev["locator"]}: {ev["quote"][:80]}')
    assert not missing, "quotes not found:\n" + "\n".join(missing)


def test_superseded_passages_have_a_correction():
    for cq in DATA["cqs"]:
        roles = [ev["role"] for ev in cq["evidence"]]
        if "superseded" in roles:
            assert "corrects" in roles, cq["id"]


def _due(machine: dict, interval_days: int) -> date:
    return date.fromisoformat(machine["last_check"]) + timedelta(days=interval_days)


def test_plant_gold_follows_from_plant_facts():
    as_of = date.fromisoformat(PLANT["as_of"])
    machines = {m["id"]: m for m in PLANT["machines"]}

    overdue = {mid for mid, m in machines.items() if _due(m, m["check_interval_days"]) < as_of}
    assert overdue == set(CQS["CQ13"]["answer"]["value"])

    part_a = {mid for mid, m in machines.items() if (m["annex_i"] or "").startswith("A.")}
    assert part_a == set(CQS["CQ14"]["answer"]["value"])

    pro07 = next(p for p in PLANT["procedures"] if p["id"] == "PRO-07")
    p3 = machines[pro07["machine"]]
    v1 = pro07["versions"]["v1"]["check_interval_days"]
    v2 = pro07["versions"]["v2"]["check_interval_days"]
    assert v1 != p3["check_interval_days"], "PRO-07 v1 must contradict the manual (CQ15)"
    assert v2 == p3["check_interval_days"], "PRO-07 v2 must agree with the manual"
    # the trap of CQ13: with the procedure's interval P-3 would not look overdue
    assert _due(p3, v1) >= as_of
