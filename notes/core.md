# Note di Core

_Aggiornato: 13:19_

## Fatto
- **Registro dei fatti** in `atlas/ontology/statements.py`: un solo ingresso (`write_statement`), una sola uscita (`as_of`). Rifiuta e conta: citazione che non sta nel testo, valore che non sta nella citazione, condizione persa. Una versione nuova dello stesso documento chiude il fatto vecchio; tra fonti diverse vince l'autorità più alta (legge > manuale > procedura); niente viene cancellato. 6 test in `tests/test_statements.py`.
- **Registrazione del corpus** in `atlas/corpus/register.py`: taglia un testo in sezioni e scrive lo sha256 di ogni documento e sezione prima che qualcosa lo legga.
- **DM 11 aprile 2011** (verifiche periodiche, testo originario dalla Gazzetta Ufficiale) in `atlas/corpus/incoming/`: 6 articoli e 4 allegati, registrati.
- `notes/core-canvas.md`: il canvas di Core della mattina, prima di leggere la decisione 1200. Superato dal piano dove dicono cose diverse.
- Letta `1200-due-regimi-catalogo`: Core la segue. Le CQ16–CQ20 non sono state lette.

- **12:42 — 16 atti UE per una fabbrica** scaricati dall'Ufficio delle pubblicazioni e registrati in `atlas/corpus/incoming/` (17 documenti con il DM, 1098 sezioni con sha256): attrezzature di lavoro 2009/104, luoghi di lavoro 89/654, DPI 89/656 e 2016/425, movimentazione carichi 90/269, segnaletica 92/58, cancerogeni 2004/37, emissioni industriali 2010/75, Seveso III 2012/18, EMC 2014/30, ascensori 2014/33, ATEX 2014/34, bassa tensione 2014/35, attrezzature a pressione 2014/68, sicurezza generale dei prodotti 2023/988, IA 2024/1689. Richiesti dal mio umano. Cinque direttive più vecchie danno 404 in XHTML (89/391, 2003/10, 2002/44, 1999/92, 98/24).

## In corso
- `atlas/corpus`: chunk per struttura di Regolamento, Direttiva, rettifica e D.Lgs. 81/08, esposti da `api.corpus()`.
- Poi strategia B sul registro dei fatti, export Turtle, agente su CQ09–CQ10 (la rettifica).

## Mi serve da te
- 12:30 — Il registro dei fatti legge un registro CSV con sha256 per sezione. Va bene se `api.corpus()` restituisce i `Chunk` e il registro resta interno a Core?
- 12:30 — `atlas/corpus/incoming/raw/dm-2011-04-11.md` è un testo di legge: se lo vuoi nel corpus, spostalo tu in `data/law/` e aggiungilo a `SOURCES.md`.
- 12:30 — Allegato VII del D.Lgs. 81/08: su Normattiva è «in formato grafico», non testo. È stato modificato dalla L. 11 marzo 2026, n. 34 (in vigore dal 7/4/2026) [verificato: Normattiva, letto oggi]: un secondo caso reale di documento che cambia, se serve.
- 12:30 — Su Control8 ho salvato un abstract (1179 caratteri) e caricato il video tagliato a 44,5 s: controlla che siano quelli giusti prima delle 12:40.

- 12:42 — I 16 atti UE sono in `incoming/` perché `data/` è tuo. Nessuna domanda del gold li riguarda: per la ricerca semplice sono rumore realistico; per il punteggio servono domande nuove, se le vuoi scrivere (`gold:`).

- 13:19 — **Leggi `docs/decisions/1315-caso-unico-cella-robotizzata.md`**: unisce le due 1250 (il tuo RSPP + macchine reali in una cella robotizzata + i sei casi di prova, con il tuo 60/45 giorni come caso 6). Se sei d'accordo cambia la riga «Stato» della tua 1250 e la mia 1315; se no, scrivi cosa cambia.
- 13:19 — Fatto: da ora i commit di Core usano l'email noreply. I primi quattro hanno l'indirizzo vecchio: la storia non si riscrive (AGENTS.md §7), decidete voi due se va bene così.
- 13:19 — `register.py` legge già gli `.xhtml`/`.html` dei testi UE (li ha scaricati lui). Il chunk dei testi del gold dietro `api.corpus()` è il prossimo commit.

## Bloccato
- Manca `.env` con la chiave del team: nessuna chiamata a un modello finora.
