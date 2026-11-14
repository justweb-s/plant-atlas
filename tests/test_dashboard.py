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


def test_document_map(page):
    from collections import Counter
    from atlas.ontology import atlas_page
    assert page.index('data-tab="ask"') < page.index('data-tab="documents"') < page.index('data-tab="ontology"')
    dmap = _data(page)["dmap"]
    store = atlas_page.viewer._store()
    count = Counter(dashboard.doc_key(s.source_doc) for s in store.statements if s.status == "current")
    assert {d["key"]: d["n"] for d in dmap["docs"]} == dict(count)
    assert dmap["edges"] and all(e["n"] > 0 for e in dmap["edges"])
    assert {e["kind"] for e in dmap["edges"]} <= {"cites", "corrects", "prevails", "applied"}


def test_left_toggle_and_deep_links(page):
    assert 'id="lefttoggle"' in page and 'data-left="facts"' in page and 'data-left="docs"' in page
    assert 'tokens.has("docs")' in page and 'tokens.has("embed")' in page
    assert 'id="why"' in page and "ontology.ttl" in page


def test_build_player(page):
    assert 'tokens.has("build")' in page and "step=(" in page and 'id="player"' in page
    dmap = _data(page)["dmap"]
    assert sorted(dmap["order"]) == sorted(d["key"] for d in dmap["docs"])
    assert len(dmap["order"]) == len(set(dmap["order"]))
    facts = _data(page)["facts"]
    assert all(a["id"] in facts for a in dmap["addfacts"])


def test_solo_mode_is_handled(page):
    assert 'tokens.has("solo")' in page and 'id="side"' in page
    assert ".app.solo .right { display: none; }" in page or ".app.solo .top, .app.solo .why, .app.solo .right { display: none; }" in page


def test_verdicts(page):
    qs = _data(page)["questions"]
    design = {q["id"] for q in json.loads((ROOT / "data" / "cq" / "cqs.json").read_text(encoding="utf-8"))["cqs"] if q["split"] == "design"}
    assert {q["id"] for q in qs} == design
    assert all(isinstance(q.get("verdict"), dict) and q["verdict"].get("kind") and q["verdict"].get("say") for q in qs)
    path = ROOT / "ontology" / "B" / "skill_traces.json"
    traced = {k for k in json.loads(path.read_text(encoding="utf-8")) if k in design} if path.exists() else set()
    for q in qs:
        if q["id"] in traced and q["B"] and q["B"]["score"] >= 0.999:
            assert q["verdict"]["kind"] == "procedure" and q["verdict"]["chain"]
        assert q["verdict"]["ok"] == bool(q["B"] and q["B"]["score"] >= 0.999)
