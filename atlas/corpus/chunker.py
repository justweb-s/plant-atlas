"""Owner: Core. Cuts the law texts along their own structure: article and paragraph, annex and point.

Every chunk has a locator a person can check by hand ("Art. 25(2)", "Annex III, 1.3.7",
"Corrigendum, point 5", "art. 71, c. 11"). The text is the official text, untouched except for
whitespace. Exposed through atlas.api.corpus().
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from functools import lru_cache
from pathlib import Path

from atlas.contracts import Chunk

ROOT = Path(__file__).resolve().parents[2]
LAW = ROOT / "data" / "law"
INCOMING = ROOT / "atlas" / "corpus" / "incoming" / "raw"
XHTML = "{http://www.w3.org/1999/xhtml}"

# The texts the gold refers to: source key, file, version label.
EU_ACTS = [
    ("REG", LAW / "eu-reg-2023-1230.en.xhtml", "OJ L 165, 29.6.2023"),
    ("DIR", LAW / "eu-dir-2006-42.en.xhtml", "OJ L 157, 9.6.2006"),
]
CORRIGENDUM = ("CORR", LAW / "eu-reg-2023-1230-corrigendum-2023-07-04.en.xhtml", "OJ L 169, 4.7.2023")

NUMBERED = re.compile(r"^(\d+(?:\.\d+)*)\.?\s+\S")        # "1.3.7. Risks related to moving parts"
POINT = re.compile(r"^(\d+)\.$")                           # a table cell holding only "5."
PART = re.compile(r"^PART\s+([A-Z])\b", re.IGNORECASE)


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _text(element: ET.Element) -> str:
    return _clean(" ".join(element.itertext()))


def _tag(element: ET.Element) -> str:
    return element.tag.replace(XHTML, "")


def _articles(root: ET.Element, source: str, version: str) -> list[Chunk]:
    chunks = []
    for div in root.iter(f"{XHTML}div"):
        match = re.fullmatch(r"art_(\d+[a-z]*)", div.get("id", ""))
        if not match:
            continue
        number = match.group(1)
        title = next((_text(p) for p in div.iter(f"{XHTML}p") if p.get("class") == "oj-sti-art"), "")
        paragraphs = [d for d in div.iter(f"{XHTML}div") if re.fullmatch(r"\d{3}\.\d{3}", d.get("id", ""))]
        if not paragraphs:
            # no numbered paragraphs: a list of definitions "(16) ..." is cut point by point
            locator, lines = f"Art. {number}", []
            pieces = [(locator, lines)]
            for p in div.iter(f"{XHTML}p"):
                text = _text(p)
                marker = re.fullmatch(r"\((\d+)\)", text)
                if marker:
                    lines = []
                    pieces.append((f"Art. {number}({marker.group(1)})", lines))
                if text:
                    lines.append(text)
            for locator, lines in pieces:
                if lines:
                    chunks.append(Chunk(f"{source}:{locator.replace(' ', '')}", source, locator,
                                        " ".join(lines), version))
            continue
        for paragraph in paragraphs:
            k = int(paragraph.get("id").split(".")[1])
            body = _text(paragraph)
            chunks.append(Chunk(f"{source}:Art.{number}({k})", source, f"Art. {number}({k})",
                                f"Article {number} {title}. {body}" if title else body, version))
    return chunks


def _annexes(root: ET.Element, source: str, version: str) -> list[Chunk]:
    chunks: list[Chunk] = []
    seen: set[str] = set()
    for container in root.iter(f"{XHTML}div"):
        match = re.fullmatch(r"anx_([IVXLC]+)", container.get("id", ""))
        if not match or match.group(1) in seen:
            continue
        roman = match.group(1)
        seen.add(roman)
        locator, part, lines = f"Annex {roman}", "", []
        pieces: list[tuple[str, list[str]]] = [(locator, lines)]
        paragraphs = list(container.iter(f"{XHTML}p"))
        # an annex with numbered headings ("1.3.7. ...") is cut by them; a list annex by Part and point
        by_heading = any(p.get("class", "").startswith("oj-ti-grseq") and NUMBERED.match(_text(p))
                         for p in paragraphs)
        for p in paragraphs:
            text = _text(p)
            if not text:
                continue
            new_locator = None
            if by_heading:
                if p.get("class", "").startswith("oj-ti-grseq") and NUMBERED.match(text):
                    new_locator = f"Annex {roman}, {NUMBERED.match(text).group(1)}"
            elif PART.match(text):
                part = PART.match(text).group(1).upper()
                new_locator = f"Annex {roman}, Part {part}"
            elif part and POINT.match(text):
                new_locator = f"Annex {roman}, Part {part}, point {POINT.match(text).group(1)}"
            if new_locator:
                lines = []
                pieces.append((new_locator, lines))
            lines.append(text)
        counts: dict[str, int] = {}
        for locator, lines in pieces:
            if not lines:
                continue
            counts[locator] = counts.get(locator, 0) + 1
            suffix = "" if counts[locator] == 1 else f"#{counts[locator]}"
            chunks.append(Chunk(f"{source}:{locator.replace(' ', '')}{suffix}", source, locator,
                                " ".join(lines), version))
    return chunks


def _recitals(root: ET.Element, source: str, version: str) -> list[Chunk]:
    chunks = []
    for div in root.iter(f"{XHTML}div"):
        match = re.fullmatch(r"rct_(\d+)", div.get("id", ""))
        if match:
            chunks.append(Chunk(f"{source}:Recital{match.group(1)}", source, f"Recital {match.group(1)}",
                                _text(div), version))
    return chunks


def eu_act(source: str, path: Path, version: str) -> list[Chunk]:
    """An act as published in the Official Journal (XHTML from the EU Publications Office)."""
    root = ET.parse(path).getroot()
    return _recitals(root, source, version) + _articles(root, source, version) + _annexes(root, source, version)


def corrigendum(source: str, path: Path, version: str) -> list[Chunk]:
    text = _text(ET.parse(path).getroot())
    starts = [(m.start(), m.group(1)) for m in re.finditer(r"(?<!\d)(\d+)\.\s+On page", text)]
    chunks = []
    for i, (start, number) in enumerate(starts):
        end = starts[i + 1][0] if i + 1 < len(starts) else len(text)
        body = text[start:end].split(".", 1)[1].strip()
        chunks.append(Chunk(f"{source}:point{number}", source, f"Corrigendum, point {number}", body, version))
    return chunks


def italian_article(path: Path) -> list[Chunk]:
    """D.Lgs. 81/2008, one article per file: three header lines, then the text with numbered commi."""
    number = re.search(r"art(\d+)", path.name).group(1)
    source = f"DLGS{number}"
    version = "testo vigente, Normattiva, letto il 14.11.2026"
    body = _clean(path.read_text(encoding="utf-8").split("\n\n", 1)[1])
    found, expected = [], 1
    for match in re.finditer(r"(?:^|\s)(\d+)(-(?:bis|ter|quater|quinquies))?\.\s", body):
        k = int(match.group(1))
        if (match.group(2) and k == expected - 1) or (not match.group(2) and k == expected):
            found.append((match.start(), f"{k}{match.group(2) or ''}"))
            expected = k + 1
    if not found:
        return [Chunk(f"{source}:art", source, f"art. {number}", body, version)]
    chunks = []
    for i, (start, comma) in enumerate(found):
        end = found[i + 1][0] if i + 1 < len(found) else len(body)
        chunks.append(Chunk(f"{source}:c{comma}", source, f"art. {number}, c. {comma}",
                            body[start:end].strip(), version))
    return chunks


@lru_cache(maxsize=None)
def load(with_incoming: bool = True) -> tuple[Chunk, ...]:
    """The whole corpus. The gold's texts first; then the acts Core registered in incoming/."""
    chunks: list[Chunk] = []
    for source, path, version in EU_ACTS:
        chunks += eu_act(source, path, version)
    chunks += corrigendum(*CORRIGENDUM)
    for path in sorted(LAW.glob("it-dlgs-81-2008-art*.txt")):
        chunks += italian_article(path)
    if with_incoming:
        for path in sorted(INCOMING.glob("eu-*.html")):
            try:
                chunks += eu_act(path.stem, path, "as published in the Official Journal")
            except ET.ParseError:
                continue   # not well-formed XHTML: stays out of the chunks, still in the registry
    seen: dict[str, int] = {}
    for chunk in chunks:   # ids are unique: a repeated one gets a counter
        seen[chunk.id] = seen.get(chunk.id, 0) + 1
        if seen[chunk.id] > 1:
            chunk.id = f"{chunk.id}#{seen[chunk.id]}"
    return tuple(chunks)


def root_of(locator: str) -> str:
    """'Directive, Art. 12(3)(a)' -> 'Art. 12'; 'Annex III, 1.3.7' -> 'Annex III'; 'art. 71, c. 11' -> 'art. 71'."""
    match = re.search(r"(Art\. \d+[a-z]*|Annex [IVXLC]+|art\. \d+|Corrigendum, point \d+|Recital \d+)", locator)
    return match.group(1) if match else locator


def passage(source: str, locator: str) -> str:
    """The text of an article or annex as a whole: every chunk of that source under the same root, in order."""
    root = root_of(locator)
    return " ".join(c.text for c in load() if c.source == source and root_of(c.locator) == root)
