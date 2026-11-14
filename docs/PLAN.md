# Plant Atlas — il piano (track «Building an ontology from a knowledge base»)

In vigore dal 14/11/2026, ore 11:35. È nato come visione di Prodotto (11:15) a partire dal piano di Core, che ora sta in `docs/archive/PLAN-plant-atlas-v2.md`. Le decisioni, con il loro perché, sono in `docs/decisions/`; le regole di lavoro in `AGENTS.md`.
Marcatori: **[verificato: fonte]** · **[dichiarato]** · **[non verificato]**. Le decisioni da prendere insieme sono al §1.

## Aggiornamento delle 12:00 (decisione `1200-due-regimi-catalogo`): vale questo, dove il resto dice altro

- **Il problema:** dal 20 gennaio 2027 alcune macchine che oggi si autocertificano avranno bisogno di un organismo notificato, e il costruttore deve scoprire quali, in documenti che mescolano le regole vecchie e quelle nuove. Esempio verificato: un ponte sollevatore per veicoli con norme armonizzate complete oggi usa il controllo interno (Direttiva, Art. 12(3)(a)); dal 20/1/2027 è nell'Allegato I, parte A, e serve B+C, H o G (Regolamento, Art. 25(2)).
- **Il cliente:** il costruttore di macchine (ufficio tecnico, documentazione tecnica). Riceve una scheda d'impatto per ogni modello; l'ontologia è il motore e la traccia per un controllo. Il Regolamento serve a entrare; tenere la mappa aggiornata è il valore che si ripete.
- **Il corpus:** Direttiva 2006/42/CE + Regolamento 2023/1230 + rettifica + D.Lgs. 81/08 artt. 69–73. L'Allegato XII del Regolamento (tavola di concordanza) è il riferimento ufficiale per il cambio di regime.
- **I dati di istanza:** non più la fabbrica ma il catalogo di un costruttore di fantasia, 5 modelli (`catalogue` in `data/cq/cqs.json`).
- **Le domande:** 20; 15 di progetto e 5 tenute da parte (CQ16–CQ20), che la strategia B non vede. Il tabellone mostra i punteggi separati.
- **La domanda della demo:** la CQ13, «quali modelli, oggi autocertificati, dal 20/1/2027 dovranno passare da un organismo notificato?». Risposta: SL-30 e RC-5. La rettifica della data (CQ9–CQ10) resta come secondo esempio.
- **Ancora da fare:** una voce reale (mentor call: come fa oggi un costruttore la gap analysis verso il 2023/1230, chi la fa, quanto costa).

## 0. In 30 secondi

