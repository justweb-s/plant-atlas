"""What a change of document does to the ontology (Core): computed from anchors, quotes and fingerprints."""
from atlas.contracts import Chunk
from atlas.ontology import impact
from atlas.ontology.statements import ChunkCorpus, Statement, Store


def small_world():
    chunks = [Chunk("DIR:Art.1", "DIR", "Art. 1", "This Directive applies to machinery.", "v1", layer="law"),
              Chunk("arm-manual:p1", "arm-manual", "p. 1", "Declaration in accordance with 2006/42/EC Annex II B.", "v1",
                    layer="manufacturer")]
    store = Store(ChunkCorpus(chunks))
    law = store.write_statement(Statement(subject="Directive", predicate="appliesTo", object="machinery",
                                          object_as_written="machinery", quote="This Directive applies to machinery.",
                                          source_doc="DIR", anchor="Art. 1", asserted_by="test"))
    manual = store.write_statement(Statement(subject="arm", predicate="hasDeclaration", object="2006/42/EC Annex II B",
                                             object_as_written="2006/42/EC Annex II B",
                                             quote="Declaration in accordance with 2006/42/EC Annex II B.",
                                             source_doc="arm-manual", anchor="p. 1", asserted_by="test"))
    law.status = manual.status = "current"
    return store, chunks


def test_every_fact_is_found_in_its_piece_and_a_changed_piece_is_noticed():
    store, chunks = small_world()
    assert impact.health(store, chunks)["quote_found"] == 2
    chunks[1].text = "Declaration in accordance with Regulation (EU) 2023/1230."   # the manual is reissued
    report = impact.health(store, chunks)
    assert report["quote_missing"] == 1 and report["problems"][0]["why"].startswith("the piece no longer")
    assert impact.health(store, chunks[:1])["piece_missing"] == 1                  # the manual is withdrawn


def test_a_document_knows_which_facts_of_other_layers_cite_it():
    store, chunks = small_world()
    directive = next(d for d in impact.documents(store, chunks) if d["source"] == "DIR")
    assert directive["facts_anchored"] == 1
    assert directive["referred_by"] == [{"layer": "manufacturer", "count": 1,
                                         "examples": directive["referred_by"][0]["examples"]}]
    assert directive["referred_by"][0]["examples"][0]["source_doc"] == "arm-manual"


def test_the_real_store_has_its_worked_changes():
    from atlas.ontology.build import raw_store
    from atlas.strategies.plant import device_records

    store = raw_store("B")
    cases = {c["id"]: c for c in impact.what_if(store, device_records(store.statements))}
    assert len(cases["corrigendum-withdrawn"]["facts_affected"]) == 9
    assert cases["annex-vii-2026"]["added"] and "reconstructed" in cases["annex-vii-2026"]["note"]
