# Tabellone RAG / A / B

Generato da `python -m evaluation.board` su `data/cq/cqs.json`. ✓ giusta · ✗ sbagliata · ? «non lo so» · un numero = giusta in parte · — non lanciata.

## Domande di progetto

| | Giuste | «Non lo so» | Sbagliate | Media |
|---|---|---|---|---|
| RAG | 10/22 | 8 | 4 | 0.48 |
| A (free extraction) | non lanciata | | | |
| B (checked facts) | 14/22 | 3 | 5 | 0.73 |

## Domande tenute da parte (quelle oneste)

| | Giuste | «Non lo so» | Sbagliate | Media |
|---|---|---|---|---|
| RAG | 6/12 | 5 | 1 | 0.50 |
| A (free extraction) | non lanciata | | | |
| B (checked facts) | 4/12 | 3 | 5 | 0.36 |

## Solo le domande sui documenti che B ha già letto (`CORR`, `DIR`, `DLGS69`, `DLGS70`, `DLGS71`, `DLGS72`, `DLGS73`, `DLGSALLVII`, `DM2011`, `REG`, `igea-equipment`, `inail-guide`, `mastar-manual`, `nanoscan3-manual`, `robot-cell-sheet`, `unict-guideline`, `univpm-guideline`, `ur10e-manual`, `ur5e-manual`), progetto e tenute insieme

| | Giuste | «Non lo so» | Sbagliate | Media |
|---|---|---|---|---|
| RAG | 16/31 | 10 | 5 | 0.54 |
| A (free extraction) | non lanciata | | | |
| B (checked facts) | 18/31 | 3 | 10 | 0.66 |

## Domanda per domanda

| CQ | Parte | B ha letto i documenti? | RAG | A (free extraction) | B (checked facts) |
|---|---|---|---|---|---|
| CQ01 | progetto | sì | ✗ | — | 0.55 |
| CQ02 | progetto | sì | 0.67 | — | 0.67 |
| CQ03 | progetto | sì | ✓ | — | ✓ |
| CQ04 | progetto | sì | ✓ | — | ✓ |
| CQ05 | progetto | sì | ? | — | ✗ |
| CQ06 | progetto | sì | ✓ | — | ✓ |
| CQ07 | progetto | sì | ✓ | — | 0.33 |
| CQ08 | progetto | sì | ✓ | — | ✓ |
| CQ09 | progetto | sì | ✗ | — | ✓ |
| CQ10 | progetto | sì | ✗ | — | ✓ |
| CQ11 | progetto | sì | ✓ | — | ✓ |
| CQ12 | progetto | sì | ? | — | ✓ |
| CQ13 | progetto | no | ? | — | ? |
| CQ14 | progetto | no | ? | — | ? |
| CQ15 | progetto | no | ? | — | ? |
| CQ16 | tenuta | sì | ? | — | 0.33 |
| CQ17 | tenuta | sì | ✓ | — | ✓ |
| CQ18 | tenuta | sì | ✓ | — | ✗ |
| CQ19 | tenuta | sì | ? | — | ? |
| CQ20 | tenuta | sì | ? | — | ? |
| CQ21 | progetto | sì | ? | — | ✓ |
| CQ22 | progetto | sì | ✓ | — | ✓ |
| CQ23 | progetto | sì | ? | — | 0.50 |
| CQ24 | progetto | sì | ✓ | — | ✓ |
| CQ25 | progetto | sì | ? | — | ✓ |
| CQ26 | progetto | sì | ✓ | — | ✓ |
| CQ27 | progetto | sì | ✓ | — | ✓ |
| CQ28 | tenuta | sì | ✗ | — | ✓ |
| CQ29 | tenuta | sì | ✓ | — | ✗ |
| CQ30 | tenuta | sì | ? | — | ? |
| CQ31 | tenuta | sì | ✓ | — | ✗ |
| CQ32 | tenuta | sì | ✓ | — | ✓ |
| CQ33 | tenuta | sì | ✓ | — | ✓ |
| CQ34 | tenuta | sì | ? | — | ✗ |
