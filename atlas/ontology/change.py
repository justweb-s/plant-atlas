"""Owner: Core. A changed document becomes a list of proposed changes, each with the passage that caused it.

Two kinds of document are read here, both by code (no model call):
- a corrigendum ("for: 'X', read: 'Y'"): one change per corrected fact of the store;
- a new version of a row-per-line text: rows are compared by fingerprint (add / remove / modify).

A decision (accepted / rejected) is kept in a small state file under ontology/B/changes/. The store is
never rewritten: `store_before` and `store_after` are views (copies of the statements with status and
`in_force_to` adjusted), so nothing is deleted and every decision can be undone.
With no state file every correction counts as accepted, which is the store as it was built.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from atlas.contracts import BuildResult, Change, ChangeSet

ROOT = Path(__file__).resolve().parents[2]
CHANGES_DIR = ROOT / "ontology" / "B" / "changes"   # one state file per changeset; tests point this elsewhere
CORRECTED_BY = "strategy_b:corrigendum"
STATUSES = ("proposed", "accepted", "rejected")


# ---- identity and state ---------------------------------------------------
def changeset_id(document: Path) -> str:
    """Stable for the same document: its name and the fingerprint of its bytes."""
    path = Path(document)
    slug = re.sub(r"[^a-z0-9]+", "-", path.stem.lower()).strip("-")[:40]
    return f"{slug}-{hashlib.sha256(path.read_bytes()).hexdigest()[:8]}"


def _state_path(changeset_id_: str) -> Path:
    return CHANGES_DIR / f"{changeset_id_}.json"


def read_state(changeset_id_: str) -> dict[str, str]:
    """Change id -> status, as last decided. Empty when nothing was decided yet."""
    path = _state_path(changeset_id_)
    if not path.exists():
        return {}
    return dict(json.loads(path.read_text(encoding="utf-8")).get("decisions", {}))


def write_state(changeset: ChangeSet, decisions: dict[str, str]) -> Path:
    CHANGES_DIR.mkdir(parents=True, exist_ok=True)
    path = _state_path(changeset.id)
    payload = {"id": changeset.id, "document": changeset.document, "decisions": decisions}
    path.write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")
    return path


def all_decisions() -> dict[str, str]:
    """Every decision recorded in the state folder (change id -> status)."""
    merged: dict[str, str] = {}
    if CHANGES_DIR.exists():
        for path in sorted(CHANGES_DIR.glob("*.json")):
            merged.update(json.loads(path.read_text(encoding="utf-8")).get("decisions", {}))
    return merged


# ---- the corrected facts of the store -------------------------------------
def pairs(store) -> dict[str, tuple[str, str]]:
    """Change id -> (id of the fact as published, id of the corrected fact). Read from the store itself."""
    out: dict[str, tuple[str, str]] = {}
    for s in store.statements:
        if s.asserted_by != CORRECTED_BY or not s.conflicts_with:
            continue
        point = re.search(r"(\d+)\s*$", s.anchor)
        base = f"corr-{point.group(1)}" if point else f"corr-{s.id}"
        key, n = base, 1
        while key in out:
            n += 1
            key = f"{base}-{n}"
        out[key] = (s.conflicts_with, s.id)
    return out


def view(store, applied: dict[str, bool]):
    """A copy of the store in which each correction is applied or not. Same number of statements.

    Applied: the published fact is closed on the day the correction took effect, the corrected one is current.
    Not applied: the published fact is current again, the corrected one is kept as "proposed".
    """
    from atlas.ontology.statements import Store

    copy = Store(store.corpus, None)   # no path: a view is never saved over statements.json
    copy.statements = [s.model_copy() for s in store.statements]
    copy.rejections = list(store.rejections)
    by_id = {s.id: s for s in copy.statements}
    for change_id, (old_id, new_id) in pairs(store).items():
        old, new = by_id.get(old_id), by_id.get(new_id)
        if old is None or new is None:
            continue
        if applied.get(change_id, True):
            old.status, old.in_force_to = "closed", new.in_force_from
            new.status = "current"
        else:
            old.status, old.in_force_to = "current", None
            new.status = "proposed"
    return copy


def current_view(store):
    """The store as the recorded decisions leave it. With no decision it is the store itself."""
    decisions = all_decisions()
    known = pairs(store)
    undone = {cid for cid, status in decisions.items() if cid in known and status != "accepted"}
    if not undone:
        return store
    return view(store, {cid: cid not in undone for cid in known})


def _base():
    from atlas.ontology import build

    return build.raw_store("B")


def _applied_elsewhere(changeset: ChangeSet, store) -> dict[str, bool]:
    """Decisions of the other changesets, so a view of this one does not undo them."""
    own = {c.id for c in changeset.changes}
    return {cid: status == "accepted" for cid, status in all_decisions().items()
            if cid in pairs(store) and cid not in own}


def store_before(changeset: ChangeSet):
    """The world before the document: none of its changes applied (published facts current)."""
    store = _base()
    applied = _applied_elsewhere(changeset, store)
    applied.update({c.id: False for c in changeset.changes})
    return view(store, applied)


def store_after(changeset: ChangeSet, accepted: list[str] | None = None):
    """The world after the document: only the accepted changes applied (all of them when `accepted` is None)."""
    store = _base()
    applied = _applied_elsewhere(changeset, store)
    applied.update({c.id: accepted is None or c.id in accepted for c in changeset.changes})
    return view(store, applied)


# ---- proposing ------------------------------------------------------------
def _is_corrigendum(document: Path) -> bool:
    if "corrigendum" in document.name.lower():
        return True
    if document.suffix.lower() not in (".xhtml", ".html", ".xml"):
        return False
    return "read:" in document.read_text(encoding="utf-8", errors="ignore")


def propose_corrigendum(document: Path) -> ChangeSet:
    """One change per corrected fact. The quote is the corrigendum's own point, read from `document`."""
    from atlas.corpus import chunker

    document = Path(document)
    source, _, version = chunker.CORRIGENDUM
    points = {c.locator: c.text for c in chunker.corrigendum(source, document, version)}
    store = _base()
    by_id = {s.id: s for s in store.statements}
    cs_id = changeset_id(document)
    state = read_state(cs_id)
    changes = []
    for change_id, (old_id, new_id) in pairs(store).items():
        old, new = by_id[old_id], by_id[new_id]
        if new.anchor not in points:     # this document does not carry that correction
            continue
        changes.append(Change(
            id=change_id, kind="modify", target=f"{new.subject} · {new.predicate}",
            before=old.object_as_written, after=new.object_as_written,
            locator=new.anchor, quote=points[new.anchor],
            status=state.get(change_id, "accepted")))   # no decision yet: the store has it applied
    return ChangeSet(cs_id, str(document), changes)


