# 1450 — Il gold si allarga: l'elenco IGEA come caso principale, più le macchine reali

- **Stato:** in vigore
- **Quando:** 2026-11-14 14:50
- **Chi:** Core + Prodotto (proposta di Core alle 14:35 in `notes/core.md`, sì di Prodotto a voce)
- **Contesto:** il corpus ha ora cinque strati con documenti reali, tra cui l'elenco dei 24 apparecchi di sollevamento di IGEA S.p.A. e i quattro manuali delle macchine della cella. Le 20 domande del gold riguardano solo la legge e un catalogo di fantasia.
- **Decisione:** 14 domande nuove, CQ21–CQ34 (7 di progetto, 7 tenute da parte), aggiunte in coda: le 20 esistenti non cambiano. Il caso principale è «ogni quanto va verificato questo apparecchio di IGEA?», che incrocia la riga dell'Allegato VII (tipo fisso o mobile, settore, età) con l'elenco. La cella robotizzata resta la seconda scena. Nuovo tipo di risposta `unknown`: per CQ31 («è scaduta oggi?») l'unica risposta giusta è «non lo so», perché le date delle ultime verifiche non sono nel documento.
- **Perché:** è la domanda dell'RSPP («cosa devo fare, ed entro quando») su dati reali [verificato: scheda tecnica IGEA, sha256 in `atlas/corpus/incoming/documents.csv`; Allegato VII in `data/law/`]. CQ28 e CQ29 sono la stessa gru a due anni di distanza: la risposta cambia perché cambia l'età, non la legge. Le domande sono committate prima che la strategia B giri sui manuali e sui documenti di stabilimento.
- **Ipotesi scritte nel gold (`about.assumptions`):** IGEA lavora in aree minerarie, quindi valgono le righe del settore «estrattivo» [dichiarato: la scheda parla di «area mineraria», non di modalità di utilizzo]; la «piattaforma elevatrice» HINOWA è una piattaforma di lavoro mobile elevabile [non verificato sul libretto]. Se un esperto le corregge, si corregge il gold con un commit `gold:` e si rifanno girare tutti i metodi.
- **Alternative scartate:** riscrivere CQ13–CQ20 sulle macchine reali (cambierebbe domande già misurate); chiedere «è scaduto?» per tutti i 24 apparecchi (le date non ci sono: una sola domanda basta a misurare il «non lo so»).
- **Sostituisce:** — (completa 1315-caso-unico-cella-robotizzata)
