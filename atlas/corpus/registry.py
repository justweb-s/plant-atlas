"""Owner: Core. The register of sources: every piece of every document, fingerprinted before anything reads it.

`python -m atlas.corpus.registry` writes atlas/corpus/incoming/chunks_registry.csv: one row per piece with its
source, locator, layer and sha256. It is the reference for two things:
- a fact can only quote a piece that is in the register;
- when a document changes, comparing two registers tells which pieces changed, so only those are read again.
"""
from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

REGISTER = Path(__file__).resolve().parent / "incoming" / "chunks_registry.csv"
FIELDS = ["id", "source", "locator", "layer", "version", "sha256", "characters", "registered"]


def rows() -> list[dict]:
    from atlas.corpus.chunker import load

    today = date.today().isoformat()
    return [{"id": c.id, "source": c.source, "locator": c.locator, "layer": c.layer, "version": c.version,
             "sha256": c.sha256, "characters": len(c.text), "registered": today} for c in load()]


def read(path: Path = REGISTER) -> dict[str, dict]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as handle:
        return {row["id"]: row for row in csv.DictReader(handle)}


def write(path: Path = REGISTER) -> list[dict]:
    """Write the register. A piece whose fingerprint did not change keeps the day it was first registered."""
    previous = read(path)
    current = rows()
    for row in current:
        old = previous.get(row["id"])
        if old and old["sha256"] == row["sha256"]:
            row["registered"] = old["registered"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(current)
    return current


def changed(before: dict[str, dict], after: dict[str, dict]) -> dict[str, list[str]]:
    """Which pieces were added, removed or modified between two registers (by fingerprint)."""
    return {
        "added": sorted(i for i in after if i not in before),
        "removed": sorted(i for i in before if i not in after),
        "modified": sorted(i for i in after if i in before and after[i]["sha256"] != before[i]["sha256"]),
    }


if __name__ == "__main__":
    import collections

    written = write()
    by_layer = collections.Counter(row["layer"] for row in written)
    print(f"registered {len(written)} pieces from {len({row['source'] for row in written})} documents: {dict(by_layer)}")
