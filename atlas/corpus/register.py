"""Register the corpus before anything reads it.

Owner: Core. Reads atlas/corpus/incoming/sources.csv, downloads a source when its raw file is
missing and it has a URL, splits every raw file into sections, and writes incoming/registry.csv
with a sha256 per document and per section. A source that cannot be downloaded is reported,
never silently replaced: save it by hand into incoming/raw/<doc_id>.html (or .txt / .md) and run
this again. The texts in incoming/ wait for Product to move them into data/law (AGENTS.md §2).

Run: python -m atlas.corpus.register
"""
from __future__ import annotations

import csv
import hashlib
import re
import sys
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

import urllib.error
import urllib.request

HERE = Path(__file__).resolve().parent / "incoming"
SOURCES = HERE / "sources.csv"
RAW = HERE / "raw"
DOCS = HERE / "docs"
REGISTRY = HERE / "registry.csv"
FIELDS = ["id", "doc_id", "anchor", "kind", "version", "in_force_from", "fictional",
          "source", "retrieved", "sha256", "path", "heading"]

HEADING = re.compile(
    r"^(#{1,4}\s+\S.*|Article\s+\d+[a-z]*\b.*|Art\.\s*\d+.*|Articolo\s+\d+.*|"
    r"ANNEX\s+[IVXLC]+\b.*|ALLEGATO\s+[IVXLC]+\b.*|Allegato\s+[IVXLC]+\b.*)$"
)
BLOCK_TAGS = {"p", "div", "br", "tr", "li", "table", "h1", "h2", "h3", "h4", "h5", "h6"}


class _Text(HTMLParser):
    """HTML to plain text: one line per block, table cells joined with ' | '."""

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1
        elif tag in BLOCK_TAGS:
            self.parts.append("\n")
        elif tag in ("td", "th"):
            self.parts.append(" | ")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip = max(0, self.skip - 1)
        elif tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def to_text(raw: Path) -> str:
    content = raw.read_text(encoding="utf-8", errors="replace")
    if raw.suffix == ".html":
        parser = _Text()
        parser.feed(content)
        content = "".join(parser.parts)
    lines = [re.sub(r"[ \t ]+", " ", line).strip() for line in content.splitlines()]
    return "\n".join(line for line in lines if line)


def slug(heading: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", heading.lower()).strip("-")[:48] or "section"


MD_HEADING = re.compile(r"^#{1,4}\s+\S.*$")


def split_sections(text: str, markdown: bool = False) -> list[tuple[str, str, str]]:
    """Return (anchor, heading, body) per section; text before the first heading is 'preamble'.

    A .md raw file was already cut into sections when it was saved: only its '#' headings split it.
    """
    sections: list[tuple[str, str, list[str]]] = [("preamble", "", [])]
    seen: dict[str, int] = {}
    pattern = MD_HEADING if markdown else HEADING
    for line in text.splitlines():
        if pattern.match(line):
            anchor = slug(line)
            seen[anchor] = seen.get(anchor, 0) + 1
            if seen[anchor] > 1:
                anchor = f"{anchor}-{seen[anchor]}"
            sections.append((anchor, line.lstrip("# ").strip(), [line]))
        else:
            sections[-1][2].append(line)
    return [(a, h, "\n".join(body)) for a, h, body in sections if "\n".join(body).strip()]


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def find_raw(doc_id: str) -> Path | None:
    for suffix in (".html", ".md", ".txt", ".csv"):
        path = RAW / f"{doc_id}{suffix}"
        if path.exists():
            return path
    return None


def download(doc_id: str, url: str) -> Path | None:
    request = urllib.request.Request(url, headers={"User-Agent": "plant-atlas hackathon corpus fetch"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            content = response.read()
    except (urllib.error.URLError, TimeoutError) as error:
        print(f"FAIL download {doc_id}: {error}")
        return None
    path = RAW / f"{doc_id}.html"
    path.write_bytes(content)
    return path


def main() -> int:
    RAW.mkdir(exist_ok=True)
    DOCS.mkdir(exist_ok=True)
    for stale in DOCS.glob("*.txt"):  # sections are generated: rebuild them on every run
        stale.unlink()
    old = {}
    if REGISTRY.exists():
        with REGISTRY.open() as handle:
            old = {row["id"]: row for row in csv.DictReader(handle)}
    rows, missing = [], []
    with SOURCES.open() as handle:
        sources = list(csv.DictReader(handle))
    for source in sources:
        doc_id = source["doc_id"]
        raw = find_raw(doc_id) or (download(doc_id, source["url"]) if source.get("url") else None)
        if raw is None:
            missing.append(doc_id)
            continue
        text = to_text(raw)

        def row(row_id: str, anchor: str, body: str, path: Path, heading: str) -> dict:
            digest = sha(body)
            previous = old.get(row_id)
            retrieved = previous["retrieved"] if previous and previous["sha256"] == digest \
                else date.today().isoformat()
            return {"id": row_id, "doc_id": doc_id, "anchor": anchor, "kind": source["kind"],
                    "version": source["version"], "in_force_from": source.get("in_force_from", ""),
                    "fictional": source.get("fictional", ""), "source": source.get("url") or "written today",
                    "retrieved": retrieved, "sha256": digest,
                    "path": str(path.relative_to(HERE)), "heading": heading}

        rows.append(row(doc_id, "", text, raw, source.get("title", "")))
        for anchor, heading, body in split_sections(text, markdown=raw.suffix == ".md"):
            path = DOCS / f"{doc_id}__{anchor}.txt"
            path.write_text(body + "\n", encoding="utf-8")
            rows.append(row(f"{doc_id}#{anchor}", anchor, body, path, heading))
    with REGISTRY.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    documents = sum(1 for r in rows if not r["anchor"])
    print(f"registered {documents} documents, {len(rows) - documents} sections -> {REGISTRY.name}")
    for r in rows:
        print(f"  {r['id']:<60} {r['sha256'][:12]}  {r['kind']}")
    for doc_id in missing:
        print(f"MISSING {doc_id}: save it by hand as atlas/corpus/incoming/raw/{doc_id}.html and run again")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
