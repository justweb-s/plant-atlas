# Come mettiamo insieme i pezzi (proposta delle 13:00)

Accompagna la decisione `docs/decisions/1250-rspp-un-solo-motore.md`, che è ancora una proposta. È la base per la discussione tra Core e Prodotto: quando avremo deciso, i punti chiusi diventano decisioni e le domande aperte si cancellano da qui.
Marcatori: **[verificato: fonte]** · **[dichiarato]** · **[non verificato]**.

## 1. Da dove partiamo

| | Visione di Core | Visione di Prodotto (decisione 1200) |
|---|---|---|
| Chi paga | l'RSPP di uno stabilimento da 50 a 250 dipendenti; i consulenti di sicurezza come canale | il costruttore di macchine |
| La domanda | «questa macchina si può usare oggi?» | «quali miei modelli, dal 20/1/2027, devono passare da un organismo notificato?» |
| Urgenza | scadenze che tornano ogni anno (verifiche, controlli) | una data sola, 20/1/2027 |
| Corpus | D.Lgs. 81/08, DM 11/4/2011, 16 atti UE sulla sicurezza in fabbrica, manuali e procedure | Direttiva 2006/42/CE, Regolamento 2023/1230, rettifica, D.Lgs. 81/08 artt. 69–73, catalogo di 5 modelli |
| Motore | registro dei fatti: citazione obbligatoria, validità da/a, autorità, niente si cancella (scritto e testato) | ontologia OWL + SHACL, due strategie A/B contro RAG |
| Misura | criterio di stop su 15 domande | 20 domande, 5 tenute da parte, gold verificato sui testi |
| Foto | sì, la memoria visiva | no |
| Video delle 12:30 | **racconta questa storia** | — |

I due approcci non si escludono: il principio è lo stesso. Un fatto senza citazione non esiste, il tempo conta, un fatto superato si chiude invece di cancellarlo, e il confronto si fa con la ricerca semplice. Il `as_of(data)` di Core serve a entrambi: fa scadere una verifica e fa scattare un cambio di regime.

## 2. La visione unita

**Plant Atlas risponde all'RSPP: «questa macchina si può usare oggi, e cosa devo fare entro quando?».** Ogni passo della risposta porta la frase di legge, di manuale o di procedura da cui viene. Quando un documento cambia, il sistema propone la modifica, l'RSPP la accetta e la risposta cambia.

- **Il cliente è quello del video:** l'RSPP, e il consulente che segue molti stabilimenti.
- **Il motore è quello di Core:** il registro dei fatti diventa la strategia B. Il file per la giuria è l'export in Turtle con le forme SHACL.
- **La misura è quella di Prodotto:** domande scritte prima, una parte tenuta da parte, tabellone RAG / A / B.
- **Il cambio di regime resta,** ma visto dall'RSPP: cosa controllare su una macchina comprata dopo il 20/1/2027, e cosa succede se la modifichi.
- **Il catalogo resta,** con un altro ruolo: i 5 modelli diventano le macchine dello stabilimento, ognuna con data d'acquisto, ultima verifica, manuale e procedura interna.

## 3. Casi reali da considerare

I casi verificati sul testo sono candidati per il gold. Gli altri vanno verificati prima di scriverli come domande.

