# Note di Core

_Aggiornato: 14:58_

## Fatto
- **Registro dei fatti** in `atlas/ontology/statements.py`: un solo ingresso (`write_statement`), una sola uscita (`as_of`). Rifiuta e conta: citazione che non sta nel testo, valore che non sta nella citazione, condizione persa. Una versione nuova dello stesso documento chiude il fatto vecchio; tra fonti diverse vince l'autorità più alta (legge > manuale > procedura); niente viene cancellato. 6 test in `tests/test_statements.py`.
- **Registrazione del corpus** in `atlas/corpus/register.py`: taglia un testo in sezioni e scrive lo sha256 di ogni documento e sezione prima che qualcosa lo legga.
- **DM 11 aprile 2011** (verifiche periodiche, testo originario dalla Gazzetta Ufficiale) in `atlas/corpus/incoming/`: 6 articoli e 4 allegati, registrati.
- `notes/core-canvas.md`: il canvas di Core della mattina, prima di leggere la decisione 1200. Superato dal piano dove dicono cose diverse.
- Letta `1200-due-regimi-catalogo`: Core la segue. Le CQ16–CQ20 non sono state lette.

- **12:42 — 16 atti UE per una fabbrica** scaricati dall'Ufficio delle pubblicazioni e registrati in `atlas/corpus/incoming/` (17 documenti con il DM, 1098 sezioni con sha256): attrezzature di lavoro 2009/104, luoghi di lavoro 89/654, DPI 89/656 e 2016/425, movimentazione carichi 90/269, segnaletica 92/58, cancerogeni 2004/37, emissioni industriali 2010/75, Seveso III 2012/18, EMC 2014/30, ascensori 2014/33, ATEX 2014/34, bassa tensione 2014/35, attrezzature a pressione 2014/68, sicurezza generale dei prodotti 2023/988, IA 2024/1689. Richiesti dal mio umano. Cinque direttive più vecchie danno 404 in XHTML (89/391, 2003/10, 2002/44, 1999/92, 98/24).

- **13:31 — `api.corpus()` è reale** (`atlas/corpus/chunker.py`): 4375 chunk per struttura. Regolamento 579, Direttiva, rettifica 14 punti, D.Lgs. 81/08 per comma, più i 16 atti UE di `incoming/`. Locator come nel gold: `Art. 25(2)`, `Art. 3(16)`, `Annex III, 1.3.7`, `Annex I, Part A, point 5`, `Corrigendum, point 5`, `art. 71, c. 11`. `tests/test_corpus.py`: ogni citazione delle domande di progetto sta nell'articolo o nell'allegato indicato. Con `ATLAS_FAKE=0` il RAG può già girare su tutto il corpus. `passage(source, locator)` dà il testo intero di un articolo o allegato.

- **14:05 — strategia B, esportazione e agente pushati** (blocchi 4, 5, 6 in prima versione). Run completo: 773 passaggi, 1668 fatti proposti, 1602 ancorati, 66 rifiutati, 9 corretti dalla rettifica; `ontology/B/ontology.ttl` 13.963 triple, SHACL trova 5 violazioni vere; costo circa 0,36 dollari. Punteggio sulle 12 domande di progetto sulla legge: 7,72. La CQ10 è sbagliata (risponde «no»): i fatti corretti ci sono, l'errore è nel passo di risposta. Il secondo lettore non c'è ancora. Le domande tenute da parte già committate alle 12:00 non sono state lette.

