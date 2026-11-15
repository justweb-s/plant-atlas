"""The only door to the models. SHARED FILE (AGENTS.md §2, §6).

Every model call of the product goes through chat() or embed():
- the key and the base URL come from .env (AI_GATEWAY_API_KEY, AI_GATEWAY_BASE_URL);
- every response is saved in cache/llm/<sha256>.json and committed, so a rerun costs nothing
  for either of us and the demo works with the wifi off (ATLAS_OFFLINE=1);
- tests never reach this code with the network on.

ATLAS_LLM_BACKEND=claude-cli sends chat() through the Claude command line (`claude -p`) instead of the
gateway, for when the event key no longer works. Tools, settings and project files are switched off, so
the model sees only the messages. temperature and max_tokens cannot be set there: they are ignored.
A call already answered by the gateway is still read from its cache file; new answers go to their own
cache files (kind "chat-cli"), so the two never mix. embed() has no such backend: cache only.
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


def _cli_model(model: str) -> str:
    for name in ("haiku", "sonnet", "opus"):
        if name in model:
            return name
    raise RuntimeError(f"the claude-cli backend has no model for {model!r}")


def _cli_chat(payload: dict) -> dict:
    """One answer from `claude -p`: system messages as the system prompt, the rest on stdin."""
    import re
    import subprocess
    import tempfile

    system = "\n\n".join(m["content"] for m in payload["messages"] if m["role"] == "system") or "Answer the user."
    turns = [m for m in payload["messages"] if m["role"] != "system"]
    prompt = turns[0]["content"] if len(turns) == 1 else "\n\n".join(f"[{m['role']}]\n{m['content']}" for m in turns)
    command = ["claude", "-p", "--model", _cli_model(payload["model"]), "--system-prompt", system, "--tools", "",
               "--strict-mcp-config", "--no-session-persistence", "--setting-sources", "", "--no-chrome",
               "--output-format", "json"]
    error = None
    for _ in range(3):
        with tempfile.TemporaryDirectory() as empty:   # an empty folder: no project instructions to pick up
            done = subprocess.run(command, input=prompt, capture_output=True, text=True, encoding="utf-8",
                                  cwd=empty, timeout=600)
        try:
            reply = json.loads(done.stdout)
        except ValueError:
            error = (done.stderr or done.stdout)[:300]
            continue
        if reply.get("is_error") or not isinstance(reply.get("result"), str):
            error = str(reply.get("result"))[:300]
            continue
        text = reply["result"].strip()
        if payload.get("response_format", {}).get("type") == "json_object":   # no JSON mode there: drop a code fence
            fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.S)
            text = fenced.group(1) if fenced else text
        usage = reply.get("usage") or {}
        tokens_in = sum(usage.get(k, 0) or 0 for k in ("input_tokens", "cache_creation_input_tokens",
                                                       "cache_read_input_tokens"))
        tokens_out = usage.get("output_tokens", 0) or 0
        return {"text": text, "model": next(iter(reply.get("modelUsage") or {}), payload["model"]),
                "usage": {"prompt_tokens": tokens_in, "completion_tokens": tokens_out,
                          "total_tokens": tokens_in + tokens_out}}
    raise RuntimeError(f"claude -p gave no answer: {error}")


def chat(messages: list[dict], model: str | None = None, **params) -> dict:
    """Returns {"text", "model", "usage"}. params go to chat.completions (temperature, max_tokens, ...)."""
    payload = {"model": model or os.getenv("ATLAS_TEXT_MODEL", "anthropic/claude-haiku-5.5"),
               "messages": messages, **params}
    path = _cache_path("chat", payload)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))["response"]
    if os.getenv("ATLAS_LLM_BACKEND") == "claude-cli" and os.getenv("ATLAS_OFFLINE") != "1":
        path = _cache_path("chat-cli", payload)
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))["response"]
        out = _cli_chat(payload)
        _store(path, payload, out)
        return out
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
