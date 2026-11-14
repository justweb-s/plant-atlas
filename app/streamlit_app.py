"""Owner: Product. Imports only from atlas.api and atlas.contracts (AGENTS.md §2)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st  # noqa: E402

from atlas import api  # noqa: E402

st.set_page_config(page_title="Plant Atlas", layout="wide")
st.title("Plant Atlas")

COLORS = {"green": "🟢", "orange": "🟠", "grey": "⚪", "red": "🔴"}

ask, atlas_tab, blackbox = st.tabs(["Ask", "Atlas", "Black box"])

with ask:
    q = st.text_input("Question", "Can a line operator run press P-3 today?")
    photo = st.file_uploader("Photo from the floor (optional)", type=["jpg", "jpeg", "png"])
    if st.button("Ask"):
        if photo is not None:
            st.caption(f"Read {len(api.ingest_photo(Path(photo.name)))} facts from the photo")
        a = api.answer(q)
        st.subheader(f"{a.label.upper()} — {a.text}")
        for i, step in enumerate(a.steps, 1):
            with st.expander(f"{i}. {step.text}"):
                if step.source is not None:
                    where = f"page {step.source.page}" if step.source.type == "page" else "photo"
                    st.write(f"**{step.source.doc_id}**, {where}")
                if step.quote:
                    st.code(step.quote)

with atlas_tab:
    for card in api.atlas_cards():
        st.markdown(f"### {COLORS[card.color]} {card.machine} — {card.headline}")
        for r in card.reasons + card.changed_sources:
            st.write(f"- {r}")

with blackbox:
    st.write("Chain intact" if api.verify_chain() else "Chain BROKEN")
    for v in api.verdicts():
        st.markdown(f"**{v.decided_at:%Y-%m-%d %H:%M}** · {v.question} → **{v.label}**")
        st.caption(f"rules: {', '.join(v.rules)} · facts: {', '.join(v.statement_ids)} · model: {v.model}")
