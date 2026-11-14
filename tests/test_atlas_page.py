"""The atlas page (Core): a fragment, only real quotes, six scenes over the bands, and equal to the rule for device 13."""
import re
from datetime import date

import pytest

from atlas.ontology import atlas_page, viewer
from atlas.ontology.build import raw_store
from atlas.ontology.rules import verification_interval
from atlas.strategies.plant import device_records


@pytest.fixture(scope="module")
def page(tmp_path_factory):
    path = atlas_page.write(tmp_path_factory.mktemp("atlas") / "atlas.html", answers=False)   # no model call
    html = path.read_text(encoding="utf-8")
    return path, html, atlas_page.extract_data(html)


def test_file_is_a_fragment_that_starts_with_the_title(page):
    path, html, _ = page
    assert html.startswith("<title>Plant Atlas</title>")
    assert not re.search(r"<(html|body|head|!doctype)[\s>]", html, re.IGNORECASE)
    assert "<script src" not in html
    assert path.stat().st_size < 1_500_000


def test_every_embedded_fact_has_its_quote_in_the_store(page):
    _, _, data = page
    quotes = {s.id: s.quote for s in raw_store("B").statements}
    assert data["facts"]
    for fid, fact in data["facts"].items():
        assert fact["q"] and quotes[fid] == fact["q"]


def test_six_scenes_each_with_cards_in_at_least_two_bands(page):
    _, _, data = page
    assert len(data["scenes"]) == 6
    for scene in data["scenes"]:
        for variant in scene["variants"]:
            bands = {data["facts"][c["f"]]["l"] if c.get("f") else c["band"] for c in variant["cards"]}
            assert len(bands) >= 2, (scene["id"], variant["label"])
            keys = {c["k"] for c in variant["cards"]}
            assert all(link["a"] in keys and link["b"] in keys and link["kind"] in ("stored", "derived")
                       for link in variant["links"])


def test_stored_links_are_only_the_ones_the_store_holds(page):
    _, _, data = page
    for scene in data["scenes"]:
        for variant in scene["variants"]:
            for link in variant["links"]:
                if link["kind"] == "stored":
                    assert data["facts"][link["b"]].get("x") == link["a"] or data["facts"][link["a"]].get("x") == link["b"]


def test_scenario_input_appears_only_with_its_label(page):
    _, html, data = page
    label = atlas_page.SCENARIO_LABEL
    cards = [c for s in data["scenes"] for v in s["variants"] for c in v["cards"] if not c.get("f")]
    assert all(c["state"] in ("scenario", "gap") for c in cards)
    assert any(c["state"] == "scenario" for c in cards)
    zone = f"{atlas_page.SCENARIO_ZONE_MM} mm zone"
    for scene in data["scenes"]:
        for variant in scene["variants"]:
            text = variant["result"]["text"]
            if zone in text:
                assert f"{zone} ({label})" in text
    assert 'class="tag">\' + esc(DATA.scenario_label)' in html   # the card always carries the label


def test_device_13_result_equals_the_rule_on_both_dates(page):
    _, _, data = page
    statements = raw_store("B").statements
    device = next(d for d in device_records(statements) if d["position"] == atlas_page.DEVICE)
    variants = data["scenes"][0]["variants"]
    assert len(variants) == 2
    for variant, day in zip(variants, (date(2026, 11, 14), date(2027, 11, 14))):
        expected = verification_interval(device, viewer.annex_facts(statements), day)
        assert variant["rule"]["interval"] == expected.get("interval")
        assert variant["rule"]["row_id"] == expected.get("row_id", "")
        assert variant["rule"]["why"] == expected.get("why", "")
    assert variants[0]["result"]["text"] == "Device 13: verification every 2 years."
