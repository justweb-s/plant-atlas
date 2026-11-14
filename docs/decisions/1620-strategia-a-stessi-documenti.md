# 1620 — Strategia A: estrazione libera sugli stessi documenti di B, lanciata una volta sola

- **Stato:** in vigore
- **Quando:** 2026-11-14 16:20
- **Chi:** Prodotto
- **Contesto:** la colonna «Estrazione libera» del tabellone diceva «non costruito»: senza A non si può mostrare quanto valgono lo schema e il controllo delle citazioni di B. Il credito è limitato ($25 per la squadra).
- **Decisione:** `atlas/strategies/a.py` legge **gli stessi 1080 pezzi** che B ha letto (legge con rettifica, DM 2011, Allegato VII, pagine selezionate dei manuali, linee guida, elenco IGEA). Il modello scrive i fatti come vuole: nessuno schema, parole sue, citazione scelta da lui. Tutti i fatti entrano. `Store.write_statement()` si usa solo per contare quanti fatti i controlli di B avrebbero rifiutato. Le risposte usano lo stesso agente di B. Lanciata una volta sola: 1080 chiamate, circa 0,48 $; le risposte sono in `cache/llm/`.
- **Perché:** il confronto è onesto solo se A e B leggono lo stesso testo e rispondono con lo stesso agente: cambia soltanto il modo di estrarre.
- **Alternative scartate:** A su un sottoinsieme di documenti (più economico, ma il confronto non vale); A sul corpus intero di 5105 pezzi (5 volte il costo, e B non li ha letti).
- **Sostituisce:** —
