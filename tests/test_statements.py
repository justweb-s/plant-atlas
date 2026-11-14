"""The fact store (Core): one way in, one way out, nothing deleted.

Each rule has a planted bad case that must be rejected and counted.
"""
import csv
from datetime import date

from atlas.ontology.statements import Corpus, Statement, Store

FIELDS = ["id", "doc_id", "anchor", "kind", "version", "in_force_from", "fictional",
          "source", "retrieved", "sha256", "path", "heading"]
MANUAL = "Inspection table\nLifting chain | inspect every 2 years; yearly if older than 10 years\n"
PROCEDURE = "The lifting chain is inspected every 90 days.\n"


def corpus(tmp_path, docs):
    """docs: {doc_id: (kind, version, in_force_from, text)} with one section 'sec' each."""
    (tmp_path / "docs").mkdir(exist_ok=True)
    rows = []
    for doc_id, (kind, version, start, text) in docs.items():
        path = tmp_path / "docs" / f"{doc_id}__sec.txt"
        path.write_text(text, encoding="utf-8")
        common = {"doc_id": doc_id, "kind": kind, "version": version, "in_force_from": start}
        rows.append({"id": doc_id, "anchor": "", **common})
        rows.append({"id": f"{doc_id}#sec", "anchor": "sec", "path": f"docs/{doc_id}__sec.txt", **common})
    with (tmp_path / "registry.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, restval="")
        writer.writeheader()
        writer.writerows(rows)
    return Corpus(tmp_path)


def fact(**overrides):
    base = dict(subject="lifting-chain", predicate="hasInspectionInterval", object="P2Y",
                object_as_written="every 2 years", object_normalised="P2Y",
                condition="unless older than 10 years",
                quote="Lifting chain | inspect every 2 years; yearly if older than 10 years",
                source_doc="manual", anchor="sec", asserted_by="strategy_b")
    return Statement(**{**base, **overrides})


def store(tmp_path, **extra):
    docs = {"manual": ("manual", "v1", "2024-01-01", MANUAL), **extra}
    return Store(corpus(tmp_path, docs))


def test_a_quote_that_is_not_in_the_source_is_rejected(tmp_path):
    s = store(tmp_path)
    assert s.write_statement(fact(quote="Lifting chain | inspect every 5 years")) is None
    assert s.rejections[0]["reason"] == "no_anchor"


def test_a_value_that_is_not_in_the_quote_is_rejected(tmp_path):
    s = store(tmp_path)
    assert s.write_statement(fact(object_as_written="every 3 years")) is None
    assert s.rejections[0]["reason"] == "value_not_in_quote"


def test_a_fact_that_drops_its_condition_is_rejected(tmp_path):
    s = store(tmp_path)
    assert s.write_statement(fact(condition="")) is None
    assert s.rejections[0]["reason"] == "missing_condition"


def test_a_fact_with_quote_value_and_condition_is_stored_as_proposed(tmp_path):
    s = store(tmp_path)
    written = s.write_statement(fact())
    assert written is not None and written.status == "proposed"
    assert written.in_force_from == date(2024, 1, 1)
    assert s.counts()["anchored"] == 1 and s.counts()["rejected"] == 0


def test_a_newer_version_closes_the_old_fact_and_nothing_is_deleted(tmp_path):
    s = store(tmp_path, proc=("procedure", "v1", "2025-01-01", PROCEDURE))
    old = s.write_statement(fact(source_doc="proc", condition="", object="P90D", object_normalised="P90D",
                                 object_as_written="90 days", quote=PROCEDURE.strip()))
    s.make_current(old.id)
    # the procedure is replaced by version 2: 60 days, in force from 1 June 2026
    s.corpus = corpus(tmp_path, {"manual": ("manual", "v1", "2024-01-01", MANUAL),
                                 "proc": ("procedure", "v2", "2026-06-01",
                                          "The lifting chain is inspected every 60 days.\n")})
    new = s.write_statement(fact(source_doc="proc", condition="", object="P60D", object_normalised="P60D",
                                 object_as_written="60 days",
                                 quote="The lifting chain is inspected every 60 days."))
    s.make_current(new.id)
    assert len(s.statements) == 2                      # nothing deleted
    assert old.status == "closed" and old.in_force_to == date(2026, 6, 1)
    assert [x.object for x in s.as_of(date(2026, 1, 15))] == ["P90D"]
    assert [x.object for x in s.as_of(date(2026, 11, 14))] == ["P60D"]


def test_when_two_sources_disagree_the_higher_authority_wins_and_both_are_kept(tmp_path):
    s = store(tmp_path, proc=("procedure", "v1", "2025-01-01", PROCEDURE),
              law=("law", "v1", "2020-01-01", "The lifting chain shall be inspected every 60 days.\n"))
    low = s.write_statement(fact(source_doc="proc", condition="", object="P90D", object_normalised="P90D",
                                 object_as_written="90 days", quote=PROCEDURE.strip()))
    s.make_current(low.id)
    high = s.write_statement(fact(source_doc="law", condition="", object="P60D", object_normalised="P60D",
                                  object_as_written="60 days",
                                  quote="The lifting chain shall be inspected every 60 days."))
    s.make_current(high.id)
    assert high.status == "current"
    assert low.status == "conflict" and low.conflicts_with == high.id
    assert len(s.statements) == 2
