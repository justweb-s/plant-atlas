"""Owner: Core. The second reader, without the network: atlas.llm.chat is replaced by a fixed answer."""
import json
from types import SimpleNamespace

import pytest

from atlas import llm
from atlas.ontology import verify
from atlas.ontology.statements import ChunkCorpus, Statement, Store

TEXT = ("Guards shall be fixed. Machinery shall be accompanied by instructions for use. "
        "This does not apply where the machinery is intended for professional users only. Final sentence.")
QUOTE = "Machinery shall be accompanied by instructions for use."


def make_store(n: int = 3) -> Store:
    chunk = SimpleNamespace(source="REG", locator="Art. 10(7)", text=TEXT, version="v1")
    store = Store(ChunkCorpus([chunk]))
    for i in range(n):
        written = store.write_statement(Statement(
            subject=f"machinery {i}", predicate="mustAccompany", object="instructions for use",
            object_as_written="instructions for use", quote=QUOTE, source_doc="REG", anchor="Art. 10(7)",
            asserted_by="strategy_b"))
        written.status = "current"
    return store


def answer(monkeypatch, label: str, seen: list | None = None) -> None:
    def fake(messages, model=None, **params):
        if seen is not None:
            seen.append((messages, model))
        return {"text": json.dumps({"label": label, "confidence": 0.9, "why": "test"}), "model": "fake", "usage": None}
    monkeypatch.setattr(llm, "chat", fake)


def test_context_has_the_sentence_before_and_after():
    fact = make_store(1).statements[0]
    context = verify.context_of(fact, TEXT)
    assert QUOTE in context
    assert "Guards shall be fixed." in context
    assert "This does not apply where the machinery is intended for professional users only." in context
    assert "Final sentence." not in context


def test_context_at_the_start_of_a_chunk_and_off_sentence_borders():
    fact = make_store(1).statements[0]
    fact.quote = "Guards shall be fixed."
    assert verify.context_of(fact, TEXT).startswith("Guards shall be fixed. Machinery shall")
    fact.quote = "accompanied by instructions"
    context = verify.context_of(fact, TEXT)
    assert "accompanied by instructions" in context and "Machinery shall be" in context


def test_the_reader_sees_the_neighbours_and_is_not_told_who_proposed_the_fact(monkeypatch):
    seen: list = []
    answer(monkeypatch, verify.STATED, seen)
    verify.verify(make_store(1).statements[0], TEXT)
    prompt = " ".join(m["content"] for m in seen[0][0])
    assert "professional users only" in prompt and "Guards shall be fixed." in prompt
    for word in ("strategy_b", "extract", "proposed by", "model", "probably"):
        assert word not in prompt.lower()


@pytest.mark.parametrize("label,states,dropped", [
    (verify.STATED, "yes", "no"), (verify.DROPPED, "yes", "yes"),
    (verify.NOT_STATED, "no", "no"), (verify.UNCLEAR, "unclear", "no")])
def test_verdict_shape(monkeypatch, label, states, dropped):
    answer(monkeypatch, label)
    verdict = verify.verify(make_store(1).statements[0], TEXT)
    assert (verdict["states"], verdict["dropped_condition"]) == (states, dropped)
    assert 0.0 <= verdict["confidence"] <= 1.0


def test_an_answer_that_cannot_be_read_is_never_a_pass(monkeypatch):
    monkeypatch.setattr(llm, "chat", lambda messages, model=None, **p: {"text": "I think so", "usage": None})
    assert verify.decide("q", verify.LABELS, "t") == (verify.UNCLEAR, 0.0)
    assert not verify.passes(verify.verify(make_store(1).statements[0], TEXT))


def test_no_and_dropped_condition_go_back_to_proposed_yes_stays_current_nothing_is_deleted(monkeypatch):
    store = make_store(4)
    kept, not_stated, dropped, unchecked = store.statements
    verdicts = {}
    for fact, label in ((kept, verify.STATED), (not_stated, verify.NOT_STATED), (dropped, verify.DROPPED)):
        answer(monkeypatch, label)
        verdicts[fact.id] = verify.verify(fact, TEXT)
    counts = verify.apply_verdicts(store, verdicts)
    assert kept.status == "current"
    assert not_stated.status == "proposed" and dropped.status == "proposed"
    assert unchecked.status == "current"
    assert len(store.statements) == 4
    assert counts == {"checked": 3, "passed": 1, "not_stated": 1, "unclear": 0, "dropped_condition": 1,
                      "sent_back": 2, "unchecked": 1}


def test_a_verdict_given_for_another_wording_is_not_applied(monkeypatch):
    store = make_store(1)
    fact = store.statements[0]
    answer(monkeypatch, verify.NOT_STATED)
    verdicts = {fact.id: verify.verify(fact, TEXT)}
    fact.subject = "another subject"
    assert verify.apply_verdicts(store, verdicts)["unchecked"] == 1
    assert fact.status == "current"
