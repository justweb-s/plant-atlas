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
    a, seen = _ask({"kind": "unknown", "value": None, "text": "t", "used": []}, monkeypatch,
                   "When is the next verification of the crane at position 7 due?", facts)
    assert a.value is None and agent.NO_DATES in seen["user"] and a.steps == []   # shown as context, never the value
    a, seen = _ask({"kind": "unknown", "value": None, "used": []}, monkeypatch, "What is at position 7?", facts)
    assert a.value is None and "Computed by rule" not in seen["user"]   # not a verification question: no rule


def test_the_graph_is_queried_by_relation_and_one_regime_is_kept(monkeypatch):
    def fact(i, source, subject, predicate, value, anchor="Art. 1"):
        return Statement(id=f"g-{i}", subject=subject, predicate=predicate, object=value, object_as_written=value,
                         quote=f"quote {value}", source_doc=source, anchor=anchor, status="current",
                         asserted_by="test")

    facts = [fact(1, "REG", "saws", "listedIn", "point 1", "Annex I, Part A, point 1"),
             fact(2, "REG", "lifts", "listedIn", "point 2", "Annex I, Part A, point 2"),
             fact(3, "REG", "presses", "listedIn", "point 1", "Annex I, Part B, point 1"),
             fact(4, "REG", "machinery", "mustAccompany", "EU declaration"),
             fact(5, "DIR", "machinery", "mustAccompany", "EC declaration"),
             fact(6, "CORR", "Regulation", "appliesFrom", "2027-01-20"),
             fact(7, "REG", "records", "retentionPeriod", "P10Y")]
    query = {"relations": ["listedIn", "noSuchRelation"], "subject_terms": ["category"], "place": "Annex I, Part A",
             "source_hint": None, "wants": "all"}
    monkeypatch.setattr(llm, "chat", lambda messages, **params: {"text": json.dumps(query)})
    matched, _ = agent.graph_query("Which categories are listed in Annex I, Part A?", facts)
    assert [s.id for s in matched] == ["g-1", "g-2"]                 # every fact of the relation under the place
    query = {"relations": ["mustAccompany"], "subject_terms": ["machinery", "macchina"], "place": None, "wants": "one"}
    matched, _ = agent.graph_query("What accompanies machinery?", facts)
    assert {s.id for s in matched} == {"g-4", "g-5"}
    kept, line = agent.one_regime("What accompanies machinery?", matched, facts, [])
    assert [s.id for s in kept] == ["g-4"] and "Regulation's" in line
    kept, line = agent.one_regime("What accompanies machinery on 1 May 2026?", matched, facts, [date(2026, 5, 1)])
    assert [s.id for s in kept] == ["g-5"] and "Directive's" in line
    monkeypatch.setattr(llm, "chat", lambda messages, **params: {"text": "not json"})
    assert agent.graph_query("Anything?", facts) == ([], {})


def test_set_items_are_put_in_the_facts_own_words():
    def fact(i, subject, predicate, value, condition="", quote="q", anchor="Art. 25(2)"):
        return Statement(id=f"p-{i}", subject=subject, predicate=predicate, object=value, object_as_written=value,
                         condition=condition, quote=quote, source_doc="REG", anchor=anchor, status="current",
                         asserted_by="test")

    used = [fact(1, "Vehicle servicing lifts", "listedIn", "4.", anchor="Annex I, Part A, point 4"),
            fact(2, "machinery", "requiresProcedure", "full quality assurance (module H)"),
            fact(3, "machinery", "requiresProcedure", "module B followed by module C",
                 quote="EU type-examination (module B) followed by module C"),
            fact(4, "machinery", "mustAccompany", "instructions for use"),
            fact(5, "machinery", "mustAccompany", "digital instructions", condition="or alternatively, on request")]
    polish = agent.polish_set
    assert polish(["Option (a): vehicle servicing lifts (Annex I, Part A, point 4)"], used) == ["Vehicle servicing lifts"]
    assert polish(["Full quality assurance (module H)"], used) == ["full quality assurance (module H)"]   # a name
    assert polish(["EU declaration (before making it available)"], used) == ["EU declaration"]
    assert polish(["module C followed by module B"], used) == ["module B followed by module C"]           # fact order
    assert polish(["Instructions for use", "instructions for use (Art. 10)", "digital instructions"], used) == \
        ["instructions for use"]                                    # no repeat, no alternative
    assert polish(["presses", "presses and saws"], used) == ["presses"]   # the item that only extends another goes
    body = fact(6, "subsequent verifications", "verifiedBy", "ASL",
                quote="Le verifiche sono effettuate dalla ASL o da soggetti pubblici o privati abilitati.")
    assert agent.all_bodies("The ASL.", [body]) == "The ASL; ASL o da soggetti pubblici o privati abilitati"
    assert agent.all_bodies("INAIL", [body]) == "INAIL"


