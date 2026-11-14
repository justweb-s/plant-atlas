# 1135 — Il repo come cervello della squadra

- **Stato:** in vigore
- **Quando:** 2026-11-14, registrata alle 11:35
- **Chi:** Core + Prodotto
- **Contesto:** due persone e due agenti scrivono nello stesso repo per cinque ore. È il problema della challenge: molti agenti che scrivono nella stessa memoria senza contraddirsi, e il bisogno di sapere perché si è deciso qualcosa.
- **Decisione:** valgono le regole di `AGENTS.md`. Ogni file ha un solo scrittore; c'è un file di note per ruolo; ogni decisione è un file che non si modifica ma si sostituisce; il contratto cambia solo con commit `contract:` e il gold solo con commit `gold:`; un hook pre-commit blocca chiavi e test rotti.
- **Perché:** con un solo scrittore per file i conflitti di git non possono nascere. Con le decisioni scritte come file nuovi nessuno sovrascrive il perché di un altro. Gli agenti leggono le stesse regole e le stesse note a inizio sessione, quindi sanno cosa ha fatto l'altro.
- **Alternative scartate:** un solo file di note condiviso (conflitti a ogni push); decidere solo a voce (gli agenti non lo sanno e il perché si perde).
- **Sostituisce:** la versione di `AGENTS.md` delle 10:36
