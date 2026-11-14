# 1445 — L'app è in Next.js, sopra un piccolo server Python

- **Stato:** in vigore
- **Quando:** 2026-11-14 14:45
- **Chi:** Prodotto
- **Contesto:** il cervello è in Python (`atlas/`) e alle 14:08 Core ha reso reali `api.answer`, `api.build_ontology` e `api.validate`. Serve un'app da mostrare alla giuria e da pubblicare. Il team preferisce Next.js a Streamlit.
- **Decisione:**
  - **`web/` (Next.js 16, App Router, Tailwind):** tre viste, Chiedi, Tabellone e Ontologia. In Chiedi la risposta della strategia B è affiancata da RAG e A; ogni passo mostra la citazione e il punto del testo; c'è la scelta del giorno, per leggere i fatti in vigore in una data. Nel browser non c'è nessuna chiave.
  - **`server/main.py` (FastAPI):** l'unico ponte tra `web/` e il cervello. Importa solo `atlas.api`, `atlas.contracts` ed `evaluation/` (AGENTS.md §4). Next.js inoltra `/api/*` a `127.0.0.1:8000`.
  - **Quando una funzione non c'è ancora** (RAG, A, `propose_change`), l'app lo dice («non ancora costruito»). Quando una risposta non è nella cache e manca la chiave, l'app dice anche questo, senza rompersi.
  - **`app/streamlit_app.py` resta** solo come riserva in modalità finta; non lo si sviluppa più.
  - **`web/` e `server/` sono di Prodotto.**
- **Perché:** Next.js si pubblica facilmente ed è più curato per la giuria. Il ponte in Python evita di riscrivere il cervello e tiene la chiave solo lato server.
- **Alternative scartate:** Streamlit (scelta del team); chiamare i modelli da Next.js (si duplicherebbe `atlas/llm.py` e la sua cache).
- **Sostituisce:** in `1135-architettura`, l'app Streamlit.
