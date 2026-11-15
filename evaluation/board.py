"""The board: RAG, strategy A and strategy B on the same questions. Owner: Product.

Each mode's answers live in results/<mode>.json (rows + summary), written by
    python -m evaluation.rag          (RAG)
    python -m evaluation.board run B  (strategy B through api.answer; A the same once it exists)
Then
    python -m evaluation.board        -> results/board.json and results/board.md
A mode with no results file is shown as "not run", never as zero.

Rules of the board: design and held-out questions are kept apart (the held-out mean is the honest one);
"I don't know" (value None) is counted apart from "wrong"; on a question whose gold is "unknown",
"I don't know" is the right answer.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from evaluation.score import load_cqs, run, summary

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
MODES = ("free", "rag", "A", "B")
LABELS = {"free": "Free search (model + folder)", "rag": "RAG", "A": "A (free extraction)", "B": "B (checked facts)"}


def run_mode(mode: str) -> dict:
    """Ask every question with strategy A or B and save results/<mode>.json."""
    from atlas import api
    cqs = load_cqs()
    done = [0]

    def ask(question: str):
        done[0] += 1
        print(f"{mode} {done[0]}/{len(cqs)}", file=sys.stderr, flush=True)   # progress, to see a stuck call
        return api.answer(question, mode)

    rows = run(ask, cqs)
    out = {"summary": summary(rows), "rows": rows}
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / f"{mode}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def _load(mode: str) -> dict | None:
    path = RESULTS / f"{mode}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def _cell(row: dict | None) -> str:
    if row is None:
        return "—"
    if row["score"] == 1.0:
        return "✓"
    if row.get("value") is None:
        return "?"
    return "✗" if row["score"] == 0 else f"{row['score']:.2f}"


def _split_line(rows: list[dict]) -> dict:
    s = summary(rows) if rows else {"n": 0, "correct": 0, "unknown": 0, "wrong": 0, "mean": 0.0}
    return {k: s[k] for k in ("n", "correct", "unknown", "wrong", "mean")}


def sources_read_by_b() -> set[str]:
    """The documents strategy B has extracted facts from (ontology/B/statements.json and parts/*.json, by Core)."""
    folder = ROOT / "ontology" / "B"
    read: set[str] = set()
    for path in [folder / "statements.json", *sorted((folder / "parts").glob("*.json"))]:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            facts = data if isinstance(data, list) else data.get("statements", [])
            read |= {s.get("source_doc") for s in facts if isinstance(s, dict)}
    return read


def covered(cq: dict, read: set[str]) -> bool:
    """Every document the gold cites for this question has been read by B."""
    sources = {e.get("source") for e in cq.get("evidence", [])}
    return bool(sources) and sources <= read


def board() -> dict:
    cqs = load_cqs()
    read = sources_read_by_b()
    covered_ids = {c["id"] for c in cqs if covered(c, read)}
    loaded = {m: _load(m) for m in MODES}
    by_mode = {m: {r["id"]: r for r in d["rows"]} for m, d in loaded.items() if d}
    known = {c["id"] for c in cqs}
    totals = {}
    for m, rows in by_mode.items():
        rows = [r for r in rows.values() if r["id"] in known]   # a stale results file may lack new questions
        totals[m] = {"design": _split_line([r for r in rows if r["split"] == "design"]),
                     "heldout": _split_line([r for r in rows if r["split"] == "heldout"]),
                     "covered_by_b": _split_line([r for r in rows if r["id"] in covered_ids]),
                     "answered": len(rows), "of": len(cqs)}
    questions = [{"id": c["id"], "split": c.get("split", "design"), "type": c["type"],
                  "question": c["question_en"], "covered_by_b": c["id"] in covered_ids,
                  **{m: (by_mode[m].get(c["id"]) or {}).get("score") if m in by_mode else None for m in MODES}}
                 for c in cqs]
    return {"modes": [m for m in MODES if m in by_mode], "not_run": [m for m in MODES if m not in by_mode],
            "b_read": sorted(read),
            "totals": totals, "questions": questions, "_rows": by_mode}


def markdown(b: dict) -> str:
    out = ["# Tabellone ricerca libera / RAG / A / B", "",
           "Generato da `python -m evaluation.board` su `data/cq/cqs.json`. ✓ giusta · ✗ sbagliata · "
           "? «non lo so» · un numero = giusta in parte · — non lanciata.", ""]
    sections = (("design", "Domande di progetto"), ("heldout", "Domande tenute da parte (quelle oneste)"),
                ("covered_by_b", "Solo le domande sui documenti che B ha già letto ("
                 + ", ".join(f"`{s}`" for s in b["b_read"]) + "), progetto e tenute insieme"))
    for split, title in sections:
        out += [f"## {title}", "", "| | Giuste | «Non lo so» | Sbagliate | Media |", "|---|---|---|---|---|"]
        for m in MODES:
            if m in b["totals"]:
                t = b["totals"][m][split]
                out.append(f"| {LABELS[m]} | {t['correct']}/{t['n']} | {t['unknown']} | {t['wrong']} | {t['mean']:.2f} |")
            else:
                out.append(f"| {LABELS[m]} | non lanciata | | | |")
        out.append("")
    out += ["## Domanda per domanda", "", "| CQ | Parte | B ha letto i documenti? | "
            + " | ".join(LABELS[m] for m in MODES) + " |", "|---|---|---|" + "---|" * len(MODES)]
    for q in b["questions"]:
        cells = [_cell(b["_rows"][m].get(q["id"])) if m in b["_rows"] else "—" for m in MODES]
        out.append(f"| {q['id']} | {'tenuta' if q['split'] == 'heldout' else 'progetto'} | "
                   f"{'sì' if q['covered_by_b'] else 'no'} | " + " | ".join(cells) + " |")
    stale = [m for m, t in b["totals"].items() if t["answered"] < t["of"]]
    if stale:
        out += ["", f"Attenzione: {', '.join(LABELS[m] for m in stale)} non ha risposto a tutte le domande attuali: va rilanciata."]
    return "\n".join(out) + "\n"


def main(argv: list[str]) -> None:
    if argv[:1] == ["run"]:
        for mode in argv[1:]:
            print(mode, json.dumps(run_mode(mode)["summary"]))
    b = board()
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "board.json").write_text(json.dumps({k: v for k, v in b.items() if k != "_rows"},
                                                   ensure_ascii=False, indent=1), encoding="utf-8")
    (RESULTS / "board.md").write_text(markdown(b), encoding="utf-8")
    sys.stdout.buffer.write(markdown(b).encode("utf-8"))   # ✓ ✗ on a Windows console


if __name__ == "__main__":
    main(sys.argv[1:])
