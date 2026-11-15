"""Free search: the third way to answer. Owner: Product (written by Core).

A model is given a folder with every registered document as a text file and three tools: list files, search
them, read them. Nothing else: no index, no fact store, no rules. It looks for the answer as a person would.

    python -m evaluation.free export     -> runtime/free_search/docs/<source>.md   (one file per document)
    python -m evaluation.free            -> results/free.json (every question of data/cq/cqs.json)

The model runs through the Claude command line (`claude -p`) with only Read, Grep and Glob, started inside
the folder. Same answering model as the other ways (ATLAS_TEXT_MODEL), same JSON answer, same fixed day.
Answers are cached in cache/llm/ like every other model call.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

from atlas import llm
from atlas.contracts import Answer, Step

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "runtime" / "free_search" / "docs"
SYSTEM = """You answer a question about machines at work using ONLY the documents in the current folder: EU and
Italian law, guidance, manufacturers' manuals, a company's documents and a plant's records, one text file per
document. README.md lists them. Use your tools (Glob, Grep, Read) to find and read what you need; search in
English and in Italian, since the documents are in both languages.

Rules:
- Use only what the files say. Do not use anything you know from elsewhere.
- If the files do not answer the question, the kind is "unknown" and the value is null.
- If the question asks about a day, compare that day with the dates in the files.
- If the question asks "which" or "what" and several things answer it, list every one of them.
- If the question asks who does something and within what time, the kind is "text" and the value names both.
- When you have the answer, or are sure the files do not hold it, reply with JSON only, nothing before or after:
  {"kind": "set|date|duration|boolean|text|unknown",
   "value": <list of short strings for set | "YYYY-MM-DD" for date | ISO 8601 duration like "P10Y" | true/false | a short text | null>,
   "text": "one or two sentences for a person, naming the document and the article, section or page",
   "sources": [{"file": "<file name>", "place": "<heading of the section>", "quote": "<the sentence relied on, copied>"}]}"""


def export() -> int:
    """Every registered document as one text file, its pieces under their own headings."""
    from atlas import api

    DOCS.mkdir(parents=True, exist_ok=True)
    by_source: dict[str, list] = {}
    for chunk in api.corpus():
        by_source.setdefault(chunk.source, []).append(chunk)
    index = ["# Documents", "", "| File | Kind of document | Version | Sections |", "|---|---|---|---|"]
    for source, chunks in sorted(by_source.items()):
        lines = [f"# {source}", "", f"Kind of document: {chunks[0].layer}. Version: {chunks[0].version}.", ""]
        for chunk in chunks:
            lines += [f"## {chunk.locator}", "", chunk.text, ""]
        (DOCS / f"{source}.md").write_text("\n".join(lines), encoding="utf-8")
        index.append(f"| {source}.md | {chunks[0].layer} | {chunks[0].version} | {len(chunks)} |")
    (DOCS / "README.md").write_text("\n".join(index) + "\n", encoding="utf-8")
    return len(by_source)


def _model() -> str:
    name = os.getenv("ATLAS_TEXT_MODEL", "anthropic/claude-haiku-5.5")
    return next((short for short in ("haiku", "sonnet", "opus") if short in name), "haiku")


def _ask(question: str, day: date) -> dict:
    """One agent run; {"text", "turns", "usage"}. Cached under its own kind."""
    payload = {"model": _model(), "system": SYSTEM, "question": question, "day": day.isoformat(),
               "tools": ["Read", "Grep", "Glob"]}
    path = llm._cache_path("free-cli", payload)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))["response"]
    if not (DOCS / "README.md").exists():
        export()
    command = ["claude", "-p", "--model", payload["model"], "--system-prompt", SYSTEM, "--tools", "Read,Grep,Glob",
               "--allowedTools", "Read,Grep,Glob", "--strict-mcp-config", "--no-session-persistence",
               "--setting-sources", "", "--no-chrome", "--output-format", "json"]
    error = None
    for _ in range(2):
        try:
            done = subprocess.run(command, input=f"Today is {day.isoformat()}.\nQuestion: {question}",
                                  capture_output=True, text=True, encoding="utf-8", cwd=DOCS, timeout=900)
            reply = json.loads(done.stdout)
        except (ValueError, subprocess.TimeoutExpired) as problem:
            error = str(problem)[:200]
            continue
        if reply.get("is_error") or not isinstance(reply.get("result"), str):
            error = str(reply.get("result"))[:200]
            continue
        usage = reply.get("usage") or {}
        out = {"text": reply["result"], "turns": reply.get("num_turns"),
               "usage": {"prompt_tokens": sum(usage.get(k, 0) or 0 for k in (
                   "input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")),
                   "completion_tokens": usage.get("output_tokens", 0) or 0}}
        llm._store(path, payload, out)
        return out
    raise RuntimeError(f"free search gave no answer: {error}")


def answer(question: str, as_of: date | None = None) -> Answer:
    fixed = os.getenv("ATLAS_TODAY")
    day = as_of or (date.fromisoformat(fixed) if fixed else date.today())
    out = _ask(question, day)
    found = re.findall(r"\{.*\}", out["text"] or "", re.DOTALL)
    try:
        data = json.loads(found[-1]) if found else {}
    except json.JSONDecodeError:
        data = {}
    sources = [s for s in data.get("sources") or [] if isinstance(s, dict)]
    value = None if data.get("kind") == "unknown" else data.get("value")
    steps = [Step(text=str(s.get("quote") or "")[:300], quote=str(s.get("quote") or "")[:300],
                  locator=f"{str(s.get('file') or '').removesuffix('.md')}, {s.get('place')}") for s in sources]
    usage = out.get("usage") or {}
    return Answer(question=question, mode="free", value=value,
                  text=data.get("text") or "The documents searched do not answer this question.", steps=steps,
                  tokens=(usage.get("prompt_tokens") or 0) + (usage.get("completion_tokens") or 0), basis="free search")


def main(argv: list[str]) -> None:
    if argv[:1] == ["export"]:
        print(f"{export()} documents in {DOCS}")
        return
    from concurrent.futures import ThreadPoolExecutor

    from evaluation.score import load_cqs, score, summary

    cqs = load_cqs()

    def one(cq: dict) -> dict:
        try:
            a = answer(cq["question_en"])
        except RuntimeError as problem:
            a = Answer(question=cq["question_en"], mode="free", value=None, text=f"ERROR: {problem}")
        return {"id": cq["id"], "type": cq["type"], "split": cq.get("split", "design"),
                "score": score(cq, a.value), "value": a.value, "text": a.text, "tokens": a.tokens, "cost_usd": a.cost_usd}

    with ThreadPoolExecutor(int(os.getenv("ATLAS_FREE_PARALLEL", "4"))) as pool:
        rows = list(pool.map(one, cqs))
    out = {"summary": summary(rows), "rows": rows}
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results" / "free.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("free", json.dumps(out["summary"]))


if __name__ == "__main__":
    main(sys.argv[1:])
