"""Owner: Core. The facts of the manufacturer, guidance and company layers: the parts files load and every
statement in them still passes the store's checks against the chunks as they are now."""
import json
from pathlib import Path

import pytest

from atlas.corpus.chunker import load
from atlas.ontology.statements import ChunkCorpus, Statement, Store
from atlas.strategies import b
from atlas.strategies.schema_b import LAW_RELATIONS, LAYER_RELATIONS, RELATIONS, describe

PARTS = Path(__file__).resolve().parents[1] / "ontology" / "B" / "parts"
LAYERS = ("manufacturer", "guidance", "company")


def _payload(layer: str) -> dict:
    path = PARTS / f"{layer}.json"
    if not path.exists():
        pytest.skip(f"{path.name} is not built yet")
    return json.loads(path.read_text(encoding="utf-8"))


def test_schema_keeps_the_law_relations_and_adds_the_layers():
    from atlas.strategies.schema_b import PLANT_RELATIONS   # written by code, added on top
    assert set(LAW_RELATIONS) | set(LAYER_RELATIONS) | set(PLANT_RELATIONS) == set(RELATIONS)
    assert not set(LAW_RELATIONS) & set(LAYER_RELATIONS)
    assert all(len(spec) == 3 and spec[2] for spec in RELATIONS.values())   # every relation has its description
    assert "hasReach" not in describe()   # the prompt of the law texts is the one the committed run used


def test_layer_spans_give_back_the_text():
    text = ("Maximum payload 5 kg / 11 lb specification Reach 850 mm / 33.5 in " * 12) + "Carry out tests. Once a year."
    spans = b.spans_for_layer(text)
    assert max(len(span) for span in spans) <= b.MAX_SPAN_CHARS
    assert " ".join(spans) == text


@pytest.mark.parametrize("layer", LAYERS)
def test_part_loads_and_every_statement_passes_the_quote_check(layer):
    payload = _payload(layer)
    statements = [Statement(**item) for item in payload["statements"]]
    assert statements, "an empty part means the extraction did not run"
    chunks = list(load())
    of_layer = {c.source for c in chunks if c.layer == layer}
    if not of_layer:
        pytest.skip("the documents of this layer are not on this machine (PDFs stay out of git)")
    store = Store(ChunkCorpus(chunks))
    for statement in statements:
        assert statement.source_doc in of_layer
        assert statement.status in ("current", "open_point", "closed")   # closed: replaced by a learned rule, kept
        assert statement.status == "open_point" or statement.predicate in RELATIONS
        assert statement.asserted_by == f"strategy_b:{layer}"
        again = store.write_statement(statement.model_copy())
        assert again is not None, f"{statement.id}: {store.rejections[-1]['reason']}"
    assert all("reason" in rejection for rejection in payload["rejections"])
