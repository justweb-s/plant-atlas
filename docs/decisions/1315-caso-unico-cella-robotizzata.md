# 1315 — Un caso solo: l'RSPP di uno stabilimento con una cella robotizzata di macchine reali

- **Stato:** in vigore (assunta da Core alle 13:15, confermata da Prodotto alle 13:50)
- **Quando:** 2026-11-14 13:15
- **Chi:** Core, da confermare con Prodotto
- **Contesto:** alle 12:50 sono nate due proposte con lo stesso numero. `1250-rspp-un-solo-motore` (Prodotto): il cliente è l'RSPP, il motore è il registro dei fatti, lo stabilimento è di fantasia. `1250-layout-unico` (Core): macchine reali in una cella robotizzata, due punti di demo, sei casi di prova. Sul motore dicono la stessa cosa; sul caso si completano.

## Decisione

**1. Cliente e domanda (da Prodotto).** L'RSPP di uno stabilimento, o il consulente che ne segue molti: «questa macchina si può usare oggi, e cosa devo fare entro quando?». È la storia del video delle 12:30.

**2. Lo strato di conoscenza (da entrambi).** Tra i documenti e l'agente c'è un'ontologia: le cose dello stabilimento, le relazioni tipizzate tra loro, i vincoli che devono valere. L'agente segue le relazioni invece di cercare nel testo: il percorso è prevedibile e ogni passo si può controllare.

**3. Il motore (da Core, confermato da Prodotto).** Il registro dei fatti è la fonte di verità: nessuna citazione, nessun fatto; il modello non scrive un fatto, indica una frase e il codice la controlla parola per parola; la condizione viaggia con il fatto; un fatto superato si chiude, non si cancella; si legge sempre a una data. Il Turtle con le forme SHACL è l'esportazione per la giuria.

**4. Le macchine sono reali (da Core).** Lo stabilimento ha una cella robotizzata come quelle di una carrozzeria d'auto: un braccio robotico (quasi-macchina), uno scanner o una barriera di sicurezza (componente di sicurezza), un robot mobile, una pressa o un'unità di saldatura, un ponte sollevatore. Modelli veri, manuali pubblici: nel repo vanno link, impronta e citazioni brevi, non i file. **Dato di scenario, dichiarato ad alta voce nella demo:** la disposizione della cella, la misura delle zone protette, le date di acquisto e di ultima verifica. Le classificazioni delle macchine restano [non verificato] finché non c'è la citazione.

**5. I due punti della demo.**
- **Cambia la fabbrica.** Il braccio viene sostituito con uno più grande e si carica il manuale nuovo. L'ontologia mostra che la zona protetta non basta più (sbraccio dal manuale, zona dalla tabella di scenario, regola come vincolo), con le citazioni, e segna la cella come non rilasciabile. Se il testo lo regge: chi fa la modifica diventa fabbricante (modifica sostanziale, caso R5 di `INSIEME.md`).
- **Cambia la legge.** La cella resta uguale e si sposta la data: al 16/1/2027 e al 20/1/2027 le risposte sono diverse, con la rettifica e il Regolamento citati. È il punto sicuro: i fatti sono già verificati (CQ09–CQ10, R2).

**6. Il banco di prova: sei casi**, ognuno con risposta attesa e citazioni. Obiettivo: l'ontologia ne risolve almeno 5 su 6 con le citazioni; la ricerca semplice si misura sugli stessi sei e si pubblica il risultato comunque vada.

| # | Caso | Cosa prova | Stato |
|---|---|---|---|
| 1 | Sostituzione del braccio: la zona protetta basta ancora? | documento che cambia + vincolo numerico tra due fonti | nuovo: servono due manuali reali |
| 2 | Il 16/1/2027 si può ancora vendere una macchina conforme alla Direttiva? | una rettifica sostituisce una data | nel gold (CQ10) |
| 3 | Quale macchina della cella avrà bisogno di un organismo notificato dal 20/1/2027? | due regimi, classificazione | CQ13, da riscrivere sulle macchine reali |
| 4 | Dopo la sostituzione, chi è il fabbricante della cella? | regola con condizioni, tre documenti | nuovo; definizione nel Regolamento [verificata da Prodotto] |
| 5 | Una domanda a cui i documenti non rispondono | «non lo so», mai un'ipotesi | nuovo, costa poco |
| 6 | Prima verifica INAIL: 60 giorni (DM 11/4/2011, art. 2 c. 1) o 45 (D.Lgs. 81/08, art. 71 c. 11)? | due testi in vigore che si contraddicono | R1, [verificato da Prodotto] |

Must: 2, 3, 5, 6. Il caso 1 è il titolo della demo se i due manuali sono letti entro le 14:15; altrimenti resta nel pitch come prossimo test e il «documento che cambia» è il caso 2. Il caso 4 segue l'1.

**7. Le due strategie e il numero della regola.** B = schema dalle domande `design` + estrazione a puntatore + secondo lettore, tutto dal cancello. A = estrazione libera senza cancello, sui soli documenti delle domande; poi i suoi fatti passano dallo stesso controllo solo per contare quanti sarebbero rifiutati. Se A scrive un fatto che non sta in nessun documento, quello è il terzo punto della demo; il conteggio c'è in ogni caso. RAG su tutto il corpus, compresi i 16 atti UE come rumore realistico.

**8. Risposte alle domande aperte di `INSIEME.md` che toccano Core.**
- (7) Il registro esporta in Turtle entro le 15:00; B non scrive RDF direttamente.
- (9) Tra due testi di legge: la norma primaria (decreto legislativo) prevale sul decreto ministeriale; a pari rango prevale il più recente; se non si può decidere resta un conflitto mostrato. L'ordine di autorità del registro prende un livello in più.
- (10) A solo sui documenti delle domande. Prima di ogni run completo la stima delle chiamate va nelle note.
- (12) Criterio di stop adottato: B corretto su meno di 2 domande in più della ricerca semplice, o sotto A sulle domande tenute da parte → presentiamo il confronto come risultato negativo.

## Chi fa cosa
| Fino a | Core | Prodotto |
|---|---|---|
| 14:15 | `api.corpus()` sui testi del gold; due manuali del braccio con link e impronta | DM in `data/law/`; i sei casi nel gold (`gold:`); tabella di scenario della cella |
| 15:00 | strategia B sul registro; esportazione Turtle + SHACL; `api.answer()` con data | RAG reale; tabellone reale |
| 15:40 | cambio di documento (`propose_change` / `apply_change`); vincolo della zona | tab «Chiedi» e «Modifiche»; modello economico |
| 16:00 | strategia A e conteggio dei rifiuti; freeze | script della demo; primo `pitch` |

**Ordine dei tagli:** caso 1 e 4 → A su meno documenti → secondo lettore al minimo. Non si taglia: il cancello, la lettura a una data, i casi 2 e 6, il tabellone.

- **Perché:** tiene la promessa del video, toglie il catalogo di fantasia, usa il conflitto reale trovato da Prodotto nel DM, e mostra i due modi in cui la conoscenza di uno stabilimento cambia: da dentro (una macchina) e da fuori (la legge).
- **Punti deboli dichiarati:** i dati di scenario sono nostri; i manuali non sono ancora stati letti; nessuna voce reale di un RSPP; il motore non estrae ancora nulla.
- **Alternative scartate:** lo stabilimento tutto di fantasia (richiesta esplicita di non farlo); il costruttore come cliente principale (contraddice il video).
- **Sostituisce:** `1250-layout-unico` e `1250-rspp-un-solo-motore` (entrambe proposte).
