"""The rules learned from the second reader's failures: one planted bad case and one good case per rule
(the good case must come back untouched), and apply() then revert() on a tiny store. No network, no model."""
import json
from types import SimpleNamespace

from atlas.ontology.statements import ChunkCorpus, Statement, Store
from atlas.strategies import learned_rules as rules

DEFINITION = ("(5) ‘lifting accessory’ means a component or equipment, not attached to the lifting machinery, "
              "which enables the load to be held; (6) ‘chains’ means chains designed for lifting purposes;")
LIST = ("1. A notified body shall inform the notifying authority of the following: (a) any refusal, restriction, "
        "suspension or withdrawal of a certificate; (b) any circumstances affecting the scope of, or the conditions "
        "for, its notification.")
DUTY = ("4. Distributors shall ensure that, while a product is under their responsibility, the storage conditions "
        "do not jeopardise its conformity. Furthermore, where the product presents a risk to the health of persons "
        "and, where appropriate, domestic animals, the importer shall inform the manufacturer to that effect.")
KEEP = ("2. Economic operators shall retain the information for at least 10 years after they supplied the products. "
        "The body shall keep the file for a period of five years.")
ANNEX = "3. Thicknessers for one-side dressing having a built-in mechanical feed device for woodworking."
FORCE = ("Article 28 Entry into force This Directive shall enter into force on the 20th day following its "
         "publication. It shall apply from 29 December 2009.")
CONTENTS = ("Contents of the instructions Each instruction manual must contain the following information. "
            "All machinery must be accompanied by instructions in the official language.")


def fact(predicate, value, quote, condition="", subject="s", anchor="a", **more):
    return Statement(id="st-0001", subject=subject, predicate=predicate, object=value, object_as_written=value,
                     condition=condition, quote=quote, source_doc="REG", anchor=anchor, asserted_by="strategy_b",
                     status="current", **more)


def test_definition_is_lengthened_to_the_end_of_its_sentence():
    quote = DEFINITION.split("; (6)")[0] + ";"
    bad = fact("definedAs", "a component or equipment, not attached to the lifting machinery", quote)
    fixed = rules.fix_definition_whole(bad, DEFINITION)
    assert fixed.object_as_written == ("a component or equipment, not attached to the lifting machinery, "
                                       "which enables the load to be held")
    assert (fixed.subject, fixed.predicate) == (bad.subject, bad.predicate)
    good = fact("definedAs", "chains designed for lifting purposes", "(6) ‘chains’ means chains designed for lifting purposes;")
    assert rules.fix_definition_whole(good, DEFINITION) is None
    assert rules.fix_definition_whole(fact("hasObligation", "a component", quote), DEFINITION) is None


def test_definition_that_is_a_list_takes_the_list_from_the_chunk():
    chunk = "(18) ‘manufacturer’ means any person who: (a) makes products; or (b) puts products into service;"
    bad = fact("definedAs", "any person who", "(18) ‘manufacturer’ means any person who:")
    fixed = rules.fix_definition_whole(bad, chunk)
    assert fixed.object_as_written == "any person who: (a) makes products; or (b) puts products into service"
    assert fixed.quote == chunk


def test_obligation_that_stops_on_a_connective_is_lengthened():
    quote = DUTY.split(" Furthermore")[0][3:]
    bad = fact("hasObligation", "Distributors shall ensure that", quote, condition="while a product is under their responsibility")
    fixed = rules.fix_obligation_whole(bad, DUTY)
    assert fixed.object_as_written.endswith("the storage conditions do not jeopardise its conformity")
    good = fact("hasObligation", "the storage conditions do not jeopardise its conformity", quote,
                condition="while a product is under their responsibility")
    assert rules.fix_obligation_whole(good, DUTY) is None
    cut_but_meaningful = fact("hasObligation", "shall inform the manufacturer", DUTY.split(". ")[2])
    assert rules.fix_obligation_whole(cut_but_meaningful, DUTY) is None       # the narrow rule leaves it
    assert rules.fix_obligation_whole_wide(cut_but_meaningful, DUTY) is not None


def test_condition_cut_at_its_first_comma_is_made_whole():
    quote = DUTY.split(". ", 1)[1]
    bad = fact("hasObligation", "shall inform the manufacturer to that effect", quote,
               condition="where the product presents a risk to the health of persons")
    fixed = rules.fix_condition_whole(bad, DUTY)
    assert fixed.condition == ("where the product presents a risk to the health of persons and, where appropriate, "
                               "domestic animals")
    assert fixed.object_as_written == bad.object_as_written
    good = bad.model_copy(update={"condition": fixed.condition})
    assert rules.fix_condition_whole(good, DUTY) is None
    other = bad.model_copy(update={"condition": "only in winter"})
    assert rules.fix_condition_whole(other, DUTY) is None


def test_condition_between_the_verb_and_the_duty_is_found():
    quote = "Importers shall, for at least 10 years after the product has been placed on the market, keep a copy of the declaration."
    fixed = rules.fix_condition_whole(fact("hasObligation", "keep a copy of the declaration", quote), quote)
    assert fixed.condition == "for at least 10 years after the product has been placed on the market"


