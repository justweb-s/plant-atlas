"""Runs in fake mode from the start; the five real test questions go in tests/test_questions.py."""
import os

os.environ.setdefault("ATLAS_FAKE", "1")

from atlas import api  # noqa: E402


def test_answer_has_cited_steps():
    a = api.answer("Can a line operator run press P-3 today?")
    assert a.label in {"allowed", "blocked", "unknown"}
    assert a.steps and all(s.source is not None and s.quote for s in a.steps)


def test_cards_have_valid_colors():
    assert all(c.color in {"green", "orange", "grey", "red"} for c in api.atlas_cards())


def test_chain_verifies():
    assert api.verify_chain()
