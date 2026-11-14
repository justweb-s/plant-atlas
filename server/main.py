"""Owner: Product. The HTTP door between the Next.js app (web/) and the brain.

Imports only atlas.api, atlas.contracts and Product's own modules (AGENTS.md §4). The team key never leaves
this process: the browser talks to Next.js, Next.js talks to this server on localhost.

Run (from the repo root): PYTHONUTF8=1 python -m uvicorn server.main:app --port 8000
"""
from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from atlas import api
from evaluation import rag
from evaluation import score as ev

app = FastAPI(title="Plant Atlas")
CQS = ev.load_cqs()
BY_ID = {cq["id"]: cq for cq in CQS}


def _call(fn, *args):
    """A contract function, or a clear reason why it cannot answer yet."""
    try:
        return fn(*args), None
    except (NotImplementedError, FileNotFoundError) as e:
        return None, {"state": "not_built", "detail": str(e)}
    except RuntimeError as e:  # ATLAS_OFFLINE=1 and not in cache/llm/
        return None, {"state": "not_cached", "detail": str(e)}


def _answer(mode: str, question: str, day: date | None):
    if mode == "rag":
        return _call(rag.answer, question)
    return _call(api.answer, question, mode, day)


@app.get("/api/status")
def status():
    return {"fake": api.fake_mode(), "today": date.today().isoformat()}


@app.get("/api/questions")
def questions():
    return [{"id": c["id"], "split": c["split"], "type": c["type"], "question": c["question_en"],
             "question_it": c["question_it"], "expected": c["answer_text"]} for c in CQS]


@app.get("/api/machines")
def machines():
    """The real machines of the cell: every fact with the words of its manual and a link to it."""
    data = json.loads((api.ROOT / "data" / "machines" / "machines.json").read_text(encoding="utf-8"))
    docs = {d["id"]: {k: d[k] for k in ("title", "manufacturer", "url", "pages")} for d in data["documents"]}
    return {"machines": [{**m, "facts": [{**f, "source": docs.get(f["doc"])} for f in m["facts"]]}
                         for m in data["machines"]],
            "not_yet": data["not_yet"]}


class Ask(BaseModel):
    question: str
    mode: str = "B"               # "B", "A" or "rag"
    as_of: date | None = None
    cq: str | None = None         # a gold question id, to score the answer


@app.post("/api/answer")
def answer(body: Ask):
    if body.mode not in ("A", "B", "rag"):
        raise HTTPException(400, "mode must be A, B or rag")
    a, err = _answer(body.mode, body.question, body.as_of)
    if err:
        return {"mode": body.mode, "error": err}
    out = {"mode": body.mode, "answer": asdict(a)}
    if body.cq in BY_ID:
        out["score"] = ev.score(BY_ID[body.cq], a.value)
    return out


@app.get("/api/score/{cq_id}")
def score_one(cq_id: str):
    """One row of the scoreboard: the gold question asked to every approach."""
    cq = BY_ID.get(cq_id)
    if cq is None:
        raise HTTPException(404, "unknown question")
    row = {"id": cq_id, "split": cq["split"], "question": cq["question_en"], "results": {}}
    for mode in ("rag", "A", "B"):
        a, err = _answer(mode, cq["question_en"], None)
        row["results"][mode] = ({"state": err["state"]} if err else
                                {"state": "unknown" if a.value is None else "answered",
                                 "score": ev.score(cq, a.value), "value": a.value})
    return row


@app.get("/api/ontology/{strategy}")
def ontology(strategy: str):
    if strategy not in ("A", "B"):
        raise HTTPException(404, "unknown strategy")
    if not api.fake_mode() and not api.ontology_file(strategy).exists():
        missing = {"state": "not_built", "detail": f"strategy {strategy} has not been built yet"}
        return {"build": None, "build_error": missing, "validation": None, "validation_error": missing,
                "counts": None, "turtle_available": False}
    built, err = _call(api.build_ontology, strategy)
    report, verr = _call(api.validate, strategy)
    counts_file = api.ROOT / "ontology" / strategy / "build.json"
    return {
        "build": None if err else {**asdict(built), "ontology_path": None, "shapes_path": None},
        "build_error": err,
        "validation": None if verr else asdict(report),
        "validation_error": verr,
        "counts": json.loads(counts_file.read_text(encoding="utf-8")) if counts_file.exists() and not api.fake_mode() else None,
        "turtle_available": api.ontology_file(strategy).exists(),
    }


@app.get("/api/ontology/{strategy}/turtle")
def turtle(strategy: str):
    path = api.ontology_file(strategy) if strategy in ("A", "B") else None
    if path is None or not path.exists():
        raise HTTPException(404, "no Turtle file for this strategy yet")
    return FileResponse(path, media_type="text/turtle", filename=f"plant-atlas-{strategy}.ttl")
