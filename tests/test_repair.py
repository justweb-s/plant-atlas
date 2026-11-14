"""Owner: Core. The law repairs: the parts file loads, every fact in it still passes the store's checks, the
risks of point 1.3.7 are risks, and the three procedures of Art. 25(2) are three facts in the order of the text."""
import json
from pathlib import Path

import pytest

from atlas.corpus.chunker import load
from atlas.ontology import build
from atlas.ontology.statements import ChunkCorpus, Statement, Store
from atlas.strategies import repair

PART = Path(__file__).resolve().parents[1] / "ontology" / "B" / "parts" / "law_repairs.json"


@pytest.fixture(scope="module")
def payload() -> dict:
    return json.loads(PART.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def store():
    build.raw_store.cache_clear()
    return build.raw_store("B")


def test_part_loads_with_its_prefix(payload):
    assert payload["statements"] and "rejections" in payload
    assert all(item["id"].startswith("law_repairs-") for item in payload["statements"])
    assert all(item["asserted_by"].startswith("code:") and item["layer"] == "law" for item in payload["statements"])


def test_every_statement_passes_the_quote_check(payload):
    checker = Store(ChunkCorpus(list(load())))
    for item in payload["statements"]:
        assert checker.write_statement(Statement(**item)) is not None, (item["id"], checker.rejections[-1]["reason"])
    assert not checker.rejections


def test_point_1_3_7_names_its_risks(store):
    risks = [s.object_as_written.lower() for s in store.statements if s.status == "current"
             and s.source_doc == "REG" and s.anchor == "Annex III, 1.3.7" and s.predicate == "addressesRisk"]
    assert len(risks) >= 3
    for words in ("contact", "accidental blockage", "psychological stress"):
        assert any(words in risk for risk in risks), words


def test_art_25_2_has_three_procedures_in_the_order_of_the_text(store):
    facts = [s for s in store.statements if s.source_doc == "REG" and s.anchor == "Art. 25(2)"
             and s.predicate == "requiresProcedure"]
    current = [s for s in facts if s.status == "current"]
    assert len(current) == 3
    assert sorted(s.object_normalised for s in current) == ["module B followed by module C", "module G", "module H"]
    sequence = next(s for s in current if "module B" in s.object_normalised)
    assert sequence.object_as_written.index("module B") < sequence.object_as_written.index("module C")
    assert "Annex I, Part A" in sequence.condition
    closed = {s.id for s in facts if s.status == "closed"}
    assert closed and all(s.conflicts_with in closed for s in current)
    assert all(s.in_force_to == repair.REPAIR_DAY for s in facts if s.status == "closed")


def test_list_items_and_short_form():
    text = "Where X applies, one of: (a) first (module B), followed by second (module C); (b) third (module H)."
    chapeau, items = repair.list_items(text)
    assert chapeau.startswith("Where X") and [letter for letter, _, _ in items] == ["a", "b"]
    assert all(quote in text and value in quote for _, value, quote in items)
    assert [repair.short_form(value) for _, value, _ in items] == ["module B followed by module C", "module H"]
