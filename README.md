# Plant Atlas

An ontology built from a company's documents, measured on questions written before building it, and kept current when a document changes.

First domain: machine safety. The corpus is Regulation (EU) 2023/1230 on machinery, its corrigendum of 4 July 2023 and the Italian D.Lgs. 81/2008 on work equipment, plus a small fictional plant. Built on 14 November 2026 at the KVA Hackathon "AI brain for industry", track "Building an ontology from a knowledge base".

## What it does

1. Reads the documents and splits them by their own structure: article, paragraph, annex point.
2. Builds the ontology with two strategies and scores both on the same 15 competency questions:
   - **A**, free extraction with no schema;
   - **B**, guided by the questions and by the structure of the law, aligned with the Industrial Ontologies Foundry (IOF) and checked with SHACL constraints.
3. Answers questions through the ontology (SPARQL), and compares the answers with plain retrieval (RAG).
4. When a document changes, proposes the changes to the ontology. Each change is linked to the passage that caused it, and a person accepts or rejects it.

Example: the Regulation as published says it applies from 14 January 2027. A corrigendum (OJ L 169, 4.7.2023) changes the date to 20 January 2027. Retrieval over the published text gives the old date; the ontology knows the corrigendum replaces it.

## Run

```bash
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env          # macOS/Linux: cp .env.example .env — then put the key in .env
git config core.hooksPath .githooks
python -m pytest -q
streamlit run app/streamlit_app.py
```

With `ATLAS_FAKE=1` (the default in `.env.example`) the app runs on fake data, clearly marked, without the brain or a model key.

## Layout

| Path | What |
|---|---|
| `data/cq/cqs.json` | the 15 competency questions with their gold answers, written before building |
| `data/law/` | the official law texts (sources in `data/law/SOURCES.md`) |
| `atlas/contracts.py`, `atlas/api.py` | the contract between the brain and the app |
| `atlas/llm.py` | the only door to the models, with a committed cache |
| `atlas/corpus/`, `atlas/strategies/`, `atlas/ontology/`, `atlas/agent/` | the brain |
| `ontology/` | the generated ontologies (Turtle, SHACL shapes, versions) |
| `evaluation/` | scoring against the gold, and the RAG baseline |
| `app/` | the Streamlit app: scoreboard, ask, ontology, changes |

## How we work

- [AGENTS.md](AGENTS.md): the rules for people and coding agents.
- [docs/decisions/](docs/decisions/): what we decided, and why.
- [notes/](notes/): who is doing what right now.
- [docs/PLAN.md](docs/PLAN.md): the plan.
- [AI_TOOLS.md](AI_TOOLS.md): the models and AI tools we used.

## Licence

To be chosen by the team.
