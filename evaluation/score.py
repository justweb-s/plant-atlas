"""Scores answers against the gold in data/cq/cqs.json. Owner: Product. No network, no model."""
from __future__ import annotations

import json
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path
from typing import Callable

from atlas.contracts import Answer

ROOT = Path(__file__).resolve().parents[1]


def load_cqs() -> list[dict]:
    return json.loads((ROOT / "data/cq/cqs.json").read_text(encoding="utf-8"))["cqs"]


def _norm(s) -> str:
    s = unicodedata.normalize("NFKC", str(s)).casefold()
    s = re.sub(r"[^\w\s-]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _same(a: str, b: str) -> bool:
    a, b = _norm(a), _norm(b)
    if a == b:
        return True
    if min(len(a), len(b)) >= 4 and (a in b or b in a):
        return True
    return SequenceMatcher(None, a, b).ratio() >= 0.85


def score(cq: dict, value) -> float:
    """1.0 = right, 0.0 = wrong or no answer. Sets score F1; text scores the share of keyword groups found."""
    if value is None:
        return 0.0
    kind, gold = cq["answer"]["kind"], cq["answer"]["value"]
    if kind != "set" and isinstance(value, list):
        if len(value) != 1:
            return 0.0
        value = value[0]  # a model may wrap a single date or duration in a list: same answer
    if kind == "set":
        pred = [value] if isinstance(value, str) else list(value)
        if not pred:
            return 0.0
        precision = sum(any(_same(p, g) for g in gold) for p in pred) / len(pred)
        recall = sum(any(_same(g, p) for p in pred) for g in gold) / len(gold)
        return 0.0 if precision + recall == 0 else round(2 * precision * recall / (precision + recall), 3)
    if kind == "boolean":
        return float(value is gold)
    if kind in ("date", "duration"):
        return float(str(value).strip().upper() == str(gold).upper())
    if kind == "text":
        text = _norm(value)
        groups = cq["answer"]["keywords"]
        return round(sum(any(_norm(k) in text for k in group) for group in groups) / len(groups), 3)
    raise ValueError(f"unknown answer kind {kind!r} in {cq['id']}")


def run(answer_fn: Callable[[str], Answer], cqs: list[dict] | None = None, lang: str = "en") -> list[dict]:
    """Ask every CQ and score it. answer_fn takes the question text and returns an Answer."""
    rows = []
    for cq in cqs or load_cqs():
        a = answer_fn(cq[f"question_{lang}"])
        rows.append({"id": cq["id"], "type": cq["type"], "split": cq.get("split", "design"),
                     "score": score(cq, a.value), "value": a.value, "text": a.text,
                     "tokens": a.tokens, "cost_usd": a.cost_usd})
    return rows


def _means(rows: list[dict], key: str) -> dict[str, float]:
    groups: dict[str, list[float]] = {}
    for r in rows:
        groups.setdefault(r.get(key, "design"), []).append(r["score"])
    return {k: round(sum(v) / len(v), 3) for k, v in sorted(groups.items())}


def summary(rows: list[dict]) -> dict:
    """Totals; by_split keeps the design and the held-out questions apart (the held-out mean is the honest one)."""
    n = len(rows)
    return {
        "n": n,
        "correct": sum(r["score"] == 1.0 for r in rows),
        "unknown": sum("value" in r and r["value"] is None for r in rows),   # "I don't know" is not "wrong"
        "wrong": sum(r["score"] < 1.0 and not ("value" in r and r["value"] is None) for r in rows),
        "mean": round(sum(r["score"] for r in rows) / n, 3) if n else 0.0,
        "by_type": _means(rows, "type"),
        "by_split": _means(rows, "split"),
        "cost_usd": round(sum(r["cost_usd"] for r in rows), 4),
    }