def test_distinct_facts_stay_links_are_followed_and_headings_go():
    def fact(i, subject, predicate, value, anchor, normal=""):
        return Statement(id=f"x-{i}", subject=subject, predicate=predicate, object=value, object_as_written=value,
                         object_normalised=normal, quote="q", source_doc="REG", anchor=anchor, status="current",
                         asserted_by="test")

    procedures = [fact(1, "Part A machinery", "requiresProcedure", "EU type-examination (module B), followed by "
                       "conformity to type (module C)", "Art. 25(2)", "module B followed by module C"),
                  fact(2, "Part A machinery", "requiresProcedure", "full quality assurance (module H)", "Art. 25(2)", "module H"),
                  fact(3, "Part A machinery", "requiresProcedure", "unit verification (module G)", "Art. 25(2)", "module G")]
    got = agent.polish_set(["EU type-examination (module B) followed by conformity to type (module C)",
                            "full quality assurance (module H)", "unit verification (module G)"], procedures)
    assert got == ["module B followed by module C", "module H", "module G"]   # three facts, three short items
    members = [fact(4, "saws", "listedIn", "1.", "Annex I, Part A, point 1"),
               fact(5, "lifts", "listedIn", "2.", "Annex I, Part A, point 2"),
               fact(6, "presses", "listedIn", "1.", "Annex I, Part B, point 1")]
    used = [procedures[1]]
    got = agent.polish_set(["machinery in categories listed in Annex I, Part A"] * 2, used, members + procedures)
    assert got == ["saws", "lifts"] and {s.id for s in used} == {"x-2", "x-4", "x-5"}   # the place is followed
    assert agent.polish_set(["categories of machinery"], [], [], "Which categories of machinery need it?") == []
    risks = [fact(7, "1.3.7", "addressesRisk", "Risks related to moving parts", "Annex III, 1.3.7"),
             fact(8, "1.3.7", "addressesRisk", "contact with moving parts leading to accidents", "Annex III, 1.3.7"),
             fact(9, "1.3.7", "addressesRisk", "contact with moving parts of the transmission", "Annex III, 1.3.7"),
             fact(10, "1.3.7", "addressesRisk", "accidental blockage", "Annex III, 1.3.7")]
    got = agent.polish_set([f.object_as_written for f in risks], risks)
    assert got == ["contact with moving parts leading to accidents", "accidental blockage"]


LONG = ("the manufacturer shall: (a) determine the limits of the machinery, which include the intended use; "
        "(b) identify the hazards that may be generated by the machinery and the associated hazardous situations; "
        "(c) estimate the risks, taking into account the severity of the possible injury")


def _long(i, subject, predicate, written, **more):
    return Statement(id=f"L-{i}", subject=subject, predicate=predicate, object=more.pop("value", written.lower()),
                     object_as_written=written, object_normalised=more.pop("normal", written),
                     quote=f"quote {i}", source_doc=more.pop("source", "REG"), anchor="Art. 10(1)", status="current",
                     asserted_by="test", **more)


