# Regole del repo: il cervello della squadra

Questo repo lo scrivono due persone, Core e Prodotto, e i loro agenti di coding. È una memoria condivisa con più scrittori: lo stesso problema che il nostro prodotto risolve. Usiamo quindi gli stessi principi.

| Nel prodotto | Nel repo |
|---|---|
| ogni fatto ha una fonte | ogni decisione ha il suo perché; ogni commit ha un prefisso che dice di cosa si tratta |
| un fatto superato si chiude, non si cancella | una decisione superata resta dov'è, con «Stato: superata da …» |
| due scrittori non si sovrascrivono | ogni file ha un solo scrittore; i file condivisi si cambiano solo aggiungendo |
| i vincoli bloccano i dati sbagliati | il pre-commit blocca chiavi in chiaro e test rotti |
| domande scritte prima misurano il risultato | `data/cq/cqs.json` è il gold, controllato dai test |

Le regole valgono per le persone e per gli agenti. `CLAUDE.md` importa questo file; Codex, Cursor e OpenCode leggono `AGENTS.md`.

## 1. Chi sei

- Ogni sessione di un agente lavora per **un solo ruolo**, Core o Prodotto. Se non lo sai, chiedilo al tuo umano prima di scrivere qualsiasi file.
- **Core** costruisce il cervello: corpus e chunking, strategie A e B, ontologia, vincoli, diff, agente che risponde.
- **Prodotto** costruisce ciò che lo misura e lo mostra: domande e gold, dati, baseline RAG, valutazione, app, video, pitch, modello economico.

## 2. Chi scrive dove

| Percorso | Chi scrive | Note |
|---|---|---|
| `atlas/corpus/`, `atlas/strategies/`, `atlas/ontology/`, `atlas/agent/` | Core | |
| `ontology/` | Core | file generati dalla pipeline (`.ttl`, shapes, `build.json`, modifiche): si committano |
| `evaluation/`, `app/`, `atlas/fake.py`, `results/` | Prodotto | |
| `data/` (`cq/`, `law/`, `catalogue/`), `pitch/` | Prodotto | `data/cq/cqs.json` è il gold (§5) |
| `notes/core.md` | Core | |
| `notes/product.md` | Prodotto | |
| `atlas/contracts.py`, `atlas/api.py`, `atlas/llm.py` | condivisi | il contratto (§4) |
| `docs/decisions/` | entrambi | solo file nuovi (§3) |
| `cache/llm/` | entrambi | solo file nuovi; i nomi sono hash, quindi niente conflitti |
| `docs/PLAN.md` | entrambi | si cambia solo insieme a una decisione |
| `tests/`, `requirements.txt`, `README.md`, `AI_TOOLS.md` | entrambi | solo aggiunte |

Dalle 14:20 vale la decisione `1410-due-corsie`: `data/law/` e `data/scenario/` sono di Core, `atlas/strategies/a.py` è di Prodotto.

La cartella dell'altro si legge, non si scrive. Se serve una modifica lì, chiedila in «Mi serve da te» nelle tue note e dillo a voce.

## 3. La memoria della squadra

- **Note, la memoria di lavoro:** `notes/<ruolo>.md` con quattro sezioni (Fatto, In corso, Mi serve da te, Bloccato) e l'ora dell'ultimo aggiornamento. Le scrive solo il proprietario, quindi non entrano mai in conflitto.
- **Decisioni, la memoria lunga:** un file per decisione in `docs/decisions/`, con nome `HHMM-argomento.md` e il modello di `TEMPLATE.md`.
  - Una decisione accettata non si modifica. Se si cambia idea, si scrive una decisione nuova con «Sostituisce: …»; nella vecchia si cambia solo la riga «Stato».
  - L'indice è l'elenco dei file (`ls docs/decisions`): non c'è un file indice da tenere aggiornato.
  - Quando gli umani decidono qualcosa a voce, l'agente lo registra come decisione, con il perché.
- **Registro, cioè `git log`:** prefissi `core:` · `ontology:` · `eval:` · `app:` · `data:` · `gold:` · `contract:` · `decision:` · `docs:` · `notes:` · `pitch:`.

## 4. Il contratto

