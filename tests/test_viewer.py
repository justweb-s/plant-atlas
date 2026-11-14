"""The ontology page (Core): generated from the store, self-contained, and equal to the rule for the devices."""
from datetime import date

import pytest

from atlas.ontology import viewer
from atlas.ontology.rules import verification_interval
from atlas.strategies.plant import device_records


@pytest.fixture(scope="module")
def page(tmp_path_factory):
    path = viewer.write(tmp_path_factory.mktemp("view") / "view.html")
    html = path.read_text(encoding="utf-8")
    return path, html, viewer.extract_data(html)


def test_file_is_a_fragment_that_starts_with_the_title(page):
    path, html, _ = page
    assert html.startswith("<title>Plant Atlas Ontology</title>")
    import re

    assert not re.search(r"<(html|body|head|!doctype)[\s>]", html, re.IGNORECASE)
    assert path.stat().st_size < 3_000_000


def test_only_d3_and_the_fonts_come_from_outside(page):
    import re

    _, html, _ = page
    markup = html[:html.index("const DATA = ")] + html[html.index("/*END-DATA*/"):]
    urls = set(re.findall(r"https?://[^\s\"')]+", markup))
    assert urls == {"https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js",
                    "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Space+Grotesk:wght@500;600&display=swap"}


def test_embedded_data_has_the_nine_corrected_pairs(page):
    _, _, data = page
    facts = {f["id"]: f for f in data["facts"]}
    new = [f for f in data["facts"] if f["d"] == "CORR" and f.get("x")]
    assert len(new) == 9
    for f in new:
        old = facts[f["x"]]
        assert old["d"] == "REG" and old["st"] == "closed" and old["t"] == "2023-07-04" == f["f"]
        assert f["st"] == "current" and old["p"] == f["p"] and old["o"] != f["o"]
    correction = [e for e in data["events"] if e["kind"] == "correction"]
    assert [(e["date"], e["touched"]) for e in correction] == [("2023-07-04", 18)]
    assert any(e["date"] == "2027-01-20" for e in data["events"])
    assert data["total"] == len(data["facts"]) == sum(l["count"] for l in data["layers"]) + data["no_layer"]


def test_device_table_equals_the_rule_on_two_dates(page):
    _, _, data = page
    statements = viewer._store().statements
    annex = viewer.annex_facts(statements)
    devices = device_records(statements)
    assert len(devices) == len(data["devices"]) == 24
    for day in (date(2019, 6, 1), date(2026, 11, 14)):
        table = {row["position"]: row for row in viewer.device_table(statements, day)}
        for device, embedded in zip(devices, data["devices"]):
            expected = verification_interval(device, annex, day)
            shown = embedded["by_year"][str(day.year)]
            assert embedded["position"] == device["position"]
            assert shown["interval"] == expected.get("interval") == table[device["position"]]["interval"]
            assert shown["row_id"] == (expected.get("row_id") or "")
            assert shown["why"].replace("{date}", str(day)) == (expected.get("why") or "")


def test_ready_focuses_and_conflict_come_from_the_data(page):
    _, _, data = page
    ids = {f["id"] for f in data["facts"]}
    assert len(data["focuses"]) >= 4
    assert all(focus["ids"] and set(focus["ids"]) <= ids for focus in data["focuses"])
    lost = [f for f in data["facts"] if f["st"] == "conflict"]
    assert lost and all(f["x"] in ids and f.get("y") for f in lost)
