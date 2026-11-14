# 1125 — Le 15 competency questions sono il gold

- **Stato:** in vigore
- **Quando:** 2026-11-14 11:25 (commit «data: 15 competency questions with gold answers, written before building»), registrata alle 11:35
- **Chi:** Prodotto, da rivedere con Core
- **Contesto:** la track chiede 10–20 domande scritte prima di costruire, con il punteggio ottenuto su di esse.
- **Decisione:** `data/cq/cqs.json` contiene 15 domande (10 di schema, 2 di versione, 3 sulla fabbrica) con risposta attesa, citazioni dai testi ufficiali e termini attesi nel formato CQ4OE. La fabbrica di fantasia è definita nello stesso file. Le domande le cambia solo Prodotto, con commit nuovi `gold:`; `tests/test_cqs.py` controlla ogni citazione e ricalcola le risposte sulla fabbrica.
- **Perché:** il commit delle 11:25, fatto prima di qualsiasi estrattore, dimostra che le domande sono venute prima. Le citazioni verificate evitano un gold sbagliato, che renderebbe inutile qualsiasi punteggio.
- **Alternative scartate:** scrivere le domande dopo aver visto l'ontologia (punteggio gonfiato); usare solo il benchmark CQ4OE (non copre il nostro dominio; resta un confronto esterno opzionale).
- **Sostituisce:** —
