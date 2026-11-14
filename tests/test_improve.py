"""The improvement round, with no network: the model and the second reader are replaced by functions."""
import json

import pytest

from atlas.contracts import Chunk
from atlas.ontology import verify as second_reader
from atlas.ontology.statements import ChunkCorpus, Statement, Store
from atlas.strategies import improve

TEXT_A = "The manufacturer shall keep the file for ten years. This does not apply if the machine is a prototype."
TEXT_B = "The importer shall keep a copy for five years. This holds unless the authority asks otherwise."
CHUNKS = [Chunk("REG:Art.1", "REG", "Art. 1", TEXT_A, "v1", layer="law"),
          Chunk("REG:Art.2", "REG", "Art. 2", TEXT_B, "v1", layer="law")]


def _fact(anchor, text, subject, value):
    return Statement(subject=subject, predicate="retentionPeriod", object=value, object_as_written=value,
                     quote=text.split(". ")[0] + ".", source_doc="REG", anchor=anchor, asserted_by="strategy_b")


@pytest.fixture
def world(tmp_path, monkeypatch):
    store = Store(ChunkCorpus(CHUNKS), tmp_path / "statements.json")
    for fact in (_fact("Art. 1", TEXT_A, "manufacturer", "ten years"), _fact("Art. 2", TEXT_B, "importer", "five years")):
        store.write_statement(fact).status = "current"
    store._reject(_fact("Art. 2", TEXT_B, "importer", "six years"), "value_not_in_quote")
    store.save()
    (tmp_path / "parts").mkdir()
    verdicts = {s.id: {"states": "yes", "dropped_condition": "yes", "confidence": 0.8, "why": "the next sentence adds an exception",
                       "fingerprint": second_reader.fingerprint(s)} for s in store.statements}
    seen = {"lesson_calls": 0, "systems": []}

    def chat(messages, model=None, **params):
        system, user = messages[0]["content"], messages[1]["content"]
        if system == improve.LESSON_SYSTEM:
            seen["lesson_calls"] += 1
            return {"text": "When the next sentence starts with an exception, put it in the condition (Article 12).", "usage": {}}
        seen["systems"].append(system)
        if "Art. 1" in user:   # the exception is now kept
            return {"text": "retentionPeriod | manufacturer | ten years | P10Y | if the machine is a prototype | 0 | 1", "usage": {}}
        return {"text": "retentionPeriod | importer | five years | P5Y |  | 0 | 0", "usage": {}}   # still without it

    def verify(statement, chunk_text):
        ok = bool(statement.condition)
        return {"states": "yes", "dropped_condition": "no" if ok else "yes", "confidence": 0.9, "why": "",
                "fingerprint": second_reader.fingerprint(statement)}

    monkeypatch.setattr("atlas.llm.chat", chat)
    monkeypatch.setattr("atlas.ontology.verify.verify", verify)
    return tmp_path, verdicts, seen


def test_failures_are_grouped_into_lessons(world):
    folder, verdicts, seen = world
    passages = improve.collect(folder, improve.load_files(folder), verdicts)
    groups = improve.group_failures(passages)
    assert [(g["relation"], g["kind"], g["source"], len(g["examples"])) for g in groups] == [
        ("retentionPeriod", "dropped_condition", "second_reader", 2), ("retentionPeriod", "value_not_in_quote", "gate", 1)]
    improve.run_round(folder, CHUNKS, verdicts)
    lessons = json.loads((folder / "lessons.json").read_text(encoding="utf-8"))
    assert seen["lesson_calls"] == 2 and len(lessons) == 2
    assert lessons[0]["evidence"] == {"count": 2, "kind": "dropped_condition", "examples": ["st-0001", "st-0002"]}
    assert lessons[0]["source"] == "second_reader" and lessons[1]["source"] == "gate"
    assert "Article" not in lessons[0]["pattern"] and len(lessons[0]["pattern"].split()) <= 30
    assert all("Lessons from earlier checks:" in system for system in seen["systems"])


def test_a_passing_fact_closes_the_old_one_and_a_failing_one_changes_nothing(world):
    folder, verdicts, _ = world
    before = json.loads((folder / "statements.json").read_text(encoding="utf-8"))
    entry = improve.run_round(folder, CHUNKS, verdicts)
    after = json.loads((folder / "statements.json").read_text(encoding="utf-8"))
    assert len(after["statements"]) == len(before["statements"]) and after["rejections"] == before["rejections"]
    old_a, old_b = after["statements"]
    assert (old_a["status"], old_a["in_force_to"]) == ("closed", "2026-11-14")
    assert {k: v for k, v in old_a.items() if k not in ("status", "in_force_to")} == \
           {k: v for k, v in before["statements"][0].items() if k not in ("status", "in_force_to")}
    assert old_b == before["statements"][1]   # its re-reading did not pass: nothing changes
    new = json.loads((folder / "parts" / "reextracted.json").read_text(encoding="utf-8"))["statements"]
    assert len(new) == 1
    assert (new[0]["status"], new[0]["conflicts_with"], new[0]["asserted_by"]) == ("current", "st-0001", "strategy_b:round2")
    assert new[0]["condition"] == "if the machine is a prototype"
    assert (entry["replaced_by_passing_fact"], entry["still_failing"], entry["still_failing_ids"]) == (1, 1, ["st-0002"])


def test_the_log_gains_one_entry_per_round(world):
    folder, verdicts, _ = world
    assert improve.run_round(folder, CHUNKS, verdicts, dry=True)["dry"] and not (folder / "improve_log.json").exists()
    improve.run_round(folder, CHUNKS, verdicts)
    improve.run_round(folder, CHUNKS, verdicts)
    log = json.loads((folder / "improve_log.json").read_text(encoding="utf-8"))
    assert [e["round"] for e in log] == [2, 3]
    assert log[0]["old_failures"] == 2 and log[1]["old_failures"] == 1 and log[0]["passages_reextracted"] == 2
