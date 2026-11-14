# Note di Prodotto

_Aggiornato: 12:50_

## Fatto
- **Repo pubblico:** https://github.com/justweb-s/plant-atlas. Clona e lancia una volta `git config core.hooksPath .githooks`.
- **Nuova versione (decisione `1200-due-regimi-catalogo`):** il problema è il passaggio dalla Direttiva 2006/42/CE al Regolamento 2023/1230. Esempio verificato: un ponte sollevatore oggi autocertificato dal 20/1/2027 avrà bisogno di un organismo notificato.
- **20 competency questions** in `data/cq/cqs.json`: 15 di progetto e 5 tenute da parte (CQ16–CQ20). Ogni citazione è controllata sul testo ufficiale da `tests/test_cqs.py`.
- **Catalogo di fantasia** (5 modelli: SL-30, CS-400, PR-80, RC-5, TC-200) nel blocco `catalogue` di `cqs.json`: è la specifica delle schede prodotto da scrivere in `data/catalogue/`.
- **Testi di legge** in `data/law/`: Direttiva 2006/42/CE, Reg. 2023/1230, rettifica, D.Lgs. 81/08 artt. 69–73.
- **Punteggio** (`evaluation/score.py`): punteggi separati per domande di progetto e tenute da parte. App in modalità finta: `streamlit run app/streamlit_app.py`.

## In corso
- Video e abstract, entro le 12:30.
- Poi schede prodotto del catalogo, baseline RAG (`evaluation/rag.py`) e tabellone reale.

## Mi serve da te
- 12:50 — Il video racconta l'RSPP: ho scritto `docs/decisions/1250-rspp-un-solo-motore.md` (proposta). Il tuo registro dei fatti diventa il motore della strategia B, con export Turtle + SHACL. Confermala o correggila prima di continuare.
- 12:50 — Trappola trovata nel tuo DM: art. 2 c. 1 dice 60 giorni per la prima verifica INAIL, l'art. 71 c. 11 vigente dice 45. Ottimo caso per `make_current` e `as_of`.
- 12:50 — Risposta alla tua domanda: sì, `api.corpus()` restituisce i `Chunk` e il registro resta interno a Core. Serve che `register.py` legga anche i `.xhtml` dei testi UE.
- 12:50 — Per i prossimi commit usa l'email noreply di GitHub: il repo è pubblico.
- 12:05 — Leggi `docs/decisions/1200-due-regimi-catalogo.md`: cambia il problema e la domanda della demo, non l'architettura. Se non sei d'accordo, scrivi una decisione che la sostituisce.
- 12:05 — La strategia B legge solo le domande con `split: design`. Le CQ16–CQ20 non vanno mai lette dal codice in `atlas/`: un test lo controlla.
- 12:05 — Il corpus ora include `data/law/eu-dir-2006-42.en.xhtml` (Direttiva): va chunkato come il Regolamento.

## Bloccato
- Manca `.env` con la chiave del team: va presa da `/me` («Show the key»).
