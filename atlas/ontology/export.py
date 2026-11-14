"""Owner: Core. The fact store as a file: Turtle with the schema, the facts in force at a date and their provenance.

The store is the source of truth; this file is what a jury, Protégé or another platform reads.
SHACL shapes are written next to it and checked with pySHACL.
"""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from rdflib import OWL, RDF, RDFS, XSD, Graph, Literal, Namespace, URIRef

from atlas.ontology.statements import Statement, Store

PA = Namespace("https://github.com/justweb-s/plant-atlas/ontology#")
SH = Namespace("http://www.w3.org/ns/shacl#")
PROV = Namespace("http://www.w3.org/ns/prov#")
DATATYPES = {"date": XSD.date, "duration": XSD.duration, "text": XSD.string}

SHAPES = """@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix pa: <https://github.com/justweb-s/plant-atlas/ontology#> .

# No quote, no fact: every statement names exactly one passage and carries its words.
pa:StatementShape a sh:NodeShape ;
    sh:targetClass pa:Statement ;
    sh:property [ sh:path pa:quote ; sh:minCount 1 ; sh:maxCount 1 ; sh:minLength 1 ;
                  sh:message "A statement without its quote." ] ;
    sh:property [ sh:path pa:sourceDocument ; sh:minCount 1 ; sh:maxCount 1 ;
                  sh:message "A statement must come from exactly one document." ] ;
    sh:property [ sh:path pa:locator ; sh:minCount 1 ; sh:maxCount 1 ;
                  sh:message "A statement must name the article or annex point it comes from." ] ;
    sh:property [ sh:path pa:relation ; sh:minCount 1 ; sh:maxCount 1 ] .

# An act is repealed from one date only: an uncorrected and a corrected date cannot both be in force.
pa:RepealShape a sh:NodeShape ;
    sh:targetSubjectsOf pa:repealedFrom ;
    sh:property [ sh:path pa:repealedFrom ; sh:maxCount 1 ; sh:datatype xsd:date ;
                  sh:message "An act has two repeal dates in force at the same time." ] .

pa:DateShape a sh:NodeShape ;
    sh:targetSubjectsOf pa:appliesFrom ;
    sh:property [ sh:path pa:appliesFrom ; sh:datatype xsd:date ;
                  sh:message "An application date that is not a date." ] .

pa:RetentionShape a sh:NodeShape ;
    sh:targetSubjectsOf pa:retentionPeriod ;
    sh:property [ sh:path pa:retentionPeriod ; sh:datatype xsd:duration ;
                  sh:message "A retention period that is not a duration." ] .
"""


def slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_")[:60] or "thing"


def _value(s: Statement, kind: str):
    datatype = DATATYPES.get(kind)
    if datatype in (XSD.date, XSD.duration):
        ok = re.fullmatch(r"\d{4}-\d{2}-\d{2}", s.object) if datatype == XSD.date else re.fullmatch(r"P[0-9YMWDTHS.]+", s.object)
        return Literal(s.object, datatype=datatype) if ok else Literal(s.object_as_written)
    if datatype == XSD.string:
        return Literal(s.object_as_written)
    return None   # an individual of the value class


def to_graph(store: Store, day: date, classes: dict, relations: dict) -> Graph:
    g = Graph()
    for prefix, ns in (("pa", PA), ("prov", PROV), ("owl", OWL)):
        g.bind(prefix, ns)
    g.add((URIRef(str(PA)[:-1]), RDF.type, OWL.Ontology))
    g.add((URIRef(str(PA)[:-1]), OWL.versionInfo, Literal(f"facts in force on {day.isoformat()}")))
    for name, comment in classes.items():
        g.add((PA[name], RDF.type, OWL.Class))
        g.add((PA[name], RDFS.comment, Literal(comment, lang="en")))
    g.add((PA.Statement, RDF.type, OWL.Class))
    g.add((PA.Statement, RDFS.comment, Literal("A fact with its quote, its condition, its source and its validity.", lang="en")))
    for name, (subject_class, value, what) in relations.items():
        is_data = value in DATATYPES
        g.add((PA[name], RDF.type, OWL.DatatypeProperty if is_data else OWL.ObjectProperty))
        g.add((PA[name], RDFS.domain, PA[subject_class]))
        g.add((PA[name], RDFS.range, DATATYPES[value] if is_data else PA[value]))
        g.add((PA[name], RDFS.comment, Literal(what, lang="en")))
    for s in store.as_of(day):
        if s.status != "current" or s.predicate not in relations:
            continue
        subject_class, value_kind, _ = relations[s.predicate]
        subject = PA[f"{subject_class}_{slug(s.subject)}"]
        g.add((subject, RDF.type, PA[subject_class]))
        g.add((subject, RDFS.label, Literal(s.subject)))
        value = _value(s, value_kind)
        if value is None:
            value = PA[f"{value_kind}_{slug(s.object_as_written)}"]
            g.add((value, RDF.type, PA[value_kind]))
            g.add((value, RDFS.label, Literal(s.object_as_written)))
        g.add((subject, PA[s.predicate], value))
        node = PA[s.id]
        g.add((node, RDF.type, PA.Statement))
        g.add((node, PA.about, subject))
        g.add((node, PA.relation, PA[s.predicate]))
        g.add((node, PA.value, value))
        g.add((node, PA.quote, Literal(s.quote)))
        g.add((node, PA.sourceDocument, Literal(s.source_doc)))
        g.add((node, PA.locator, Literal(s.anchor)))
        g.add((node, PROV.wasAttributedTo, Literal(s.asserted_by)))
        if s.condition:
            g.add((node, PA.condition, Literal(s.condition)))
        if s.in_force_from:
            g.add((node, PA.validFrom, Literal(s.in_force_from.isoformat(), datatype=XSD.date)))
        if s.conflicts_with:
            g.add((node, PA.supersedes, PA[s.conflicts_with]))
    return g


def write(store: Store, folder: Path, day: date, classes: dict, relations: dict) -> tuple[Path, Path, Graph]:
    folder.mkdir(parents=True, exist_ok=True)
    graph = to_graph(store, day, classes, relations)
    ontology, shapes = folder / "ontology.ttl", folder / "shapes.ttl"
    graph.serialize(ontology, format="turtle")
    shapes.write_text(SHAPES, encoding="utf-8")
    return ontology, shapes, graph


def validate(ontology: Path, shapes: Path) -> tuple[bool, list[str]]:
    from pyshacl import validate as shacl_validate

    data = Graph().parse(ontology, format="turtle")
    conforms, report, _ = shacl_validate(data, shacl_graph=Graph().parse(shapes, format="turtle"))
    messages = [f"{focus}: {message}" for focus, message in
                report.query("SELECT ?f ?m WHERE { ?r <http://www.w3.org/ns/shacl#focusNode> ?f ; "
                             "<http://www.w3.org/ns/shacl#resultMessage> ?m }")]
    return bool(conforms), [str(m) for m in messages]
