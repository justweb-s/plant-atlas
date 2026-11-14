"""Owner: Product (decision 1410-due-corsie). Strategy A: free extraction, the line to beat.

The model reads the same pieces of text as strategy B and writes the facts as it likes: no schema, its own
words, a quote it chooses. Nothing is checked: every fact goes into the store. Each fact is also passed
through Store.write_statement() on a separate store, only to count how many B's checks would have refused.

Run: python -m atlas.strategies.a   -> ontology/A/statements.json and ontology/A/build.json
"""
from __future__ import annotations

import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from atlas import llm
from atlas.contracts import Chunk
from atlas.ontology.statements import ChunkCorpus, Statement, Store

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "ontology" / "A"
SYSTEM = """Read one passage of a document about machines at work (law, manual, guidance, internal guideline,
plant record) and write down the important facts it states.

Answer with one line per fact, fields separated by " | ", nothing else, no header, no code fence:
subject | predicate | object | condition | quote
- predicate: a short camelCase verb phrase of your choice.
- condition: any condition or exception, or "" if none.
- quote: the words of the passage the fact comes from.
At most 12 facts. If the passage states nothing important, answer with the single word NONE."""


def chunks_read_by_b(chunks: list[Chunk]) -> list[Chunk]:
    """The same pieces strategy B read: the law body (with the corrigendum, which A reads like any text),
    the decree and Annex VII, the selected pages of the other layers and the plant's list."""
    from atlas.strategies.b import select_pages

    law = [c for c in chunks if (c.source in ("REG", "DIR", "CORR", "DM2011") or c.source.startswith("DLGS"))
           and not c.locator.startswith("Recital")]
    layers = [p for layer in ("manufacturer", "guidance", "company") for p in select_pages(chunks, layer)]
    plant = [c for c in chunks if c.source == "igea-equipment"]
    return law + layers + plant


def extract(chunk: Chunk) -> tuple[list[Statement], dict]:
    out = llm.chat([{"role": "system", "content": SYSTEM},
                    {"role": "user", "content": f"Passage: {chunk.source}, {chunk.locator}\n\n{chunk.text}"}],
                   temperature=0, max_tokens=3000)
    facts = []
    for line in (out["text"] or "").splitlines():
        cells = [c.strip() for c in re.split(r"\s*\|\s*", line.strip().strip("`"))]
        if len(cells) != 5 or not cells[0] or not cells[2]:
            continue
        subject, predicate, obj, condition, quote = cells
        facts.append(Statement(subject=subject, predicate=predicate, object=obj, object_as_written=obj,
                               object_normalised=obj.lower(), condition=condition.strip('"'), quote=quote,
                               source_doc=chunk.source, anchor=chunk.locator, source_version=chunk.version,
                               layer=chunk.layer, status="current", asserted_by="strategy_a"))
    return facts, out.get("usage") or {}


def build(chunks: list[Chunk], workers: int = 16) -> tuple[Store, dict]:
    corpus = ChunkCorpus(chunks)
    store, checker = Store(corpus, OUT / "statements.json"), Store(corpus)
    read = chunks_read_by_b(chunks)
    usage = {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0}
    done = [0]

    def one(chunk):
        result = extract(chunk)
        done[0] += 1
        if done[0] % 50 == 0:
            print(f"A {done[0]}/{len(read)}", file=sys.stderr, flush=True)
        return result

    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(one, read))
    for statements, used in results:
        usage["calls"] += 1
        usage["prompt_tokens"] += used.get("prompt_tokens", 0) or 0
        usage["completion_tokens"] += used.get("completion_tokens", 0) or 0
        for s in statements:
            s.id = f"st-{len(store.statements) + 1:04d}"
            store.statements.append(s)                                 # A keeps everything
            checker.write_statement(s.model_copy(update={"id": "", "status": "proposed"}))   # only to count
    counts = {"proposed_total": len(store.statements), "kept": len(store.statements),
              "would_pass_b_checks": len(checker.statements), "would_be_rejected": len(checker.rejections),
              **{f"would_be_{k}": v for k, v in checker.counts().items() if k.startswith("rejected_")},
              "predicates": len({s.predicate for s in store.statements}),
              "chunks_read": len(read), **usage}
    return store, counts


def main() -> None:
    from atlas.corpus.chunker import load

    started = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    store, counts = build(list(load()))
    store.save()
    counts["seconds"] = round(time.time() - started, 1)
    (OUT / "build.json").write_text(json.dumps(counts, indent=1), encoding="utf-8")
    print(json.dumps(counts))


if __name__ == "__main__":
    main()