- **Cambia il prodotto, non il dominio.** Restiamo sulla sicurezza delle macchine (Reg. UE 2023/1230 e D.Lgs. 81/08). Il prodotto diventa: **un'ontologia costruita dai documenti, misurata su domande scritte prima di costruirla, e aggiornata con una modifica revisionabile quando un documento cambia.** La memoria del piano di Core (citazione, validità, nessuna cancellazione) diventa la provenienza e il versioning dell'ontologia.
- **Il caso perfetto per la demo esiste ed è reale.** Il Regolamento pubblicato in Gazzetta (GU L 165 del 29/6/2023) dice che si applica dal **14 gennaio 2027** e che la Direttiva 2006/42/CE è abrogata dalla stessa data. Una rettifica (GU L 169 del 4/7/2023, p. 35) corregge 14 date: quella giusta è il **20 gennaio 2027** [verificato: entrambi i testi scaricati oggi dall'Ufficio delle pubblicazioni UE]. Una ricerca sui documenti trova la data sbagliata; l'ontologia sa che la rettifica la sostituisce.
- **Due strategie a confronto, sulle stesse 15 domande.** A = estrazione libera, come fanno gli strumenti generici che trasformano documenti in grafi. B = estrazione guidata dalle domande e dalla struttura della legge, con vincoli SHACL. In più una baseline RAG.
- **La valutazione è il nostro vantaggio.** Un tabellone domande × strategie, con metriche prese da due delle risorse consigliate (CQ4OE e Text2KGBench).
- **Memoria visiva fuori dal Must.** Questa track non la premia. Se avanza tempo, le foto diventano dati di istanza validati da SHACL.

## 1. Decisioni (ognuna ha il suo file in `docs/decisions/`)

| # | Tema | Decisione |
|---|---|---|
| 1 | Track | «Building an ontology from a knowledge base». **Su Control8 il nostro progetto non ha ancora una track** [verificato: `get_project_context` alle 11:05]: va scelta su `/me` **prima delle 12:15** |
| 2 | Che cos'è il prodotto | ontologia dai documenti, punteggio sulle domande, aggiornamento tramite diff (§3) |
| 3 | Corpus | circa 35 documenti: Regolamento diviso in sezioni, rettifica, D.Lgs. 81/08 Titolo III, piccola fabbrica di fantasia (§4) |
| 4 | Le due strategie | A libera contro B guidata (§6) |
| 5 | Il documento che cambia | Must: la rettifica. Should: Direttiva 2006/42 → Regolamento, sull'elenco delle macchine ad alto rischio. Procedura v1 → v2 solo se avanza tempo |
| 6 | Dove sta l'ontologia | rdflib + file Turtle versionati in git: ogni versione è un commit. Niente Neo4j né SQLite |
| 7 | Memoria visiva | fuori dal Must |
| 8 | Chi presenta | da decidere |
| 9 | Domanda agli organizzatori (mentor call) | quale rubrica vale: quella della pagina della track o quella del form della giuria (§2) |

## 2. Cosa chiede la track e come ci valutano

| La track chiede | Come lo copriamo | § |
|---|---|---|
| Un corpus di qualche decina di documenti di un solo dominio | circa 35 documenti: legge + rettifica + fabbrica di fantasia | §4 |
| L'ontologia come file, non solo un'immagine | `ontology.ttl` (OWL 2) + `shapes.ttl` (SHACL), export JSON-LD | §8 |
| 10–20 competency questions scritte **prima** di costruire, con il punteggio | 15 domande con risposta e fonte, committate prima del primo estrattore: l'orario del commit lo dimostra | §5 |
| Due strategie sullo stesso corpus e sulle stesse domande | A contro B, più la baseline RAG | §6 |
| Un agente che risponde, tramite l'ontologia, a una domanda che la ricerca sbaglia | la data di abrogazione della Direttiva | §9 |
| Cosa succede all'ontologia quando cambia un documento | diff proposto, revisione, rilancio delle domande | §10 |

**Trappole della track:** un grafo di co-occorrenze senza classi (la strategia A lo mostra come baseline e B lo batte); nessuna valutazione (c'è il tabellone); uno schema generico tipo Person/Organisation/Document (classi del dominio, allineate a IOF, §8).

**Pesi: due fonti dicono cose diverse.**
- Pagina della track: Fit 25 · Technical quality 25 · Problem and impact 25 · Business case 20 · Demo clarity 5.
- Form della giuria in Control8, colonna `3-ontology` (quasi certamente la nostra track):
  - **Gate 1** (12:30, solo per decidere chi continua): Fit 30 · Right-to-win 25 · Explainability 20 · Willingness to invest 15 · Sentiment 10.
  - **Gate 2** (la classifica finale): Technical feasibility 18 · Demo or reality 18 · Build quality 17 · Financial sustainability 13 · Selling story 12 · Frictionless adoption 12 · Fidelity to the 12:30 proposal 10.
- In entrambe contano soprattutto aderenza alla track, qualità tecnica e demo vera: il piano non cambia. Chiediamolo comunque in una mentor call.

**Scadenze:** track entro le 12:15 · video (MP4, al massimo 50 s) e abstract (al massimo 1200 caratteri) entro le 12:30. Control8 adesso dice 12:40, ma puntiamo alle 12:30 · alle 13:30 si sa chi continua · pitch entro le 16:45. Su Control8 oggi mancano: video, abstract, pitch, repo, modello economico [verificato: `get_project_context`].

**Fedeltà alla proposta delle 12:30 (10/100):** nel video promettiamo solo il Must: ontologia dal corpus sulla sicurezza macchine, punteggio su 15 domande, due strategie, aggiornamento con la rettifica.

## 3. L'idea

**In una frase:** dai documenti di un'azienda (leggi, manuali, procedure) costruiamo un'ontologia che si apre in Protégé, misurata sulle domande che l'azienda vuole porre, e che si aggiorna con una modifica revisionabile quando un documento cambia.

**UVP da testare:** per il responsabile della documentazione tecnica di un costruttore di macchine, che deve riallineare prodotti e manuali al Regolamento 2023/1230 entro gennaio 2027, otteniamo in pochi giorni una prima ontologia dei suoi prodotti e dei requisiti che li riguardano. Ha il punteggio sulle sue domande e la fonte di ogni assioma. È diverso da un ontologo con Protégé, che ci mette settimane, e da un grafo estratto senza schema, che non ha né vincoli né punteggio. Funziona perché le domande guidano lo schema, la legge dà la struttura e ogni modifica passa da un diff revisionato. Ipotesi, test e criterio di stop sono al §13.

**Cosa resta del piano di Core:**

| Nel piano di Core | Diventa |
|---|---|
| Statement con citazione, pagina, tipo e validità | provenienza e validità di ogni assioma e di ogni istanza (`prov:wasDerivedFrom` verso il passaggio, `validFrom`/`validTo`, `supersededBy`) |
| `write_statement()`: la citazione deve esistere, i numeri devono stare nella citazione | cancello anti-allucinazione dell'estrazione; è la metrica di hallucination di Text2KGBench usata come filtro |
| `as_of(data)` | interrogare l'ontologia a una data: la rettifica cambia la risposta |
| Registro delle regole di stato | vincoli SHACL, anche SHACL-SPARQL per le regole sulle date |
| Ordine di autorità legge > manuale > procedura | in letteratura si chiama *preferred repair* con livelli di affidabilità (survey Nentidis et al. 2025): stesso meccanismo, con un nome formale da usare nel pitch |
| Verdetti a tre valori | risposta certa / possibile / sconosciuta quando le fonti sono in conflitto (ragionamento tollerante all'inconsistenza, stessa survey) |
| Impronta delle pagine e rilettura delle sole parti cambiate | aggiornamento incrementale dell'ontologia (§10) |
| Scatola nera con hash, simulatore di 12 mesi, curatore notturno, reset del contesto, foto | slide «next», oppure tagliati |

## 4. Il corpus (circa 35 documenti, un solo dominio)

| Gruppo | Documenti | Fonte e diritti |
|---|---|---|
| Reg. (UE) 2023/1230, una sezione per documento (~18) | Art. 3 (definizioni) · Art. 10–13 (obblighi degli operatori) · modifica sostanziale · Art. 21 e 24 (dichiarazione UE e marcatura CE) · Art. 25 (procedure di conformità) · Art. 51–54 (abrogazione, transitorie, applicazione) · Allegato I parti A e B · Allegato III, punti 1.1.9, 1.2.1, 1.3.7 e 1.4 · Allegato IV | GU L 165 del 29/6/2023 [verificato] |
| Rettifica (1) | 14 correzioni di date: Art. 6, 47, 50, 51, 52, 53, 54 | GU L 169 del 4/7/2023, p. 35 [verificato] |
| Direttiva 2006/42/CE (2, solo per lo Should) | Art. 12 · Allegato IV | [download non provato] |
| D.Lgs. 81/2008, Titolo III (~7) | art. 69–73 · Allegato VII | Normattiva o Gazzetta Ufficiale. Gli atti ufficiali sono esclusi dal diritto d'autore (art. 5 L. 633/1941) [non verificato oggi] |
| Fabbrica di fantasia (~8, scritta oggi e dichiarata) | 5 schede macchina · procedura v1 e v2 · registro delle verifiche | nostra |

**Download.** EUR-Lex agli script risponde con una pagina vuota (provato). L'Ufficio delle pubblicazioni invece restituisce il testo completo (provato):

```bash
curl -sSL -H "Accept: application/xhtml+xml" -H "Accept-Language: eng" -o data/law/reg-2023-1230.xhtml "https://publications.europa.eu/resource/celex/32023R1230"
curl -sSL -H "Accept: application/xhtml+xml" -H "Accept-Language: eng" -o data/law/reg-2023-1230-corrigendum.xhtml "https://publications.europa.eu/resource/celex/32023R1230R%2801%29"
```

- **Italiano:** `Accept-Language: ita` [non provato]. Avere il testo in italiano e in inglese ci dà etichette bilingui (`skos:prefLabel` e `skos:altLabel`): un valore concreto per le aziende italiane.
- **Riuso:** i testi UE sono riutilizzabili citando la fonte [non verificato oggi: avviso legale di EUR-Lex].
- **Norme armonizzate** (EN ISO 12100, 13849…): sono a pagamento, quindi ne citiamo solo i codici.

## 5. Le competency questions (bozza, da chiudere entro le 11:55)

> **Aggiornamento delle 11:25.** La versione di riferimento è `data/cq/cqs.json`, committata alle 11:25: ogni risposta è controllata sui testi ufficiali da `tests/test_cqs.py`. Rispetto alla tabella qui sotto cambiano la CQ01 (categorie che richiedono *sempre* un organismo notificato), la CQ04 (ripari mobili interbloccati: quando è previsto un accesso frequente, All. III 1.3.8.1) e la CQ11 (prima verifica dell'INAIL entro 45 giorni, art. 71 c. 11). La fabbrica di fantasia è definita nello stesso file.

Regola: si scrivono e si committano **prima** di qualsiasi codice di estrazione, con risposta attesa, fonte e tipo. Il commit è la prova.
Tipo: **T** = schema (classi e relazioni) · **I** = istanze (la fabbrica) · **V** = versioni e validità.

| # | Domanda | Tipo | Risposta attesa | Fonte |
|---|---|---|---|---|
| 1 | Quali categorie di macchine richiedono una procedura con organismo notificato? | T | le 6 categorie dell'Allegato I parte A [verificato] | Art. 25(2), All. I A |
| 2 | Quali procedure di conformità può scegliere il fabbricante per una macchina dell'Allegato I parte A? | T | Modulo B + C, oppure H, oppure G [da verificare su Art. 25(2)] | Art. 25(2) |
| 3 | In quale categoria rientra un componente di sicurezza con comportamento auto-evolutivo basato su machine learning? | T | Allegato I parte A, punto 5 [verificato] | All. I A.5 |
| 4 | Quali requisiti essenziali riguardano i ripari mobili interbloccati? | T | All. III, 1.4 [da verificare il punto esatto] | All. III |
| 5 | Quali pericoli affronta il requisito 1.3.7? | T | quelli dovuti agli elementi mobili | All. III 1.3.7 |
| 6 | Chi diventa fabbricante dopo una modifica sostanziale? | T | chi la esegue [da verificare l'articolo] | modifica sostanziale |
| 7 | Quali documenti devono accompagnare una macchina immessa sul mercato? | T | istruzioni e dichiarazione UE di conformità [da verificare] | Art. 10 |
| 8 | Per quanto tempo il fabbricante conserva la documentazione tecnica? | T | almeno 10 anni [verificato] | Art. 10(3) |
| 9 | Da quando si applica il Regolamento? | V | 20/1/2027; il testo originale diceva 14/1/2027 [verificato] | Art. 54 + rettifica, punto 10 |
| 10 | Il 16/1/2027 si può immettere sul mercato una macchina conforme alla Direttiva 2006/42/CE? | V | Sì: la Direttiva è abrogata con effetto dal 20/1/2027 [verificato] | Art. 51(2), 52(1) + rettifica, punti 5–6 |
| 11 | Quali attrezzature richiedono verifiche periodiche secondo il D.Lgs. 81/08? | T | l'elenco dell'Allegato VII [non verificato oggi] | art. 71 |
| 12 | Per quanto tempo il datore di lavoro conserva i risultati dei controlli? | T | almeno gli ultimi tre anni [non verificato oggi] | art. 71 |
| 13 | Quali macchine dello stabilimento hanno il controllo scaduto oggi? | I | dai dati di fantasia | registro + schede |
| 14 | Quali macchine dello stabilimento rientrano nell'Allegato I parte A? | I | dai dati di fantasia | schede + All. I |
| 15 | Quale procedura interna contraddice il manuale, e su quale intervallo? | I | procedura 90 giorni contro manuale 60 | fabbrica |

Per ogni domanda annotiamo anche i termini che servono a rispondere, come fa CQ4OE: **espliciti** (nella frase), **impliciti** (sinonimi) e **derivati** (necessari ma non nominati). Questa annotazione è il riferimento per la metrica di copertura.

## 6. Le due strategie (stesso corpus, stesse domande, stesso modello, stesso budget)

| Passo | A · Estrazione libera (baseline) | B · Guidata dalle domande e dalla struttura (nostra) | In B, chi decide |
|---|---|---|---|
| Chunking | finestre fisse (~800 token) | per struttura: articolo, paragrafo, punto d'allegato. Ogni chunk ha un id, ad esempio «Art. 25(2)» | codice |
| Schema | nessuno: tipi ed etichette liberi | seme ricavato dalle domande, una alla volta (CQbyCQ, Lippolis et al. 2025), con le classi alte riusate da IOF | il modello propone, una persona approva le ~15 classi alte |
| Estrazione | triple libere per chunk | guidata dallo schema (come SPIRES/OntoGPT), più i termini nuovi candidati, sempre con la citazione | il modello; il codice scarta ciò che non sta nella citazione |
| Classi | cluster di embedding dei tipi estratti | gerarchia proposta e ancorata a IOF | il modello propone, una persona approva |
| Duplicati | confronto di stringhe con una soglia | stringhe + embedding + giudice. La fascia incerta (es. similarità 0,75–0,90) va a una persona. Italiano e inglese diventano sinonimi | una persona, solo sulla fascia incerta |
| Vincoli | nessuno | SHACL dallo schema (dominio, range, cardinalità) e da alcune frasi «shall» (es. All. I parte A → procedura in {B+C, H, G}) | una persona approva i vincoli che hanno peso legale |
| Validità | nessuna | `validFrom`, `validTo`, `supersededBy` | codice |
| Uscita | Turtle | Turtle + shapes + provenienza | — |

- **A non è un fantoccio.** È ciò che fa un generico estrattore documenti → grafo senza schema. La ricerca degli organizzatori cita questo rischio per Neo4j LLM Graph Builder [non verificato da noi]. Non diciamo di aver usato quello strumento: ne riproduciamo l'approccio.
- **Ripiego se manca tempo:** confrontare solo il chunking (finestre fisse contro struttura) dentro B. Restano due strategie.
- **Risposta alla domanda della track** («quali passi automatizzare e quali richiedono una persona»):
  - **automatico:** parsing, chunking, estrazione, classi candidate, duplicati oltre soglia, SHACL dallo schema, diff, punteggi;
  - **una persona:** domande e perimetro, classi alte, fusioni incerte, vincoli con peso legale, accettazione delle modifiche.
  Contiamo le decisioni umane: sono i «minuti di esperto» del business case.

## 7. Come sappiamo che è buona: il tabellone

| Metrica | Cosa misura | Da dove | Automatica |
|---|---|---|---|
| Copertura delle domande (AtLeastOne / Mean / Full) | l'ontologia contiene i termini che servono a ogni domanda | CQ4OE, task CQ2Term | sì, con mapping per etichetta e controllo a mano |
| Accuratezza delle risposte | l'agente risponde giusto via SPARQL | le risposte attese del §5 | sì |
| Conformità all'ontologia | % di triple che usano relazioni dell'ontologia | Text2KGBench | sì |
| Allucinazioni di soggetto e oggetto | % di entità che non compaiono nel testo | Text2KGBench | sì |
| Violazioni SHACL e consistenza | pySHACL; owlrl, oppure HermiT in Protégé | W3C SHACL, OWL 2 | sì |
| Errori tipici | dominio e range sbagliati, inverse errate, classi superflue | Lippolis et al. 2025; OOPS! se raggiungibile | in parte |
| Costo | token, dollari e tempo per strategia | gateway | sì |
| Sforzo umano | decisioni di revisione richieste | log | sì |

- **Colonne:** RAG · A · B. **Righe:** le 15 domande e i totali.
- Si rilancia a ogni modifica: diventa il test di regressione dell'ontologia.
- **Opzionale:** far girare B su uno dei 6 domini di CQ4OE, per avere un punteggio confrontabile con la loro classifica (le loro baseline sono: tutte le domande insieme, una domanda alla volta, agentica).

## 8. Formato e strumenti

**File:**
- `ontology/msafety.ttl` (OWL 2), `ontology/shapes.ttl` (SHACL), `ontology/CHANGELOG.md`, export JSON-LD;
- una versione per commit (`owl:versionInfo`).

**Allineamento a IOF.** IOF Core (basata su BFO, licenza MIT, stato Released) con i moduli Maintenance e Certification, anch'essi Released [verificato: repo iofoundry/ontology]. Corrispondenze che si possono usare subito (sono etichette che esistono nei file IOF):

| Nostra classe | Classe IOF |
|---|---|
| Macchina | `piece of equipment` |
| RequisitoEssenziale | `requirement specification` (relazione `satisfies requirement`) |
| Fabbricante | `manufacturer role` |
| OrganismoNotificato | `certifying body` |
| CertificatoDiEsameUETipo | `certificate` |
| ControlloPeriodico | `maintenance activity` |

**Classi attese da B (specifiche del dominio, non generiche):** Macchina, QuasiMacchina, ComponenteDiSicurezza, CategoriaAllegatoI (parte A, parte B), RequisitoEssenziale (per sezione dell'Allegato III), Pericolo, Riparo (fisso, mobile interbloccato, regolabile), ProceduraDiConformità (moduli A, B, C, G, H), OrganismoNotificato, DichiarazioneUE, MarcaturaCE, DocumentazioneTecnica, Istruzioni, OperatoreEconomico (fabbricante, importatore, distributore, mandatario), ModificaSostanziale, DatoreDiLavoro, ControlloPeriodico, Disposizione (articolo o punto, con validità).

**Librerie:**
- rdflib (RDF, SPARQL, JSON-LD);
- pySHACL (SHACL, anche SHACL-SPARQL);
- owlrl (ragionamento OWL 2 RL in Python puro, senza Java);
- Protégé solo per mostrare il file in demo: da installare **adesso**.

**Modelli** via gateway: uno economico per l'estrazione, uno più forte per lo schema. Ogni risposta del modello viene salvata su disco, così rilanciare non costa nulla.

**Contratto** (`atlas/api.py`): cambia e va concordato nella riunione. Proposta: `build_ontology(strategy)`, `evaluate(strategy)`, `answer(question, mode)` con `mode` = `ontology` o `rag`, `propose_change(doc)`, `apply_change(change_id)`.

## 9. L'agente contro la ricerca

- **Strumenti dell'agente:** `sparql(query)`, `describe(term)`, `validate()`. La risposta cita le triple e il passaggio da cui vengono.
- **Baseline RAG:** stessi chunk, i 5 più simili per embedding, stesso modello.

**La domanda che la ricerca dovrebbe sbagliare** (da provare entro le 12:15; se il RAG la indovina, si passa a una di riserva):

> «Il 16 gennaio 2027 posso immettere sul mercato una macchina conforme alla Direttiva 2006/42/CE?»

- Il testo in Gazzetta dice «abrogata con effetto dal 14 gennaio 2027» (Art. 51(2)), quindi il RAG risponde **No**.
- La rettifica dice di leggere «20 gennaio 2027», quindi l'ontologia risponde **Sì, fino al 19 gennaio**, citando il punto 5 della rettifica [verificato: entrambi i testi].

**Domande di riserva:** la 13 (aggregazione su tutte le macchine) e la 15 (conflitto tra procedura e manuale).

## 10. Quando cambia un documento

1. **Arriva un documento nuovo o una nuova versione.** Si calcola l'impronta di ogni sezione (l'idea di Core) e si rileggono solo le sezioni nuove o cambiate.
2. **Diff semantico tra due versioni dell'ontologia:** classi, proprietà, vincoli e valori aggiunti, tolti o cambiati, ognuno collegato al passaggio che lo ha causato.
3. **Coda di revisione:** una persona accetta o rifiuta ogni modifica. Quelle accettate formano la nuova versione, cioè un nuovo commit.
4. **Si rilanciano le domande:** quali risposte cambiano, e il punteggio prima e dopo.

- **Must:** la rettifica. Il sistema propone 14 modifiche di data e la risposta alle domande 9 e 10 si ribalta.
- **Should:** dall'Allegato IV della Direttiva all'Allegato I del Regolamento. Nascono categorie nuove (i componenti di sicurezza con machine learning), quindi classi nuove: una modifica a livello di schema.

## 11. Demo in 3 minuti (il resto dello slot di 5 minuti è per le domande)

1. **Il punto di partenza** *(20 s)*: «15 domande scritte alle 11:xx, prima di costruire: ecco il commit.» Il corpus è di 35 documenti.
2. **Il tabellone** *(40 s)*: RAG, A e B sulle 15 domande. L'ontologia di B si apre in Protégé (classi del dominio, allineamento a IOF) e SHACL gira dal vivo.
3. **La domanda che la ricerca sbaglia** *(50 s)*: il RAG risponde «No», sbagliando; l'agente risponde «Sì, fino al 19/1», con il percorso nell'ontologia e la rettifica citata.
4. **Un documento cambia** *(50 s)*: carichiamo la rettifica (o la procedura v2). Compare il diff proposto, ogni modifica con il suo passaggio; accettiamo e il tabellone si aggiorna.
5. **Chiusura** *(20 s)*: cosa è reale e cosa no, il prossimo test, i modelli e gli strumenti AI usati (regole §7).

## 12. Mercato e business case (Prodotto)

- **Chi paga** [non verificato, da testare]: il costruttore di macchine (PMI), nella persona del responsabile della documentazione tecnica o dell'ufficio normativo. È il segmento che la ricerca degli organizzatori indica come early adopter (aziende con molti manuali e procedure).
  - **Utente:** il tecnico che scrive manuali e fascicoli.
  - **Canale possibile:** consulenti di marcatura CE e organismi notificati.
- **Perché ora:**
  - il Regolamento si applica dal 20/1/2027 [verificato];
  - a giugno 2026 Schneider Electric ha concordato l'acquisto di Cognite per 3,1 miliardi di dollari, chiusura in attesa delle autorizzazioni [verificato dagli organizzatori];
  - Microsoft Fabric IQ importa ontologie RDF, Turtle e OWL [verificato dagli organizzatori]. Il nostro file entra quindi nelle piattaforme che i clienti hanno già: è il criterio «adozione senza attrito».
- **Alternative di oggi** (dalla ricerca degli organizzatori):
  - un ontologo con Protégé, per settimane;
  - Palantir, Cognite e Fabric IQ, che partono da dati e tabelle, non da documenti;
  - Graphwise, TopQuadrant e Stardog, pensati per chi sa già modellare;
  - Neo4j LLM Graph Builder, gratuito ma senza schema.
- **Dove c'è spazio** (stessa fonte): ontologia ricavata dai documenti; aggiornamento quando cambia un documento; un punteggio sulle domande, pubblicato, per confrontare due ontologie; PMI che non hanno né Foundry, né Fabric, né un ontologo.
- **Rischio che diventi una funzione degli assistenti generici:** un assistente scrive un file OWL se glielo chiedi, ma senza punteggio, senza fonte per ogni assioma, senza vincoli validati e senza aggiornamento incrementale [non verificato: da controllare nelle note di rilascio].
- **Prezzi** (ipotesi da portare alla validazione finanziaria, non fatti): un progetto di avvio per famiglia di prodotti (corpus, domande, prima ontologia) più un abbonamento per tenerla aggiornata. Per partire: €6.000 di avvio e €500 al mese per corpus, da sostituire con quello che dicono un mentor o un costruttore.
- **Dimensione dal basso:** il numero di imprese NACE C28 (costruzione di macchinari) in Italia, dalle statistiche strutturali di Eurostat [da cercare]. Mai «1% di un mercato da X miliardi».
- **In Control8 prima delle 16:30:** il modello economico (`/8hack economic-model`).

## 13. Rischio principale, test, criterio di stop

| | Ipotesi | Test oggi | Criterio di stop, scritto prima |
|---|---|---|---|
| **Venture** | un responsabile tecnico accetta di revisionare una bozza generata se vede il punteggio e la fonte di ogni assioma | 2 mentor call + 2–3 persone in sala con esperienza in manifattura, 10 minuti ciascuna: «l'ultima volta che avete riallineato requisiti e manuali, quanto ci avete messo e con cosa?» | meno di 2 su 3 riconoscono il problema negli ultimi 12 mesi → cambiamo segmento (responsabili HSE di stabilimento, il piano originale di Core) senza cambiare il motore |
| **Tecnica** | B batte A sulla copertura delle domande, con lo stesso budget | il tabellone alle 15:00 | se B non supera A di almeno 15 punti di Mean coverage, presentiamo il confronto così com'è (vale comunque per la track) e il pitch punta sul meccanismo di aggiornamento |
| **Demo** | il RAG sbaglia la domanda 10 | un RAG minimo entro le 12:15 | se la indovina, usiamo la 13 o la 15 |

**Punti di rottura della demo:**

| Cosa può rompersi | Rimedio |
|---|---|
| Credito del gateway ($25, errore 402) | cache di ogni risposta, una sola esecuzione completa |
| Wifi | risultati precalcolati e Protégé in locale |
| EUR-Lex che blocca gli script | Ufficio delle pubblicazioni (provato) e testi committati nel repo |
| Installazione di Protégé | Turtle e report pySHACL mostrati nell'app |
| Un solo portatile | push su GitHub ogni 30–45 minuti |

## 14. Chi fa cosa, da adesso

| Ora | Core | Prodotto |
|---|---|---|
| 11:20–11:35 | riunione | riunione · scegliere la track su `/me` |
| 11:35–11:55 | scaricare il corpus, chunker per struttura | le 15 domande con risposte e termini → commit |
| 11:55–12:25 | strategia A minima · RAG minimo sulla domanda 10 | video da 45 s + abstract |
| **12:30** | video e abstract caricati (Control8 chiude alle 12:40) | |
| 13:30–15:00 | strategia B: schema dalle domande, estrazione guidata, SHACL, agente | valutazione e tabellone in Streamlit · pitch v1 alle 14:00 · modello economico |
| 15:00–15:30 | diff della rettifica e rilancio delle domande | tab «Modifiche» · prove della demo |
| 15:30 | decisione sui tagli | |
| 16:00 | feature freeze · aggiornare `8hack-check` | |
| 16:15 | code freeze · video di backup | |
| 16:30 | validazione finanziaria | |
| **16:45** | pitch finale (genere `pitch`) e repo registrato | |

## 15. Le fonti, e cosa prendiamo da ciascuna

**Risorse consigliate dagli organizzatori:**
- **CQ4OE** (OEG-UPM, Apache-2.0) [verificato: README]: due task, CQ2Term (dalla domanda ai termini) e CQ2Onto (dalle domande all'ontologia). Metriche: precision, recall e F1 dei termini; copertura AtLeastOne, Mean e Full; ragionamento con HermiT. Annotazione dei termini in espliciti, impliciti e derivati. Baseline: tutte le domande insieme, una alla volta, agentica. → Il nostro protocollo di valutazione.
- **Text2KGBench** (ISWC 2023; codice Apache-2.0) [verificato: README e `run_eval.py`]: precision, recall e F1 delle triple; conformità all'ontologia; allucinazioni di soggetto, relazione e oggetto. → Le metriche del passo di estrazione.
- **IOF** (Industrial Ontologies Foundry, MIT) [verificato: README e file]: Core basata su BFO; moduli Maintenance, Certification, Supply Chain e Production Planning, tutti Released; consistenti con HermiT secondo il README. → Le classi alte, così evitiamo uno schema generico.
- **SHACL** (W3C) → i vincoli. **OWL 2 Primer** → assiomi di classe, disgiunzione, caratteristiche delle proprietà. **Protégé** → aprire e controllare il file con il reasoner durante la demo.

**I paper nella cartella `paper/`:**
- **Noy e McGuinness, *Ontology Development 101*:** i sette passi, partendo dalle competency questions e dal riuso di ontologie esistenti. «There is no single correct ontology»: per questo misuriamo su domande e non su una presunta verità. → Automatizziamo i passi centrali; la persona resta su perimetro, riuso e accettazione.
- **LLMs4OL** (Babaei Giglou et al., ISWC 2023): i modelli generici sono discontinui nei compiti di ontology learning (tipizzazione dei termini, tassonomia, relazioni non tassonomiche) e da soli non bastano dove servono ragionamento e competenza di dominio. → La revisione umana va proprio lì.
- **SPIRES / OntoGPT** (Caufield et al.): estrazione zero-shot guidata da uno schema, ricorsiva, con ancoraggio a identificativi. → La parte di popolamento di B.
- **OntoChat** (Zhang et al. 2024): un agente conversazionale per raccogliere user story e competency questions e testare le ontologie. → Come un cliente scrive le sue domande: una funzione del prodotto.
- ***Ontology Generation using LLMs*** (Lippolis et al. 2025): Memoryless CQbyCQ e Ontogenia; i modelli commerciali arrivano al livello dei principianti. Errori ricorrenti: dominio e range sbagliati, inverse errate, classi superflue. Serve una valutazione su più dimensioni (OOPS!, criteri strutturali, esperti). → Lo schema di B e i controlli che facciamo.
- ***Dealing with Inconsistency for Reasoning over KGs*** (Nentidis et al. 2025): rilevare, riparare, ragionare nonostante l'inconsistenza; riparazioni preferite secondo livelli di affidabilità; riparazioni minime guidate da SHACL. → Il nome formale dell'ordine di autorità di Core.

**Fonti primarie del dominio** [verificato oggi]:
- Reg. (UE) 2023/1230, GU L 165 del 29/6/2023: `https://publications.europa.eu/resource/celex/32023R1230`
- Rettifica, GU L 169 del 4/7/2023, p. 35: `https://publications.europa.eu/resource/celex/32023R1230R%2801%29`
