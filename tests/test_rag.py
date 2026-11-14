"""The RAG baseline, with the models replaced: no network (AGENTS.md §6)."""
from unittest import mock

from atlas import llm
from atlas.contracts import Chunk
import evaluation.rag as rag

CHUNKS = [Chunk("A", "REG", "Art. 1", "machinery scope"), Chunk("B", "DIR", "Art. 2", "lifts and hoists")]


def _embed(texts, model=None, **params):
    assert params.get("dimensions") == rag.DIMENSIONS
    return [[1.0, 0.0] if "lift" in t else [0.0, 1.0] for t in texts]


def _run(reply: str, monkeypatch):
    monkeypatch.setenv("ATLAS_FAKE", "0")
    rag._index.cache_clear()
    with mock.patch("atlas.api.corpus", return_value=CHUNKS), mock.patch.object(llm, "embed", _embed), \
            mock.patch.object(llm, "chat", lambda m, **p: {"text": reply, "usage": None}):
        out = rag.answer("which lift?")
    rag._index.cache_clear()
    return out


def test_answer_cites_the_passages_it_used(monkeypatch):
    a = _run('{"kind": "set", "value": ["SL-30"], "text": "t", "used": [0]}', monkeypatch)
    assert a.mode == "rag" and a.value == ["SL-30"]
    assert a.steps[0].locator == "DIR, Art. 2"        # the nearest passage comes first


def test_unknown_and_unsupported_answers_are_none(monkeypatch):
    assert _run('{"kind": "unknown", "value": null, "used": []}', monkeypatch).value is None
    assert _run('{"kind": "boolean", "value": true, "used": []}', monkeypatch).value is None   # no passage, no answer
    assert _run("not json", monkeypatch).value is None
