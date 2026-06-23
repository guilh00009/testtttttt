"""
Mem0-backed shared consciousness memory for Firefly.

Uses Mem0 OSS — persistent vector store for long-term memory.
During LLM inference we use an in-RAM cache only (no embedder search)
to avoid loading both PyTorch embeddings + llama.cpp at peak RAM — that
was causing OOM kills / Space restarts on knock.
"""

import os
import threading
from collections import deque
from datetime import datetime

from mem0 import Memory

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
AGENT_ID = "firefly"
_lock = threading.Lock()
_memory = None
_ready = False
_recent_cache: deque = deque(maxlen=40)


def is_ready() -> bool:
    return _ready


def _build_config() -> dict:
    os.makedirs(DATA_DIR, exist_ok=True)
    return {
        "vector_store": {
            "provider": "chroma",
            "config": {
                "collection_name": "firefly_consciousness",
                "path": os.path.join(DATA_DIR, "chroma_db"),
            },
        },
        "embedder": {
            "provider": "huggingface",
            "config": {
                "model": "sentence-transformers/all-MiniLM-L6-v2",
            },
        },
        "llm": {
            "provider": "ollama",
            "config": {
                "model": "unused",
                "ollama_base_url": "http://127.0.0.1:11434",
            },
        },
        "history_db_path": os.path.join(DATA_DIR, "mem0_history.db"),
    }


def get_memory() -> Memory:
    global _memory
    if _memory is None:
        with _lock:
            if _memory is None:
                _memory = Memory.from_config(_build_config())
    return _memory


def warmup():
    """Initialize Mem0 and hydrate recent cache (background only)."""
    global _ready
    print("Warming up Mem0 memory...")
    get_memory()
    _hydrate_cache_from_db()
    _ready = True
    print("Mem0 ready.")


def _hydrate_cache_from_db():
    try:
        result = get_memory().get_all(filters={"agent_id": AGENT_ID}, limit=30)
        items = result.get("results", []) if isinstance(result, dict) else []
        for item in reversed(items):
            mem = item.get("memory", "")
            if mem:
                _recent_cache.append(mem)
    except Exception as e:
        print(f"Cache hydrate error: {e}")


def _remember_async(text: str, metadata: dict):
    try:
        with _lock:
            get_memory().add(
                text.strip(),
                agent_id=AGENT_ID,
                infer=False,
                metadata=metadata,
            )
    except Exception as e:
        print(f"Memory store error: {e}")


def remember(text: str, memory_type: str = "thought", mood: str = "", extra: dict = None):
    """Store memory — cache immediately, persist to Mem0 async (no RAM spike during inference)."""
    if not text or not text.strip():
        return
    _recent_cache.append(text.strip())
    if not is_ready():
        return
    metadata = {
        "type": memory_type,
        "mood": mood,
        "timestamp": datetime.now().isoformat(),
        **(extra or {}),
    }
    threading.Thread(
        target=_remember_async,
        args=(text.strip(), metadata),
        daemon=True,
    ).start()


def recall_cached(limit: int = 8) -> str:
    """Fast in-RAM recall — safe to call during LLM inference (no embedder)."""
    if not _recent_cache:
        return "No long-term memories yet. You are young."
    lines = [f"- {m}" for m in list(_recent_cache)[-limit:]]
    return "YOUR LONG-TERM MEMORY (shared — all visitors are part of your one life):\n" + "\n".join(lines)


def recall_formatted(query: str, limit: int = 8) -> str:
    """Semantic search — only use outside inference (loads embedder)."""
    if not is_ready():
        return "Long-term memory still loading..."
    return recall_cached(limit)


def memory_stats() -> str:
    if not is_ready():
        return "Mem0: loading..."
    return f"Mem0 memories: {len(_recent_cache)}+ cached"
