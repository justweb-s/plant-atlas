"""The only door to the models. SHARED FILE (AGENTS.md §2, §6).

Every model call of the product goes through chat() or embed():
- the key and the base URL come from .env (AI_GATEWAY_API_KEY, AI_GATEWAY_BASE_URL);
- every response is saved in cache/llm/<sha256>.json and committed, so a rerun costs nothing
  for either of us and the demo works with the wifi off (ATLAS_OFFLINE=1);
- tests never reach this code with the network on.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "cache" / "llm"


def _cache_path(kind: str, payload: dict) -> Path:
    blob = json.dumps({"kind": kind, **payload}, sort_keys=True, ensure_ascii=False)
    return CACHE / f"{hashlib.sha256(blob.encode('utf-8')).hexdigest()}.json"


def _client():
    if os.getenv("ATLAS_OFFLINE") == "1":
        raise RuntimeError("ATLAS_OFFLINE=1 and this call is not in cache/llm/")
    from openai import OpenAI
    return OpenAI(api_key=os.environ["AI_GATEWAY_API_KEY"],
                  base_url=os.getenv("AI_GATEWAY_BASE_URL", "https://ai-gateway.vercel.sh/v1"))


def _store(path: Path, request: dict, response: dict) -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"request": request, "response": response}, ensure_ascii=False, indent=1),
                    encoding="utf-8")


def chat(messages: list[dict], model: str | None = None, **params) -> dict:
    """Returns {"text", "model", "usage"}. params go to chat.completions (temperature, max_tokens, ...)."""
    payload = {"model": model or os.getenv("ATLAS_TEXT_MODEL", "anthropic/claude-haiku-5.5"),
               "messages": messages, **params}
    path = _cache_path("chat", payload)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))["response"]
    resp = _client().chat.completions.create(**payload)
    out = {"text": resp.choices[0].message.content, "model": resp.model,
           "usage": resp.usage.model_dump() if resp.usage else None}
    _store(path, payload, out)
    return out


def embed(texts: list[str], model: str | None = None, **params) -> list[list[float]]:
    """One vector per text, cached like chat(). params go to embeddings.create (e.g. dimensions=256);
    without params the cache key is the same as before."""
    payload = {"model": model or os.getenv("ATLAS_EMBED_MODEL", "openai/text-embedding-3-small"),
               "input": texts, **params}
    path = _cache_path("embed", payload)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))["response"]["vectors"]
    resp = _client().embeddings.create(**payload)
    out = {"vectors": [d.embedding for d in resp.data], "model": resp.model,
           "usage": resp.usage.model_dump() if resp.usage else None}
    _store(path, payload, out)
    return out["vectors"]
