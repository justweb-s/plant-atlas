"""The Annex VII rule and the two parts files it reads (Core): every fact quoted, nothing guessed."""
import json
from datetime import date
from pathlib import Path

from atlas.ontology.rules import verification_interval
from atlas.ontology.statements import ChunkCorpus, Statement, Store

PARTS = Path(__file__).resolve().parents[1] / "ontology" / "B" / "parts"


def part(name):
    return [Statement(**item) for item in json.loads((PARTS / f"{name}.json").read_text(encoding="utf-8"))["statements"]]


def annex():
    return [s for s in part("law_verification") if s.predicate == "verificationInterval"]


def device(**overrides):
    return {"kind": "GRU A PONTE SCORREVOLE", "capacity_kg": 5000, "year_built": 1985, "sector": "estrattivo",
            **overrides}


def test_fixed_crane_of_1985_in_mining_is_annual():
    result = verification_interval(device(), annex(), date(2019, 6, 1))
    assert result["interval"] == "P1Y" and result["row_id"].endswith("r15")
    assert result["row_id"] in [fact_id for fact_id, _ in result["because"]]


def test_recent_fixed_crane_in_mining_is_biennial_then_annual():
    new = device(year_built=2017)
    assert verification_interval(new, annex(), date(2019, 6, 1))["row_id"].endswith("r16")
    assert verification_interval(new, annex(), date(2026, 11, 14))["interval"] == "P2Y"
    assert verification_interval(new, annex(), date(2028, 6, 1))["interval"] == "P1Y"


def test_tenth_year_is_decided_by_the_year_alone():
    # Annex VII speaks of the YEAR of manufacture: 2017 is "not earlier than 10 years" for the whole of 2027,
    # and earlier than that from 2028 on. No month is needed.
    assert verification_interval(device(year_built=2017), annex(), date(2027, 6, 1))["interval"] == "P2Y"
    assert verification_interval(device(year_built=2017), annex(), date(2028, 1, 1))["interval"] == "P1Y"


def test_mobile_crane_in_mining_is_annual_whatever_its_age():
    for kind, year in (("AUTOGRU'", 2010), ("GRU IDRAULICA PER AUTOCARRO", 2017)):
        result = verification_interval(device(kind=kind, year_built=year), annex(), date(2019, 6, 1))
        assert result["interval"] == "P1Y" and result["row_id"].endswith("r12")


def test_regular_use_reads_the_other_rows():
    result = verification_interval(device(sector="alimentare", year_built=2015), annex(), date(2019, 6, 1))
    assert result["interval"] == "P3Y" and result["row_id"].endswith("r18")


def test_200_kg_or_less_is_unknown():
    result = verification_interval(device(capacity_kg=200), annex(), date(2019, 6, 1))
    assert result["interval"] is None and "200" in result["why"]


def test_unmapped_kind_and_missing_values_are_unknown():
    assert verification_interval(device(kind="CARRELLO ELEVATORE"), annex(), date(2019, 6, 1))["interval"] is None
    assert verification_interval(device(capacity_kg=None), annex(), date(2019, 6, 1))["interval"] is None
    assert verification_interval(device(sector=""), annex(), date(2019, 6, 1))["interval"] is None
    assert verification_interval(device(year_built=None), annex(), date(2019, 6, 1))["interval"] is None
    assert verification_interval(device(), [], date(2019, 6, 1))["interval"] is None


def test_parts_load_and_every_statement_passes_the_quote_check():
    from atlas.corpus.chunker import load

    chunks = list(load())
    corpus, on_machine = ChunkCorpus(chunks), {c.source for c in chunks}
    for name, minimum in (("law_verification", 29), ("plant_igea", 60)):
        statements = part(name)
        assert len(statements) >= minimum
        store = Store(corpus)
        for s in statements:
            if s.source_doc not in on_machine:   # a document that is not on this machine cannot be checked here
                continue
            assert store.write_statement(s.model_copy()) is not None, (name, s.id, store.rejections[-1]["reason"])


def test_all_24_devices_have_kind_capacity_and_year():
    from atlas.strategies.plant import device_records

    devices = device_records(part("plant_igea"))
    assert [d["position"] for d in devices] == list(range(1, 25))
    assert all({"kind", "capacity_kg", "year_built", "sector"} <= set(d) for d in devices)
    by_position = {d["position"]: d for d in devices}
    assert (by_position[8]["kind"], by_position[8]["capacity_kg"], by_position[8]["year_built"]) == \
        ("GRU A PONTE SCORREVOLE", 5000, 1985)
    assert (by_position[22]["capacity_kg"], by_position[22]["year_built"]) == (2095, 1997)


def test_sixty_days_loses_to_forty_five():
    conflicts = [s for s in part("law_verification") if s.status == "conflict"]
    assert len(conflicts) == 1 and conflicts[0].object == "P60D" and conflicts[0].conflicts_with


def test_service_terms_load_pass_the_quote_check_and_hold_the_fifteen_day_notice():
    import pytest

    from atlas.corpus.chunker import load

    statements = part("plant_igea_terms")
    assert statements and all(s.id.startswith("plant_igea_terms-") for s in statements)
    notices = [s for s in statements if s.predicate == "hasTimeLimit" and s.object == "P15D" and s.status == "current"]
    assert notices and all(s.anchor == "p. 5" and "15 giorni" in s.quote for s in notices)
    assert any("aggiudicatario" in s.subject for s in notices)   # whose notice it is
    chunks = [c for c in load() if c.source == "igea-equipment"]
    if not chunks:
        pytest.skip("the plant's document is not on this machine")
    store = Store(ChunkCorpus(chunks))
    for s in statements:
        assert store.write_statement(s.model_copy()) is not None, (s.id, store.rejections[-1]["reason"])
