# Law texts in this folder

All downloaded on 14 November 2026. The files are the official texts as published; nothing was edited except removing the website navigation from the Normattiva pages.

| File | What | Source |
|---|---|---|
| `eu-reg-2023-1230.en.xhtml` | Regulation (EU) 2023/1230 on machinery, as published in OJ L 165 of 29.6.2023 (English) | `https://publications.europa.eu/resource/celex/32023R1230` |
| `eu-reg-2023-1230-corrigendum-2023-07-04.en.xhtml` | Corrigendum, OJ L 169 of 4.7.2023, p. 35: 14 dates corrected (e.g. "14 January 2027" → "20 January 2027") | `https://publications.europa.eu/resource/celex/32023R1230R%2801%29` |
| `it-dlgs-81-2008-art69.txt` … `art73.txt` | D.Lgs. 9 aprile 2008, n. 81, Titolo III, artt. 69–73 (testo vigente) | `https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:decreto.legislativo:2008-04-09;81~art69` (and `~art70` … `~art73`) |

## How to download again

EUR-Lex answers scripts with an empty page. The EU Publications Office returns the full text:

```bash
curl -sSL -H "Accept: application/xhtml+xml" -H "Accept-Language: eng" -o eu-reg-2023-1230.en.xhtml "https://publications.europa.eu/resource/celex/32023R1230"
curl -sSL -H "Accept: application/xhtml+xml" -H "Accept-Language: eng" -o eu-reg-2023-1230-corrigendum-2023-07-04.en.xhtml "https://publications.europa.eu/resource/celex/32023R1230R%2801%29"
```

Italian version: `Accept-Language: ita` (not tried yet).

## Reuse

- EU legal texts: reuse is authorised with acknowledgement of the source (to be checked against the EUR-Lex legal notice).
- Italian laws: official acts of the State are excluded from copyright (art. 5, L. 633/1941) (to be checked).
- Harmonised standards (EN ISO 12100, 13849, …) are paid documents: only their codes may appear here.

## Not here yet

- D.Lgs. 81/08, Allegato VII (list of equipment subject to periodic verification).
- Directive 2006/42/EC (only needed for the "Should" change: Annex IV of the Directive → Annex I of the Regulation).
