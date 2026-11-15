"""Baseline: plain retrieval over the same chunks, with the same model, no ontology. Owner: Product.

How it works: every chunk of api.corpus() is embedded once (atlas.llm.embed, cached), the question is
embedded, the TOP most similar chunks go to atlas.llm.chat with the same output format as strategy B.
No passage used means value None: "unknown", kept apart from "wrong" on the board.

Fair comparison with B: same corpus, same text model (ATLAS_TEXT_MODEL), same JSON answer, same
"today is" line. The only difference is what the model reads: raw passages here, checked facts in B.

Run: python -m evaluation.rag            -> results/rag.json (rows + summary)
     python -m evaluation.rag --estimate -> how many calls a full run makes, no network
"""
from __future__ import annotations

import json
import math
import os
import re
import sys
from datetime import date
from functools import lru_cache
from pathlib import Path

from atlas.contracts import Answer, Chunk, Step

ROOT = Path(__file__).resolve().parents[1]
TOP = 10                 # passages given to the model
MAX_CHARS = 4000         # a passage longer than this is cut (a few annexes are 20k+ characters)
BATCH = 200              # chunks per embedding call; each batch is one cache file
DIMENSIONS = int(os.getenv("ATLAS_RAG_DIMENSIONS", "256"))   # small vectors keep cache/llm/ small

SYSTEM = """You answer a question about machinery and work-equipment law using ONLY the numbered passages given.

Rules:
- Use only these passages. Do not use anything you know from elsewhere.
- If the passages do not answer the question, the kind is "unknown" and the value is null.
- If the question asks about a day, compare that day with the dates in the passages.
- If the question asks "which" or "what" and several passages answer it, list every one of them.
- If the question asks who does something and within what time, the kind is "text" and the value names both.
- Return JSON only:
  {"kind": "set|date|duration|boolean|text|unknown",
   "value": <list of short strings for set | "YYYY-MM-DD" for date | ISO 8601 duration like "P10Y" | true/false | a short text | null>,
   "text": "one or two sentences for a person, naming the article or annex point",
   "used": [passage numbers you relied on]}"""


def _fake() -> bool:
    return os.getenv("ATLAS_FAKE", "1") == "1"


def _passage(c: Chunk) -> str:
    return f"{c.source}, {c.locator}: {c.text[:MAX_CHARS]}"


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    return dot / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)) or 1.0)


@lru_cache(maxsize=1)
def _index() -> tuple[list[Chunk], list[list[float]]]:
    from atlas import api, llm
    chunks = api.corpus()
    texts = [_passage(c) for c in chunks]
    vectors: list[list[float]] = []
    for start in range(0, len(texts), BATCH):
        vectors += llm.embed(texts[start:start + BATCH], dimensions=DIMENSIONS)
    return chunks, vectors


def retrieve(question: str, top: int = TOP) -> list[Chunk]:
    from atlas import llm
    chunks, vectors = _index()
    q = llm.embed([question], dimensions=DIMENSIONS)[0]
    ranked = sorted(range(len(chunks)), key=lambda i: _cosine(q, vectors[i]), reverse=True)
    return [chunks[i] for i in ranked[:top]]


def _parse(text: str) -> dict:
    match = re.search(r"\{.*\}", text or "", re.DOTALL)
    try:
        return json.loads(match.group(0)) if match else {}
    except json.JSONDecodeError:
        return {}


def answer(question: str, as_of: date | None = None) -> Answer:
    if _fake():
        from atlas import fake
        return fake.rag_answer(question, as_of)
    from atlas import llm
    import os
    fixed = os.getenv("ATLAS_TODAY")   # the same fixed 'today' as the agent, so a board can be repeated later
    day = as_of or (date.fromisoformat(fixed) if fixed else date.today())
    chosen = retrieve(question)
    numbered = "\n\n".join(f"[{i}] {_passage(c)}" for i, c in enumerate(chosen))
    out = llm.chat([{"role": "system", "content": SYSTEM},
                    {"role": "user", "content": f"Today is {day.isoformat()}.\nQuestion: {question}\n\nPassages:\n{numbered}"}],
                   temperature=0, max_tokens=3000)
    data = _parse(out["text"])
    used = [chosen[i] for i in data.get("used", []) if isinstance(i, int) and 0 <= i < len(chosen)]
    value = None if data.get("kind") == "unknown" or not used else data.get("value")
    usage = out.get("usage") or {}
    steps = [Step(text=c.text[:300], quote=c.text[:300], locator=f"{c.source}, {c.locator}") for c in used]
    return Answer(question=question, mode="rag", value=value,
                  text=data.get("text") or "The passages found do not answer this question.",
                  steps=steps, tokens=(usage.get("prompt_tokens") or 0) + (usage.get("completion_tokens") or 0))


def estimate(n_questions: int) -> dict:
    """Calls and tokens of a full run, before any network call (AGENTS.md §6)."""
    from atlas import api
    chunks = api.corpus()
    chars = sum(len(_passage(c)) for c in chunks)
    return {"chunks": len(chunks), "embed_calls": math.ceil(len(chunks) / BATCH) + n_questions,
            "embed_tokens": chars // 4, "chat_calls": n_questions,
            "chat_tokens_in_max": n_questions * (TOP * MAX_CHARS + 2000) // 4}


def main(argv: list[str]) -> None:
    from evaluation.score import load_cqs, run, summary
    cqs = load_cqs()
    if "--estimate" in argv:
        print(json.dumps(estimate(len(cqs)), indent=1))
        return
    rows = run(answer, cqs)
    out = ROOT / "results" / "rag.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"summary": summary(rows), "rows": rows}, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(json.dumps(summary(rows), indent=1))


if __name__ == "__main__":
    main(sys.argv[1:])
