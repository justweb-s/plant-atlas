import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import os

# Tests never load the local embedding model: the RAG tests use the gateway path with a stubbed embed().
os.environ.setdefault("ATLAS_RAG_EMBED", "gateway")

# The tests of the answering chain exercise the fact store and the readings with a stubbed model, not the search agent.
os.environ.setdefault("ATLAS_DECIDE", "readings")