def test_a_fact_is_shown_and_ranked_by_its_structure_not_its_length(monkeypatch):
    whole = _long(1, "manufacturer", "hasObligation", LONG, condition="before placing machinery on the market; "
                  "and in every case where the machinery is modified, rebuilt, repainted, refitted with other tools, "
                  "given new software, connected to other machines, moved to another site or sold again")
    line = agent._line(whole)
    assert line.startswith("manufacturer | has obligation | the manufacturer shall") and "…" in line
    assert "identify the hazards" not in line and "moved to another site" not in line and len(line) < 360
    assert line.endswith("… | [REG, Art. 10(1)]") and "| if: before placing machinery on the market; and in every" in line
    dated = _long(2, "Old act", "repealedFrom", "20 January 2027", value="2027-01-20", normal="")
    assert agent._line(dated) == "Old act | repealed from | 20 January 2027 (2027-01-20) | [REG, Art. 10(1)]"
    named = _long(3, "machinery", "requiresProcedure", "full quality assurance (module H)", normal="module H")
    assert "| full quality assurance (module H) (module H) | [REG" in agent._line(named)   # written, then normal form
    assert agent._item_of(whole) == "the manufacturer shall: (a) determine the limits of the machinery, which include the intended use"
    assert agent._item_of(named) == "module H"                                     # a clause, never the whole sentence
    # a fact repaired to hold its whole sentence ranks like the short fact, not above a fact about the subject asked
    monkeypatch.setattr(llm, "chat", lambda messages, **params: {"text": "Chi identifica i pericoli?"})
    short = _long(4, "hazards of machinery", "identifiedBy", "the manufacturer")
    assert [s.id for s in agent.lexical("Who must identify the hazards of machinery?", [whole, short])] == ["L-4", "L-1"]
    # grounding still reads the whole value, and a locator bracket holding "5(1)" is stripped from a set item
    assert agent.grounded("text", "The manufacturer must estimate the risks.", [whole], "What must he do?")[0]
    assert agent.polish_set(["EC declaration (Directive 2006/42/EC, Art. 5(1))"], []) == ["EC declaration"]


def test_one_regime_is_shown_when_the_matched_facts_come_from_both(monkeypatch):
    facts = [_long(i, f"thing {i}", "definedAs", f"definition {i}", source="LAW") for i in range(60)]
    facts += [_long(100, "machinery", "mustAccompany", "EU declaration of conformity"),
              _long(101, "machinery", "mustAccompany", "EC declaration of conformity", source="DIR"),
              _long(102, "Regulation", "appliesFrom", "20 January 2027", value="2027-01-20", source="CORR")]
    seen = {}

    def chat(messages, **params):
        if messages[0]["content"].startswith("You turn a question"):
            return {"text": json.dumps({"relations": ["mustAccompany"], "subject_terms": ["machinery"], "wants": "all"})}
        if "Facts:" in messages[1]["content"]:
            seen["user"] = messages[1]["content"]
            return {"text": json.dumps({"kind": "set", "value": ["EU declaration of conformity"], "text": "t", "used": [0]})}
        return {"text": "Cosa accompagna la macchina?"}

    monkeypatch.setattr(llm, "chat", chat)
    monkeypatch.setattr(llm, "embed", lambda texts, **params: [[1.0, 0.0] for _ in texts])
    monkeypatch.setenv("ATLAS_SKILLS", "0")
    a = agent.answer("What must accompany machinery?", TinyStore(facts), date(2026, 11, 14))
    assert a.value == ["EU declaration of conformity"] and a.steps[0].statement_id == "L-100"
    assert "EU declaration of conformity" in seen["user"] and "EC declaration" not in seen["user"]   # the other act is left out
    assert "use the Regulation's" in seen["user"] and "applies from | 20 January 2027 (2027-01-20)" in seen["user"]


def test_a_duration_written_in_words_supports_the_answer():
    def kept(written, value):
        fact = _fact(9, "protective device", "requiresPeriodicCheck", written, written)
        return agent.grounded("duration", value, [fact], "How often must the protective device be tested?")[0]

    assert kept("at least once a year", "P1Y") == "P1Y" and kept("ogni anno", "P1Y") == "P1Y"
    assert kept("verifica annuale", "P1Y") == "P1Y" and kept("ten years after the last unit", "P10Y") == "P10Y"
    assert kept("every 6 months", "P6M") == "P6M" and kept("daily visual check", "P1D") == "P1D"
    assert kept("at least once a year", "P2Y") is None and kept("as often as needed", "P1Y") is None


def test_a_reply_whose_reasoning_breaks_the_json_is_still_read(monkeypatch):
    reply = '{"reasoning": "the check is "in many cases" daily, so not it", "kind": "date", "value": "2027-01-20", "text": "t", "used": [0]}'
    a, _ = _ask(reply, monkeypatch)
    assert a.value == "2027-01-20" and a.steps[0].statement_id == "st-0002"
    assert agent._reply("no json here") == {} and agent._reply('{"kind": "x", "value": "broken "quote"" }') == {}
