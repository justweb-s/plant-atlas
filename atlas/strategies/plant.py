"""Owner: Core. Facts that code can read without a model: the Annex VII table and the plant's device list.

Three groups, two files under ontology/B/parts/:
- law_verification.json: one verificationInterval fact per Annex VII row (code), plus the time limits of the
  ministerial decree of 11 April 2011, art. 1 to 3 (model pointing, strategy B), with the sixty-day limit
  marked as losing to the forty-five days of D.Lgs. 81/08 art. 71 c. 11.
- plant_igea.json: kind, capacity and year of construction of each lifting device of the plant's list.

Every fact goes through Store.write_statement, so every quote is in the chunk it names.
Run: python -m atlas.strategies.plant
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

from atlas.ontology.statements import ChunkCorpus, Statement, Store, norm

ROOT = Path(__file__).resolve().parents[2]
PARTS = ROOT / "ontology" / "B" / "parts"
PDF = ROOT / "runtime" / "docs" / "igea-scheda-tecnica-apparecchi-sollevamento.pdf"
PLANT_SOURCE = "igea-equipment"

# The periodicity words of Annex VII, as ISO durations.
PERIODS = {"annuale": "P1Y", "annuali": "P1Y", "biennale": "P2Y", "biennali": "P2Y", "triennale": "P3Y",
           "triennali": "P3Y", "quadriennale": "P4Y", "quinquennale": "P5Y", "decennale": "P10Y"}
LIFTING = "Apparecchi di sollevamento materiali"


# ---- 1. Annex VII ---------------------------------------------------------------------------------------
def annex_candidates(chunks) -> list[Statement]:
    """One fact per row and per kind of verification named in the row. Rows code cannot read become open points."""
    out = []
    for chunk in chunks:
        if chunk.source != "DLGSALLVII" or " | " not in chunk.text:
            continue
        row = int(re.search(r"\d+", chunk.locator).group())
        description, periodicity = (part.strip() for part in chunk.text.rsplit(" | ", 1))
        subject, condition = _subject_and_condition(description)
        typed = re.findall(r"((Verifica di funzionamento|Visita interna|Verifica di integrità): (\w+))", periodicity)
        plain = re.fullmatch(r"Verific(?:a|he) (\w+)", periodicity)
        found = [(written, word, kind) for written, kind, word in typed] if typed else \
            [(periodicity, plain.group(1), "")] if plain else []
        common = dict(subject=subject, quote=chunk.text, source_doc=chunk.source, anchor=chunk.locator,
                      asserted_by="code:annex_vii")
        if not found or any(word not in PERIODS for _, word, _ in found):
            out.append(Statement(predicate="openPoint", object="periodicity not read by code", object_as_written="",
                                 status="open_point", id=f"law_verification-annex7-r{row:02d}-open", **common))
            continue
        for index, (written, word, kind) in enumerate(found):
            suffix = f"-{index + 1}" if len(found) > 1 else ""
            out.append(Statement(
                predicate="verificationInterval", object=PERIODS[word], object_as_written=written,
                object_normalised=PERIODS[word], condition="; ".join(p for p in (condition, kind) if p),
                id=f"law_verification-annex7-r{row:02d}{suffix}", **common))
    return out


def _subject_and_condition(description: str) -> tuple[str, str]:
    """The lifting rows share one subject and differ by their conditions; other rows keep their own words."""
    if description.startswith(LIFTING):
        return LIFTING, description[len(LIFTING):].strip(" ,")
    match = re.search(r",? (con diametro|aventi|operanti con) ", description)
    if match:
        return description[:match.start()].strip(), description[match.start():].strip(" ,")
    return description, ""


# ---- 2. the decree of 11 April 2011 -----------------------------------------------------------------------
def decree_candidates(chunks) -> tuple[list[Statement], dict]:
    """Strategy B's pointing extraction on art. 1 to 3 (four chunks, four cached model calls)."""
    from atlas.strategies import b

    out, usage = [], {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0}
    for chunk in chunks:
        if chunk.source == "DM2011" and re.match(r"art\. [123](,|$)", chunk.locator):
            statements, used = b.extract(chunk)
            usage["calls"] += 1
            for key in ("prompt_tokens", "completion_tokens"):
                usage[key] += int((used or {}).get(key, 0) or 0)
            out += statements
    return out, usage


def settle_first_verification(store: Store, main_statements: list[dict]) -> str:
    """Sixty days (ministerial decree) against forty-five days (legislative decree): the higher source wins.

    Returns the id of the winning fact, or "" if the documents in the store do not hold both sides.
    """
    winner = next((s for s in main_statements if s["source_doc"] == "DLGS71" and s["predicate"] == "hasTimeLimit"
                   and (s.get("object_normalised") or s["object"]) == "P45D" and s["status"] == "current"), None)
    if winner is None:
        return ""
    settled = False
    for fact in store.statements:
        if (fact.source_doc == "DM2011" and fact.predicate == "hasTimeLimit"
                and "sessanta giorni" in fact.object_as_written.lower()):
            fact.status, fact.conflicts_with, settled = "conflict", winner["id"], True
    return winner["id"] if settled else ""