- **14:17 — il corpus ha due strati**: 5067 pezzi, 4386 di legge e 681 del costruttore. I tuoi quattro manuali sono tagliati per pagina (`ur5e-manual`, `ur10e-manual`, `nanoscan3-manual`, `mastar-manual`, locator `p. N`, testo da pdftotext se c'è, altrimenti pypdf); le tue 17 citazioni si ritrovano tutte in una pagina. Il DM 11/4/2011 è nel corpus come `DM2011` (`art. 2, c. 1`: «sessanta giorni»). Ogni `Chunk` ha `layer` e `sha256` (commit `contract:` fatto, con default). I manuali compaiono solo se i PDF sono sulla macchina: `python data/machines/fetch.py`.

- **14:35 — cinque strati, tutti con documenti reali**: 5195 pezzi. Legge 4415 (ora anche l'Allegato VII, una riga per pezzo, 29 righe con le condizioni di tipo, settore ed età, e il DM in `data/law/`). Indicazioni di enti pubblici 58 (`inail-guide`, `robot-cell-sheet`: la scheda «Isola robotizzata» dice che l'area va delimitata tenendo conto della massima estensione delle macchine: è la regola della zona). Costruttore 681. Azienda 32 (`unict-guideline`, `univpm-guideline`: linee guida reali sulla gestione delle attrezzature). Stabilimento 9 (`igea-equipment`: l'elenco reale dei 24 apparecchi di sollevamento di IGEA S.p.A., area mineraria di Monteponi, con tipo, portata, matricola INAIL e anno di costruzione; **senza** date di ultima verifica). Registro in `atlas/corpus/incoming/documents.csv` (link, impronta, strato); i PDF stanno in `runtime/docs/`, fuori da git.

- **14:58 — sei lavori in parallelo, cinque finiti e pushati:**
  - **Fatti dagli altri strati** (`ontology/B/parts/`): costruttore 481 fatti correnti (i tuoi 4 manuali; 15 delle tue 17 citazioni ritrovate: mancano la dichiarazione CE del MA STAR e la sua data), indicazioni 144, azienda 111, stabilimento 73 (i 24 apparecchi reali di IGEA), più Allegato VII (39 fatti, per codice) e DM 11/4/2011. Costo circa 0,30 dollari.
  - **La domanda guida ha risposta:** `atlas/ontology/rules.py` → `verification_interval(device, annex_facts, on)` sceglie la riga dell'Allegato VII per tipo, portata, settore ed età: 23 apparecchi su 24 decisi (quasi tutti annuali; il carroponte del 2017 biennale), il 24 «non lo so». Ipotesi dichiarate: gru su autocarro e autogru = mobili; carroponte, cavalletto e paranchi = fissi; settore estrattivo per tutti.
  - **60 contro 45 giorni:** il fatto del DM è `conflict` verso quello dell'art. 71 c. 11.
  - **Documento che cambia:** `api.propose_change(Path(rettifica))` dà 9 modifiche con citazione; `api.apply_change(cs, accepted)`; per il prima/dopo `atlas.ontology.change.store_before(cs)` / `store_after(cs, accepted)` e `change.reopen(cs)` per partire dal «prima».
  - **Strati:** ogni fatto ha `layer`; ordine fine dentro la legge; `settle(a, b)` dà chi vince e perché; nel Turtle `pa:layer` e il vincolo della zona protetta (SHACL-SPARQL).
  - **Secondo lettore** (`atlas/ontology/verify.py`, modello diverso dall'estrattore): 345 fatti riletti, 228 passano, 117 tornano indietro (87 condizione persa, 23 non detto dal testo, 7 incerti). Non ancora applicato alle risposte: prima misuro il punteggio con e senza. Costo 1,16 dollari.
  - **Registro delle fonti:** `atlas/corpus/incoming/chunks_registry.csv`, 5195 pezzi con impronta.

## In corso
- Correzione del passo di risposta (CQ10 e le domande «quali») e una pagina che mostra il grafo e come cambia nel tempo (`ontology/B/view.html`).
- **13:41 — run completo della strategia B** su Regolamento, Direttiva e D.Lgs. 81/08 (773 passaggi, senza i considerando). Stima scritta prima di lanciare: 773 chiamate a `anthropic/claude-haiku-5.5`, circa 0,65 M token in ingresso e 0,85 M in uscita, cioè meno di 1 dollaro ai prezzi del gateway (0,10 e 0,50 dollari per milione). La pilota su 12 passaggi: 39 fatti proposti, 37 ancorati, 2 rifiutati; la rettifica chiude 8 fatti e ne apre 8 corretti (es. abrogazione della Direttiva dal 14 al 20/1/2027).
- Strategia B sul registro dei fatti, export Turtle, agente su CQ09–CQ10 (la rettifica).

## Mi serve da te
- 12:30 — Il registro dei fatti legge un registro CSV con sha256 per sezione. Va bene se `api.corpus()` restituisce i `Chunk` e il registro resta interno a Core?
- 12:30 — `atlas/corpus/incoming/raw/dm-2011-04-11.md` è un testo di legge: se lo vuoi nel corpus, spostalo tu in `data/law/` e aggiungilo a `SOURCES.md`.
- 12:30 — Allegato VII del D.Lgs. 81/08: su Normattiva è «in formato grafico», non testo. È stato modificato dalla L. 11 marzo 2026, n. 34 (in vigore dal 7/4/2026) [verificato: Normattiva, letto oggi]: un secondo caso reale di documento che cambia, se serve.
- 12:30 — Su Control8 ho salvato un abstract (1179 caratteri) e caricato il video tagliato a 44,5 s: controlla che siano quelli giusti prima delle 12:40.

- 12:42 — I 16 atti UE sono in `incoming/` perché `data/` è tuo. Nessuna domanda del gold li riguarda: per la ricerca semplice sono rumore realistico; per il punteggio servono domande nuove, se le vuoi scrivere (`gold:`).

- 13:19 — **Leggi `docs/decisions/1315-caso-unico-cella-robotizzata.md`**: unisce le due 1250 (il tuo RSPP + macchine reali in una cella robotizzata + i sei casi di prova, con il tuo 60/45 giorni come caso 6). Se sei d'accordo cambia la riga «Stato» della tua 1250 e la mia 1315; se no, scrivi cosa cambia.
- 13:19 — Fatto: da ora i commit di Core usano l'email noreply. I primi quattro hanno l'indirizzo vecchio: la storia non si riscrive (AGENTS.md §7), decidete voi due se va bene così.
- 13:19 — `register.py` legge già gli `.xhtml`/`.html` dei testi UE (li ha scaricati lui). Il chunk dei testi del gold dietro `api.corpus()` è il prossimo commit.

- 14:05 — **Leggi `docs/decisions/1410-due-corsie.md`** (proposta): Core tiene i documenti dei quattro strati e il motore; a te gold, RAG, tabellone, strategia A, app e storia. Le tue macchine in `data/machines/` restano tue e le uso così come sono. Dimmi sì o no: finché non rispondi non scrivo in `data/`.
- 14:05 — Ho scaricato anche UR10e, UR20 e microScan3 (`atlas/corpus/incoming/manuals.csv`): doppione parziale dei tuoi, li tengo come riserva e non li estraggo.
- 14:05 — Non lancio B sui manuali finché le domande tenute da parte sulle macchine reali non sono committate.

- 14:08 — **COMPITO PER TE, il più urgente: una demo che gira per davvero (POC) il prima possibile.** Con `ATLAS_FAKE=0` nel tuo `.env` ora sono reali: `api.corpus()`, `api.build_ontology("B")` (legge `ontology/B/`, non rilancia l'estrazione), `api.validate("B")` (5 violazioni SHACL vere) e `api.answer(domanda, "B", as_of)` (risponde dai fatti, ogni passo ha citazione e punto del testo, `value=None` se non ci sono fatti). Tutte le risposte dei modelli sono in `cache/llm/`: fai `git pull` e non paghi niente per ciò che è già stato chiesto. Quello che ci serve vedere: (1) la tab «Chiedi» che chiama `api.answer` e mostra i passi con le citazioni; (2) il tabellone con B reale; (3) il file Turtle e il risultato SHACL. `propose_change`, `apply_change` e la strategia A danno ancora `NotImplementedError`: lasciali in modalità finta o nascondili. Dimmi cosa si rompe e lo sistemo subito.

- 14:35 — **Proposta per il gold: il caso IGEA come caso principale.** «Per ciascuno dei 24 apparecchi di IGEA: ogni quanto va verificato, da chi, ed entro quanti giorni dalla richiesta?» La risposta incrocia la riga giusta dell'Allegato VII (tipo fisso o mobile, settore estrattivo, più o meno di 10 anni) con tipo e anno dell'elenco IGEA. «È scaduto oggi?» resta «non lo so»: le date non ci sono. La cella robotizzata resta la seconda scena. La scheda IGEA cita l'art. 71 c. 11 «modificato dalla Legge 98 del 9 agosto 2013»: probabile risposta alla tua domanda su chi ha portato il termine da 60 a 45 giorni [non verificato sul testo della legge].
- 14:35 — Per vedere questi pezzi sulla tua macchina servono i PDF in `runtime/docs/`: gli indirizzi sono in `documents.csv`. Se vuoi, aggiungo uno script che li scarica come il tuo `fetch.py`.

- 14:58 — **Onestà sulla misura:** l'estrazione sugli strati nuovi è partita prima che esistessero domande tenute da parte su quei documenti. Se le scrivi ora, scrivile dai documenti e non dai fatti in `ontology/B/parts/`, e il tabellone dovrebbe dirlo.

## Bloccato
- Manca `.env` con la chiave del team: nessuna chiamata a un modello finora.
