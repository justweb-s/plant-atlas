# 1410 — Due corsie: «dai documenti ai fatti» e «dalle domande alla prova»

- **Stato:** proposta di Core su indicazione del suo umano; Prodotto la conferma o la corregge
- **Quando:** 2026-11-14 14:10
- **Chi:** Core, da confermare con Prodotto
- **Contesto:** `docs/LAVORI.md` divide il lavoro in 12 blocchi senza assegnarli. Alle 14:00 il blocco 1 (macchine reali) è già fatto da Prodotto, e i blocchi 4, 5 e 6 (strategia B, esportazione, agente) hanno una prima versione di Core, pushata. L'umano di Core chiede di tenere per sé il lato documenti, su cui lavora da stamattina, così ognuno può concentrarsi su un flusso senza aspettare l'altro.

## Decisione

**Corsia 1 — Core: dai documenti ai fatti.** Tutto ciò che sta tra un documento e un fatto controllato.

| Cosa | Blocchi di `LAVORI.md` | File |
|---|---|---|
| I documenti dei quattro strati (legge, costruttore, azienda, stabilimento): trovarli, scaricarli, impronta, taglio in pezzi con un indirizzo | 2; del blocco 3 solo il DM 11/4/2011 e l'Allegato VII | `atlas/corpus/`, `data/law/`, `data/scenario/` |
| Lo scenario della cella: disposizione, zone protette, procedura interna, registro delle verifiche, dichiarati come dati nostri | 2 | `data/scenario/` |
| Strategia B, registro dei fatti, strati, vincoli, esportazione Turtle e SHACL | 4, 5 | `atlas/strategies/b.py`, `atlas/ontology/`, `ontology/` |
| Agente e documento che cambia | 6, 7 | `atlas/agent/`, `atlas/api.py` (solo il collegamento delle funzioni reali) |

**Corsia 2 — Prodotto: dalle domande alla prova.** Tutto ciò che misura, mostra e racconta.

| Cosa | Blocchi | File |
|---|---|---|
| Macchine reali (già fatto) | 1 | `data/machines/` |
| Gold: i sei casi, CQ13–CQ15 e le domande tenute da parte sulle macchine reali | 3 (senza i testi di legge) | `data/cq/`, `tests/test_cqs.py` |
| RAG e tabellone, con «non lo so» separato da «sbagliato» | 9 | `evaluation/`, `results/` |
| Strategia A e conteggio dei rifiuti: è la linea di confronto, quindi sta con la misura; usa `store.write_statement()` solo per contare | 8 | `atlas/strategies/a.py` (file nuovo, un solo scrittore) |
| App, storia, consegna, voce reale | 10, 11, 12 | `app/`, `pitch/`, Control8, `notes/` |

**I tre punti di contatto, e nient'altro:**
1. `api.corpus()` → i pezzi dei documenti, con fonte, indirizzo e strato. Lo scrive Core, lo legge Prodotto (RAG, strategia A).
2. `api.answer()`, `api.build_ontology()`, `api.validate()`, `api.propose_change()`, `api.apply_change()` → li scrive Core, li chiama Prodotto (tabellone, app).
3. `data/cq/cqs.json` → lo scrive Prodotto. Core legge solo le domande `design`; le altre mai.

**Cosa cambia rispetto ad `AGENTS.md` §2:** `data/law/` e `data/scenario/` passano a Core; `atlas/strategies/a.py` passa a Prodotto. `data/machines/` e `data/cq/` restano a Prodotto.

**Passaggi che una corsia deve all'altra, con l'ora:**
- Core → Prodotto, entro le 14:40: lo scenario in `data/scenario/` (serve ai casi 1, 3, 4 del gold) e `api.answer()` collegata.
- Prodotto → Core, prima che B legga i manuali: le domande tenute da parte sulle macchine reali, committate (`gold:`). Core non lancia B sui manuali prima di quel commit.
- Chi fa il commit `contract:` (0c di `LAVORI.md`): Core, entro le 14:30, con `atlas/fake.py` aggiornato nello stesso commit.

- **Perché:** ogni corsia ha i suoi file e può lavorare senza aspettare l'altra, tranne nei tre punti di contatto. La strategia A sta meglio con chi misura: è il confronto, non il prodotto, e alleggerisce la corsia del motore, che è il percorso critico.
- **Rischio dichiarato:** la corsia 1 resta la più pesante (documenti e motore). Se alle 15:00 il documento che cambia non funziona, lo scenario si riduce a una sola tabella e la procedura interna esce.
- **Alternative scartate:** la divisione di `LAVORI.md` (motore contro dati, misura e storia): lascia i documenti a chi non ci ha lavorato; tre corsie: siamo in due.
- **Sostituisce:** — . Assegna i blocchi di `docs/LAVORI.md`; modifica `AGENTS.md` §2 nei tre percorsi indicati.
