"""Owner: Core. What atlas.api calls when ATLAS_FAKE=0: the built ontology of a strategy, read from ontology/<strategy>/.

The extraction itself is run once (python -m atlas.strategies.b) and its results are committed,
so the app and the scoreboard never pay for it again.
"""
from __future__ import annotations

import json
from datetime import date
from functools import lru_cache
from pathlib import Path

from atlas.contracts import Answer, BuildResult, ValidationReport

ROOT = Path(__file__).resolve().parents[2]
PRICE_IN, PRICE_OUT = 0.10 / 1_000_000, 0.50 / 1_000_000   # anthropic/claude-haiku-5.5 on the gateway, 14.11.2026


def folder(strategy: str) -> Path:
    return ROOT / "ontology" / strategy


@lru_cache(maxsize=None)
def store_for(strategy: str):
    """The store the answers read: the built one, with the decisions of ontology/B/changes/ applied."""
    store = raw_store(strategy)
    if strategy == "B":
        from atlas.ontology import change

        return change.current_view(store)   # no decision recorded: the store itself
    return store


@lru_cache(maxsize=None)
def raw_store(strategy: str):
    """The store as built and committed (every correction applied). Views are made from it, never saved."""
    from atlas.corpus.chunker import load
    from atlas.ontology.statements import ChunkCorpus, Statement, Store

    path = folder(strategy) / "statements.json"
    if not path.exists():
        raise FileNotFoundError(f"ontology {strategy} is not built yet: {path} is missing")
    store = Store.load(ChunkCorpus(list(load())), path)
    # Further extractions (other layers, the plant's records) live in ontology/<strategy>/parts/<name>.json,
    # one file per extraction and one writer per file. Their ids are prefixed with the part's name.
    for part in sorted((folder(strategy) / "parts").glob("*.json")):
        payload = json.loads(part.read_text())
        if "statements" not in payload:
            continue
        for item in payload["statements"]:
            statement = Statement(**item)
            if not statement.id.startswith(part.stem):
                statement.id = f"{part.stem}-{statement.id}"
            store.statements.append(statement)
        store.rejections += payload.get("rejections", [])
    return store


def build_result(strategy: str) -> BuildResult:
    from rdflib import OWL, RDF, Graph

    counts = json.loads((folder(strategy) / "build.json").read_text())
    ontology = folder(strategy) / "ontology.ttl"
    shapes = folder(strategy) / "shapes.ttl"
    graph = Graph().parse(ontology, format="turtle")
    properties = set(graph.subjects(RDF.type, OWL.ObjectProperty)) | set(graph.subjects(RDF.type, OWL.DatatypeProperty))
    tokens_in, tokens_out = counts.get("prompt_tokens", 0), counts.get("completion_tokens", 0)
    proposed, anchored, rejected = (counts.get(k, 0) for k in ("proposed_total", "anchored", "rejected"))
    for part in sorted((folder(strategy) / "parts").glob("*.json")):   # what the further extractions add
        try:
            payload = json.loads(part.read_text())
        except ValueError:
            continue
        if not isinstance(payload, dict) or "statements" not in payload:
            continue
        kept, refused = len(payload["statements"]), len(payload.get("rejections", []))
        proposed, anchored, rejected = proposed + kept + refused, anchored + kept, rejected + refused
    return BuildResult(
        strategy=strategy, ontology_path=ontology, shapes_path=shapes if shapes.exists() else None,
        n_classes=len(set(graph.subjects(RDF.type, OWL.Class))), n_properties=len(properties), n_triples=len(graph),
        human_decisions=counts.get("human_decisions", 0), tokens=tokens_in + tokens_out,
        cost_usd=round(tokens_in * PRICE_IN + tokens_out * PRICE_OUT, 2), seconds=counts.get("seconds", 0.0),
        proposed=proposed, anchored=anchored, rejected=rejected)


def counts(strategy: str) -> dict:
    """proposed / anchored / rejected by reason / corrections: the numbers of the rule."""
    return json.loads((folder(strategy) / "build.json").read_text())


def validation(strategy: str) -> ValidationReport:
    from atlas.ontology import export

    conforms, violations = export.validate(folder(strategy) / "ontology.ttl", folder(strategy) / "shapes.ttl")
    return ValidationReport(strategy=strategy, conforms=conforms, violations=violations)


def answer(question: str, strategy: str = "B", as_of: date | None = None) -> Answer:
    from atlas.agent.answer import answer as ask

    return ask(question, store_for(strategy), as_of, mode=strategy)
