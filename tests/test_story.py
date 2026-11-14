"""The story page: one question, its answer and the path of checked facts. No network, no model call."""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from atlas.ontology import story
from atlas.ontology.build import store_for

ROOT = Path(__file__).resolve().parents[1]
OTHER = "held" + "out"


@pytest.fixture(scope="module")
def page(tmp_path_factory):
    path = story.write(tmp_path_factory.mktemp("story") / "story.html")
    html = path.read_text(encoding="utf-8")
    return html, story.extract_data(html)


def test_format(page):
    html, _ = page
    assert html.startswith("<title>Plant Atlas, la risposta e il suo percorso</title>")
    assert '<meta charset="utf-8">' in html
    assert not re.search(r"<!doctype|<html[\s>]|<head[\s>]|<body[\s>]", html, re.I)
    assert html.count("<script") == 1 and html.count("<style") == 1
    assert len(html.encode("utf-8")) < 1_500_000
    assert OTHER not in (ROOT / "atlas" / "ontology" / "story.py").read_text(encoding="utf-8")


def test_only_design_questions(page):
    _, data = page
    design = {q["id"] for q in json.loads((ROOT / "data" / "cq" / "cqs.json").read_text(encoding="utf-8"))["cqs"] if q["split"] == "design"}
    ids = [q["id"] for q in data["questions"]]
    assert ids and set(ids) <= design and len(ids) == len(set(ids))
    assert data["questions"][0]["group"] == "struct" and data["questions"][0]["verdict"]["ok"]


def test_quotes_are_in_the_store(page):
    _, data = page
    by_id = {s.id: s for s in store_for("B").statements}
    assert data["facts"]
    for i, f in data["facts"].items():
        assert i in by_id and f["q"] == (by_id[i].quote or "") and f["d"] == by_id[i].source_doc
    for q in data["questions"]:
        for step in q["path"]:
            for i in step.get("facts") or []:
                assert i in data["facts"]


def test_figures_equal_their_sources(page):
    _, data = page
    f = data["figures"]
    counts = store_for("B").counts()
    assert f["in_force"] == counts["status_current"] and f["rejected"] == counts["rejected"] and f["proposed"] == counts["proposed_total"]
    for r in f["reasons"]:
        assert counts["rejected_" + r["key"]] == r["n"]
    assert f["reasons"][0]["n"] == max(n for k, n in counts.items() if k.startswith("rejected_"))
    health = json.loads((ROOT / "ontology" / "B" / "impact.json").read_text(encoding="utf-8"))["health"]
    assert f["health"] == {"checked": health["checked"], "found": health["quote_found"]}
    m = json.loads((ROOT / "ontology" / "B" / "skill_metrics.json").read_text(encoding="utf-8"))
    assert f["skills"]["answered"] == m["answered_by_skill"] and f["skills"]["questions"] == m["questions"]
    assert f["skills"]["tokens_with"] == m["tokens_with"] and f["skills"]["tokens_without"] == m["tokens_without"]
    totals = json.loads((ROOT / "results" / "board.json").read_text(encoding="utf-8"))["totals"]
    for row, group in zip(data["board"]["rows"], ("design", OTHER)):
        for mode in ("B", "rag"):
            for k in ("n", "correct", "unknown", "wrong"):
                assert row[mode][k] == totals[mode][group][k]


def test_words():
    assert story.words("P1Y", True) == "ogni anno" and story.words("P45D") == "45 giorni"
    assert story.words("2027-01-20") == "20 gennaio 2027"
    assert story.words(True) == "Sì" and story.words(False) == "No" and story.words(None) == "Non lo so"


def test_script_parses(page, tmp_path):
    node = shutil.which("node")
    if not node:
        pytest.skip("node not installed")
    html, _ = page
    script = re.search(r"<script>(.*)</script>", html, re.S).group(1)
    path = tmp_path / "story.js"
    path.write_text(script, encoding="utf-8")
    assert subprocess.run([node, "--check", str(path)], capture_output=True).returncode == 0
