> **Superato** alle 11:35 dalla decisione `docs/decisions/1115-track-ontologia.md`. Resta qui come storia: le sue idee di memoria (citazioni, validità, ordine di autorità) vivono nel piano nuovo, `docs/PLAN.md`.

# Plant Atlas v2 — piano per il 14 novembre 2026

> Revisione del piano di Core. Adattata a regole, orari e criteri reali dell'evento, con la memoria visiva aggiunta.
> Ruoli: **Core** = motore, estrazione, memoria · **Prodotto** = app, demo, video, business case.
> Nel repo pubblico e nel pitch: solo ruoli, nessun nome (regole §11).

---

## 1. In una frase

**Il registro di sicurezza delle macchine che si controlla da solo.** Legge leggi, manuali e procedure, guarda le foto scattate in reparto e dice per ogni macchina se oggi si può usare. Ogni risposta indica la pagina o la foto che la prova, e ogni decisione resta registrata.

## 2. Il problema (reale)

- Dal **20 gennaio 2027** si applica il Regolamento Macchine UE 2023/1230. Il D.Lgs. 81/08 (Titolo III, art. 71 e All. VII) impone già controlli periodici sulle attrezzature di lavoro e la loro registrazione.
- Oggi le aziende usano Excel e carta, e **la carta e il reparto non coincidono**. Il registro dice "ispezionata", ma sulla macchina l'etichetta è scaduta o la protezione è stata tolta. Le procedure interne contraddicono il manuale e nessuno se ne accorge.
- Durante un'ispezione o dopo un infortunio bisogna dimostrare **cosa si sapeva e quando**. Oggi è quasi impossibile.
- Chi ha il problema: l'**RSPP / responsabile HSE** di aziende manifatturiere tra 50 e 250 dipendenti, e i **consulenti di sicurezza** che seguono molte di queste aziende.

## 3. La memoria visiva: cosa aggiunge (e cosa no)

Una **foto è una fonte**, allo stesso livello di una pagina. Dalla foto il sistema estrae **fatti osservati**:

| Dalla foto di… | Fatto estratto | A cosa serve |
|---|---|---|
| Targhetta della macchina | modello, matricola, anno, marcatura CE | identifica la macchina e la collega al manuale e alle regole giuste |
| Etichetta di verifica | data dell'ultima verifica, ente | confronta con il registro: carta contro reparto |
| Protezioni e cartelli | presenti / assenti / non visibili | blocca la macchina se manca un requisito |

Tre comportamenti nuovi, tutti costruiti sul core già previsto:
1. **Carta contro reparto.** Il registro dice 10/09, l'etichetta in foto dice 12/06: si apre un disaccordo e il verdetto diventa "sconosciuto, chiedi una verifica", non "sì".
2. **La memoria invecchia.** Un fatto osservato scade (ad esempio dopo 30 giorni) e la card diventa grigia: "da rifotografare". È il tipo *observed* già previsto nel piano v1.
3. **Citazione visiva.** La risposta mostra la foto e il testo letto, con data e ora dello scatto.

**Fuori scope oggi:** video, telecamere fisse, riconoscimento generico dei pericoli, persone nelle foto.

## 4. Come fa soldi

- **Chi paga:** l'azienda manifatturiera, tramite l'RSPP/HSE, con un abbonamento per stabilimento.
- **Canale:** i consulenti di sicurezza. Ognuno segue molti clienti e userebbe lo strumento su tutti: rivendono, oppure pagano una licenza da consulente.
- **Prezzi (ipotesi da validare, dichiarate come tali):**
  - stabilimento fino a 50 macchine: **€300/mese**
  - consulente: **€150/mese per ogni cliente gestito**
  - avvio: **€1.500** una tantum (caricamento documenti e prima ricognizione fotografica)
- **Perché pagano:** meno ore per tenere il registro, nessuna scadenza persa, e soprattutto **una prova difendibile** di cosa si sapeva e quando. L'urgenza la crea la scadenza del gennaio 2027.
- **Modello economico in Control8** (`/8hack economic-model`): una riga di ricavi (prezzo × stabilimenti), un canale (consulenti: costo per lead e conversione) e il payback. Le dimensioni del mercato si citano solo da fonte pubblica (es. Istat, imprese manifatturiere per dimensione); se manca la fonte, si scrive "da verificare".
- **Validazione oggi:** due conversazioni (un mentor e chiunque in sala abbia esperienza di fabbrica o di RSPP), da cui due frasi citate come prova.

## 5. Cosa costruiamo (circa 5 ore reali di sviluppo)

**Stack:** Python · **SQLite** (niente Neo4j: meno setup, deploy banale) · Streamlit su Streamlit Community Cloud · modelli via Vercel AI Gateway (un modello economico per il testo, uno con visione per le foto).

**Core (dal piano v1, semplificato):**

| # | Pezzo | Cosa è |
|---|---|---|
| 1 | **Statement** | soggetto, proprietà, valore, citazione, fonte (**pagina o foto**), tipo (persistente / datato / osservato), validità da-a, stato |
| 2 | **`write_statement()`** | unico ingresso: la citazione deve esistere nella fonte e i numeri devono stare nella citazione; poi conferma, sostituisce o apre un disaccordo. Non cancella mai, chiude. |
| 3 | **`as_of(data)`** | unica uscita: i fatti validi in una certa data |
| 4 | **Regole di stato** | scaduta, bloccata, da rifotografare: query calcolate al momento della domanda, mai salvate |
| 5 | **Log eventi** | solo append; la catena di hash si aggiunge se avanza tempo (circa 20 righe) |

