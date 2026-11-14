# Note di Core

_Aggiornato: 12:30_

## Fatto
- **Registro dei fatti** in `atlas/ontology/statements.py`: un solo ingresso (`write_statement`), una sola uscita (`as_of`). Rifiuta e conta: citazione che non sta nel testo, valore che non sta nella citazione, condizione persa. Una versione nuova dello stesso documento chiude il fatto vecchio; tra fonti diverse vince l'autorità più alta (legge > manuale > procedura); niente viene cancellato. 6 test in `tests/test_statements.py`.
- **Registrazione del corpus** in `atlas/corpus/register.py`: taglia un testo in sezioni e scrive lo sha256 di ogni documento e sezione prima che qualcosa lo legga.
- **DM 11 aprile 2011** (verifiche periodiche, testo originario dalla Gazzetta Ufficiale) in `atlas/corpus/incoming/`: 6 articoli e 4 allegati, registrati.
- `notes/core-canvas.md`: il canvas di Core della mattina, prima di leggere la decisione 1200. Superato dal piano dove dicono cose diverse.
- Letta `1200-due-regimi-catalogo`: Core la segue. Le CQ16–CQ20 non sono state lette.

## In corso
- `atlas/corpus`: chunk per struttura di Regolamento, Direttiva, rettifica e D.Lgs. 81/08, esposti da `api.corpus()`.
- Poi strategia B sul registro dei fatti, export Turtle, agente su CQ09–CQ10 (la rettifica).

## Mi serve da te
- 12:30 — Il registro dei fatti legge un registro CSV con sha256 per sezione. Va bene se `api.corpus()` restituisce i `Chunk` e il registro resta interno a Core?
- 12:30 — `atlas/corpus/incoming/raw/dm-2011-04-11.md` è un testo di legge: se lo vuoi nel corpus, spostalo tu in `data/law/` e aggiungilo a `SOURCES.md`.
- 12:30 — Allegato VII del D.Lgs. 81/08: su Normattiva è «in formato grafico», non testo. È stato modificato dalla L. 11 marzo 2026, n. 34 (in vigore dal 7/4/2026) [verificato: Normattiva, letto oggi]: un secondo caso reale di documento che cambia, se serve.
- 12:30 — Su Control8 ho salvato un abstract (1179 caratteri) e caricato il video tagliato a 44,5 s: controlla che siano quelli giusti prima delle 12:40.

## Bloccato
- Manca `.env` con la chiave del team: nessuna chiamata a un modello finora.
