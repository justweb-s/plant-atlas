# Tabellone ricerca libera / RAG / A / B

Generato da `python -m evaluation.board` su `data/cq/cqs.json`. ✓ giusta · ✗ sbagliata · ? «non lo so» · «Non lo so» a torto = ha detto di non saperlo ma la risposta c'era · un numero = giusta in parte · — non lanciata.

## Domande di progetto

| | Giuste | «Non lo so» a torto | Sbagliate | Media |
|---|---|---|---|---|
| Free search (model + folder) | 13/22 | 2 | 7 | 0.69 |
| RAG | 11/22 | 7 | 4 | 0.55 |
| A (free extraction) | 7/22 | 8 | 7 | 0.41 |
| B (checked facts) | 17/22 | 2 | 3 | 0.83 |

## Domande tenute da parte (quelle oneste)

| | Giuste | «Non lo so» a torto | Sbagliate | Media |
|---|---|---|---|---|
| Free search (model + folder) | 9/12 | 2 | 1 | 0.75 |
| RAG | 4/12 | 8 | 0 | 0.33 |
| A (free extraction) | 4/12 | 5 | 3 | 0.33 |
| B (checked facts) | 9/12 | 2 | 1 | 0.75 |

## Solo le domande sui documenti che B ha già letto (`CORR`, `DIR`, `DLGS69`, `DLGS70`, `DLGS71`, `DLGS72`, `DLGS73`, `DLGSALLVII`, `DM2011`, `REG`, `igea-equipment`, `inail-guide`, `mastar-manual`, `nanoscan3-manual`, `robot-cell-sheet`, `unict-guideline`, `univpm-guideline`, `ur10e-manual`, `ur5e-manual`), progetto e tenute insieme

| | Giuste | «Non lo so» a torto | Sbagliate | Media |
|---|---|---|---|---|
| Free search (model + folder) | 22/31 | 2 | 7 | 0.78 |
| RAG | 15/31 | 12 | 4 | 0.52 |
| A (free extraction) | 11/31 | 10 | 10 | 0.42 |
| B (checked facts) | 26/31 | 2 | 3 | 0.88 |

## Domanda per domanda

| CQ | Parte | B ha letto i documenti? | Free search (model + folder) | RAG | A (free extraction) | B (checked facts) |
|---|---|---|---|---|---|---|
| CQ01 | progetto | sì | ✓ | ? | 0.60 | ✓ |
| CQ02 | progetto | sì | 0.67 | 0.67 | 0.67 | ✓ |
| CQ03 | progetto | sì | ✓ | ✓ | ✓ | ✓ |
| CQ04 | progetto | sì | ✓ | ✓ | ✓ | ✓ |
| CQ05 | progetto | sì | 0.50 | ? | 0.22 | 0.57 |
| CQ06 | progetto | sì | ✓ | ✓ | ✓ | ✓ |
| CQ07 | progetto | sì | 0.50 | 0.40 | ✗ | 0.80 |
| CQ08 | progetto | sì | ✓ | ✓ | ✓ | ✓ |
| CQ09 | progetto | sì | ✗ | ? | ✓ | ✓ |
| CQ10 | progetto | sì | ✓ | ✗ | ✗ | ✓ |
| CQ11 | progetto | sì | 0.50 | ✓ | ? | ✓ |
| CQ12 | progetto | sì | ✓ | ✓ | ? | ✓ |
| CQ13 | progetto | no | ✗ | ? | ? | ✗ |
| CQ14 | progetto | no | ? | ? | ? | ? |
| CQ15 | progetto | no | ? | ? | ? | ? |
| CQ16 | tenuta | sì | ✓ | ? | ? | ✓ |
| CQ17 | tenuta | sì | ✓ | ✓ | ✗ | ✓ |
| CQ18 | tenuta | sì | ✓ | ? | ✓ | ✓ |
| CQ19 | tenuta | sì | ? | ? | ? | ? |
| CQ20 | tenuta | sì | ? | ? | ? | ? |
| CQ21 | progetto | sì | ✓ | ? | ? | ✓ |
| CQ22 | progetto | sì | ✓ | ✗ | ✗ | ✓ |
| CQ23 | progetto | sì | ✗ | ✓ | 0.50 | ✓ |
| CQ24 | progetto | sì | ✓ | ✓ | ? | ✓ |
| CQ25 | progetto | sì | ✓ | ✓ | ✓ | ✓ |
| CQ26 | progetto | sì | ✓ | ✓ | ? | ✓ |
| CQ27 | progetto | sì | ✓ | ✓ | ✓ | ✓ |
| CQ28 | tenuta | sì | ✓ | ? | ? | ✓ |
| CQ29 | tenuta | sì | ✗ | ? | ✗ | ✗ |
| CQ30 | tenuta | sì | ✓ | ? | ✗ | ✓ |
| CQ31 | tenuta | sì | ✓ | ✓ | ✓ | ✓ |
| CQ32 | tenuta | sì | ✓ | ✓ | ? | ✓ |
| CQ33 | tenuta | sì | ✓ | ✓ | ✓ | ✓ |
| CQ34 | tenuta | sì | ✓ | ? | ✓ | ✓ |
