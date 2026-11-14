"""Strategy A keeps every fact the model writes, and only counts what B's checks would refuse. No network."""
from atlas.contracts import Chunk
from atlas.strategies import a

TEXT = "The manufacturer shall keep the technical documentation for 10 years, unless the machine is withdrawn."
CHUNK = Chunk(id="X:Art.1", source="X", locator="Art. 1", text=TEXT, layer="law")


def test_free_facts_are_kept_and_checks_only_counted(monkeypatch, tmp_path):
    reply = ("manufacturer | keepsDocumentation | 10 years | | the manufacturer shall keep the technical documentation\n"
             "manufacturer | mustNotify | the authority | | words that are not in the text\n"
             "a line that does not fit\n")
    monkeypatch.setattr(a.llm, "chat", lambda *args, **kw: {"text": reply, "usage": {"prompt_tokens": 5}})
    monkeypatch.setattr(a, "chunks_read_by_b", lambda chunks: chunks)
    monkeypatch.setattr(a, "OUT", tmp_path)
    store, counts = a.build([CHUNK], workers=1)
    assert len(store.statements) == 2 and all(s.status == "current" for s in store.statements)
    assert counts["kept"] == 2 and counts["would_pass_b_checks"] == 0 and counts["would_be_rejected"] == 2
    assert counts["calls"] == 1 and counts["predicates"] == 2
