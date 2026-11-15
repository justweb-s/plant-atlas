"""Embeddings computed on this machine, so the RAG baseline needs no key. Owner: Product (written by Core).

Model: BAAI/bge-m3 (multilingual), ONNX files from the local Hugging Face cache; needs onnxruntime, tokenizers
and numpy. Vectors of the corpus are kept in runtime/embed/ (not in git: they are rebuilt from the documents).
A text longer than 512 tokens is embedded by its first 512 tokens, as in a plain RAG pipeline.
"""
from __future__ import annotations

import glob
import hashlib
import os
import sys
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / "runtime" / "embed"
MODEL = "BAAI/bge-m3"
TOKENS = 512


@lru_cache(maxsize=1)
def _model():
    import onnxruntime as ort
    from tokenizers import Tokenizer

    found = glob.glob(os.path.expanduser("~/.cache/huggingface/hub/models--BAAI--bge-m3/snapshots/*/onnx"))
    if not found:
        raise RuntimeError(f"{MODEL} (ONNX) is not in the local Hugging Face cache")
    tokenizer = Tokenizer.from_file(found[0] + "/tokenizer.json")
    tokenizer.enable_truncation(TOKENS)
    tokenizer.enable_padding(pad_id=1, pad_token="<pad>")
    return ort.InferenceSession(found[0] + "/model.onnx", providers=["CPUExecutionProvider"]), tokenizer


def embed(texts: list[str], batch: int = 8, progress: bool = False):
    """One unit vector per text (numpy array, n x 1024)."""
    import numpy as np

    session, tokenizer = _model()
    order = sorted(range(len(texts)), key=lambda i: len(texts[i]))   # similar lengths together: less padding
    out = np.zeros((len(texts), 1024), dtype=np.float32)
    for start in range(0, len(order), batch):
        ids = order[start:start + batch]
        enc = tokenizer.encode_batch([texts[i] for i in ids])
        vectors = session.run(["sentence_embedding"], {
            "input_ids": np.array([e.ids for e in enc], dtype=np.int64),
            "attention_mask": np.array([e.attention_mask for e in enc], dtype=np.int64)})[0]
        out[ids] = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
        if progress and (start // batch) % 20 == 0:
            print(f"embedded {start + len(ids)}/{len(texts)}", file=sys.stderr, flush=True)
    return out


def corpus_vectors(texts: list[str]):
    """The vectors of the corpus passages, computed once and kept on disk under a name made from the texts."""
    import numpy as np

    name = hashlib.sha256(("\x00".join(texts) + MODEL + str(TOKENS)).encode("utf-8")).hexdigest()[:16]
    path = STORE / f"bge-m3-{name}.npy"
    if path.exists():
        return np.load(path)
    vectors = embed(texts, progress=True)
    STORE.mkdir(parents=True, exist_ok=True)
    np.save(path, vectors)
    return vectors


if __name__ == "__main__":   # python -m evaluation.local_embed : build the corpus vectors
    from evaluation import rag

    chunks = rag.api_corpus()
    print(corpus_vectors([rag._passage(c) for c in chunks]).shape)
