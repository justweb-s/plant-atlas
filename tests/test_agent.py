"""Owner: Core. The answering agent, with the models replaced: no network (AGENTS.md §6)."""
import json
from datetime import date

from atlas import llm
from atlas.agent import answer as agent
from atlas.ontology.statements import Statement


class TinyStore:
    """Just what the agent reads from a store: the statements and the facts in force on a day."""

    def __init__(self, statements):
        self.statements = statements

    def as_of(self, day):
        return [s for s in self.statements if s.status in ("current", "closed")
                and not (s.in_force_to and s.in_force_to <= day)]


def _fact(i, subject, predicate, value, written, anchor="Art. 1", status="current", condition="", closed=None):
    return Statement(id=f"st-{i:04d}", subject=subject, predicate=predicate, object=value, object_as_written=written,
                     condition=condition, quote=f"quote {i}: {written}", source_doc="REG", anchor=anchor,
                     status=status, in_force_to=closed, asserted_by="test")


FACTS = [
    _fact(1, "Old act", "repealedFrom", "2027-01-14", "14 January 2027", status="closed", closed=date(2023, 7, 4)),
    _fact(2, "Old act", "repealedFrom", "2027-01-20", "20 January 2027", anchor="Corrigendum, point 5"),
    _fact(3, "products under the old act", "placingAllowedUntil", "2027-01-20", "20 January 2027",
          condition="placed on the market before 14 January 2027"),
    _fact(4, "technical documentation", "retentionPeriod", "P10Y", "at least 10 years"),
    _fact(5, "saws", "listedIn", "annex i, part a, point 1", "1.", anchor="Annex I, Part A, point 1"),
]


def _ask(reply, monkeypatch, question="When is the old act repealed?", facts=FACTS, **kwargs):
    seen = {}

    def chat(messages, **params):
        seen["system"], seen["user"] = messages[0]["content"], messages[1]["content"]
        return {"text": reply if isinstance(reply, str) else json.dumps(reply), "usage": None}

    monkeypatch.setattr(llm, "chat", chat)
    monkeypatch.setattr(llm, "embed", lambda texts, **params: [[1.0, 0.0] for _ in texts])
    return agent.answer(question, TinyStore(facts), date(2026, 11, 14), **kwargs), seen


def test_no_retrieved_fact_means_unknown(monkeypatch):
    for reply in ({"kind": "boolean", "value": True, "text": "t", "used": []},     # no fact, no answer
                  {"kind": "boolean", "value": True, "text": "t", "used": [99]},    # a fact that was not given
                  {"kind": "unknown", "value": None, "used": [0]}, "not json"):
        a, _ = _ask(reply, monkeypatch)
        assert a.value is None and a.text
    a, _ = _ask({"kind": "date", "value": "2027-01-20", "used": [0]}, monkeypatch, facts=[])
    assert a.value is None and a.steps == []


def test_value_is_normalised_to_its_kind(monkeypatch):
    # each case cites the fact that carries its value: 0 the repeal date, 2 the retention period, 3 the saws
    cases = [({"kind": "date", "value": ["20 January 2027"]}, 0, "2027-01-20"),
             ({"kind": "date", "value": "2027-01-20"}, 0, "2027-01-20"),
             ({"kind": "duration", "value": ["at least 10 years"]}, 2, "P10Y"),
             ({"kind": "duration", "value": "dieci anni (10 anni)"}, 2, "P10Y"),
             ({"kind": "boolean", "value": "Yes"}, 0, True),
             ({"kind": "boolean", "value": False}, 0, False),
             ({"kind": "set", "value": "saws"}, 3, ["saws"]),
             ({"kind": "set", "value": ["saws [fact 3]", "saws", " lifts "]}, 3, ["saws"]),   # lifts: in no fact
             ({"kind": "text", "value": ["the body", "within 10 years"]}, 2, "the body; within 10 years")]
    for reply, fact, expected in cases:
        a, _ = _ask({**reply, "text": "t", "used": [fact]}, monkeypatch)
        assert a.value == expected and type(a.value) is type(expected), reply


def test_no_supporting_fact_means_no_answer(monkeypatch):
    unsupported = [{"kind": "date", "value": "2030-05-01", "used": [0]},        # a date no used fact carries
                   {"kind": "duration", "value": "P45D", "used": [2]},          # the fact says ten years
                   {"kind": "set", "value": ["lifts", "presses"], "used": [3]}, # no item is in the fact
                   {"kind": "text", "value": "INAIL, within 45 days", "used": [2]}]   # body and number unsupported
    for reply in unsupported:
        a, _ = _ask({**reply, "text": "t"}, monkeypatch)
        assert a.value is None and "(" in a.text, reply
    current = [f for f in FACTS if f.status == "current"]
    assert agent.grounded("boolean", True, [current[3]], "Is it raining?")[0] is None   # undated, off the subject
    assert agent.grounded("boolean", True, [current[0]], "Is it raining?")[0] is True   # a dated fact supports it
    value, used, _ = agent.grounded("text", "The body keeps it. INAIL checks within 45 days.", [current[2]], "Who?")
    assert value == "The body keeps it."                                                # the unsupported clause goes
    _, used, _ = agent.grounded("date", "2027-01-20", [current[0], current[3]], "When is the old act repealed?")
    assert [s.id for s in used] == ["st-0002"]                                          # the unrelated fact is dropped


