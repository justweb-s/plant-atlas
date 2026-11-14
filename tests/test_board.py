"""The board keeps the splits apart, counts "I don't know" apart and never shows a mode not run as zero."""
import json

import evaluation.board as board
from evaluation.score import load_cqs


def test_board_from_results_files(tmp_path, monkeypatch):
    cqs = load_cqs()
    rows = [{"id": c["id"], "type": c["type"], "split": c.get("split", "design"),
             "score": 1.0 if i == 0 else 0.0, "value": "x" if i < 2 else None, "cost_usd": 0.0}
            for i, c in enumerate(cqs)]
    (tmp_path / "rag.json").write_text(json.dumps({"rows": rows}), encoding="utf-8")
    monkeypatch.setattr(board, "RESULTS", tmp_path)
    b = board.board()
    assert b["modes"] == ["rag"] and b["not_run"] == ["A", "B"]
    t = b["totals"]["rag"]
    assert t["design"]["n"] + t["heldout"]["n"] == len(cqs)
    assert t["design"]["correct"] == 1 and t["design"]["wrong"] == 1
    md = board.markdown(b)
    assert "non lanciata" in md and "| CQ01 |" in md


def test_coverage_needs_every_cited_document():
    cq = {"evidence": [{"source": "REG"}, {"source": "CORR"}]}
    assert board.covered(cq, {"REG", "CORR", "DIR"})
    assert not board.covered(cq, {"REG"})
    assert not board.covered({"evidence": []}, {"REG"})
