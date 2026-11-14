"""The scorer gives full marks to the gold and zero to the known traps."""
from evaluation.score import load_cqs, score, summary

CQS = {cq["id"]: cq for cq in load_cqs()}


def test_gold_scores_full_marks():
    for cq in CQS.values():
        assert score(cq, cq["answer"]["value"]) == 1.0, cq["id"]


def test_no_answer_scores_zero():
    assert all(score(cq, None) == 0.0 for cq in CQS.values())


def test_traps_score_below_full():
    assert score(CQS["CQ09"], "2027-01-14") == 0.0      # the date before the corrigendum
    assert score(CQS["CQ10"], False) == 0.0             # "repealed from 14 January" -> wrong "no"
    assert score(CQS["CQ13"], ["C-4"]) < 1.0            # P-3 missed: the 90-day procedure trap


def test_summary_counts():
    rows = [{"id": "x", "type": "T", "score": 1.0, "cost_usd": 0.0},
            {"id": "y", "type": "V", "score": 0.0, "cost_usd": 0.0}]
    s = summary(rows)
    assert (s["n"], s["correct"], s["by_type"]) == (2, 1, {"T": 1.0, "V": 0.0})
