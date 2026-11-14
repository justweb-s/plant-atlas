"""Fake data so the app and the evaluation run before the brain exists. Owner: Product.

Same signatures as atlas/api.py (plus rag_answer for evaluation/rag.py). Everything here is
FAKE: the app must show it as fake, and it never goes in the pitch as a result.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from atlas.contracts import Answer, BuildResult, Change, ChangeSet, Chunk, Step, ValidationReport

ROOT = Path(__file__).resolve().parents[1]
_CQS = json.loads((ROOT / "data/cq/cqs.json").read_text(encoding="utf-8"))["cqs"]

_ART51 = "Directive 2006/42/EC is repealed with effect from 14 January 2027."
_CORR5 = "On page 38, Article 51, paragraph 2, first subparagraph: for: '14 January 2027', read: '20 January 2027'"
_CORR10 = "On page 39, Article 54, second paragraph: for: '14 January 2027', read: '20 January 2027'"


def _cq_id(question: str) -> str | None:
    q = question.strip().casefold()
    for cq in _CQS:
        if q in (cq["question_it"].casefold(), cq["question_en"].casefold()):
            return cq["id"]
    return None


def corpus() -> list[Chunk]:
    return [
        Chunk("REG:Art.54", "REG", "Art. 54", "It shall apply from 14 January 2027.", "OJ L 165, 29.6.2023"),
        Chunk("REG:Art.51(2)", "REG", "Art. 51(2)", _ART51, "OJ L 165, 29.6.2023"),
        Chunk("CORR:10", "CORR", "Corrigendum, point 10", _CORR10, "OJ L 169, 4.7.2023"),
    ]


def build_ontology(strategy) -> BuildResult:
    shapes = ROOT / "ontology" / "B" / "shapes.ttl" if strategy == "B" else None
    return BuildResult(strategy, ROOT / "ontology" / strategy / "ontology.ttl", shapes, 0, 0, 0)


def answer(question: str, strategy="B", as_of: date | None = None) -> Answer:
    if strategy == "B" and _cq_id(question) == "CQ10":
        return Answer(
            question, "B", True,
            "(FAKE) Yes. The Directive is repealed with effect from 20 January 2027, as corrected by the corrigendum.",
            [
                Step("The published text says 14 January 2027", quote=_ART51, locator="Art. 51(2)"),
                Step("The corrigendum replaces it with 20 January 2027", quote=_CORR5, locator="Corrigendum, point 5"),
                Step("16 January 2027 is before 20 January 2027",
                     sparql='ASK { :Directive_2006_42 :repealedWithEffectFrom ?d . FILTER (?d > "2027-01-16"^^xsd:date) }'),
            ],
        )
    return Answer(question, strategy, None, "(FAKE) not implemented yet")


def rag_answer(question: str, as_of: date | None = None) -> Answer:
    if _cq_id(question) == "CQ10":
        return Answer(
            question, "rag", False,
            "(FAKE) No: Directive 2006/42/EC is repealed with effect from 14 January 2027.",
            [Step("Most similar passage", quote=_ART51, locator="Art. 51(2)")],
        )
    return Answer(question, "rag", None, "(FAKE) not implemented yet")


def validate(strategy) -> ValidationReport:
    return ValidationReport(strategy, True, [])


def propose_change(document: Path) -> ChangeSet:
    return ChangeSet("fake-corrigendum", str(document), [
        Change("corr-10", "modify", "Regulation (EU) 2023/1230 · appliesFrom", "2027-01-14", "2027-01-20",
               "Corrigendum, point 10", _CORR10),
        Change("corr-5", "modify", "Directive 2006/42/EC · repealedWithEffectFrom", "2027-01-14", "2027-01-20",
               "Corrigendum, point 5", _CORR5),
    ])


def apply_change(changeset: ChangeSet, accepted: list[str]) -> BuildResult:
    result = build_ontology("B")
    result.human_decisions = len(changeset.changes)
    return result