- `atlas/contracts.py` (tipi), `atlas/api.py` (funzioni) e `atlas/llm.py` (unica porta ai modelli) sono l'unico punto di contatto tra Core e Prodotto. `evaluation/` e `app/` importano solo da questi tre file e dai file di Prodotto.
- Con `ATLAS_FAKE=1`, `api.py` restituisce i dati di `atlas/fake.py`: Prodotto lavora prima che il cervello sia pronto. Quando una funzione reale funziona, Core la collega in `api.py` e lo scrive nelle sue note.
- Per cambiare il contratto: un commit dedicato `contract:`, con `atlas/fake.py` aggiornato nello stesso commit se il cambio lo rompe, e l'altro avvisato. Aggiungere un campo con un valore di default è sempre permesso.

## 5. Il gold e la misura

- `data/cq/cqs.json` (20 domande, risposte attese, citazioni, fatti del catalogo) è stato committato prima di qualsiasi estrattore: le prime 12 domande alle 11:25, le altre e il catalogo alle 12:00. È la prova che le domande sono venute prima.
- Le domande con `split: heldout` (CQ16–CQ20) le legge solo `evaluation/`. Il codice in `atlas/` usa solo quelle con `split: design`: se vedesse le altre, il confronto tra strategie non varrebbe più. Lo controlla `tests/test_cqs.py`.
- Lo cambia solo Prodotto, con un commit nuovo `gold:` che dice perché. Mai `--amend`, mai riscrivere la storia.
- `tests/test_cqs.py` deve passare: ogni citazione deve esistere nel testo ufficiale.
- Nessuno ritocca il gold per far salire un punteggio. Se una risposta attesa è sbagliata, la si corregge con la sua fonte e si rifanno girare tutte le strategie.

## 6. Modelli e credito

- Ogni chiamata a un modello passa da `atlas/llm.py`. Usa la chiave del team e salva ogni risposta in `cache/llm/`, che si committa: chi rilancia la stessa chiamata non paga, e la demo funziona anche senza wifi (`ATLAS_OFFLINE=1`).
- Il credito è di $25 per tutta la squadra. Prima di un run su tutto il corpus, stima quante chiamate fa e scrivilo nelle tue note. Mai cicli senza un limite.
- La chiave del team serve solo al prodotto. Gli agenti di coding usano il proprio abbonamento.
- I test non chiamano mai la rete: modalità finta o cache.

## 7. Git

- Tutti su `main`. Prima di ogni push: `git pull --rebase`, poi `python -m pytest -q`, poi `git push`.
- Commit piccoli, push ogni 30–45 minuti: quello che non è pushato non esiste per l'altro.
- Mai `push --force`. Mai `reset --hard` o `commit --amend` su commit già pushati.
- Conflitto durante il rebase su un file che non è tuo: `git rebase --abort` e chiedi. Su un file condiviso dove si aggiunge soltanto: tieni entrambe le parti.
- Una volta per ogni clone: `git config core.hooksPath .githooks`. Il pre-commit blocca i file `.env`, le chiavi in chiaro e i test rotti.

## 8. Protocollo di sessione per gli agenti

**All'inizio**
1. `git pull --rebase`
2. Leggi le note dell'altro ruolo e le decisioni più recenti (`ls docs/decisions`).
3. `python -m pytest -q`
4. Conferma con il tuo umano il ruolo e il compito.

**Durante**
- Scrivi solo nelle tue cartelle; un commit per ogni passo che funziona.
- Nei documenti e nel pitch ogni fatto porta un marcatore: [verificato: fonte] · [dichiarato] · [non verificato].

**Alla fine**
1. Aggiorna le tue note, con l'ora.
2. Registra le decisioni prese.
3. Test, commit, `git pull --rebase`, `git push`.

## 9. Sicurezza e regole dell'evento

- `.env` non va mai in git. La chiave non va mai in codice, note, log, cache o screenshot. Se finisce in un commit, va detto subito agli organizzatori, che la revocano: riscrivere la storia non basta.
- Il repo è pubblico (regole §11): niente nomi di persone (solo i ruoli Core e Prodotto), niente codice o schermate delle nostre aziende, niente testi coperti da copyright (le norme armonizzate si citano solo per codice), niente foto di persone.
- Tutto è costruito oggi (regole §7). Ogni modello o strumento AI usato va in `AI_TOOLS.md`.

## 10. Orari (Roma)

| Ora | Cosa |
|---|---|
| 12:15 | la track si blocca |
| 12:30 | video e abstract caricati (Control8 chiude alle 12:40) |
| 13:30 | si sa chi continua |
| 15:00 | tabellone completo; alle 15:30 si decide cosa tagliare |
| 16:00 | feature freeze; aggiornare `8hack-check` |
| 16:15 | code freeze; video di backup della demo |
| 16:30 | validazione finanziaria |
| 16:45 | pitch pubblicato (genere `pitch`) e repo registrato |
