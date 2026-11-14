# I lavori da qui alle 16:45 (proposta delle 13:40)

Segue la decisione `docs/decisions/1315-caso-unico-cella-robotizzata.md`: un RSPP, una cella robotizzata di macchine reali, sei casi di prova, il registro dei fatti come motore. Il lavoro è diviso in **blocchi**, senza assegnarli. Ogni blocco ha i suoi file: chi lo prende ne è l'unico scrittore (AGENTS.md §2). Due blocchi che toccano gli stessi file vanno alla stessa persona.

Stato alle 13:40: `api.corpus()` è reale (4375 chunk, locator uguali al gold); registro dei fatti con test; 22 test passano; nessuna chiamata a un modello, perché manca `.env`.

## Prima di tutto (10 minuti, insieme)

- **0a. Confermare la 1315** e cambiare la riga «Stato» delle due 1250 (lo fa chi ha scritto ciascuna).
- **0b. `.env` con la chiave del team** su entrambe le macchine (da `/me`, «Show the key»). Blocca i blocchi 4, 6, 7 e 8.
- **0c. Un solo commit `contract:`** con le aggiunte della 1250-layout: `Chunk.sha256`, `Step.statement_id`, `BuildResult.proposed/anchored/rejected`, tutte con default. Lo fa una persona sola, con `atlas/fake.py` nello stesso commit.

## I blocchi

| # | Blocco | Uscita (cosa esiste quando è fatto) | File | Dipende da | Entro | Peso |
|---|---|---|---|---|---|---|
| 1 | **Macchine reali e manuali** | 4–5 macchine con modello, link al manuale pubblico, sha256, citazioni brevi; due manuali del braccio (vecchio e nuovo) con lo sbraccio citato | `data/machines/` (+ `SOURCES.md`) | — | 14:15 | M |
| 2 | **Scenario della cella** | una tabella: macchine, disposizione, misura delle zone protette, date di acquisto e ultima verifica; dichiarata come dato nostro | `data/scenario/` | 1 | 14:15 | S |
| 3 | **Gold: i sei casi** | casi 1–6 nel gold con risposta attesa e citazioni; CQ13–CQ15 e le tenute da parte riscritte sulle macchine reali; DM 11/4/2011 in `data/law/`; test verdi | `data/cq/`, `data/law/`, `tests/test_cqs.py` | 1, 2 | 14:30 | M |
| 4 | **Strategia B** | schema dalle domande `design` + classi IOF; estrazione a puntatore; secondo lettore; tutto passa da `write_statement()` | `atlas/strategies/`, `atlas/ontology/` | 0b, 0c | 15:00 | L |
| 5 | **Esportazione e vincoli** | Turtle a una data con `prov:wasDerivedFrom`, `validFrom`, `validTo`; forme SHACL, compreso il vincolo della zona protetta; `validate()` reale | `atlas/ontology/`, `ontology/` | 4 | 15:00 | M |
| 6 | **Agente** | `api.answer(question, as_of)` sui casi 2, 3, 5, 6; «non lo so» con `value=None` | `atlas/agent/` | 4 | 15:10 | M |
| 7 | **Documento che cambia** | `propose_change` / `apply_change` reali: la rettifica e la sostituzione del braccio | `atlas/ontology/`, `atlas/agent/` | 4, 1 | 15:40 | M |
| 8 | **Strategia A e conteggio dei rifiuti** | estrazione libera sui documenti delle domande; poi i suoi fatti passano dal controllo solo per contarli | `atlas/strategies/` | 0b, 4 | 16:00 | M |
| 9 | **RAG e tabellone** | baseline RAG reale su tutto il corpus; tabellone RAG / A / B con «non lo so» separato da «sbagliato» e le tenute da parte in una colonna a sé | `evaluation/`, `results/` | 0b, 3 | 15:00 | M |
| 10 | **App** | tab Chiedi e Modifiche sulle funzioni reali; modalità finta come riserva | `app/`, `atlas/fake.py` | 6, 7 | 15:40 | S |
| 11 | **Storia e consegna** | modello economico su Control8; script della demo (3 minuti); primo `pitch` pubblicato entro le 15:30 e ripubblicato alle 16:40; `8hack-check`; repo registrato; video di backup alle 16:15 | `pitch/`, Control8 | 6, 9 per i numeri | 16:45 | M |
| 12 | **Voce reale** | una mentor call (14:00–16:30) con le domande 13 e 14 di `INSIEME.md`; due frasi citate per il pitch | `notes/` | — | 15:30 | S |

Peso: S ≈ 30 minuti, M ≈ 1 ora, L ≈ 2 ore.

## Come stanno insieme

- **Percorso critico:** 0b → 4 → 5 e 6 → 7. Se il blocco 4 non estrae nulla entro le 14:45, il resto del motore slitta: è il blocco da proteggere.
- **In parallelo al motore:** 1 → 2 → 3 (i dati), 9 (la misura), 11 e 12 (la storia).
- **Blocchi che vanno alla stessa persona, perché toccano gli stessi file:** 4, 5 e 7 (`atlas/ontology/`); 4 e 8 (`atlas/strategies/`); 9 e 10 se si tocca `atlas/fake.py`.
- **Una divisione naturale** è in due corsie: **motore** (4, 5, 6, 7, 8) e **dati, misura e storia** (1, 2, 3, 9, 10, 11, 12). Le due corsie hanno lo stesso peso (circa 6 ore ciascuna). Si toccano solo nel contratto (0c) e nel gold (3, che il motore legge e non scrive).

## Attenzione

- **Le domande tenute da parte vanno scritte prima che B estragga.** Se il blocco 3 arriva dopo il 4, il confronto non vale più. Il blocco 3 va committato prima del primo run di B.
- **Le macchine reali sono il rischio di tempo più grande.** Se alle 14:15 il blocco 1 non ha i due manuali del braccio, i casi 1 e 4 escono (ordine dei tagli della 1315) e la demo usa la rettifica come documento che cambia.
- **Le classificazioni delle macchine reali** (quale va in Allegato I del Regolamento, cosa è quasi-macchina) entrano nel gold solo con la citazione: altrimenti restano [non verificato].
- **Il credito è di $25.** Prima di ogni run su tutto il corpus si scrive la stima delle chiamate nelle note.

## Ordine dei tagli (dalla 1315)

casi 1 e 4 → A su meno documenti → secondo lettore al minimo. Non si taglia: il cancello, la lettura a una data, i casi 2 e 6, il tabellone.
