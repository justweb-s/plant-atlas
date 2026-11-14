# 1250 — Un solo layout: il motore di Core dentro il prodotto di Prodotto

- **Stato:** proposta di Core, in attesa di Prodotto <!-- diventa «in vigore» quando Prodotto è d'accordo -->
- **Quando:** 2026-11-14 12:50
- **Chi:** Core, da confermare con Prodotto
- **Contesto:** la mattina sono nati due progetti. Quello di Prodotto ha il cliente, il caso reale, le 20 domande con il gold, il contratto e la valutazione, ma il motore è vuoto. Quello di Core ha la regola del motore (nessuna citazione, nessun fatto), il registro dei fatti con i test e un corpus più largo, ma non ha cliente, domande né valutazione. Serve un layout unico prima di scrivere altro codice.

## Decisione

**1. Un prodotto, una frase.** Un'ontologia costruita dai documenti di legge e di prodotto, in cui ogni fatto ha la sua citazione, la sua condizione e le sue date; misurata su domande scritte prima; aggiornata con modifiche che una persona accetta o rifiuta.

**2. Il caso: una cella robotizzata reale, come in una carrozzeria d'auto** (richiesta del mio umano alle 13:00: niente dati di fantasia). Al posto del catalogo di fantasia, 4–5 macchine reali con manuale pubblico: un braccio robotico (quasi-macchina, con dichiarazione di incorporazione), uno scanner o una barriera di sicurezza (componente di sicurezza), un robot mobile, una pressa o un'unità di saldatura, un ponte sollevatore (l'esempio già verificato). Dei manuali committiamo link, impronta e citazioni brevi, non il file (diritto d'autore). L'unica cosa nostra, dichiarata come dato di scenario: una tabella con la disposizione della cella e la misura delle zone protette. Le classificazioni delle macchine sono [non verificato] finché non c'è la citazione.

**2a. I due punti della demo.**
- **Cambia la fabbrica:** il braccio viene sostituito con uno più grande e si carica il manuale nuovo. L'ontologia mostra che la zona protetta non basta più (sbraccio dal manuale, zona dalla tabella, regola come vincolo), con le due citazioni, e, se il testo lo regge, che chi fa la modifica diventa fabbricante (modifica sostanziale, CQ06).
- **Cambia la legge:** la cella resta uguale e si sposta la data. Al 16/1/2027 e al 20/1/2027 le risposte sono diverse (CQ10 con la rettifica; il ponte sollevatore che dal 20/1 richiede un organismo notificato). È il punto sicuro: i fatti sono già verificati.

**2b. Il banco di prova: sei casi**, ognuno con risposta attesa e citazioni. Obiettivo: l'ontologia ne risolve almeno 5 su 6 con le citazioni; il RAG si misura sugli stessi sei. Must: 1, 2, 3, 5.
1. Sostituzione del braccio: la zona protetta basta ancora? (cambio di documento + vincolo numerico tra due fonti)
2. Il 16/1/2027 si può ancora vendere una macchina conforme alla Direttiva? (CQ10)
3. Quale macchina della cella avrà bisogno di un organismo notificato dal 20/1/2027? (CQ13 sulle macchine reali)
4. Dopo la sostituzione, chi è il fabbricante della cella? (regola con condizioni, tre documenti)
5. Una domanda a cui i documenti non rispondono: la risposta è «non lo so». 
6. Manuale e procedura della cella danno intervalli diversi: quale vale? (ordine di autorità; il primo da tagliare)

**Cosa chiede a Prodotto:** riscrivere CQ13–CQ15 e le domande tenute da parte sulle macchine reali, e aggiungere i sei casi al gold. Le 12 domande sulla legge restano.

**3. Il motore (di Core).** La fonte di verità è il registro dei fatti (`atlas/ontology/statements.py`), non il file Turtle:
- un fatto entra solo da `write_statement()`: la citazione deve stare nel testo, il valore nella citazione, la condizione non si perde; chi non passa è rifiutato e contato;
- un fatto proposto diventa corrente dopo il secondo lettore (`verify`), poi `make_current()` lo confronta con quelli correnti: stessa fonte e versione nuova → il vecchio si chiude; fonti diverse → vince l'autorità più alta, il perdente resta come conflitto;
- si legge solo con `as_of(data)`: è così che la rettifica cambia la risposta alla CQ10;
- il Turtle in `ontology/<strategia>/` è un'esportazione del registro a una data, con `prov:wasDerivedFrom`, `validFrom`, `validTo`; SHACL gira sull'esportazione.

