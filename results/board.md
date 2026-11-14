# Tabellone RAG / A / B

Generato da `python -m evaluation.board` su `data/cq/cqs.json`. ✓ giusta · ✗ sbagliata · ? «non lo so» · un numero = giusta in parte · — non lanciata.

## Domande di progetto

| | Giuste | «Non lo so» | Sbagliate | Media |
|---|---|---|---|---|
| RAG | 8/22 | 7 | 7 | 0.42 |
| A (free extraction) | non lanciata | | | |
| B (checked facts) | 8/22 | 7 | 7 | 0.41 |

## Domande tenute da parte (quelle oneste)

| | Giuste | «Non lo so» | Sbagliate | Media |
|---|---|---|---|---|
| RAG | 4/12 | 8 | 0 | 0.33 |
| A (free extraction) | non lanciata | | | |
| B (checked facts) | 2/12 | 9 | 1 | 0.17 |

## Solo le domande sui documenti che B ha già letto (`CORR`, `DIR`, `DLGS69`, `DLGS70`, `DLGS71`, `DLGS72`, `DLGS73`, `REG`), progetto e tenute insieme

| | Giuste | «Non lo so» | Sbagliate | Media |
|---|---|---|---|---|
| RAG | 6/18 | 6 | 6 | 0.40 |
| A (free extraction) | non lanciata | | | |
| B (checked facts) | 8/18 | 3 | 7 | 0.51 |

## Domanda per domanda

| CQ | Parte | B ha letto i documenti? | RAG | A (free extraction) | B (checked facts) |
|---|---|---|---|---|---|
| CQ01 | progetto | sì | ✗ | — | ✗ |
| CQ02 | progetto | sì | 0.67 | — | 0.67 |
| CQ03 | progetto | sì | ✓ | — | ✓ |
| CQ04 | progetto | sì | ✓ | — | ✓ |
| CQ05 | progetto | sì | ? | — | ✗ |
| CQ06 | progetto | sì | ✓ | — | ✓ |
| CQ07 | progetto | sì | 0.50 | — | 0.44 |
| CQ08 | progetto | sì | ✓ | — | ✓ |
| CQ09 | progetto | sì | ✗ | — | ✓ |
| CQ10 | progetto | sì | ✗ | — | ✗ |
| CQ11 | progetto | sì | ✓ | — | ✓ |
| CQ12 | progetto | sì | ✗ | — | ✓ |
| CQ13 | progetto | no | ? | — | ✗ |
| CQ14 | progetto | no | ? | — | ? |
| CQ15 | progetto | no | ? | — | ? |
| CQ16 | tenuta | sì | ? | — | ? |
| CQ17 | tenuta | sì | ✓ | — | ✓ |
| CQ18 | tenuta | sì | ? | — | ✗ |
| CQ19 | tenuta | sì | ? | — | ? |
| CQ20 | tenuta | sì | ? | — | ? |
| CQ21 | progetto | no | ? | — | ? |
| CQ22 | progetto | no | ✗ | — | ? |
| CQ23 | progetto | sì | ? | — | ✗ |
| CQ24 | progetto | no | ✓ | — | ✓ |
| CQ25 | progetto | no | ? | — | ? |
| CQ26 | progetto | no | ✓ | — | ? |
| CQ27 | progetto | no | ✓ | — | ? |
| CQ28 | tenuta | no | ? | — | ? |
| CQ29 | tenuta | no | ✓ | — | ? |
| CQ30 | tenuta | no | ? | — | ? |
| CQ31 | tenuta | no | ✓ | — | ✓ |
| CQ32 | tenuta | no | ? | — | ? |
| CQ33 | tenuta | no | ✓ | — | ? |
| CQ34 | tenuta | no | ? | — | ? |
