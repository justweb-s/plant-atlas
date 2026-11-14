# Note di Prodotto

_Aggiornato: 11:45_

## Fatto
- **15 competency questions** con risposte attese, citazioni e termini attesi: `data/cq/cqs.json`, committate alle 11:25. Prova: `python -m pytest -q tests/test_cqs.py` (ogni citazione viene cercata nel testo ufficiale).
- **Testi di legge** in `data/law/`: Reg. 2023/1230, rettifica del 4/7/2023, D.Lgs. 81/08 artt. 69–73. Fonti in `data/law/SOURCES.md`.
- **Repo organizzato per la track ontologia:** regole in `AGENTS.md`, decisioni in `docs/decisions/`, piano in `docs/PLAN.md`, contratto nuovo in `atlas/contracts.py` e `atlas/api.py`, unica porta ai modelli con cache in `atlas/llm.py`.
- **Punteggio:** `evaluation/score.py` (il gold prende 1.0, le trappole 0). App con 4 tab in modalità finta: `streamlit run app/streamlit_app.py`.

## In corso
- Video e abstract, entro le 12:30.
- Poi baseline RAG (`evaluation/rag.py`) e tabellone reale.

## Mi serve da te
- 11:45 — Leggi `docs/decisions/` e il contratto nuovo (`atlas/contracts.py`, `atlas/api.py`). Se qualcosa non va, scrivi una decisione che lo sostituisce.
- 11:45 — Rivedi le 15 domande in `data/cq/cqs.json`.
- 11:45 — Una volta sola, nel tuo clone: `git config core.hooksPath .githooks`.

## Bloccato
- Manca `.env` con la chiave del team: va presa da `/me` («Show the key»).
