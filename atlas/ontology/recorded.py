"""Owner: Core. Every design answer of Plant Atlas, recorded with its steps and an Italian rendering.

    python -m atlas.ontology.recorded        # writes ontology/B/answers_design.json

Each design question is asked exactly as the board asks it (English, as of 14 November 2026), so the procedure
graphs run. One further call per answer translates the answer sentence and the outputs of the trace's nodes into
Italian. The quotes of the facts are never translated: they are the documents' own words. Only design questions
are read here; the other split is never opened.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "ontology" / "B" / "answers_design.json"
AS_OF = date(2026, 11, 14)

INSTRUCTIONS = (
    "You translate English into Italian. The user sends a JSON list of strings. Translate each string faithfully and plainly. "
    "Keep numbers, dates, document names, article and annex references, product and company names, and any text between "
    "quotation marks exactly as they are. Do not add or remove information. An empty string stays empty. "
    "Return only a JSON list of strings of the same length, in the same order, with no other text."
)


def _questions() -> list[dict]:
    return [q for q in json.loads((ROOT / "data" / "cq" / "cqs.json").read_text(encoding="utf-8"))["cqs"] if q["split"] == "design"]


def _parse(text: str):
    text = (text or "").strip()
    if text.startswith("```"):
        text = text.strip("`").strip()
        if text.lower().startswith("json"):
            text = text[4:]
    try:
        return json.loads(text)
    except ValueError:
        return None


def translate(strings: list[str]) -> list[str] | None:
    """The same list in Italian, or None when the model's reply is not a JSON list of the same length."""
    from atlas import llm

    if not any(s.strip() for s in strings):
        return list(strings)
    reply = llm.chat([{"role": "system", "content": INSTRUCTIONS},
                      {"role": "user", "content": json.dumps(strings, ensure_ascii=False)}], temperature=0)
    got = _parse(reply.get("text", ""))
    if not isinstance(got, list) or len(got) != len(strings) or not all(isinstance(x, str) for x in got):
        return None
    return got


def record_one(q: dict) -> dict:
    from atlas.ontology import build

    a = build.answer(q["question_en"], "B", AS_OF)
    value = a.value
    trace = getattr(a, "trace", None)
    entry = {
        "value": value if isinstance(value, (list, bool)) or value is None else str(value),
        "text": a.text or "",
        "steps": [{"text": s.text, "quote": s.quote or "", "locator": s.locator or "", "statement_id": s.statement_id or ""} for s in a.steps],
        "trace": trace if isinstance(trace, dict) else None,
        "tokens": a.tokens,
    }
    outputs = [str(n.get("output") or "") for n in (entry["trace"] or {}).get("nodes", [])]
    italian = translate([entry["text"]] + outputs)
    entry["translated"] = italian is not None
    entry["text_it"] = italian[0] if italian else entry["text"]
    entry["outputs_it"] = italian[1:] if italian else outputs
    return entry


def record() -> dict:
    return {q["id"]: record_one(q) for q in _questions()}


def load(path: Path | None = None) -> dict:
    """The recorded design answers, or {} when the file has not been written."""
    path = Path(path or OUT)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def main() -> None:
    from atlas import llm

    before = len(list(llm.CACHE.glob("*"))) if llm.CACHE.exists() else 0
    data = record()
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    after = len(list(llm.CACHE.glob("*")))
    print(f"wrote {OUT}: {len(data)} answers, {sum(1 for e in data.values() if e['steps'])} with steps, "
          f"{sum(1 for e in data.values() if e['translated'])} translated, {after - before} calls not cached")


if __name__ == "__main__":
    main()