| # | Caso | Perché la ricerca semplice sbaglia | Stato |
|---|---|---|---|
| R1 | **Prima verifica INAIL: 60 o 45 giorni?** Il DM 11/4/2011, art. 2, c. 1 dice sessanta giorni; l'art. 71, c. 11 del D.Lgs. 81/08 vigente dice quarantacinque. | Due testi ufficiali si contraddicono: la ricerca può trovare il DM. | [verificato: GU 29/4/2011 e Normattiva, letti oggi]. Manca l'atto che ha cambiato il termine, e da quando |
| R2 | **La data della rettifica:** il Regolamento pubblicato dice 14 gennaio 2027, la rettifica dice 20 gennaio 2027. | La ricerca trova il testo pubblicato. | [verificato: GU L 165 e GU L 169]. È già nel gold (CQ09–CQ10) |
| R3 | **Allegato VII del D.Lgs. 81/08** (attrezzature soggette a verifica periodica), modificato dalla L. 11 marzo 2026, n. 34, in vigore dal 7/4/2026. | Elenco e frequenze cambiano: una risposta su una data precedente al 7/4/2026 è diversa da una su una data successiva. | [verificato da Core su Normattiva; non ancora da Prodotto]. Su Normattiva l'allegato è un'immagine: vanno trascritte a mano solo le righe che servono |
| R4 | **Una macchina comprata dopo il 20/1/2027.** L'art. 70, c. 1 del D.Lgs. 81/08 chiede conformità alle norme «di recepimento delle direttive comunitarie di prodotto»; il Regolamento è direttamente applicabile e non si recepisce. | La ricerca risponde con la Direttiva; il testo italiano non nomina il Regolamento. | Testo [verificato]. Come si legge oggi: [non verificato], è la domanda giusta per un mentor |
| R5 | **L'RSPP modifica una macchina** (per esempio aggiunge una barriera o un sistema di visione). Il D.Lgs. 81/08, art. 71, c. 5 rimanda al DPR 459/1996; il Regolamento definisce la «substantial modification», anche «by physical or digital means». | Due regimi con criteri diversi: dal 2027 chi modifica può diventare fabbricante. | Definizione del Regolamento [verificata]; conseguenze per l'utilizzatore [non verificate] |
| R6 | **Manuale contro procedura interna:** il manuale dice di controllare la catena ogni 2 anni (ogni anno se ha più di 10 anni), la procedura interna dice ogni 90 giorni. | La ricerca prende la prima frase che trova e perde la condizione «più di 10 anni». | Di fantasia: è il caso dei test di Core |
| R7 | **Macchina vecchia, senza marcatura CE** (messa a disposizione prima delle norme di recepimento): vale l'Allegato V, art. 70, c. 2. | Caso frequente negli stabilimenti italiani [non verificato]; la ricerca risponde con il Regolamento. | Testo dell'art. 70, c. 2 [verificato]; Allegato V non scaricato |
| R8 | **Controlli e verbali da conservare:** almeno gli ultimi tre anni (art. 71, c. 9). | Facile, serve come controllo. | [verificato]. È già nel gold (CQ12) |

