"""
Mem0-backed shared consciousness memory for Firefly.

Uses Mem0 OSS (Apache-2.0) — the most adopted open-source LLM memory layer.
Configured for fully local CPU operation on HuggingFace Spaces:
  - ChromaDB vector store (persistent, shared across all visitors)
  - HuggingFace embeddings (all-MiniLM-L6-v2, no API keys)
  - infer=False (no extra LLM calls — Firefly itself curates memories)

All memories use agent_id="firefly" so every visitor talks to the same entity.
"""

import os
import threading
from datetime import datetime

from mem0 import Memory

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
AGENT_ID = "firefly"
_lock = threading.Lock()
_memory = None
_ready = False


def is_ready() -> bool:
    return _ready


def warmup():
    """Initialize Mem0 in background (heavy — do not call from Gradio timer)."""
    global _ready
    print("Warming up Mem0 memory...")
    get_memory()
    _ready = True
    print("Mem0 ready.")


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
        # Required by Mem0 init but unused when infer=False
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


def remember(text: str, memory_type: str = "thought", mood: str = "", extra: dict = None):
    """Store a memory in Firefly's shared long-term store."""
    if not text or not text.strip() or not is_ready():
        return
    metadata = {
        "type": memory_type,
        "mood": mood,
        "timestamp": datetime.now().isoformat(),
        **(extra or {}),
    }
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


def recall(query: str, limit: int = 8) -> list[str]:
    """Retrieve semantically relevant memories for the shared entity."""
    if not is_ready():
        return []
    try:
        with _lock:
            result = get_memory().search(
                query,
                filters={"agent_id": AGENT_ID},
                limit=limit,
            )
        items = result.get("results", []) if isinstance(result, dict) else []
        seen = set()
        memories = []
        for item in items:
            mem = item.get("memory", "")
            if mem and mem not in seen:
                seen.add(mem)
                memories.append(mem)
        return memories
    except Exception as e:
        print(f"Memory recall error: {e}")
        return []


def recall_formatted(query: str, limit: int = 8) -> str:
    if not is_ready():
        return "Long-term memory still loading..."
    memories = recall(query, limit=limit)
    if not memories:
        return "No long-term memories retrieved yet. You are young."
    lines = [f"- {m}" for m in memories]
    return "YOUR LONG-TERM MEMORY (shared — all visitors are part of your one life):\n" + "\n".join(lines)


def memory_stats() -> str:
    if not is_ready():
        return "Mem0: loading..."
    try:
        with _lock:
            result = get_memory().get_all(filters={"agent_id": AGENT_ID}, limit=500)
        count = len(result.get("results", [])) if isinstance(result, dict) else 0
        return f"Mem0 memories: {count}"
    except Exception:
        return "Mem0 memories: ?"
