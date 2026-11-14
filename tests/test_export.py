"""Owner: Core. The exported file carries the layers, and its shapes catch a fence smaller than the arm's reach."""
from datetime import date

from rdflib import RDF, RDFS, Graph, Literal

from atlas.ontology import export
from atlas.ontology.export import PA
from atlas.ontology.statements import LAYERS, ChunkCorpus, Statement, Store

DAY = date(2026, 11, 14)
CLASSES = {"Document": "A document that must exist.", "PeriodicVerification": "A verification that recurs.",
           "Machinery": "A machine.", "Cell": "A robotic cell."}
RELATIONS = {"retentionPeriod": ("Document", "duration", "for how long a document must be kept"),
             "hasTimeLimit": ("PeriodicVerification", "duration", "the time limit of a verification"),
             "reachMm": ("Machinery", "text", "the maximum reach of the arm, in mm"),
             "protectedZoneRadiusMm": ("Cell", "text", "the radius of the fenced area, in mm")}


class Piece:
    def __init__(self, source, locator, text, layer):
        self.source, self.locator, self.text, self.layer, self.version = source, locator, text, layer, "v1"


PIECES = [Piece("REG", "Art. 10(3)", "The technical documentation shall be kept for 10 years.", "law"),
          Piece("ur5e-manual", "p. 12", "Reach 850 mm", "manufacturer"),
          Piece("layout-cell", "p. 1", "Protected zone radius 1000 mm", "plant")]


def small_store():
    store = Store(ChunkCorpus(PIECES))
    rows = [("technical documentation", "retentionPeriod", "P10Y", "10 years", PIECES[0]),
            ("UR5e", "reachMm", "850", "850", PIECES[1]),
            ("cell 1", "protectedZoneRadiusMm", "1000", "1000", PIECES[2])]
    for subject, predicate, value, written, piece in rows:
        s = store.write_statement(Statement(subject=subject, predicate=predicate, object=value, object_as_written=written,
                                            quote=piece.text, source_doc=piece.source, anchor=piece.locator,
                                            asserted_by="strategy_b"))
        store.make_current(s.id)
    return store


def test_an_exported_store_carries_the_layers_and_validates(tmp_path):
    ontology, shapes, graph = export.write(small_store(), tmp_path, DAY, CLASSES, RELATIONS)
    layers = {str(graph.value(node, PA.layer)) for node in graph.subjects(RDF.type, PA.Statement)}
    assert layers == {"law", "manufacturer", "plant"}
    nodes = {str(graph.value(node, RDFS.label)): int(graph.value(node, PA.order))
             for node in graph.subjects(RDF.type, PA.Layer)}
    assert nodes == {name: number for number, name in enumerate(LAYERS, start=1)}
    assert export.validate(ontology, shapes) == (True, [])


def test_a_fact_stored_without_a_layer_gets_it_from_its_source_at_export(tmp_path):
    store = small_store()
    for s in store.statements:
        s.layer = ""                      # as in a store saved before layers existed
    ontology, shapes, graph = export.write(store, tmp_path, DAY, CLASSES, RELATIONS)
    assert sorted(str(o) for o in graph.objects(None, PA.layer)) == ["law", "manufacturer", "plant"]
    assert export.validate(ontology, shapes)[0]


def test_a_statement_without_a_layer_or_with_an_unknown_one_is_a_violation(tmp_path):
    store = small_store()
    store.statements[0].layer, store.statements[0].source_doc = "", "nowhere"
    store.statements[1].layer = "rumour"
    ontology, shapes, _ = export.write(store, tmp_path, DAY, CLASSES, RELATIONS)
    conforms, messages = export.validate(ontology, shapes)
    assert not conforms and len(messages) == 2
    assert all("exactly one layer" in m for m in messages)


def cell_graph(tmp_path, reach):
    """The small store, plus the cell of the plant: one arm located in a cell with a 1000 mm protected zone."""
    _, shapes, graph = export.write(small_store(), tmp_path, DAY, CLASSES, RELATIONS)
    cell, arm = PA.Cell_robotic_cell_1, PA.Machinery_arm
    graph.add((cell, RDF.type, PA.Cell))
    graph.add((cell, RDFS.label, Literal("robotic cell 1")))
    graph.add((cell, PA.protectedZoneRadiusMm, Literal(1000)))
    graph.add((arm, RDF.type, PA.Machinery))
    graph.add((arm, RDFS.label, Literal("the robot arm")))
    graph.add((arm, PA.locatedIn, cell))
    graph.add((arm, PA.reachMm, Literal(reach)))
    ontology = tmp_path / "cell.ttl"
    graph.serialize(ontology, format="turtle")
    return ontology, shapes, graph


def test_a_1000_mm_zone_around_an_850_mm_arm_passes(tmp_path):
    ontology, shapes, graph = cell_graph(tmp_path, 850)
    assert export.validate(ontology, shapes) == (True, [])
    assert export.zone_violations(graph) == []


def test_the_same_zone_around_a_1300_mm_arm_is_exactly_one_violation(tmp_path):
    ontology, shapes, graph = cell_graph(tmp_path, 1300)
    conforms, messages = export.validate(ontology, shapes)
    assert not conforms and len(messages) == 1
    sentence = ("The protected zone of robotic cell 1 has a radius of 1000 mm, but the robot arm located in it "
                "reaches 1300 mm: the fence does not cover the machine's maximum extension.")
    assert messages[0].endswith(sentence)
    assert export.zone_violations(graph) == [sentence]


def test_the_zone_rule_reads_values_written_with_their_unit(tmp_path):
    graph = Graph()
    graph.add((PA.cell, PA.protectedZoneRadiusMm, Literal("1000 mm")))
    graph.add((PA.arm, PA.locatedIn, PA.cell))
    graph.add((PA.arm, PA.reachMm, Literal("1300 mm")))
    ontology, shapes = tmp_path / "o.ttl", tmp_path / "s.ttl"
    graph.serialize(ontology, format="turtle")
    shapes.write_text(export.SHAPES, encoding="utf-8")
    conforms, messages = export.validate(ontology, shapes)
    assert not conforms and len(messages) == 1 and "the protected zone of cell" in messages[0].lower()
    assert len(export.zone_violations(graph)) == 1
