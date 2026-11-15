"""The development board: the three ways to answer on the questions of data/cq/dev/. Owner: Product (written by Core).

    python -m evaluation.dev run B rag free   -> results/dev/<mode>.json
    python -m evaluation.dev                  -> results/dev/board.md

The development questions were written from the documents alone, after the system was built, to see how it
does on questions it was not tuned on. Unlike the kept-aside questions of data/cq/cqs.json they may be read:
errors found here are what the system is improved on.
"""
from __future__ import annotations

import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from evaluation.score import score, summary

ROOT = Path(__file__).resolve().parents[1]
# ATLAS_QSET=blind: the same board on data/cq/blind/, a test set nobody tunes on. Only its totals are printed
# and written to the board; the rows stay in results/blind/<mode>.json and are not meant to be read.
QSET = os.getenv("ATLAS_QSET", "dev")
OUT = ROOT / "results" / QSET
MODES = ("free", "rag", "B")
LABELS = {"free": "Free search (model + folder of documents)", "rag": "RAG (passages by similarity)",
          "B": "Plant Atlas (fact store, reading on demand, judge)"}
SKIP = {"DEV-IGEA-05", "DEV-VER-14", "DEV-CELL-11"}   # two defensible answers: not scored


def load() -> list[dict]:
    return [c for p in sorted((ROOT / "data/cq" / QSET).glob("*.json"))
            for c in json.loads(p.read_text(encoding="utf-8"))["cqs"] if c["id"] not in SKIP]


def run_mode(mode: str) -> dict:
    if mode == "B":
        from atlas import api
        fn = lambda q: api.answer(q, "B")
    elif mode == "rag":
        from evaluation import rag
        fn = rag.answer
    else:
        from evaluation import free
        fn = free.answer
    cqs = load()

    def one(cq: dict) -> dict:
        try:
            a = fn(cq["question_en"])
            value, text, basis = a.value, a.text, getattr(a, "basis", "")
        except Exception as problem:   # a failed call is shown as such, never as a wrong answer
            value, text, basis = None, f"ERROR {type(problem).__name__}: {str(problem)[:200]}", "error"
        return {"id": cq["id"], "group": cq["id"].rsplit("-", 1)[0], "type": cq["type"], "split": "dev",
                "kind": cq["answer"]["kind"], "score": score(cq, value), "value": value, "text": text,
                "basis": basis, "cost_usd": 0.0}

    fn(cqs[0]["question_en"])   # the first call alone: it builds what the others share
    with ThreadPoolExecutor(int(os.getenv("ATLAS_DEV_PARALLEL", "5"))) as pool:
        rows = list(pool.map(one, cqs))
    out = {"summary": summary(rows), "errors": sum(r["basis"] == "error" for r in rows), "rows": rows}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{mode}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def markdown() -> str:
    loaded = {m: json.loads((OUT / f"{m}.json").read_text(encoding="utf-8")) for m in MODES if (OUT / f"{m}.json").exists()}
    cqs = load()
    out = ["# Development board: free search / RAG / Plant Atlas", "",
           f"{len(cqs)} questions of `data/cq/dev/`, written from the documents alone. ✓ right · ✗ wrong · "
           "? \"I don't know\" · a number = partly right.", "",
           "| | Right | \"I don't know\" | Wrong | Mean |", "|---|---|---|---|---|"]
    for m, d in loaded.items():
        s = d["summary"]
        out.append(f"| {LABELS[m]} | {s['correct']}/{s['n']} | {s['unknown']} | {s['wrong']} | {s['mean']:.2f} |")
    groups = sorted({c["id"].rsplit("-", 1)[0] for c in cqs})
    out += ["", "## By group of questions (right / total)", "", "| | " + " | ".join(groups) + " |", "|---|" + "---|" * len(groups)]
    for m, d in loaded.items():
        cells = []
        for g in groups:
            rows = [r for r in d["rows"] if r["group"] == g]
            cells.append(f"{sum(r['score'] == 1.0 for r in rows)}/{len(rows)}")
        out.append(f"| {LABELS[m]} | " + " | ".join(cells) + " |")
    if QSET == "blind":
        return "\n".join(out).replace("# Development board", "# Blind test board").replace(
            "`data/cq/dev/`", "`data/cq/blind/` (never used to change the system)") + "\n"
    out += ["", "## Question by question", "", "| Question | Expected | " + " | ".join(LABELS[m].split(" (")[0] for m in loaded) + " |",
            "|---|---|" + "---|" * len(loaded)]
    by = {m: {r["id"]: r for r in d["rows"]} for m, d in loaded.items()}

    def cell(r: dict | None) -> str:
        if r is None:
            return "—"
        return "✓" if r["score"] == 1.0 else "?" if r["value"] is None else "✗" if r["score"] == 0 else f"{r['score']:.2f}"

    for c in cqs:
        out.append(f"| {c['id']}: {c['question_en'][:110]} | {json.dumps(c['answer']['value'], ensure_ascii=False)[:40]} | "
                   + " | ".join(cell(by[m].get(c["id"])) for m in loaded) + " |")
    return "\n".join(out) + "\n"


def main(argv: list[str]) -> None:
    if argv[:1] == ["run"]:
        for mode in argv[1:]:
            done = run_mode(mode)
            print(mode, json.dumps({k: done["summary"][k] for k in ("n", "correct", "unknown", "wrong", "mean")}),
                  "errors", done["errors"], flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "board.md").write_text(markdown(), encoding="utf-8")
    sys.stdout.buffer.write("\n".join(markdown().splitlines()[:16]).encode("utf-8") + b"\n")


if __name__ == "__main__":
    main(sys.argv[1:])
