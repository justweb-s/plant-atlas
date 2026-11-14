# 1135 — Architettura: due strategie, file Turtle, una sola porta ai modelli

- **Stato:** in vigore
- **Quando:** 2026-11-14, registrata alle 11:35
- **Chi:** Core + Prodotto
- **Contesto:** servono due strategie confrontabili, un file di ontologia vero e un credito di $25 da non sprecare.
- **Decisione:**
  - Strategia A: estrazione libera, senza schema. Strategia B: schema ricavato dalle domande, estrazione guidata, allineamento a IOF, vincoli SHACL. Stesso corpus, stesse domande, stesso modello. In più una baseline RAG (Prodotto, `evaluation/rag.py`).
  - L'ontologia vive in file Turtle in `ontology/<strategia>/`, versionati in git, letti e scritti con rdflib, pySHACL e owlrl. Niente Neo4j né SQLite.
  - Ogni chiamata a un modello passa da `atlas/llm.py`, che salva le risposte in `cache/llm/`; la cache si committa.
  - La memoria visiva (foto) esce dal Must.
- **Perché:** il confronto è equo e misurabile. Il file si apre in Protégé e si importa in altre piattaforme. Con una versione per commit il diff tra versioni non costa nulla. La cache condivisa evita di pagare due volte e permette la demo senza wifi. Questa track non premia le foto.
- **Alternative scartate:** Neo4j (setup e deploy più fragili); un grafo senza schema come unico risultato (è una delle trappole citate dalla track).
- **Sostituisce:** le parti «SQLite», «decision model» e «foto» di `docs/archive/PLAN-plant-atlas-v2.md`