def _row_key(row: str) -> str:
    """What a row is about: the words before the first '|', without the row number."""
    head = row.split("|", 1)[0]
    return re.sub(r"^\s*\d+[.)]\s*", "", head).strip().casefold()


def _rows(path: Path) -> list[tuple[int, str]]:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return [(n, re.sub(r"\s+", " ", line).strip()) for n, line in enumerate(lines, start=1) if line.strip()]


def _fingerprint(row: str) -> str:
    return hashlib.sha256(row.encode("utf-8")).hexdigest()


def propose_rows(old_version: Path, new_version: Path) -> ChangeSet:
    """Two versions of a row-per-line text, compared by the fingerprint of each row.

    A row whose fingerprint is in both versions is unchanged. Of the others, a row about the same thing
    (same words before '|') is a modify; the rest are removes (old only) and adds (new only).
    """
    old_rows, new_rows = _rows(old_version), _rows(new_version)
    old_prints = {_fingerprint(r) for _, r in old_rows}
    new_prints = {_fingerprint(r) for _, r in new_rows}
    gone = [(n, r) for n, r in old_rows if _fingerprint(r) not in new_prints]
    came = [(n, r) for n, r in new_rows if _fingerprint(r) not in old_prints]
    gone_by_key: dict[str, list[tuple[int, str]]] = {}
    for n, r in gone:
        gone_by_key.setdefault(_row_key(r), []).append((n, r))
    cs_id = changeset_id(new_version)
    state = read_state(cs_id)
    changes: list[Change] = []

    def add(kind, target, before, after, line, quote) -> None:
        change_id = f"row-{kind}-{_fingerprint(quote)[:8]}"
        changes.append(Change(change_id, kind, target, before, after, f"row {line}", quote,
                              state.get(change_id, "proposed")))

    for n, row in came:
        rivals = gone_by_key.get(_row_key(row))
        if rivals:
            _, old_row = rivals.pop(0)
            add("modify", row.split("|", 1)[0].strip(), old_row, row, n, row)
        else:
            add("add", row.split("|", 1)[0].strip(), None, row, n, row)
    for rivals in gone_by_key.values():
        for n, row in rivals:
            add("remove", row.split("|", 1)[0].strip(), row, None, n, row)
    return ChangeSet(cs_id, str(new_version), changes)


def propose_change(document: Path) -> ChangeSet:
    """A new or changed document: the proposed changes to ontology B, each with its passage."""
    document = Path(document)
    if not document.exists():
        raise FileNotFoundError(document)
    if _is_corrigendum(document):
        return propose_corrigendum(document)
    # A new version of a text already in the corpus (same file name under data/): compare the rows.
    known = [p for p in (ROOT / "data").rglob(document.name) if p.resolve() != document.resolve()]
    if known:
        return propose_rows(known[0], document)
    return ChangeSet(changeset_id(document), str(document), [])


# ---- deciding -------------------------------------------------------------
def apply_change(changeset: ChangeSet, accepted: list[str]) -> BuildResult:
    """Record the decision; from now on store_for("B") answers with only the accepted changes applied."""
    from atlas.ontology import build

    decisions = {c.id: ("accepted" if c.id in accepted else "rejected") for c in changeset.changes}
    write_state(changeset, decisions)
    for change in changeset.changes:
        change.status = decisions[change.id]
    build.store_for.cache_clear()
    result = build.build_result("B")
    result.human_decisions += len(changeset.changes)
    return result


def reopen(changeset: ChangeSet) -> None:
    """Put every change of the set back to "proposed" (not applied): the world before the document."""
    from atlas.ontology import build

    write_state(changeset, {c.id: "proposed" for c in changeset.changes})
    for change in changeset.changes:
        change.status = "proposed"
    build.store_for.cache_clear()


def forget(changeset: ChangeSet) -> None:
    """Remove the state file: back to the store as built (every correction applied)."""
    from atlas.ontology import build

    _state_path(changeset.id).unlink(missing_ok=True)
    build.store_for.cache_clear()
