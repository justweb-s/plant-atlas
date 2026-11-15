"""Owner: Core. Rules that combine facts: which Annex VII row applies to one lifting device on one day.

The rule reads the rows from their facts (the conditions as written in D.Lgs. 81/08 Annex VII) and the device
from its facts. It returns the row and the reasons, or says what the documents leave open. It never guesses.
"""
from __future__ import annotations

import re
from datetime import date

# How the device kinds of a plant list map onto the two types the Annex names. Anything else is not decided here.
PLATFORM = r"\bPIATTAFORMA (ELEVATRICE|DI LAVORO)\b|\bELEVATING (WORK )?PLATFORM\b|\bMEWP\b"
PLATFORM_ROW = "Piattaforme di lavoro mobili elevabili"
KIND_TYPE = [
    (r"\bPER AUTOCARRO\b|\bAUTOGRU\b|\bGRU MOBILE\b|\bMOBILE CRANE\b|\bTRUCK CRANE\b", "mobile"),
    (r"\bA PONTE\b|\bA CAVALLETTO\b|\bPARANCO\b|\bOVERHEAD\b|\bGANTRY\b|\bHOIST\b", "fisso"),
]


def _get(fact, name: str) -> str:
    return str(fact.get(name, "") if isinstance(fact, dict) else getattr(fact, name, "") or "")


def read_row(fact) -> dict | None:
    """The conditions of one lifting-equipment row, read from the fact's own words. None for other rows."""
    words = f"{_get(fact, 'subject')} {_get(fact, 'condition')}"
    if "Apparecchi di sollevamento materiali" not in words:
        return None
    limit = re.search(r"portata superiore a (\d+) ?Kg", words)
    kind = "mobile" if "di tipo mobile o trasferibile" in words else "fisso" if "di tipo fisso" in words else None
    sectors = re.search(r"settori di impiego quali ([^|]+?)(?: e con |$)", words)
    use = "sector" if sectors else "regular" if "utilizzo regolare" in words else None
    age = "new" if "non antecedente 10 anni" in words else "old" if "antecedente 10 anni" in words else None
    if not limit or not kind or not use:
        return None
    return {"id": _get(fact, "id"), "interval": _get(fact, "object_normalised") or _get(fact, "object"),
            "min_kg": int(limit.group(1)), "type": kind, "use": use, "age": age,
            "sectors": [s.strip() for s in sectors.group(1).split(",")] if sectors else []}


def verification_interval(device: dict, annex_facts: list, on: date) -> dict:
    """device: {"kind", "capacity_kg", "year_built", "sector", optional "facts": {field: fact id}}."""
    ids = device.get("facts") or {}
    rows = [row for row in map(read_row, annex_facts) if row]
    if not rows:
        return {"interval": None, "why": "no Annex VII row for lifting equipment among the facts"}
    kind = str(device.get("kind") or "").upper().replace("'", "")
    if re.search(PLATFORM, kind):
        # Declared assumption (decision 1450, not verified on the machine's manual): an "elevating platform" of the
        # list is a mobile elevating work platform, which has a row of its own with no sector and no age.
        row = next((f for f in annex_facts if PLATFORM_ROW in f"{_get(f, 'subject')} {_get(f, 'condition')}"), None)
        if row is None:
            return {"interval": None, "why": "no Annex VII row for mobile elevating work platforms among the facts"}
        return {"interval": _get(row, "object_normalised") or _get(row, "object"), "row_id": _get(row, "id"),
                "because": [(ids.get("kind", ""), f"{device['kind']} is taken to be a mobile elevating work platform "
                             "(declared assumption, not verified on its manual)"),
                            (_get(row, "id"), "Annex VII row for mobile elevating work platforms: no sector, no age")]}
    kind_type = next((t for pattern, t in KIND_TYPE if re.search(pattern, kind)), None)
    if kind_type is None:
        return {"interval": None, "why": f"kind '{device.get('kind')}' is not mapped to fixed or mobile lifting equipment"}
    because = [(ids.get("kind", ""), f"{device['kind']} is lifting equipment of type "
                + ("mobile o trasferibile" if kind_type == "mobile" else "fisso") + " (mapping of the rule)")]
    capacity = device.get("capacity_kg")
    if capacity is None:
        return {"interval": None, "why": "capacity not known"}
    min_kg = rows[0]["min_kg"]
    if capacity <= min_kg:
        return {"interval": None, "why": f"capacity {capacity} kg is not above {min_kg} kg: no lifting row of Annex VII applies"}
    because.append((ids.get("capacity_kg", ""), f"capacity {capacity} kg is above {min_kg} kg"))
    sector = str(device.get("sector") or "").lower()
    if not sector:
        return {"interval": None, "why": "sector of use not known"}
    listed = any(sector in row["sectors"] for row in rows)
    use = "sector" if listed else "regular"
    because.append((ids.get("sector", ""), f"sector {sector}: " + ("named in the row" if listed else "regular use")))
    candidates = [row for row in rows if row["type"] == kind_type and row["use"] == use]
    if any(row["age"] for row in candidates):
        year = device.get("year_built")
        if year is None:
            return {"interval": None, "why": "year of construction not known"}
        # The row speaks of the YEAR of manufacture ("anno di fabbricazione [non] antecedente 10 anni"): years are
        # compared, so no month is needed. A year exactly ten years back is "not earlier than 10 years".
        old = int(year) < on.year - 10
        candidates = [row for row in candidates if row["age"] in (None, "old" if old else "new")]
        because.append((ids.get("year_built", ""), f"built in {year}: " + ("more" if old else "not more") + f" than 10 years before {on}"))
    intervals = {row["interval"] for row in candidates}
    if len(intervals) != 1:
        return {"interval": None, "why": "no single Annex VII row matches" if not candidates else "the matching rows disagree"}
    row = candidates[0]
    because.append((row["id"], f"Annex VII row for type {kind_type}, {use} use" + (f", age {row['age']}" if row["age"] else "")))
    return {"interval": row["interval"], "row_id": row["id"], "because": because}
