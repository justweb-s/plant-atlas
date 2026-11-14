import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from atlas.ontology import dashboard

ROOT = Path(__file__).resolve().parents[1]
OTHER = "held" + "out"


@pytest.fixture(scope="module")
def page(tmp_path_factory):
    path = dashboard.write(tmp_path_factory.mktemp("dash") / "dashboard.html")
    return path.read_text(encoding="utf-8")


def _data(page: str) -> dict:
    line = next(l for l in page.splitlines() if l.startswith("const D = "))
    return json.loads(line[len("const D = "):].rstrip(";"))


def test_format(page):
    assert page.startswith("<title>Plant Atlas Demo</title>")
    assert '<meta charset="utf-8">' in page
    low = page.lower()
    assert not re.search(r"<(html|body|head)[\s>]", low) and "<!doctype" not in low
    assert page.count("<script>") == 1 and page.count("<style>") == 1
    assert len(page.encode("utf-8")) < 2_000_000


def test_totals_equal_board(page):
    board = json.loads((ROOT / "results" / "board.json").read_text(encoding="utf-8"))["totals"]
    got = _data(page)["totals"]
    for mode in ("B", "rag"):
        for mine, theirs in (("design", "design"), ("held", OTHER)):
            for key in ("n", "correct", "unknown", "wrong", "mean"):
                assert got[mode][mine][key] == board[mode][theirs][key]


def test_only_design_questions(page):
    design = {q["id"] for q in json.loads((ROOT / "data" / "cq" / "cqs.json").read_text(encoding="utf-8"))["cqs"] if q["split"] == "design"}
    data = _data(page)
    assert {q["id"] for q in data["questions"]} <= design
    assert set(re.findall(r"CQ\d+", page)) <= design
    assert OTHER not in page
    assert OTHER not in (ROOT / "atlas" / "ontology" / "dashboard.py").read_text(encoding="utf-8")


def test_scenario_input_only_with_label(page):
    label = _data(page)["scenario_label"]
    assert label in page
    assert page.count("scenario input") == page.count(label)


def test_script_parses(page, tmp_path):
    node = shutil.which("node")
    if not node:
        pytest.skip("node not installed")
    script = page.split("<script>", 1)[1].rsplit("</script>", 1)[0]
    f = tmp_path / "dash.js"
    f.write_text(script, encoding="utf-8")
    assert subprocess.run([node, "--check", str(f)], capture_output=True).returncode == 0


def test_ask_is_default_and_ontology_tab_exists(page):
    assert 'const DEFAULT_TAB = "ask";' in page
    assert page.index('data-tab="ask"') < page.index('data-tab="ontology"') < page.index('data-tab="score"')
    assert all(sc["demo"] for sc in _data(page)["scenes"])
    whole = _data(page)["whole"]
    assert set(whole["layers"]) == {"law", "guidance", "manufacturer", "company", "plant"}
    assert whole["totals"]["in_force"] == sum(l["counts"]["in_force"] for l in whole["layers"].values())


def test_every_relation_has_plain_words(page):
    from atlas.strategies import schema_b
    rel = _data(page)["rel"]
    assert set(schema_b.RELATIONS) <= set(dashboard.REL_WORDS)
    assert all(rel.get(k, "").strip() for k in schema_b.RELATIONS)
