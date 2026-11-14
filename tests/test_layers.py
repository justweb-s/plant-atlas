"""Owner: Core. The layers of the ontology: which fact prevails when two disagree, and when a lower rule may differ."""
import csv

import pytest

from atlas.ontology.statements import (LARGER_IS_STRICTER, LAYERS, SMALLER_IS_STRICTER, ChunkCorpus, Corpus,
                                       Statement, Store, compare_strictness, rank_of, settle)


class Piece:
    """A chunk as the store needs it."""

    def __init__(self, source, locator, text, layer):
        self.source, self.locator, self.text, self.layer, self.version = source, locator, text, layer, "v1"


SIXTY = "La prima verifica periodica e' effettuata entro sessanta giorni dalla richiesta."
FORTY_FIVE = "La prima verifica e' effettuata entro quarantacinque giorni dalla richiesta."
PIECES = [
    Piece("DM2011", "art. 2, c. 1", SIXTY, "law"),
    Piece("DLGS71", "art. 71, c. 11", FORTY_FIVE, "law"),
    Piece("REG", "Art. 1(1)", "The technical documentation shall be kept for ten years.", "law"),
    Piece("inail-guide", "p. 1", "The documentation is kept for ten years.", "guidance"),
    Piece("ur5e-manual", "p. 1", "Reach 850 mm.", "manufacturer"),
    Piece("procedure-7", "p. 1", "The fence is checked every 90 days.", "company"),
    Piece("layout-cell", "p. 1", "Protected zone radius 1000 mm.", "plant"),
]


def fact(source, anchor, quote, written, value, **more):
    return Statement(subject="first verification", predicate="hasTimeLimit", object=value, object_as_written=written,
                     object_normalised=value, quote=quote, source_doc=source, anchor=anchor,
                     asserted_by="strategy_b", **more)


def store():
    return Store(ChunkCorpus(PIECES))


def test_the_store_writes_the_layer_of_the_source_on_the_fact():
    s = store()
    written = [s.write_statement(fact(p.source, p.locator, p.text, p.text.split()[-2], "x")) for p in PIECES[2:]]
    assert [w.layer for w in written] == ["law", "guidance", "manufacturer", "company", "plant"]
    assert [w.layer for w in written] == list(LAYERS)


def test_a_layer_already_written_on_the_fact_is_kept():
    s = store()
    kept = s.write_statement(fact("REG", "Art. 1(1)", PIECES[2].text, "ten years", "P10Y", layer="guidance"))
    assert kept.layer == "guidance"


def test_each_layer_outranks_the_ones_below_it():
    ranks = [rank_of(fact("x", "y", "q", "q", "v", layer=layer)) for layer in LAYERS]
    assert ranks == sorted(ranks, reverse=True) and len(set(ranks)) == 5
    person = fact("x", "y", "q", "q", "v", layer="law").model_copy(update={"asserted_by": "person:someone"})
    assert 0 < rank_of(person) < min(ranks)
    assert rank_of(fact("unknown", "y", "q", "q", "v")) == 0


def test_inside_the_law_a_ministerial_decree_ranks_below_the_other_laws_and_above_guidance():
    s = store()
    rank = {source: s.rank_of(fact(source, "a", "q", "q", "v")) for source in
            ("REG", "DLGS71", "DM2011", "inail-guide")}
    assert rank["REG"] == rank["DLGS71"] > rank["DM2011"] > rank["inail-guide"]


def test_sixty_days_against_forty_five_settles_for_the_legislative_decree():
    s = store()
    decree = s.write_statement(fact("DM2011", "art. 2, c. 1", SIXTY, "sessanta giorni", "P60D"))
    s.make_current(decree.id)
    law = s.write_statement(fact("DLGS71", "art. 71, c. 11", FORTY_FIVE, "quarantacinque giorni", "P45D"))
    winner, reason = s.settle(decree, law)
    assert winner is law and reason == "a legislative decree outranks a ministerial decree"
    assert s.settle(law, decree) == (law, reason)          # the order of the arguments does not matter
    s.make_current(law.id)
    assert law.status == "current" and decree.status == "conflict" and decree.conflicts_with == law.id
    assert [x.object for x in s.as_of(law.in_force_from or __import__("datetime").date.today())] == ["P45D"]


def test_the_ministerial_decree_loses_even_when_it_arrives_last():
    s = store()
    law = s.write_statement(fact("DLGS71", "art. 71, c. 11", FORTY_FIVE, "quarantacinque giorni", "P45D"))
    s.make_current(law.id)
    decree = s.write_statement(fact("DM2011", "art. 2, c. 1", SIXTY, "sessanta giorni", "P60D"))
    s.make_current(decree.id)
    assert law.status == "current" and decree.status == "conflict"


def test_the_reason_names_both_layers_and_equal_rank_goes_to_the_first():
    manual = fact("ur5e-manual", "p. 1", "q", "q", "v", layer="manufacturer")
    procedure = fact("procedure-7", "p. 1", "q", "q", "v", layer="company")
    assert settle(procedure, manual) == (manual, "the manufacturer's manual outranks a company procedure")
    other = fact("procedure-8", "p. 1", "q", "q", "w", layer="company")
    winner, reason = settle(other, procedure)
    assert winner is other and "more recent" in reason
    regulation = fact("REG", "Art. 1(1)", "q", "q", "v", layer="law")
    assert settle(manual, regulation)[1] == "an EU regulation outranks the manufacturer's manual"


def test_the_registry_corpus_gives_a_layer_to_each_document_kind(tmp_path):
    fields = ["id", "doc_id", "anchor", "kind", "version", "in_force_from", "path"]
    kinds = {"a": "law", "b": "manual", "c": "procedure", "d": "log"}
    with (tmp_path / "registry.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, restval="")
        writer.writeheader()
        writer.writerows({"id": doc, "doc_id": doc, "kind": kind} for doc, kind in kinds.items())
    corpus = Corpus(tmp_path)
    assert [corpus.layer(doc) for doc in "abcd"] == ["law", "manufacturer", "company", "plant"]
    assert corpus.layer("missing") == ""


def test_an_interval_shorter_than_the_upper_rule_is_stricter_and_a_longer_one_is_looser():
    assert compare_strictness("P2Y", "P90D", SMALLER_IS_STRICTER) == "stricter"   # the procedure inspects more often
    assert compare_strictness("P90D", "P2Y", SMALLER_IS_STRICTER) == "looser"     # it inspects less often: flagged
    assert compare_strictness("P1Y", "P365D", SMALLER_IS_STRICTER) == "same"
    assert compare_strictness("P60D", "P45D", SMALLER_IS_STRICTER) == "stricter"
    assert compare_strictness("P1M", "P6W", SMALLER_IS_STRICTER) == "looser"


def test_a_protected_distance_larger_than_the_upper_rule_is_stricter_and_a_smaller_one_is_looser():
    assert compare_strictness(850, 1000, LARGER_IS_STRICTER) == "stricter"        # the fence is wider than the reach
    assert compare_strictness("1300 mm", "1000 mm", LARGER_IS_STRICTER) == "looser"
    assert compare_strictness("1.3 m", 1300, LARGER_IS_STRICTER) == "same"


def test_values_that_cannot_be_compared_are_refused():
    with pytest.raises(ValueError):
        compare_strictness("P2Y", "1000 mm", SMALLER_IS_STRICTER)
    with pytest.raises(ValueError):
        compare_strictness("soon", "P2Y", SMALLER_IS_STRICTER)
    with pytest.raises(ValueError):
        compare_strictness("P2Y", "P1Y", "whatever")