**4. Le due strategie.**
- **B (nostra):** schema dalle domande `design` e dalle classi IOF (di Prodotto) + estrazione in cui il codice sceglie i passaggi candidati e il modello può solo indicarne uno e riempire uno slot tipizzato (di Core). Tutto passa da `write_statement()` e dal secondo lettore.
- **A (il modo usuale):** estrazione libera, senza schema e senza cancello. I suoi fatti vengono poi passati dallo stesso controllo solo per contare quanti sarebbero rifiutati: è il numero che misura la regola. A gira su un sottoinsieme del corpus se il credito non basta.
- **RAG (di Prodotto):** sugli stessi chunk di tutto il corpus.

**5. Il corpus: un dominio, due lati.** La sicurezza di una macchina lungo la sua vita: quando si immette sul mercato (costruttore: Direttiva, Regolamento, rettifica) e quando si usa in fabbrica (datore di lavoro: D.Lgs. 81/08, DM 11/4/2011, Direttiva 2009/104/CE e gli altri atti UE registrati oggi). Il lato fabbrica è anche il segmento di riserva del criterio di stop «Venture» del piano (§13): stesso motore, altro cliente. B legge solo ciò che serve alle domande; il RAG cerca su tutto, che è la condizione realistica.

**6. Quando cambia un documento.** Impronta per sezione → si rileggono solo le sezioni cambiate → i fatti nuovi sono `proposed` → `propose_change()` li restituisce come `Change` con citazione e punto del testo → una persona accetta → `apply_change()` chiama `make_current()` → nuova esportazione Turtle, nuovo commit, domande rilanciate.

**7. La misura.** Il gold e `evaluation/` restano di Prodotto. In più, dal motore: proposti / ancorati / rifiutati per motivo, conflitti e come sono stati risolti, decisioni umane. Una risposta senza fatti è `value=None` («non lo so»), mai un «no»: chiediamo a Prodotto di mostrarla separata da «sbagliato».

## Cosa cambia nel contratto (solo aggiunte con default)
- `Chunk.sha256: str = ""` — l'impronta della sezione.
- `Step.statement_id: str | None = None` — il fatto usato in quel passo.
- `BuildResult.proposed: int = 0`, `anchored: int = 0`, `rejected: int = 0`.

## Chi fa cosa fino alle 16:45
| Ora | Core | Prodotto |
|---|---|---|
| 12:50–13:30 | `api.corpus()`: chunk per struttura dei 4 atti del gold | schede del catalogo, RAG minimo sulla CQ10 |
| 13:30–14:40 | schema B, estrazione a puntatore, secondo lettore, esportazione Turtle + SHACL | tabellone reale, pitch v1, modello economico |
| 14:40–15:10 | `api.answer()` con `as_of`: CQ09, CQ10, CQ13 | tab «Chiedi» sull'agente vero |
| 15:10–15:40 | la rettifica come cambio di documento: `propose_change` / `apply_change` | tab «Modifiche» |
| 15:40–16:00 | strategia A sul sottoinsieme, conteggio dei rifiuti | prove della demo |
| 16:00 | freeze | `8hack-check` |

**Ordine dei tagli se siamo indietro alle 15:00:** prima A su meno documenti, poi il secondo lettore al minimo, poi il lato fabbrica fuori dall'estrazione (resta nel RAG). Non si taglia: il cancello, `as_of`, la rettifica, il tabellone.

- **Perché:** ciascun lato copre il punto debole dell'altro. Prodotto ha ciò che la giuria pesa come problema, storia e misura; Core ha il meccanismo che rende vera la frase «ogni assioma ha la sua fonte» e che fa cambiare le risposte nel tempo. Il piano (§3) aveva già mappato i concetti di Core su quelli di Prodotto: qui si fissa quale dei due è la fonte di verità.
- **Punti deboli che restano** [dichiarati]: la disposizione della cella è un dato di scenario scritto da noi (macchine, manuali e legge sono reali); i manuali non sono ancora stati letti; il caso del braccio costa tempo al motore, e se alle 13:45 i manuali non ci sono resta come «prossimo test»; le 5 domande tenute da parte sono scelte, non estratte a caso; nessuna domanda copre gli atti del lato fabbrica; nessuna voce reale di un costruttore finora.
- **Alternative scartate:** tenere due progetti (due mezzi prodotti alle 16:45); il Turtle come fonte di verità (si perdono stato, conflitti e storia); il cancello anche su A (non sarebbe più «il modo usuale»).
- **Sostituisce:** — . Integra `1135-architettura` e `1200-due-regimi-catalogo`.