# ---- 3. the plant's device list -------------------------------------------------------------------------
def layout_pages() -> list[str]:
    """The pages of the device list with their columns kept (the chunks hold the same words, spaces collapsed)."""
    cache = PDF.with_suffix(".pages.json")
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    if PDF.exists() and shutil.which("pdftotext"):
        return subprocess.run(["pdftotext", "-layout", str(PDF), "-"], capture_output=True, text=True).stdout.split("\f")
    return []


def _runs(line: str) -> list[tuple[int, str]]:
    """(column, text) of each cell of a layout line; cells are separated by two spaces or more."""
    return [(m.start(), m.group()) for m in re.finditer(r"\S+(?: \S+)*", line)]


def parse_devices(pages: list[str]) -> list[dict]:
    """Tables A1..A6 (Allegato A) -> one record per position. A value that is not on the page stays None."""
    devices = []
    for number, page in enumerate(pages, start=1):
        if "TABELLA A" not in page:
            continue
        lines = page.splitlines()
        heads = {i: m.group(1) for i, line in enumerate(lines) if (m := re.match(r"\s{0,6}(\d{1,2})\s{2,}\S", line))}
        for i, position in heads.items():
            # The lines of the same table cell block: up and down to a blank line or another position line.
            block = [i]
            for step in (-1, 1):
                j = i + step
                while 0 <= j < len(lines) and lines[j].strip() and j not in heads and "TABELLA" not in lines[j] \
                        and not re.match(r"(?i)\s*pos\s", lines[j]):
                    block.append(j)
                    j += step
            block.sort()
            cells = _runs(lines[i])[1:]
            kind_lines = [j for j in block if any(col < 20 and not text.isdigit() for col, text in _runs(lines[j]))]
            kind_parts = [next(text for col, text in _runs(lines[j]) if col < 20 and not text.isdigit())
                          for j in kind_lines]
            if kind_parts and cells and cells[0][1] == kind_parts[kind_lines.index(i)] if i in kind_lines else False:
                cells = cells[1:]
            texts = [text for _, text in cells]
            cap_at = next((k for k, t in enumerate(texts) if t.isdigit()), None)
            year_at = next((k for k, t in enumerate(texts) if re.fullmatch(r"(19|20)\d\d", t)
                            and (cap_at is None or k > cap_at)), None)
            if year_at is None and cap_at is not None and re.fullmatch(r"(19|20)\d\d", texts[cap_at]):
                cap_at, year_at = None, cap_at   # the only number on the line is the year
            capacity, capacity_note = (int(texts[cap_at]) if cap_at is not None else None), ""
            block_text = norm(" ".join(lines[j] for j in block))
            declassed = re.search(r"(\d+) K? ?declass\..*? (\d+)$", block_text)
            if capacity is None and declassed:
                capacity, capacity_note = int(declassed.group(2)), f"declass. (da {declassed.group(1)})"
            first, last = (min(kind_lines), max(kind_lines)) if kind_lines else (i, i)
            make = " ".join(text for j in block for col, text in _runs(lines[j]) if 20 <= col < 38
                            and not text.isdigit()) or (texts[0] if cap_at else "")
            devices.append({
                "position": int(position), "kind": " ".join(kind_parts).replace("'", "").strip() or None,
                "kind_parts": kind_parts, "make_model": make or None, "capacity_kg": capacity,
                "capacity_note": capacity_note, "year_built": int(texts[year_at]) if year_at is not None else None,
                "page": f"p. {number}", "line_quote": norm(lines[i]),
                "kind_quote": norm(" ".join(lines[first:last + 1])),
                "block_quote": block_text if capacity_note else norm(lines[i]),
            })
    return sorted(devices, key=lambda d: d["position"])


