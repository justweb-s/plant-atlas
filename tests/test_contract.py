"""The contract works end to end in fake mode, so the app can be built before the brain."""
import os

os.environ["ATLAS_FAKE"] = "1"

from atlas import api  # noqa: E402
from evaluation import rag  # noqa: E402

CQ10_EN = "On 16 January 2027, can machinery conforming to Directive 2006/42/EC still be placed on the market?"


def test_answers_follow_the_contract():
    for a in (api.answer(CQ10_EN, "B"), api.answer(CQ10_EN, "A"), rag.answer(CQ10_EN)):
        assert a.question == CQ10_EN
        assert a.mode in {"rag", "A", "B"}
        assert all(s.locator for s in a.steps if s.quote), "a quote without a locator"


def test_build_validate_change():
    assert api.build_ontology("B").shapes_path is not None
    assert api.build_ontology("A").shapes_path is None
    assert api.validate("B").strategy == "B"
    cs = api.propose_change(api.ROOT / "data/law/eu-reg-2023-1230-corrigendum-2023-07-04.en.xhtml")
    assert cs.changes and all(c.quote and c.locator for c in cs.changes)
    assert api.apply_change(cs, [c.id for c in cs.changes]).human_decisions == len(cs.changes)


def test_ontology_file_layout():
    assert api.ontology_file("A").as_posix().endswith("ontology/A/ontology.ttl")
