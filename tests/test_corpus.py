"""The chunker (Core): every design question's evidence must be reachable by its locator."""
import json
from pathlib import Path

from atlas.corpus.chunker import load, passage, root_of
from tests.test_cqs import norm

ROOT = Path(__file__).resolve().parents[1]
DESIGN = [cq for cq in json.loads((ROOT / "data/cq/cqs.json").read_text(encoding="utf-8"))["cqs"]
          if cq["split"] == "design"]


def test_ids_are_unique_and_chunks_have_text():
    chunks = load()
    assert len({c.id for c in chunks}) == len(chunks)
    assert all(c.text and c.locator and c.source for c in chunks)


def test_the_gold_texts_are_cut_by_article_and_annex_point():
    locators = {(c.source, c.locator) for c in load()}
    for expected in [("REG", "Art. 25(2)"), ("REG", "Art. 3(16)"), ("REG", "Annex III, 1.3.7"),
                     ("REG", "Annex I, Part A, point 5"), ("CORR", "Corrigendum, point 5"),
                     ("DIR", "Art. 12(3)"), ("DLGS71", "art. 71, c. 11")]:
        assert expected in locators, expected


def test_every_design_quote_is_in_the_article_or_annex_its_locator_names():
    missing = []
    for cq in DESIGN:
        for ev in cq["evidence"]:
            if ev["source"] == "CATALOGUE":
                continue
            if norm(ev["quote"]) not in norm(passage(ev["source"], ev["locator"])):
                missing.append(f'{cq["id"]} {ev["source"]} {ev["locator"]} (root {root_of(ev["locator"])})')
    assert not missing, "\n".join(missing)


def test_exact_locators_hold_their_quote():
    """Where the gold's locator is a chunk of ours, the quote is in that very chunk."""
    by_locator = {}
    for chunk in load():
        by_locator.setdefault((chunk.source, chunk.locator), []).append(chunk)
    checked = 0
    for cq in DESIGN:
        for ev in cq["evidence"]:
            hits = by_locator.get((ev["source"], ev["locator"]))
            if hits:
                checked += 1
                assert any(norm(ev["quote"]) in norm(c.text) for c in hits), (cq["id"], ev["locator"])
    assert checked >= 20