def device_candidates(devices: list[dict], chunks) -> list[Statement]:
    out = []
    for d in devices:
        subject = f"IGEA device {d['position']}"
        common = dict(subject=subject, source_doc=PLANT_SOURCE, anchor=d["page"], asserted_by="code:plant_register",
                      kind="observed")
        key = f"plant_igea-d{d['position']:02d}"
        if d["kind"]:
            out.append(Statement(predicate="deviceKind", object=d["kind"], object_as_written=d["kind_parts"][0],
                                 object_normalised=d["kind"].lower(), quote=d["kind_quote"], id=f"{key}-kind", **common))
        if d["capacity_kg"] is not None:
            out.append(Statement(predicate="capacityKg", object=str(d["capacity_kg"]),
                                 object_as_written=str(d["capacity_kg"]), object_normalised=str(d["capacity_kg"]),
                                 condition=d["capacity_note"], quote=d["block_quote"], id=f"{key}-capacity", **common))
        if d["year_built"] is not None:
            out.append(Statement(predicate="yearBuilt", object=str(d["year_built"]),
                                 object_as_written=str(d["year_built"]), object_normalised=str(d["year_built"]),
                                 quote=d["line_quote"], id=f"{key}-year", **common))
    for chunk in chunks:   # where the devices are: the list places all of them in mining areas
        match = chunk.source == PLANT_SOURCE and re.search(r"Qtà COMUNE Area mineraria .*? Miniera Furtei", chunk.text)
        if match:
            out.append(Statement(subject="IGEA site", predicate="siteSector", object="estrattivo",
                                 object_as_written="Area mineraria", object_normalised="estrattivo",
                                 quote=match.group(), source_doc=PLANT_SOURCE, anchor=chunk.locator,
                                 asserted_by="code:plant_register", kind="observed", id="plant_igea-site-sector"))
    return out


def device_records(statements) -> list[dict]:
    """The devices as the rule wants them, rebuilt from the facts (so the answer cites fact ids)."""
    devices: dict[int, dict] = {}
    sector = next((s for s in statements if s.predicate == "siteSector" and s.status == "current"), None)
    for s in statements:
        match = re.fullmatch(r"IGEA device (\d+)", s.subject)
        if not match or s.status != "current":
            continue
        d = devices.setdefault(int(match.group(1)), {"position": int(match.group(1)), "facts": {}})
        field = {"deviceKind": "kind", "capacityKg": "capacity_kg", "yearBuilt": "year_built"}.get(s.predicate)
        if field:
            d[field] = s.object if field == "kind" else int(s.object)
            d["facts"][field] = s.id
    for d in devices.values():
        if sector:
            d["sector"], d["facts"]["sector"] = sector.object, sector.id
    return [devices[k] for k in sorted(devices)]


# ---- build ----------------------------------------------------------------------------------------------
def _write(store: Store, candidates: list[Statement]) -> None:
    for candidate in candidates:
        stored = store.write_statement(candidate)
        if stored is not None and stored.status == "proposed":
            stored.status = "current"


def build() -> dict:
    from atlas.corpus.chunker import load

    chunks = list(load())
    corpus = ChunkCorpus(chunks)
    main = json.loads((ROOT / "ontology" / "B" / "statements.json").read_text())["statements"]

    law = Store(corpus, PARTS / "law_verification.json")
    _write(law, annex_candidates(chunks))
    annex_counts = dict(law.counts())
    decree, usage = decree_candidates(chunks)
    for index, candidate in enumerate(decree, start=1):
        candidate.id = f"law_verification-dm2011-{index:02d}"
    _write(law, decree)
    winner = settle_first_verification(law, main)
    law.save()

    plant = Store(corpus, PARTS / "plant_igea.json")
    devices = parse_devices(layout_pages())
    _write(plant, device_candidates(devices, chunks))
    plant.save()
    return {"annex": annex_counts, "law": law.counts(), "plant": plant.counts(), "devices": devices,
            "usage": usage, "conflict_winner": winner, "law_store": law, "plant_store": plant}


def table(law_statements, plant_statements, days) -> list[str]:
    from atlas.ontology.rules import verification_interval

    annex = [s for s in law_statements if s.predicate == "verificationInterval"]
    lines = ["pos | kind | kg | year | " + " | ".join(f"{day} (row)" for day in days)]
    for d in device_records(plant_statements):
        cells = []
        for day in days:
            result = verification_interval(d, annex, day)
            row = re.search(r"r(\d+)", result.get("row_id", "") or "")
            cells.append(f"{result['interval']} ({int(row.group(1))})" if result["interval"] else f"unknown: {result['why']}")
        lines.append(f"{d['position']} | {d.get('kind', '?')} | {d.get('capacity_kg', '?')} | {d.get('year_built', '?')} | "
                     + " | ".join(cells))
    return lines


def main() -> None:
    from datetime import date

    result = build()
    for name in ("annex", "law", "plant", "usage", "conflict_winner"):
        print(name, result[name])
    print("devices parsed:", len(result["devices"]))
    for store in (result["law_store"], result["plant_store"]):
        for rejection in store.rejections:
            s = rejection["statement"]
            print("REJECTED", rejection["reason"], s["source_doc"], s["anchor"], s["predicate"], s["object_as_written"])
    print("\n".join(table(result["law_store"].statements, result["plant_store"].statements,
                          [date(2019, 6, 1), date(2026, 11, 14)])))


if __name__ == "__main__":
    main()
