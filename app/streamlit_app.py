"""Owner: Product. Imports only atlas.api, atlas.contracts and Product's own modules (AGENTS.md §4)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st  # noqa: E402

from atlas import api  # noqa: E402
from evaluation import rag  # noqa: E402
from evaluation import score as ev  # noqa: E402

st.set_page_config(page_title="Plant Atlas", layout="wide")
st.title("Plant Atlas")
st.caption("An ontology built from documents, measured on questions written before building it, "
           "kept current when a document changes.")
if api.fake_mode():
    st.warning("Fake mode (ATLAS_FAKE=1): nothing on this page is a real result.")

CQS = ev.load_cqs()
MODES = {
    "RAG": lambda q: rag.answer(q),
    "A · free": lambda q: api.answer(q, "A"),
    "B · guided": lambda q: api.answer(q, "B"),
}


def mark(s: float) -> str:
    return "✓" if s == 1.0 else ("~" if s > 0 else "✗")


def safe(fn, *args):
    """Run a contract function; if it is not built yet, say so instead of crashing the demo."""
    try:
        return fn(*args), None
    except NotImplementedError as e:
        return None, f"not built yet: {e}"


board, ask, onto, changes = st.tabs(["Scoreboard", "Ask", "Ontology", "Changes"])

with board:
    st.write("The 15 competency questions, written before building, answered by each approach.")
    if st.button("Compute the scoreboard"):
        results, errors = {}, {}
        for name, fn in MODES.items():
            results[name], errors[name] = safe(ev.run, fn)
        table = []
        for i, cq in enumerate(CQS):
            row = {"CQ": cq["id"], "type": cq["type"], "split": cq["split"], "question": cq["question_en"]}
            for name in MODES:
                row[name] = mark(results[name][i]["score"]) if results[name] else "—"
            table.append(row)
        st.dataframe(table, hide_index=True)
        for col, name in zip(st.columns(len(MODES)), MODES):
            if results[name]:
                s = ev.summary(results[name])
                col.metric(name, f'{s["correct"]}/{s["n"]}',
                           help=f'mean {s["mean"]} · held-out {s["by_split"].get("heldout", 0.0)} · by type {s["by_type"]}')
            else:
                col.metric(name, "—", help=errors[name])

with ask:
    labels = [f'{c["id"]} · {c["question_en"]}' for c in CQS]
    pick = st.selectbox("Question", labels, index=12)
    cq = CQS[labels.index(pick)]
    for col, name in zip(st.columns(2), ("RAG", "B · guided")):
        a, err = safe(MODES[name], cq["question_en"])
        if err:
            col.subheader(name)
            col.info(err)
            continue
        col.subheader(f"{name} {mark(ev.score(cq, a.value))}")
        col.write(a.text)
        for step in a.steps:
            with col.expander(step.text):
                if step.locator:
                    st.write(f"**{step.locator}**")
                if step.quote:
                    st.code(step.quote, language=None)
                if step.sparql:
                    st.code(step.sparql, language="sparql")
    st.caption(f'Expected: {cq["answer_text"]}')

with onto:
    strategy = st.radio("Strategy", ["A", "B"], index=1, horizontal=True)
    path = api.ontology_file(strategy)
    if path.exists():
        st.download_button("Download the Turtle file", path.read_bytes(), file_name=path.name)
        st.code(path.read_text(encoding="utf-8")[:4000], language="turtle")
    else:
        st.info(f"{path.relative_to(api.ROOT).as_posix()} does not exist yet: Core's pipeline writes it.")
    report, err = safe(api.validate, strategy)
    if err:
        st.info(err)
    else:
        st.write("SHACL:", "conforms" if report.conforms else f"{len(report.violations)} violations")
        for v in report.violations:
            st.write("-", v)

with changes:
    doc = st.text_input("New or changed document", "data/law/eu-reg-2023-1230-corrigendum-2023-07-04.en.xhtml")
    if st.button("Propose the changes"):
        cs, err = safe(api.propose_change, api.ROOT / doc)
        st.session_state["changeset"] = cs
        if err:
            st.info(err)
    cs = st.session_state.get("changeset")
    if cs:
        accepted = []
        for ch in cs.changes:
            if st.checkbox(f"{ch.kind} · {ch.target}: {ch.before} → {ch.after}", value=True, key=ch.id):
                accepted.append(ch.id)
            st.caption(f"{ch.locator}: “{ch.quote}”")
        if st.button("Apply the accepted changes"):
            result, err = safe(api.apply_change, cs, accepted)
            if err:
                st.info(err)
            else:
                st.success(f"New version of ontology {result.strategy}: {len(accepted)} changes accepted, "
                           f"{result.human_decisions} human decisions.")