**Proposta:** nel gold entrano R1, R6 e R7 (con l'Allegato V), più R3 se la trascrizione è pronta entro le 14:30. R4 e R5 vanno nel pitch come «domande che il sistema mostra aperte» e a un mentor.

## 4. La demo: una mattina in uno stabilimento (3 minuti)

**Situazione.** Uno stabilimento con le 5 macchine del catalogo, un registro delle verifiche in un foglio di calcolo, i manuali, una procedura interna e le leggi. È lunedì mattina. L'RSPP deve decidere cosa si può usare.

1. **(0:00–0:25) Il problema, detto da una persona.** «Ogni lunedì apro il foglio delle verifiche, il manuale e la procedura, e spero che dicano la stessa cosa.» Se lo dice un RSPP vero o un mentor, è una citazione; altrimenti è marcato [dichiarato].
2. **(0:25–1:10) La domanda.** «Il ponte SL-30 si può usare oggi?» A sinistra la ricerca semplice risponde «sì, verifica ogni 2 anni» e perde la condizione. A destra Plant Atlas risponde «bloccato: la verifica è scaduta il …», con i passi in fila e la frase di manuale, procedura e legge su ogni passo (R6).
3. **(1:10–1:50) La trappola.** «Ho chiesto la prima verifica all'INAIL il 3 novembre: entro quando deve venire?» La ricerca semplice dice 60 giorni (il DM); Plant Atlas dice 45 (art. 71, c. 11) e mostra perché il DM perde (R1).
4. **(1:50–2:30) Il documento che cambia.** Carichiamo la nuova versione di un documento: il manuale v2, oppure l'Allegato VII dopo la L. 34/2026 (R3). Il sistema propone le modifiche, ognuna con la frase che l'ha causata; l'RSPP accetta, e la risposta del punto 2 cambia davanti alla giuria.
5. **(2:30–3:00) La prova.** Il tabellone: RAG, A e B sulle stesse domande, con quelle tenute da parte in una colonna a sé. Il file Turtle si apre e passa la validazione SHACL.

**Cosa è vero e cosa è finto, detto ad alta voce:** leggi vere e verificate; stabilimento, manuali e procedura di fantasia; registro delle verifiche di fantasia.

**Piano B se manca la rete o il credito:** risposte e modifiche dalla cache (`ATLAS_OFFLINE=1`), più un video di backup registrato alle 16:15.

## 5. Domande aperte (da chiudere con Core)

**Prodotto e storia**
1. La decisione 1250 va bene così? Se no, cosa cambia?
2. Chi paga davvero: lo stabilimento, il consulente o entrambi? Il prezzo del piano v2 (300 €/mese per stabilimento, 150 €/mese per cliente del consulente) resta la nostra ipotesi [dichiarato]?
3. Chi presenta?

**Corpus**
4. I 16 atti UE che Core ha scaricato entrano nel corpus? Proposta: sì, come rumore realistico per la ricerca semplice, ma nessuna domanda su di loro. Sono testi «as published» e molti sono stati modificati dopo (per esempio la 2004/37): un fatto preso da lì può essere superato.
5. Chi trascrive le righe dell'Allegato VII (R3), ed entro quando?
6. Le cinque direttive che danno 404 (89/391, 2003/10, 2002/44, 1999/92, 98/24) servono? Proposta: no.

**Motore e ontologia**
7. Il registro dei fatti esporta in Turtle entro le 15:00, oppure la strategia B scrive direttamente in RDF?
8. Quali classi e relazioni minime? Proposta: `Machine`, `WorkEquipment`, `LegalProvision`, `Verification`, `Control`, `Document`, `DocumentVersion`, `Statement`; relazioni `requiresVerification`, `hasInterval`, `appliesFrom`, `supersedes`, `quotedFrom`; allineamento con IOF Core solo per `Machine` e `Document`.
9. Come decide il registro tra due testi di legge con la stessa autorità (R1)? Vince il più recente, la norma primaria sul decreto, o resta un conflitto da mostrare?
10. La strategia A gira su tutto il corpus o solo sui documenti delle domande? Il credito è di $25 e non abbiamo ancora fatto chiamate.

**Misura**
11. Quante domande nuove entrano nel gold, e quali restano tenute da parte? Proposta: R1, R6 e R7 di progetto; un caso del cambio di regime tenuto da parte.
12. Il criterio di stop di Core («B corretto su meno di 2 domande in più della ricerca») lo adottiamo così?

**Da chiedere a un mentor (finestra 14:00–16:30)**
13. Come gestisce oggi un RSPP le scadenze delle verifiche, e quante ore al mese ci spende?
14. Come si legge l'art. 70, c. 1 del D.Lgs. 81/08 per le macchine immesse sul mercato con il Regolamento (R4)?

## 6. Chi fa cosa, da adesso (se la 1250 passa)

| Fino a | Core | Prodotto |
|---|---|---|
| 14:30 | `register.py` legge anche i `.xhtml`; chunk dei testi UE; strategia B sul registro dei fatti | DM e Allegato VII in `data/law/`; domande nuove nel gold (commit `gold:`); schede di stabilimento, manuali e procedura |
| 15:00 | export Turtle + SHACL; strategia A | baseline RAG reale; tabellone reale |
| 16:00 | agente sulle domande della demo; diff del documento che cambia | modello economico su Control8; script della demo; primo `pitch` pubblicato |
| 16:15 | code freeze | video di backup |
| 16:45 | — | `pitch` finale e repo registrato |
