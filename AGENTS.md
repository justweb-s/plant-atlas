# Regole del repo (per persone e agenti)

Siamo in due, abbiamo circa 5 ore di sviluppo e nessun tempo per i conflitti. Queste regole valgono per noi **e per i nostri agenti di coding**: `CLAUDE.md` importa questo file, e Codex, Cursor e OpenCode leggono `AGENTS.md`.

## 1. Chi possiede cosa

Ognuno scrive **solo nelle sue cartelle**. Le cartelle dell'altro si leggono e basta.

| Cartella / file | Proprietario | Contenuto |
|---|---|---|
| `atlas/core/`, `atlas/reader/`, `atlas/vision/` | **Core** | statement, `write_statement`, `as_of`, regole di stato, log eventi, lettura documenti e foto |
| `app/`, `atlas/fake.py`, `data/`, `pitch/` | **Prodotto** | app Streamlit, dati finti per l'app, fabbrica/manuale/procedura/foto, slide e video |
| `notes/core.md` | Core | stato di Core (§4) |
| `notes/product.md` | Prodotto | stato di Prodotto (§4) |
| `atlas/contracts.py`, `atlas/api.py` | **condiviso** | il contratto tra i due lati (§2) |
| `requirements.txt`, `tests/`, `README.md`, `AI_TOOLS.md`, `docs/` | condiviso | solo aggiunte in fondo; niente riscritture dell'altro |

Se serve una modifica nella cartella dell'altro: **non farla**. Scrivila in "Mi serve da te" nel tuo file di note (§4) e dillo a voce.

## 2. Il contratto

- `atlas/contracts.py` definisce i tipi (`Statement`, `Answer`, `Step`, `Card`, `Verdict`). `atlas/api.py` definisce le uniche funzioni che l'app può chiamare.
- **L'app importa solo da `atlas.api` e `atlas.contracts`**, mai da `atlas.core` o da altri moduli interni.
- Con `ATLAS_FAKE=1` le funzioni di `api.py` restituiscono i dati di `atlas/fake.py`, così l'app funziona prima che il core sia pronto. Quando una funzione reale è pronta, Core la collega in `api.py` e lo scrive nelle note.
- **Cambiare il contratto** (nomi, campi, firme) richiede: 1) dirlo all'altro, 2) un commit dedicato con prefisso `contract:`, 3) aggiornare `atlas/fake.py` nello stesso commit, se il cambio lo rompe. Aggiungere un campo con valore di default è sempre permesso.

## 3. Git

- Si lavora **su `main`**, niente branch né PR: siamo in due e le cartelle sono separate.
- Prima di ogni push: `git pull --rebase`, poi `python -m pytest -q`, poi `git push`.
- **Commit piccoli e frequenti**, push almeno ogni 30–45 minuti. Il codice non pushato non esiste per l'altro.
- Prefissi dei messaggi: `core:`, `vision:`, `app:`, `data:`, `pitch:`, `contract:`, `docs:`, `notes:`.
- **Mai** `git push --force`, mai `git reset --hard` su commit già pushati, mai riscrivere la storia.
- Conflitto su un file condiviso: tieni entrambe le versioni se sono aggiunte; altrimenti fermati e chiedi.

## 4. Come ci passiamo le informazioni

Ognuno tiene aggiornato **solo il proprio** file in `notes/` (una sola scrittura per file, quindi nessun conflitto). Va aggiornato a ogni push che cambia qualcosa per l'altro:

```
## Fatto            — cosa funziona davvero, e come provarlo (un comando)
## In corso         — cosa sto facendo adesso
## Mi serve da te   — richieste all'altro, una per riga, con l'orario
## Bloccato         — cosa mi ferma
```

- Le cose urgenti si dicono **a voce**. Il file serve perché anche l'agente dell'altro le legga.
- Prima di iniziare un nuovo pezzo, leggi il file di note dell'altro (`git pull` e poi aprilo).
- **Gli agenti:** a inizio sessione leggono `notes/` e `docs/PLAN.md`; a fine lavoro aggiornano il file di note del proprio umano, mai quello dell'altro.

## 5. Punti di sincronizzazione (ora di Roma)

| Ora | Cosa decidiamo insieme |
|---|---|
| 10:30 | track, idea, contratto in `atlas/contracts.py` congelato nella forma base |
| 12:15 | test delle foto (almeno 4 date giuste su 5?) e cosa promettiamo nel video |
| 15:00 | stato dei Must; alle 15:30 si decide cosa tagliare |
| 16:00 | feature freeze: solo bug fix |
| 16:15 | code freeze, tag `demo`, video di backup |

## 6. Sicurezza e regole dell'evento

- **Segreti:** la chiave sta solo in `.env`, che è in `.gitignore`. Mai in codice, note, log o screenshot. Se finisce in un commit: dirlo subito agli organizzatori, che la revocano. Riscrivere la storia non basta.
- **La chiave del team è solo per il prodotto**, non per gli agenti di coding.
- **Il repo è pubblico** (regole §11): niente nomi di persone (solo i ruoli Core e Prodotto), niente codice o schermate delle nostre aziende, niente manuali con copyright, niente foto di persone o di fabbriche reali.
- **Tutto è costruito oggi** (regole §7). Ogni modello o strumento AI usato, anche per generare i dati, va aggiunto ad `AI_TOOLS.md`.

## 7. Qualità minima

- Python 3.11. Niente nuove dipendenze senza aggiungerle a `requirements.txt` e dirlo all'altro.
- `tests/` contiene le 5 domande di test: devono girare in modalità finta da subito, e in modalità reale appena il core risponde.
- Una funzione che non trova un dato restituisce `unknown`, mai `blocked` o `allowed` per default.
