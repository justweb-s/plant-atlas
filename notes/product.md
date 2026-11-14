# Note di Prodotto

_Aggiornato: 11:25_

## Fatto
- Repo creato con regole (`AGENTS.md`), contratto (`atlas/contracts.py`, `atlas/api.py`), dati finti e app Streamlit minima. Prova: `ATLAS_FAKE=1 streamlit run app/streamlit_app.py`
- **15 competency questions** con risposta attesa, citazioni e termini attesi: `data/cq/cqs.json`. Prova: `python -m pytest -q tests/test_cqs.py` (ogni citazione è cercata nel testo ufficiale).
- **Testi di legge** in `data/law/` (Reg. 2023/1230, rettifica del 4/7/2023, D.Lgs. 81/08 artt. 69–73). Fonti e comandi di download in `data/law/SOURCES.md`.
- Visione per la track ontologia: `docs/VISION-ontology.md`.

## In corso
- Riunione su `docs/VISION-ontology.md` §1, poi video e abstract (entro le 12:30).

## Mi serve da te
- 11:25 — Rivedi le 15 domande in `data/cq/cqs.json` e soprattutto le risposte attese: chi le cambia, le cambia con un commit nuovo (mai amend) prima del primo estrattore.
- 11:25 — I fatti della fabbrica (`plant` in `cqs.json`) sono la specifica dei documenti di fantasia: le risposte di CQ13–CQ15 dipendono da lì.

## Bloccato
