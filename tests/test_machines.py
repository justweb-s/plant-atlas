"""The real machines: structure, no copyrighted files in git, no people's names (rules §11)."""
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = json.loads((ROOT / "data" / "machines" / "machines.json").read_text(encoding="utf-8"))


def test_every_fact_points_to_a_known_document_with_a_short_quote():
    docs = {d["id"] for d in SPEC["documents"]}
    for d in SPEC["documents"]:
        assert re.fullmatch(r"[0-9a-f]{64}", d["sha256"]) and d["url"].startswith("https://")
    for m in SPEC["machines"]:
        for f in m["facts"]:
            assert f["doc"] in docs
            assert 0 < len(f["quote"].split()) <= 25, "short quotes only: the manuals are copyrighted"


def test_no_manual_is_tracked_by_git():
    tracked = subprocess.run(["git", "ls-files", "data/machines"], cwd=ROOT, capture_output=True, text=True).stdout
    assert ".pdf" not in tracked


def test_no_names_of_people():
    text = (ROOT / "data" / "machines" / "machines.json").read_text(encoding="utf-8")
    for word in ("Brandt", "Kerkmeier", "Geigle"):  # names printed in the declarations
        assert word not in text
