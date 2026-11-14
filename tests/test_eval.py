"""The scorer gives full marks to the gold and less to the known traps."""
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
    assert score(CQS["CQ13"], ["RC-5"]) < 1.0           # the Directive's self-certification for lifts
    assert score(CQS["CQ17"], True) == 0.0              # same trap, held out


def test_summary_keeps_splits_apart():
    rows = [{"id": "x", "type": "T", "split": "design", "score": 1.0, "cost_usd": 0.0},
            {"id": "y", "type": "V", "split": "heldout", "score": 0.0, "cost_usd": 0.0}]
    s = summary(rows)
    assert (s["n"], s["correct"]) == (2, 1)
    assert s["by_type"] == {"T": 1.0, "V": 0.0}
    assert s["by_split"] == {"design": 1.0, "heldout": 0.0}