def test_period_gets_its_floor_and_its_starting_point():
    first = KEEP.split(". The")[0][3:] + "."
    bad = fact("retentionPeriod", "10 years", first)
    fixed = rules.fix_period_floor_and_start(bad, KEEP)
    assert fixed.object_as_written == "at least 10 years"
    assert fixed.condition == "after they supplied the products"
    good = fact("retentionPeriod", "for a period of five years", "The body shall keep the file for a period of five years.")
    assert rules.fix_period_floor_and_start(good, KEEP) is None
    whole = fact("retentionPeriod", "at least 10 years", first, condition="after they supplied the products")
    assert rules.fix_period_floor_and_start(whole, KEEP) is None


def test_period_keeps_the_floor_that_follows_the_lifetime():
    quote = ("Digital declarations shall be made accessible online for the expected lifetime of the machinery and in any "
             "event for at least 10 years after the placing on the market of the machinery.")
    fixed = rules.fix_period_floor_and_start(fact("retentionPeriod", "for the expected lifetime of the machinery", quote), quote)
    assert fixed.object_as_written == "for the expected lifetime of the machinery and in any event for at least 10 years"
    assert fixed.condition == "after the placing on the market of the machinery"


def test_list_item_gets_its_opening_sentence_and_its_whole_text():
    bad = fact("hasObligation", "any circumstances affecting the scope of",
               "(b) any circumstances affecting the scope of, or the conditions for, its notification.")
    fixed = rules.fix_list_item(bad, LIST)
    assert fixed.object_as_written == "any circumstances affecting the scope of, or the conditions for, its notification"
    assert fixed.condition == "A notified body shall inform the notifying authority of the following"
    assert fixed.condition_quote == "A notified body shall inform the notifying authority of the following:"
    good = fixed.model_copy()
    assert rules.fix_list_item(good, LIST) is None
    no_list = fact("hasObligation", "shall keep the file", "The body shall keep the file for a period of five years.")
    assert rules.fix_list_item(no_list, KEEP) is None


def test_listed_entry_is_made_whole_only_when_a_word_is_lost():
    bad = fact("listedIn", "3.", ANNEX, condition="having a built-in mechanical feed device",
               subject="thicknessers for one-side dressing")
    fixed = rules.fix_listed_item_whole(bad, ANNEX)
    assert fixed.object_as_written == ("Thicknessers for one-side dressing having a built-in mechanical feed device "
                                       "for woodworking")
    good = bad.model_copy(update={"condition": "having a built-in mechanical feed device for woodworking"})
    assert rules.fix_listed_item_whole(good, ANNEX) is None
    assert rules.check_empty_value(good, ANNEX) is None       # the number of the point is a value for listedIn


def test_entry_into_force_is_not_a_date_of_application():
    bad = fact("appliesFrom", "20th day following its publication", FORCE.split(". ")[0] + ".")
    assert rules.check_entry_into_force(bad, FORCE)
    good = fact("appliesFrom", "29 December 2009", "It shall apply from 29 December 2009.")
    assert rules.check_entry_into_force(good, FORCE) is None
    both = fact("appliesFrom", "29 December 2009", FORCE)
    assert rules.check_entry_into_force(both, FORCE) is None


def test_contents_of_the_instructions_are_not_an_accompanying_document():
    bad = fact("mustAccompany", "instruction manual", CONTENTS.split(". ")[0] + ".")
    assert rules.check_accompany_not_stated(bad, CONTENTS)
    good = fact("mustAccompany", "instructions", "All machinery must be accompanied by instructions in the official language.")
    assert rules.check_accompany_not_stated(good, CONTENTS) is None


def test_empty_value_is_flagged():
    assert rules.check_empty_value(fact("definedAs", "means:", "(1) ‘machinery’ means: (a) an assembly;"), "")
    assert rules.check_empty_value(fact("hasObligation", "shall ensure that", "They shall ensure that it is safe."), "")
    assert rules.check_empty_value(fact("requiresMeasure", "4.1.", "4.1. guards shall be fitted."), "")
    assert rules.check_empty_value(fact("mustAccompany", "the declaration set out in Annex V, Part A", "q"), "") is None
    assert rules.check_empty_value(fact("hasObligation", "shall keep the file", "q"), "") is None
    assert rules.check_empty_value(fact("capacityKg", "3200", "q"), "") is None


def test_refused_fact_with_a_condition_word_is_recovered():
    refused = fact("hasStoppingLimit", "250 mm/s", "The system issues a Stop Category 0 if a violation of these limits appears.").model_dump(mode="json")
    recovered = rules.recover_missing_condition(refused)
    assert recovered.condition == "if a violation of these limits appears"
    name = fact("hasDeclaration", "Declaration", "Declaration of Conformity ACME SE & Co.").model_dump(mode="json")
    assert rules.recover_missing_condition(name) is None


