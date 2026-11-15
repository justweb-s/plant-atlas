"""The procedural graphs: every file loads, every skill walks its edges on a tiny store. No network."""
import json
from datetime import date

import pytest

from atlas.agent import answer as base
from atlas.agent import skills
from atlas.ontology.statements import Statement, Store

DAY = date(2026, 11, 14)
ROW = ("Apparecchi di sollevamento materiali con portata superiore a 200 Kg, non azionati a mano, "
       "di tipo {kind}, con modalità di utilizzo regolare")


class NoCorpus:
    def section(self, doc_id, anchor):
        return None

    def meta(self, doc_id):
        return {}

    def layer(self, doc_id):
        return ""


def fact(id, subject, predicate, obj, written=None, status="current", source="DOC", anchor="art. 1", **more):
    written = written or obj
    return Statement(id=id, subject=subject, predicate=predicate, object=obj, object_as_written=written,
                     object_normalised=more.pop("normal", obj), quote=more.pop("quote", f"{subject} {written}"),
                     source_doc=source, anchor=anchor, status=status, asserted_by="test", **more)


def tiny_store() -> Store:
    store = Store(NoCorpus())
    store.statements = [
        fact("d1", "IGEA device 1", "deviceKind", "GRU A PONTE"), fact("d2", "IGEA device 1", "capacityKg", "5000"),
        fact("d3", "IGEA device 1", "yearBuilt", "2001"), fact("d4", "IGEA site", "siteSector", "minerario"),
        fact("d5", "IGEA device 2", "deviceKind", "CARRELLO ELEVATORE"), fact("d6", "IGEA device 2", "capacityKg", "5000"),
        fact("d7", "IGEA device 2", "yearBuilt", "2001"),
        fact("r1", ROW.format(kind="fisso"), "verificationInterval", "P2Y", "biennale", normal="P2Y", layer="law"),
        fact("r2", ROW.format(kind="mobile o trasferibile"), "verificationInterval", "P1Y", "annuale", normal="P1Y", layer="law"),
        fact("a1", "Regulation Alpha", "appliesFrom", "2027-01-20", "20 January 2027", layer="law"),
        fact("a0", "Regulation Alpha", "appliesFrom", "2027-01-14", "14 January 2027", status="closed", layer="law"),
        fact("k1", "technical file of the pump", "retentionPeriod", "P10Y", "ten years", normal="P10Y", layer="law", source="LAW"),
        fact("k2", "technical file of the pump", "retentionPeriod", "P5Y", "five years", normal="P5Y", status="conflict",
             conflicts_with="k1", layer="company", source="PROC"),
        fact("m1", "sawing machines", "listedIn", "annex i, part a", "Annex I, Part A", anchor="Annex I, Part A, point 1"),
        fact("m2", "presses", "listedIn", "annex i, part a", "Annex I, Part A", anchor="Annex I, Part A, point 2"),
        fact("m3", "Presses", "listedIn", "annex i, part a", "Annex I, Part A", anchor="Annex I, Part A, point 2"),
        fact("w1", "periodic verification of lifts", "verifiedBy", "ASL", "ASL",
             quote="The verification is carried out by ASL or by an authorised body."),
    ]
    return store


def ask(monkeypatch, query: dict):
    """The relation query comes from a canned reply: the router's one model call, without the network."""
    skills._CONTEXT.clear()
    base._QUERY_OUT.clear()
    monkeypatch.setattr(base.llm, "chat", lambda *a, **k: {"text": json.dumps(query), "usage": {}})


def by_name(name: str) -> dict:
    return next(s for s in skills.load() if s["name"] == name)


def follows_edges(skill: dict, trace: dict) -> bool:
    drawn = {(e["from"], e["to"], e.get("when", "")) for e in skill["edges"]}
    ran = [n["id"] for n in trace["nodes"] if n["status"] == "run"]
    walked = [skill["nodes"][0]["id"]] + [b for _, b, _ in trace["edges_taken"]]
    chained = all(trace["edges_taken"][i][1] == trace["edges_taken"][i + 1][0] for i in range(len(trace["edges_taken"]) - 1))
    return all(tuple(e) in drawn for e in trace["edges_taken"]) and sorted(ran) == sorted(walked) and chained


def test_every_file_loads_and_its_edges_name_existing_nodes():
    loaded = skills.load()
    assert {s["name"] for s in loaded} == {"verification_interval", "value_on_date", "single_value", "members_of", "who_does"}
    for skill in loaded:
        assert skills.check(skill) == [], skill["name"]
        assert {n["kind"] for n in skill["nodes"]} <= {"lookup", "script", "decision", "answer", "unknown"}
        assert skill["when"]["relations"] and skill["description"]


