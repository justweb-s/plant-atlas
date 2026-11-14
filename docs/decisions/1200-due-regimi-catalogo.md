# 1200 — Due regimi, il catalogo di un costruttore, domande tenute da parte

- **Stato:** in vigore, in parte superata da `1315-caso-unico-cella-robotizzata` (cliente, domanda principale, catalogo di fantasia al posto delle macchine reali)
- **Quando:** 2026-11-14 12:00
- **Chi:** Prodotto, da confermare con Core
- **Contesto:** la versione delle 11:35 era troppo da manuale. Le domande sulla legge erano da libro di testo, la fabbrica era un giocattolo scritto da noi, la rettifica cambia una data sola, e la strategia B veniva valutata sulle stesse domande da cui ricava lo schema.
- **Decisione:**
  - Il corpus contiene i due regimi: Direttiva 2006/42/CE e Regolamento (UE) 2023/1230, con la rettifica e il D.Lgs. 81/08. La tavola di concordanza ufficiale (Allegato XII del Regolamento) è il riferimento per misurare cosa cambia.
  - La fabbrica diventa il catalogo di un costruttore di fantasia: 5 modelli, ognuno con il percorso di conformità che segue oggi. La domanda principale è: quali modelli dal 20/1/2027 devono passare da un organismo notificato?
  - Le domande diventano 20: 15 di progetto (`split: design`) e 5 tenute da parte (`split: heldout`) sul cambio di regime. Il codice in `atlas/` legge solo quelle di progetto, e un test lo controlla.
  - Al cliente consegniamo una scheda d'impatto per modello (cosa cambia, quale procedura, quali requisiti nuovi, ogni riga con la sua fonte). L'ontologia è il motore e la traccia per un controllo.
- **Perché:** sui testi ufficiali [verificato]: con la Direttiva un ponte sollevatore per veicoli costruito secondo norme armonizzate complete si autocertifica (Art. 12(3)(a)). Con il Regolamento è nell'Allegato I parte A e serve un organismo notificato (Art. 25(2)). I componenti di sicurezza a machine learning sono categorie nuove (parte A, punti 5–6). Il requisito 1.1.9 (protezione contro la corruzione) non esiste nella Direttiva. È un problema reale, con costi e tempi per il costruttore, e la base documentale di un'azienda mescola i due regimi.
- **Alternative scartate:** restare sulla versione delle 11:35 (problema poco reale); usare manuali veri di costruttori (coperti da copyright).
- **Sostituisce:** in `1115-track-ontologia` la persona e la domanda principale (dalla fabbrica al costruttore); in `1125-competency-questions` l'insieme delle domande (da 15 a 20, con hold-out) e la fabbrica (diventa il catalogo).