def _tiny_store():
    chunks = [SimpleNamespace(source="REG", locator="def", text=DEFINITION, version="1", layer="law"),
              SimpleNamespace(source="REG", locator="list", text=LIST, version="1", layer="law"),
              SimpleNamespace(source="REG", locator="force", text=FORCE, version="1", layer="law"),
              SimpleNamespace(source="REG", locator="keep", text=KEEP, version="1", layer="law")]
    store = Store(ChunkCorpus(chunks))
    cut = fact("definedAs", "a component or equipment, not attached to the lifting machinery",
               DEFINITION.split("; (6)")[0] + ";", anchor="def")
    whole = fact("definedAs", "chains designed for lifting purposes", "(6) ‘chains’ means chains designed for lifting purposes;",
                 anchor="def").model_copy(update={"id": "st-0002"})
    item = fact("hasObligation", "any circumstances affecting the scope of",
                "(b) any circumstances affecting the scope of, or the conditions for, its notification.",
                anchor="list").model_copy(update={"id": "st-0003"})
    force = fact("appliesFrom", "20th day following its publication", FORCE.split(". ")[0] + ".",
                 anchor="force").model_copy(update={"id": "st-0004"})
    by_code = fact("retentionPeriod", "10 years", KEEP.split(". The")[0][3:] + ".", anchor="keep").model_copy(
        update={"id": "st-0005", "asserted_by": "code:other"})
    store.statements = [cut, whole, item, force, by_code]
    return store


def test_propose_rebuilds_through_the_gate_and_leaves_good_facts_alone():
    store = _tiny_store()
    before = [s.model_dump() for s in store.statements]
    proposal = rules.propose(store)
    assert [s.model_dump() for s in store.statements] == before             # the store itself is not touched
    assert {s.conflicts_with for s in proposal["statements"]} == {"st-0001", "st-0003"}
    for new in proposal["statements"]:
        old = next(s for s in store.statements if s.id == new.conflicts_with)
        assert (new.subject, new.predicate) == (old.subject, old.predicate)
        assert new.asserted_by == "code:learned_rules" and new.status == "current"
        assert new.id.startswith("learned_rules-")
        assert Store(store.corpus).write_statement(new.model_copy(update={"id": ""})) is not None
    assert {c["id"] for c in proposal["close"]} == {"st-0001", "st-0003"}
    assert [(f["id"], f["rule"]) for f in proposal["flag_only"]] == [("st-0004", "check_entry_into_force")]
    assert "st-0002" not in {c["id"] for c in proposal["close"]}
    assert "st-0005" not in proposal["trace"]                               # written by code: not a candidate


def test_apply_then_revert_restores_the_store_exactly(tmp_path):
    store = _tiny_store()
    folder = tmp_path / "B"
    (folder / "parts").mkdir(parents=True)
    main = folder / "statements.json"
    main.write_text(json.dumps({"statements": [s.model_dump(mode="json") for s in store.statements[:3]],
                                "rejections": []}, indent=1, ensure_ascii=False), encoding="utf-8")
    other = folder / "parts" / "extra.json"                                 # another layout, ids without the prefix
    other.write_text(json.dumps({"statements": [store.statements[3].model_dump(mode="json")], "rejections": []},
                                indent=4, ensure_ascii=True), encoding="utf-8")
    proposal = rules.propose(store)
    proposal["close"].append({"id": "extra-st-0004", "file": "extra.json", "reason": "check_entry_into_force"})
    path = tmp_path / "round.json"
    rules.write_proposal(proposal, path)
    originals = {p: p.read_bytes() for p in (main, other)}

    done = rules.apply(path, folder)
    assert done == {"added": 2, "closed": 3, "files": ["extra.json", "statements.json"]}
    now = {item["id"]: item for item in json.loads(main.read_text(encoding="utf-8"))["statements"]}
    assert (now["st-0001"]["status"], now["st-0001"]["in_force_to"]) == ("closed", "2026-11-14")
    assert (now["st-0002"]["status"], now["st-0002"]["in_force_to"]) == ("current", None)
    assert now["st-0001"]["quote"] == store.statements[0].quote
    assert json.loads(other.read_text(encoding="utf-8"))["statements"][0]["status"] == "closed"
    part = json.loads((folder / "parts" / "learned_rules.json").read_text(encoding="utf-8"))
    assert len(part["statements"]) == 2 and part["rejections"] == []
    assert all(Statement(**item).conflicts_with for item in part["statements"])

    undone = rules.revert(path, folder)
    assert undone == {"reopened": 3, "removed": True}
    assert {p: p.read_bytes() for p in (main, other)} == originals
    assert not (folder / "parts" / "learned_rules.json").exists()
    assert rules.revert(path, folder) == {"reopened": 0, "removed": False}


def test_the_rules_call_no_model():
    source = open(rules.__file__, encoding="utf-8").read()
    body = source.split("def spot_check")[0]
    assert "atlas.llm" not in body and "llm." not in body and "verify.verify" not in body
