"""Does the fact store really learn? Owner: Product (written by Core).

    python -m evaluation.growth paraphrase   -> results/growth/paraphrases.json (each readable question reworded)
    python -m evaluation.growth store <tag>  -> the fact store ALONE (no search) on the questions and on their
                                                rewordings; run once with ATLAS_NO_LEARNED=1 (tag before) and
                                                once without (tag after)
    python -m evaluation.growth              -> results/growth/board.md

Three things are measured. Quality of what entered: from the learning log (how many candidates, how many
accepted, why the others were refused, how many a second attempt recovered). Retention: after learning, does
the store alone answer the questions it learned from? Transfer: does it answer the same questions asked in
other words, which it never saw? A store that only memorised strings passes the first and fails the second.
"""
from __future__ import annotations

import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

from evaluation.score import score

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "growth"
REWORD = """Reword the question so that it asks exactly the same thing in different words and a different sentence
structure. Keep every name, model, position number, article number, date and condition exactly. Do not add or
remove any detail. Return only the reworded question."""


def questions() -> list[dict]:
    from evaluation.router_eval import questions as readable
    return readable()


def paraphrase() -> None:
    from atlas import llm
    cqs = questions()

    def one(cq: dict) -> tuple[str, str]:
        out = llm.chat([{"role": "system", "content": REWORD}, {"role": "user", "content": cq["question_en"]}],
                       model="anthropic/claude-sonnet-5.5", temperature=0, max_tokens=300)
        return cq["id"], (out.get("text") or "").strip() or cq["question_en"]

    with ThreadPoolExecutor(6) as pool:
        done = dict(pool.map(one, cqs))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "paraphrases.json").write_text(json.dumps(done, ensure_ascii=False, indent=1), encoding="utf-8")
    print(len(done), "questions reworded")


def store_alone(tag: str) -> None:
    from atlas.agent.answer import from_facts
    from atlas.ontology.build import store_for

    store, day, cqs = store_for("B"), date.fromisoformat(os.environ["ATLAS_TODAY"]), questions()
    reworded = json.loads((OUT / "paraphrases.json").read_text(encoding="utf-8"))

    def one(cq: dict) -> dict:
        row = {"id": cq["id"]}
        for name, text in (("asked", cq["question_en"]), ("reworded", reworded[cq["id"]])):
            try:
                value = from_facts(text, store, day).value
            except Exception:
                value = None
            row[name] = {"value": value, "score": score(cq, value)}
        return row

    one(cqs[0])
    with ThreadPoolExecutor(6) as pool:
        rows = list(pool.map(one, cqs))
    (OUT / f"store-{tag}.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    for name in ("asked", "reworded"):
        print(tag, name, "right", sum(r[name]["score"] == 1.0 for r in rows), "wrong answer",
              sum(r[name]["score"] < 1 and r[name]["value"] is not None for r in rows), "of", len(rows))


def board() -> None:
    from atlas.ontology import learn

    q = learn.report()
    out = ["# Growth of the fact store", "", "## What entered, and how it was examined", "",
           f"- questions learned from: {q['questions']} ({q['questions_with_new_sentences']} brought sentences the store did not have)",
           f"- sentences examined: {q['sentences_examined']}",
           f"- accepted as new facts: {q['accepted']}; confirmations of facts already there: {q['confirmations']}; refused: {q['rejected']}",
           f"- refused on the first attempt: {q['first_attempts_rejected']}; recovered by the second attempt: {q['recovered_by_second_attempt']}",
           "- why the refused ones were refused: " + (", ".join(f"{k} {v}" for k, v in sorted(q["rejected_why"].items(), key=lambda kv: -kv[1])) or "—"), ""]
    runs = {tag: [json.loads(f.read_text(encoding="utf-8")) for f in sorted(OUT.glob(f"store-{tag}*.json"))] for tag in ("before", "after")}
    if all(runs.values()):
        n = len(runs["before"][0])
        out += [f"## The fact store alone, with no search ({len(runs['before'])} runs before, {len(runs['after'])} after: mean, lowest-highest)", "",
                "| | Right before | Right after | Wrong answers before | Wrong answers after |", "|---|---|---|---|---|"]

        def cell(tag: str, name: str, kind: str) -> str:
            counts = [sum((r[name]["score"] == 1.0) if kind == "right" else (r[name]["score"] < 1 and r[name]["value"] is not None)
                          for r in rows) for rows in runs[tag]]
            return f"{sum(counts) / len(counts):.1f} ({min(counts)}-{max(counts)})"

        for name, label in (("asked", "The questions it learned from (retention)"), ("reworded", "The same questions in other words (transfer)")):
            out.append(f"| {label}, of {n} | " + " | ".join(cell(tag, name, kind) for kind in ("right", "wrong") for tag in ("before", "after")) + " |")
        out.append("")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "board.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))


if __name__ == "__main__":
    args = sys.argv[1:]
    paraphrase() if args[:1] == ["paraphrase"] else store_alone(args[1]) if args[:1] == ["store"] else board()