def test_every_step_names_its_fact(monkeypatch):
    a, _ = _ask({"kind": "date", "value": "2027-01-20", "text": "t", "used": [0, 1, 1]}, monkeypatch)
    assert len(a.steps) == 2
    for step in a.steps:
        assert step.statement_id and step.quote and step.locator
    assert a.steps[0].statement_id == "st-0002" and a.steps[0].locator == "REG, Corrigendum, point 5"


def test_dates_are_compared_in_code_and_corrections_are_flagged(monkeypatch):
    _, seen = _ask({"kind": "boolean", "value": True, "text": "t", "used": [0]}, monkeypatch,
                   question="On 16 January 2027, is the old act still in force?")
    assert "2027-01-16 is 4 days before 2027-01-20" in seen["user"]
    assert "2027-01-14 quoted in this condition was corrected to 2027-01-20" in seen["user"]
    assert "st-0001" not in seen["user"] and "14 January 2027 (2027-01-14)" not in seen["user"]   # the closed fact stays out


def test_related_brings_dated_facts_and_the_facts_of_a_named_place():
    facts = [f for f in FACTS if f.status == "current"]
    assert {s.id for s in agent.related("Until when may it be sold?", facts, [facts[2]])} >= {"st-0002"}
    assert [s.id for s in agent.related("What is listed in Annex I, Part A?", facts, [facts[2]])] == ["st-0005"]
    assert [s.id for s in agent.related("For how long is it kept?", facts, [facts[0]])] == ["st-0004"]


def test_text_in_italian_leaves_the_value_alone(monkeypatch):
    a, seen = _ask({"kind": "date", "value": "2027-01-20", "text": "Dal 20 gennaio 2027.", "used": [0]}, monkeypatch,
                   lang="it")
    assert "Italian" in seen["system"] and a.value == "2027-01-20" and a.text == "Dal 20 gennaio 2027."
    a, seen = _ask("not json", monkeypatch, lang="it")
    assert a.value is None and a.text == agent.UNKNOWN["it"]
    _, seen = _ask("not json", monkeypatch)
    assert "Italian" not in seen["system"]


def test_the_verification_rule_decides_for_a_named_device(monkeypatch):
    def plant(i, subject, predicate, value):
        return Statement(id=f"pl-{i}", subject=subject, predicate=predicate, object=value, object_as_written=value,
                         quote=f"quote {value}", source_doc="PLANT", anchor="p. 1", status="current",
                         asserted_by="test")

    row = Statement(id="row-1", subject="Apparecchi di sollevamento materiali con portata superiore a 200 Kg",
                    predicate="verificationInterval", object="P1Y", object_as_written="Verifica annuale",
                    condition="di tipo mobile o trasferibile | con utilizzo regolare", quote="quote row",
                    source_doc="LAW", anchor="Allegato VII, riga 1", status="current", asserted_by="test")
    facts = [row, plant(1, "IGEA device 7", "deviceKind", "GRU PER AUTOCARRO"),
             plant(2, "IGEA device 7", "capacityKg", "5000"), plant(3, "IGEA device 7", "yearBuilt", "2017"),
             plant(4, "IGEA site", "siteSector", "estrattivo"), plant(5, "IGEA device 9", "deviceKind", "CARRELLO")]
    question = "How often must the crane at position 7 be verified?"
    a, seen = _ask({"kind": "unknown", "value": None, "text": "t", "used": []}, monkeypatch, question, facts)
    assert a.value == "P1Y" and "Computed by rule" in seen["user"] and "treated as mobile" in a.text
    assert {step.statement_id for step in a.steps} == {"row-1", "pl-1", "pl-2", "pl-3", "pl-4"}
    assert all(step.quote and step.locator for step in a.steps)
    a, _ = _ask({"kind": "duration", "value": "P2Y", "text": "t", "used": [0]}, monkeypatch,
                question.replace("7", "9"), facts)
    assert a.value is None and "not mapped" in a.text   # no interval from the rule: unknown, with its reason
    a, seen = _ask({"kind": "unknown", "value": None, "used": []}, monkeypatch, "What is at position 7?", facts)
    assert a.value is None and "Computed by rule" not in seen["user"]   # not a verification question: no rule
