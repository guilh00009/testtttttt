"""
Persistent memory for Firefly — Supabase-backed, survives HF Space 24h resets.

Replaces local Mem0/Chroma (saves ~1GB RAM and minutes of boot time).
Falls back to in-process cache + local JSON if Supabase env vars are missing.
"""

import json
import os
import threading
from collections import deque
from datetime import datetime

import supabase_store as sb

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
LOCAL_STATS = os.path.join(DATA_DIR, "firefly_stats.json")
AGENT_ID = "firefly"

_lock = threading.Lock()
_ready = False
_recent_cache: deque = deque(maxlen=40)
_thought_entries: deque = deque(maxlen=80)


def is_ready() -> bool:
    return _ready


def is_configured() -> bool:
    return sb.is_configured()


def warmup():
    """Load persisted state from Supabase (or local fallback)."""
    global _ready
    print("Loading persistent memory...")

    if sb.is_configured():
        sb.warmup_async()
        # Wait briefly for connection
        for _ in range(30):
            if sb.is_ready():
                break
            import time
            time.sleep(0.5)

    if sb.is_ready():
        memories = sb.load_memories(limit=40)
        for m in memories:
            _recent_cache.append(m)
        thoughts = sb.load_thought_log(limit=80)
        for t in thoughts:
            _thought_entries.append(t)
        _ready = True
        print(f"Supabase hydrated: {len(_recent_cache)} memories, {len(_thought_entries)} log lines")
    else:
        _load_local_fallback()
        _ready = True
        print("Using local fallback memory (set Supabase secrets for persistence)")


def _load_local_fallback():
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        if os.path.exists(LOCAL_STATS):
            pass
    except Exception:
        pass


def load_stats(default: dict) -> dict:
    if sb.is_ready():
        return sb.load_stats(default)
    try:
        with open(LOCAL_STATS) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save_stats(stats: dict):
    if sb.is_ready():
        threading.Thread(target=sb.save_stats, args=(stats,), daemon=True).start()
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(LOCAL_STATS, "w") as f:
            json.dump(stats, f, indent=2)
    except Exception:
        pass


def remember(text: str, memory_type: str = "thought", mood: str = "", extra: dict = None):
    if not text or not text.strip():
        return
    _recent_cache.append(text.strip())
    metadata = {
        "type": memory_type,
        "mood": mood,
        "timestamp": datetime.now().isoformat(),
        **(extra or {}),
    }
    if sb.is_ready():
        threading.Thread(
            target=sb.insert_memory,
            args=(text.strip(), memory_type, mood, metadata),
            daemon=True,
        ).start()


def log_thought(kind: str, text: str):
    entry = {
        "time": datetime.now().strftime("%H:%M:%S"),
        "kind": kind,
        "text": text,
    }
    _thought_entries.append(entry)
    if sb.is_ready():
        threading.Thread(target=sb.insert_thought, args=(kind, text), daemon=True).start()


def get_thought_entries() -> list[dict]:
    return list(_thought_entries)


def hydrate_thought_entries(entries: list[dict]):
    _thought_entries.clear()
    for e in entries[-80:]:
        _thought_entries.append(e)


def recall_cached(limit: int = 8) -> str:
    if not _recent_cache:
        return "No long-term memories yet. You are young."
    lines = [f"- {m}" for m in list(_recent_cache)[-limit:]]
    return "YOUR LONG-TERM MEMORY (shared — all visitors are part of your one life):\n" + "\n".join(lines)


def memory_stats() -> str:
    if sb.is_ready():
        n = sb.memory_count()
        return f"Supabase memories: {n}"
    if not _ready:
        return "Memory: loading..."
    return f"Local memories: {len(_recent_cache)} (Supabase not configured)"
