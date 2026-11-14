"""The competency questions are the gold: check them before anything is built.

- every quote is really in its source file (after normalising quotes, dashes and spaces);
- the catalogue answers (CQ13-CQ15) follow from the catalogue facts in the same file;
- the held-out questions never reach the code in atlas/.
"""
import html
import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "data/cq/cqs.json").read_text(encoding="utf-8"))
CQS = {cq["id"]: cq for cq in DATA["cqs"]}
MODELS = {m["id"]: m for m in DATA["catalogue"]["models"]}
MACHINE_QUOTES = {f["quote"] for m in json.loads((ROOT / "data/machines/machines.json").read_text(encoding="utf-8"))["machines"]
                  for f in m["facts"]}

_DROP = dict.fromkeys(map(ord, "‘’‚‛“”„«»\"'`"), None)
_DASH = {ord(c): "-" for c in "‐‑‒–—−"}


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s).translate(_DROP).translate(_DASH)
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"\s+([,.;:)\]])", r"\1", s)
    s = re.sub(r"([(\[])\s+", r"\1", s)
    return s.strip().casefold()


@lru_cache(maxsize=None)
def source_text(key: str) -> str | None:
    """The normalised text of a source; None for a PDF that is not on this machine (it is not in git)."""
    path = ROOT / DATA["sources"][key]
    if path.suffix == ".pdf":
        if not path.exists():
            return None
        from pypdf import PdfReader
        return norm(" ".join(page.extract_text() for page in PdfReader(path).pages))
    raw = path.read_text(encoding="utf-8")
    if path.suffix in {".xhtml", ".html"}:
        raw = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", raw)
        raw = html.unescape(re.sub(r"<[^>]+>", " ", raw))
    return norm(raw)


def test_structure():
    assert len(DATA["cqs"]) == 34
    assert len(CQS) == 34, "duplicate ids"
    kinds = set(DATA["about"]["answer_kinds"])
    roles = set(DATA["about"]["evidence_roles"])
    splits = set(DATA["about"]["splits"])
    for cq in DATA["cqs"]:
        assert cq["type"] in {"T", "V", "I"}, cq["id"]
        assert cq["split"] in splits, cq["id"]
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
        if cq["answer"]["kind"] == "unknown":
            assert cq["answer"]["value"] is None, cq["id"]
    assert sum(cq["split"] == "heldout" for cq in DATA["cqs"]) == 12


def test_quotes_are_in_their_sources():
    missing = []
    for cq in DATA["cqs"]:
        for ev in cq["evidence"]:
            if ev["source"] == "CATALOGUE":
                continue
            if ev["source"].endswith("-manual"):   # the manuals are not in git: the quote must be one fetch.py verifies
                if ev["quote"] not in MACHINE_QUOTES:
                    missing.append(f'{cq["id"]} {ev["locator"]}: not a quote of machines.json')
                continue
            text = source_text(ev["source"])
            if text is None:
                continue
            if norm(ev["quote"]) not in text:
                missing.append(f'{cq["id"]} {ev["locator"]}: {ev["quote"][:80]}')
    assert not missing, "quotes not found:\n" + "\n".join(missing)


def test_superseded_passages_have_a_replacement():
    for cq in DATA["cqs"]:
        roles = [ev["role"] for ev in cq["evidence"]]
        if "superseded" in roles:
            assert "corrects" in roles, cq["id"]


def test_catalogue_gold_follows_from_catalogue_facts():
    # CQ13: self-certified today and in Annex I, Part A of the Regulation
    need_nb = {mid for mid, m in MODELS.items()
               if m["procedure_today"] == "internal_checks" and (m["regulation_annex_i"] or "").startswith("A.")}
    assert need_nb == set(CQS["CQ13"]["answer"]["value"])
    # CQ14: RC-5 is the embedded machine-learning case
    assert MODELS["RC-5"]["regulation_annex_i"] == "A.6"
    # CQ15: CS-400 is Part B and built to complete harmonised standards, so module A stays possible
    cs = MODELS["CS-400"]
    assert cs["regulation_annex_i"].startswith("B.") and cs["harmonised_standards_full"]


def test_core_code_never_reads_heldout_questions():
    offenders = [p.relative_to(ROOT).as_posix() for p in (ROOT / "atlas").rglob("*.py")
                 if "heldout" in p.read_text(encoding="utf-8")]
    assert not offenders, f"atlas/ must use only split == 'design': {offenders}"


def test_annex_vii_gold_follows_from_year_and_row():
    """CQ28 and CQ29 are the same crane two years apart: only its age moves it from one row to the other."""
    built, today = 2017, int(DATA["about"]["as_of_default"][:4])
    assert today - built <= 10 and CQS["CQ28"]["answer"]["value"] == "P2Y"
    assert 2028 - built > 10 and CQS["CQ29"]["answer"]["value"] == "P1Y"
    rows = {cq: next(ev["quote"] for ev in CQS[cq]["evidence"] if ev["source"] == "DLGSALLVII" and ev["role"] != "superseded")
            for cq in ("CQ21", "CQ22", "CQ28", "CQ29", "CQ30")}
    assert "tipo fisso" in rows["CQ21"] and "estrattivo" in rows["CQ21"] and "non antecedente" not in rows["CQ21"]
    assert "tipo mobile" in rows["CQ22"] and "estrattivo" in rows["CQ22"]
    assert "non antecedente 10 anni" in rows["CQ28"] and "non antecedente" not in rows["CQ29"]
    assert "Piattaforme di lavoro mobili elevabili" in rows["CQ30"]
