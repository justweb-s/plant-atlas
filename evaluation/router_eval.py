"""Measures the router. Owner: Product (written by Core).

    python -m evaluation.router_eval collect   -> results/readers/<reader>.json : every reader alone on the
                                                  questions that may be read (design + development)
    python -m evaluation.router_eval           -> the table (ontology/B/router.json) and the comparison:
                                                  each reader alone, the fixed order, the router

The router is scored leaving each question out of the table it is routed with, so it never sees its own answer.
"""
from __future__ import annotations

import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

from atlas.contracts import Answer, Step
from evaluation.score import score

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "readers"
NAMES = ("facts", "words", "similar", "search")


def questions() -> list[dict]:
    cqs = [c for c in json.loads((ROOT / "data/cq/cqs.json").read_text(encoding="utf-8"))["cqs"] if c.get("split", "design") == "design"]
    from evaluation import dev
    return cqs + dev.load()


def collect(names: list[str]) -> None:
    from atlas.agent import readers
    from atlas.ontology.build import store_for

    readers.load_plugins()
    store, day, cqs = store_for("B"), date.fromisoformat(os.environ["ATLAS_TODAY"]), questions()
    OUT.mkdir(parents=True, exist_ok=True)
    for name in names:
        def one(cq: dict) -> dict:
            try:
                a = readers.READERS[name](cq["question_en"], store, day)
            except Exception as problem:
                a = Answer(question=cq["question_en"], mode="B", value=None, text=f"ERROR {type(problem).__name__}: {str(problem)[:160]}", basis="error")
            return {"id": cq["id"], "question": cq["question_en"], "reader": name, "value": a.value, "text": a.text,
                    "basis": a.basis, "answered": a.value is not None, "score": score(cq, a.value),
                    "right": score(cq, a.value) == 1.0, "tokens": a.tokens,
                    "steps": [{"text": s.text, "quote": s.quote, "locator": s.locator} for s in a.steps[:12]]}
        one(cqs[0])
        with ThreadPoolExecutor(int(os.getenv("ATLAS_DEV_PARALLEL", "5"))) as pool:
            rows = list(pool.map(one, cqs))
        (OUT / f"{name}.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
        print(name, "right", sum(r["right"] for r in rows), "answered", sum(r["answered"] for r in rows),
              "wrong", sum(r["answered"] and not r["right"] for r in rows), "of", len(rows),
              "errors", sum(r["basis"] == "error" for r in rows), flush=True)


def _answer(row: dict) -> Answer:
    return Answer(question=row["question"], mode="B", value=row["value"], text=row["text"], basis=row["basis"],
                  steps=[Step(text=s["text"], quote=s["quote"], locator=s["locator"]) for s in row["steps"]])


def compare() -> None:
    from atlas.agent import answer as base, router
    from atlas.agent.readers import COST

    rows = {n: {r["id"]: r for r in json.loads((OUT / f"{n}.json").read_text(encoding="utf-8"))} for n in NAMES if (OUT / f"{n}.json").exists()}
    names, cqs = list(rows), questions()
    outcomes = [r for n in names for r in rows[n].values()]
    day = date.fromisoformat(os.environ.get("ATLAS_TODAY", "2026-11-14"))

    def run(cq: dict, table: dict, fixed: list[str] | None = None) -> tuple[float, bool, float, list[dict]]:
        calls = [0.0]

        def ask(name: str) -> Answer:
            calls[0] += COST.get(name, 1)
            return _answer(rows[name][cq["id"]])

        chosen, trace = router.route(cq["question_en"], ask, names, table, same=base._same_value, ranked=fixed,
                                     judge=lambda a, b: base._judge(cq["question_en"], day, a, b))
        value = chosen.value if chosen else None
        return score(cq, value), value is not None, calls[0], trace

    def line(label: str, results: list[tuple]) -> None:
        n = len(results)
        print(f"{label:38} right {sum(s == 1.0 for s, *_ in results):3}/{n}  \"I don't know\" {sum(s < 1 and not a for s, a, *_ in results):3}  "
              f"wrong {sum(s < 1 and a for s, a, *_ in results):3}  calls per question {sum(c for *_, c, _ in results) / n:.1f}")

    for n in names:
        line(f"{n} alone", [(rows[n][c["id"]]["score"], rows[n][c["id"]]["answered"], COST.get(n, 1), []) for c in cqs])
    with ThreadPoolExecutor(6) as pool:
        line("fixed order facts > words > search", list(pool.map(lambda c: run(c, router.learn(outcomes), ["facts", "words", "search"]), cqs)))
        routed = list(pool.map(lambda c: run(c, router.learn([o for o in outcomes if o["id"] != c["id"]])), cqs))
    line("router (each question left out)", routed)
    first = {}
    for *_, trace in routed:
        if trace:
            first[trace[0]["reader"]] = first.get(trace[0]["reader"], 0) + 1
    print("first reader chosen by the router:", first)
    table = router.learn(outcomes)
    router.TABLE.write_text(json.dumps(table, ensure_ascii=False, indent=1), encoding="utf-8")
    print("table written:", router.TABLE.relative_to(ROOT), "from", table["n"], "outcomes")
    for key in sorted(k for k in table["levels"] if k.endswith("|*")):
        print("  ", f"{key:14}", {r: f"{c['right']}/{c['n']} right, {c['right_answered']}/{c['answered']} when answering" for r, c in table["levels"][key].items()})


if __name__ == "__main__":
    collect(sys.argv[2:] or list(NAMES)) if sys.argv[1:2] == ["collect"] else compare()
