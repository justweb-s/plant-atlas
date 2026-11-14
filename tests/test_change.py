"""Owner: Core. A changed document: proposed changes, the world before and after, nothing deleted. No network."""
from datetime import date
from pathlib import Path

import pytest

from atlas.ontology import build, change

ROOT = Path(__file__).resolve().parents[1]
CORRIGENDUM = ROOT / "data/law/eu-reg-2023-1230-corrigendum-2023-07-04.en.xhtml"
DAY = date(2026, 11, 14)


@pytest.fixture(autouse=True)
def state_folder(tmp_path, monkeypatch):
    """Decisions go to a temporary folder, never to ontology/B/changes/."""
    monkeypatch.setattr(change, "CHANGES_DIR", tmp_path / "changes")
    build.store_for.cache_clear()
    yield
    build.store_for.cache_clear()


def repeal_dates(store) -> list[str]:
    return [s.object for s in store.as_of(DAY)
            if s.status == "current" and s.subject == "Directive 2006/42/EC" and s.predicate == "repealedFrom"]


def test_corrigendum_yields_nine_changes_with_their_passage():
    changeset = change.propose_change(CORRIGENDUM)
    assert len(changeset.changes) == 9
    assert len({c.id for c in changeset.changes}) == 9
    for c in changeset.changes:
        assert c.kind == "modify" and c.quote.strip() and c.locator.startswith("Corrigendum, point")
        assert c.before and c.after and c.before != c.after
        assert c.before in c.quote and c.after in c.quote
    assert changeset.id == change.propose_change(CORRIGENDUM).id
    repeal = next(c for c in changeset.changes if c.id == "corr-5")
    assert (repeal.before, repeal.after) == ("14 January 2027", "20 January 2027")
    assert repeal.target == "Directive 2006/42/EC · repealedFrom"


def test_before_and_after_and_nothing_deleted():
    changeset = change.propose_change(CORRIGENDUM)
    before, after = change.store_before(changeset), change.store_after(changeset)
    assert repeal_dates(before) == ["2027-01-14"]
    assert repeal_dates(after) == ["2027-01-20"]
    total = len(build.raw_store("B").statements)
    assert len(before.statements) == len(after.statements) == total
    assert sum(s.status == "proposed" for s in before.statements) == 9
    assert before.path is None and after.path is None       # a view cannot be saved over the store


def test_rejecting_one_change_keeps_the_old_value_current():
    changeset = change.propose_change(CORRIGENDUM)
    accepted = [c.id for c in changeset.changes if c.id != "corr-5"]
    result = change.apply_change(changeset, accepted)
    assert result.strategy == "B" and result.human_decisions >= 9
    store = build.store_for("B")
    assert repeal_dates(store) == ["2027-01-14"]
    assert len(store.statements) == len(build.raw_store("B").statements)
    corrected = next(s for s in store.statements if s.source_doc == "CORR" and s.anchor == "Corrigendum, point 5")
    assert corrected.status == "proposed"
    assert sum(s.source_doc == "CORR" and s.status == "current" for s in store.statements) == 8
    reloaded = {c.id: c.status for c in change.propose_change(CORRIGENDUM).changes}
    assert reloaded["corr-5"] == "rejected" and set(reloaded.values()) == {"accepted", "rejected"}
    change.apply_change(changeset, accepted + ["corr-5"])    # a decision can be taken back
    assert repeal_dates(build.store_for("B")) == ["2027-01-20"]


def test_default_state_is_the_store_as_built():
    raw = build.raw_store("B")
    assert build.store_for("B") is raw
    assert repeal_dates(raw) == ["2027-01-20"]
    changeset = change.propose_change(CORRIGENDUM)
    assert {c.status for c in changeset.changes} == {"accepted"}
    after = change.store_after(changeset)
    assert [s.model_dump() for s in after.statements] == [s.model_dump() for s in raw.statements]
    change.reopen(changeset)
    assert repeal_dates(build.store_for("B")) == ["2027-01-14"]
    change.forget(changeset)
    assert build.store_for("B") is raw


def test_build_result_counts():
    result = build.build_result("B")
    assert result.proposed >= result.anchored > 0
    assert result.proposed == result.anchored + result.rejected


def test_rows_of_two_versions(tmp_path):
    old, new = tmp_path / "old.txt", tmp_path / "new.txt"
    old.write_text("Title of the annex\n\n1. Ladders | Yearly check\n2. Cranes | Yearly check\n3. Hoists | Every two years\n",
                   encoding="utf-8")
    new.write_text("Title of the annex\n\n1. Ladders | Yearly check\n2. Cranes | Every two years\n3. Lifts | Yearly check\n",
                   encoding="utf-8")
    changeset = change.propose_rows(old, new)
    kinds = {c.kind: c for c in changeset.changes}
    assert sorted(c.kind for c in changeset.changes) == ["add", "modify", "remove"]
    assert kinds["modify"].before == "2. Cranes | Yearly check" and kinds["modify"].after == "2. Cranes | Every two years"
    assert kinds["modify"].quote == "2. Cranes | Every two years" and kinds["modify"].locator == "row 4"
    assert kinds["add"].quote == "3. Lifts | Yearly check" and kinds["add"].before is None
    assert kinds["remove"].quote == "3. Hoists | Every two years" and kinds["remove"].after is None
    assert change.propose_rows(old, old).changes == []