CASES = [
    ("verification_interval", "How often must the apparecchio di sollevamento at position 1 be verified?",
     {"relations": ["verificationInterval"], "subject_terms": ["crane"], "wants": "one"}, "P2Y", "duration"),
    ("value_on_date", "From which date does Regulation Alpha apply?",
     {"relations": ["appliesFrom"], "subject_terms": ["Regulation Alpha"], "wants": "one"}, "2027-01-20", "date"),
    ("value_on_date", "On 16 January 2027, does Regulation Alpha apply?",
     {"relations": ["appliesFrom"], "subject_terms": ["Regulation Alpha"], "wants": "one"}, False, "boolean"),
    ("single_value", "For how long must the technical file of the pump be kept?",
     {"relations": ["retentionPeriod"], "subject_terms": ["technical file", "pump"], "wants": "one"}, "P10Y", "duration"),
    ("members_of", "Which categories are listed in Annex I, Part A?",
     {"relations": ["listedIn"], "subject_terms": ["categories"], "place": "Annex I, Part A", "wants": "all"},
     ["sawing machines", "presses"], "set"),
    ("who_does", "Who carries out the periodic verification of lifts?",
     {"relations": ["verifiedBy"], "subject_terms": ["periodic verification", "lifts"], "wants": "one"},
     "ASL; ASL or by an authorised body", "text"),
]


@pytest.mark.parametrize("name,question,query,expected,kind", CASES)
def test_each_skill_runs_and_its_trace_follows_the_edges(monkeypatch, name, question, query, expected, kind):
    ask(monkeypatch, query)
    store, skill = tiny_store(), by_name(name)
    if skill.get("enabled", True):
        assert skills.route(question, store, DAY)["name"] == name
    value, got_kind, text, used, trace = skills.run(skill, question, store, DAY)
    assert (value, got_kind) == (expected, kind)
    assert used and text and trace["skill"] == name and trace["model_calls"] == 0
    assert follows_edges(skill, trace)
    assert [n["id"] for n in trace["nodes"]] == [n["id"] for n in skill["nodes"]]


def test_a_correction_and_a_conflict_stay_in_the_trace(monkeypatch):
    ask(monkeypatch, CASES[1][2])
    trace = skills.run(by_name("value_on_date"), CASES[1][1], tiny_store(), DAY)[4]
    assert "a0" in next(n for n in trace["nodes"] if n["id"] == "in_force")["fact_ids"]
    ask(monkeypatch, CASES[3][2])
    trace = skills.run(by_name("single_value"), CASES[3][1], tiny_store(), DAY)[4]
    assert ["settle", "answer", "settled by authority"] in trace["edges_taken"]
    assert "k2" in next(n for n in trace["nodes"] if n["id"] == "settle")["fact_ids"]


def test_an_unmapped_device_ends_in_unknown(monkeypatch):
    ask(monkeypatch, CASES[0][2])
    skill = by_name("verification_interval")
    value, kind, text, used, trace = skills.run(skill, "How often must the truck at position 2 be verified?", tiny_store(), DAY)
    assert value is None and kind == "unknown" and not used and "not mapped" in text
    assert trace["edges_taken"][-1] == ["fixed_or_mobile", "unknown", "not mapped"]
    assert follows_edges(skill, trace)
    assert next(n for n in trace["nodes"] if n["id"] == "answer")["status"] == "skipped"


def test_the_hook_falls_back_when_no_skill_fits(monkeypatch):
    ask(monkeypatch, {"relations": ["definedAs"], "subject_terms": ["machinery"], "wants": "one"})
    store = tiny_store()
    assert skills.route("What is machinery?", store, DAY) is None
    assert skills.try_answer("What is machinery?", store, DAY) is None
    ask(monkeypatch, CASES[0][2])   # a skill fits but ends in unknown: also a fallback
    assert skills.try_answer("How often must the truck at position 2 be verified?", store, DAY) is None
    ask(monkeypatch, CASES[0][2])
    hit = skills.try_answer(CASES[0][1], store, DAY)
    assert hit.value == "P2Y" and hit.steps[0].text.startswith("[skill verification_interval:") and hit.trace["skill"]
    assert all(step.statement_id and step.quote and step.locator for step in hit.steps)


def test_who_does_takes_the_fact_by_its_subject_and_names_every_body_of_its_sentence(monkeypatch):
    query = {"relations": ["verifiedBy"], "subject_terms": ["subsequent verifications", "cranes"], "wants": "one"}
    ask(monkeypatch, query)
    store, skill = tiny_store(), by_name("who_does")
    sentence = "The subsequent verifications of cranes are carried out by the ASL or, where regional law says so, by ARPA."
    store.statements += [
        fact("w2", "subsequent verifications of cranes", "verifiedBy", "ASL", quote=sentence, layer="law", source="LAW"),
        fact("w3", "subsequent verifications of cranes", "verifiedBy", "ARPA", quote=sentence, layer="law", source="LAW"),
        fact("w4", "subsequent verifications of cranes", "verifiedBy", "the owner", layer="company", source="PROC"),
        fact("w5", "audits", "verifiedBy", "the notified body")]
    question = "Who carries out the subsequent verifications of cranes?"
    value, kind, text, used, trace = skills.run(skill, question, store, DAY)
    assert kind == "text" and value == "ASL; ASL or, where regional law says so, by ARPA"   # the law, not the company
    assert [s.id for s in used] == ["w2", "w3"] and follows_edges(skill, trace)
    ask(monkeypatch, {"relations": ["verifiedBy"], "subject_terms": ["boilers"], "wants": "one"})
    value, kind, _, used, trace = skills.run(skill, "Who verifies the boilers?", store, DAY)
    assert value is None and kind == "unknown" and not used     # no fact whose subject is what is asked: no answer