| Priorità | Cosa |
|---|---|
| **Must, entro le 15:00** | lettura di regolamento, manuale e procedura · foto → fatti osservati (targhetta + etichetta) · una domanda end to end con citazioni di pagina **e** foto · contraddizione carta/foto → "sconosciuto" · nuova versione della procedura → card arancioni |
| **Should** | disaccordo risolto con la gerarchia delle fonti (legge > manuale > procedura) · tab Scatola nera · test di reset del contesto |
| **Solo slide ("next")** | simulatore di 12 mesi · skill compilate · curatore notturno · scoperta automatica di nuovi stati |

Decisione sui tagli alle **15:30**. Non si taglia mai: risposte citate, verdetto salvato, foto → fatto, arancione dopo un cambio di regola.

**App (3 tab):**
- **Chiedi:** chat con upload della foto; ogni passaggio si apre su citazione e pagina o foto.
- **Atlante:** una card per macchina. Verde = ok · arancione = da rileggere · grigio = manca o è da rifotografare · rosso = bloccata.
- **Scatola nera:** verdetti salvati con regole, fatti, modello e ora; replay a una certa data.

## 6. Dati (tutti preparati oggi o pubblici)

- Estratti pubblici: Reg. UE 2023/1230 (Allegato III) e D.Lgs. 81/08 Titolo III.
- Fabbrica di fantasia: 5 macchine e 4 ruoli. Manuale della pressa P-3 di **10–15 pagine**, in testo (non PDF scansionato), con la tabella di manutenzione. Procedura interna con un intervallo diverso dal manuale (90 giorni contro 60).
- **Foto:** stampiamo una targhetta e un'etichetta di verifica di fantasia, le attacchiamo a un oggetto in sala e le fotografiamo anche **dal vivo durante la demo**. Niente foto di fabbriche reali né di persone.
- 5 domande di test con risposta, citazione e pagina o foto: sono i nostri test.
- Dichiarare tutti i modelli e gli strumenti AI usati, compresi quelli usati per scrivere i dati (regole §7).

## 7. Orari (Roma)

| Ora | Core | Prodotto |
|---|---|---|
| 09:30–10:30 | chiave in `.env`; test di una chiamata testo e una foto via gateway | repo pubblico + licenza + `.gitignore`; scrivere fabbrica, manuale e procedura; stampare le etichette |
| 10:30–10:50 | **insieme:** `/8hack start` (track, idea, rischio principale, pagina `8hack-start`) | |
| 10:50–12:15 | core 1–3; prima foto → primo fatto | **video da 50 s + abstract**; scheletro Streamlit con funzioni finte |
| **12:15** | track bloccata | |
| **12:30** | **video e abstract caricati** (obbligatorio: senza, non si passa) | |
| 13:30 | se siamo scelti, si continua | |
| 13:30–15:00 | Must | tab Chiedi e Atlante; **pitch v1 pubblicato entro le 14:00**; modello economico in Control8 |
| 15:00–16:00 | Should | slide di business; due prove della demo cronometrate |
| **16:00** | sorteggio dell'ordine · feature freeze · `8hack-check` aggiornato | |
| 16:15 | congelamento del codice; video di backup della demo | |
| **16:30** | validazione finanziaria | |
| **16:45** | pitch finale pubblicato (genere `pitch`) e repo registrato | |
| 17:05–18:15 | slot di **5 minuti** (demo + domande) | |

## 8. Demo (3 minuti, il resto per le domande)

1. **Domanda:** "Un operatore di linea può usare la pressa P-3 oggi?" Risposta: "Sì", con la catena citata (ruolo → abilitazione → intervallo di verifica dal manuale, pagina X → ultima verifica dal registro). *(45 s)*
2. **Foto dal vivo** dell'etichetta sulla macchina: la data letta è più vecchia di quella del registro. La card diventa rossa, "bloccata: carta e reparto non coincidono", con la foto citata. *(60 s)*
3. **Cambio di regola:** carichiamo la procedura v2. Le card diventano arancioni e compaiono i verdetti passati che usavano la regola vecchia. *(40 s)*
4. **Scatola nera:** perché ha deciso così, con quali fatti e a che ora. L'agente non può cancellarlo. *(35 s)*

## 9. Track e criteri

- Alle 10:30 leggere il brief della track (`get_project_context`). Candidate: **3-ontology** (ontologia aggiornata da documenti e foto) oppure **blackbox-agents** (tracciabilità delle decisioni). Si decide entro le 12:00.
- Gate 2, il criterio che pesa di più è **"Demo or reality" (18/100)**: la foto dal vivo e le citazioni vere valgono più di qualsiasi slide.
- **Fedeltà alla proposta delle 12:30 (10/100):** nel video promettiamo solo ciò che il piano Must consegna.

## 10. Rischio principale e criterio di stop

- **Rischio:** la lettura della foto non è affidabile (data dell'etichetta letta male).
- **Test entro le 12:15:** 5 foto dell'etichetta e almeno 4 date lette giuste.
- **Se fallisce:** la foto diventa un input confermato da una persona (il sistema propone, l'RSPP conferma). Il resto del piano non cambia, e diventa anche un argomento di vendita: "nessun fatto entra senza prova".

## 11. Altri rischi

- **Credito di $25:** foto solo con il modello con visione, testo con quello economico; niente simulatore che chiama l'LLM. La chiave del team è solo per il prodotto, mai per l'agente di coding.
- **Endpoint "decisions":** da verificare nei primi minuti. La soluzione di riserva è un modello economico con output strutturato (`label` + motivazione).
- **Numeri aziendali** ("measured today"): sono esperienza del team, non il prodotto; niente codice né schermate aziendali nel repo.
- **Team riformati alle 10:30:** verificare su `/me` di essere nello stesso team, poi ricollegare l'MCP `hack`.
