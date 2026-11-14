"""Download the real manuals into data/machines/raw/ (ignored by git), check their sha256, find every quote.

Owner: Product. The PDFs are copyrighted: only links, fingerprints and short quotes are committed.
Run: python data/machines/fetch.py           (downloads what is missing, then checks)
Exit code 1 if a fingerprint differs or a quote is not found: the manufacturer changed the file.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"


def norm(text: str) -> str:
    text = text.replace("’", "'").replace("-\n", "")
    return re.sub(r"\s+", "", text).lower()  # spaces dropped: pypdf joins or splits words at random


def main() -> int:
    spec = json.loads((HERE / "machines.json").read_text(encoding="utf-8"))
    RAW.mkdir(exist_ok=True)
    texts, bad = {}, 0
    for doc in spec["documents"]:
        path = RAW / doc["file"]
        if not path.exists():
            print("download", doc["id"])
            req = urllib.request.Request(doc["url"], headers={"User-Agent": "Mozilla/5.0"})
            path.write_bytes(urllib.request.urlopen(req, timeout=120).read())
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != doc["sha256"]:
            print("FAIL sha256", doc["id"], digest)
            bad += 1
            continue
        from pypdf import PdfReader  # needs `cryptography` for the MAHA file
        texts[doc["id"]] = norm("\n".join(p.extract_text() or "" for p in PdfReader(str(path)).pages))
        print("ok", doc["id"])
    for machine in spec["machines"]:
        for fact in machine["facts"]:
            text = texts.get(fact["doc"])
            if text is None:
                continue
            if norm(fact["quote"]) not in text:
                print("FAIL quote", machine["id"], fact["fact"], repr(fact["quote"]))
                bad += 1
    print("all quotes found" if not bad else f"{bad} problems")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
