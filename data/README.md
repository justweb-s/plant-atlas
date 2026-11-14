# Data

Owner: Product. Everything here is either an official text or written on 14 November 2026 for the demo; every AI tool used to write data goes in `../AI_TOOLS.md`.

| Folder | What |
|---|---|
| `law/` | official law texts: Directive 2006/42/EC, Reg. (EU) 2023/1230, its corrigendum, D.Lgs. 81/2008 artt. 69–73. Sources and download commands in `law/SOURCES.md` |
| `cq/` | `cqs.json`: the 20 competency questions (15 design, 5 held out) with gold answers, quotes and expected terms, plus the catalogue facts. Written before building; changed only with `gold:` commits |
| `machines/` | the real machines of the cell (UR5e, UR10e, SICK nanoScan3, MAHA MA STAR): links, sha256 and short verified quotes from the manufacturers' public manuals. The PDFs are not committed; `python data/machines/fetch.py` downloads and checks them |
| `catalogue/` | the product sheets of a fictional machinery manufacturer (5 models), written to match the `catalogue` block of `cq/cqs.json` |

No documents of real manufacturers in git (only links, fingerprints and short quotes), no people.
