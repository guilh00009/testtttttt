"""Supabase persistence — memories, stats, thought log survive HF Space resets."""

import os
import threading
from datetime import datetime
from typing import Optional

AGENT_ID = "firefly"
_lock = threading.Lock()
_client = None
_ready = False
_configured = False


def _get_client():
    global _client, _configured
    if _client is not None:
        return _client
    url = os.environ.get("SUPABASE_URL", "").strip()
    key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
        or os.environ.get("SUPABASE_KEY", "")
    ).strip()
    if not url or not key:
        _configured = False
        return None
    _configured = True
    from supabase import create_client
    _client = create_client(url, key)
    return _client


def is_configured() -> bool:
    _get_client()
    return _configured


def is_ready() -> bool:
    return _ready


def ping() -> bool:
    try:
        sb = _get_client()
        if not sb:
            return False
        sb.table("firefly_stats").select("id").eq("id", AGENT_ID).limit(1).execute()
        return True
    except Exception as e:
        print(f"Supabase ping failed: {e}")
        return False


def load_stats(default: dict) -> dict:
    sb = _get_client()
    if not sb:
        return default
    try:
        res = sb.table("firefly_stats").select("*").eq("id", AGENT_ID).limit(1).execute()
        rows = res.data or []
        if not rows:
            sb.table("firefly_stats").insert({"id": AGENT_ID, **default}).execute()
            return default
        row = rows[0]
        return {
            "lifetime_thoughts": row.get("lifetime_thoughts", 0),
            "chats_accepted": row.get("chats_accepted", 0),
            "chats_rejected": row.get("chats_rejected", 0),
            "first_awake": row.get("first_awake") or default.get("first_awake"),
        }
    except Exception as e:
        print(f"Supabase load_stats error: {e}")
        return default


def save_stats(stats: dict):
    sb = _get_client()
    if not sb:
        return
    try:
        sb.table("firefly_stats").upsert({
            "id": AGENT_ID,
            "lifetime_thoughts": stats.get("lifetime_thoughts", 0),
            "chats_accepted": stats.get("chats_accepted", 0),
            "chats_rejected": stats.get("chats_rejected", 0),
            "first_awake": stats.get("first_awake"),
            "updated_at": datetime.utcnow().isoformat(),
        }).execute()
    except Exception as e:
        print(f"Supabase save_stats error: {e}")


def load_memories(limit: int = 40) -> list[str]:
    sb = _get_client()
    if not sb:
        return []
    try:
        res = (
            sb.table("firefly_memories")
            .select("content")
            .eq("agent_id", AGENT_ID)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        items = [r["content"] for r in (res.data or []) if r.get("content")]
        return list(reversed(items))
    except Exception as e:
        print(f"Supabase load_memories error: {e}")
        return []


def insert_memory(text: str, memory_type: str, mood: str, metadata: dict):
    sb = _get_client()
    if not sb:
        return
    try:
        sb.table("firefly_memories").insert({
            "agent_id": AGENT_ID,
            "content": text,
            "memory_type": memory_type,
            "mood": mood,
            "metadata": metadata,
        }).execute()
    except Exception as e:
        print(f"Supabase insert_memory error: {e}")


def load_thought_log(limit: int = 80) -> list[dict]:
    sb = _get_client()
    if not sb:
        return []
    try:
        res = (
            sb.table("firefly_thought_log")
            .select("logged_at, kind, text")
            .eq("agent_id", AGENT_ID)
            .order("logged_at", desc=True)
            .limit(limit)
            .execute()
        )
        rows = res.data or []
        entries = []
        for r in reversed(rows):
            ts = r.get("logged_at", "")[:19].replace("T", " ")
            if len(ts) >= 16:
                ts = ts[11:19]  # HH:MM:SS
            entries.append({
                "time": ts or datetime.now().strftime("%H:%M:%S"),
                "kind": r.get("kind", "thought"),
                "text": r.get("text", ""),
            })
        return entries
    except Exception as e:
        print(f"Supabase load_thought_log error: {e}")
        return []


def insert_thought(kind: str, text: str):
    sb = _get_client()
    if not sb:
        return
    try:
        sb.table("firefly_thought_log").insert({
            "agent_id": AGENT_ID,
            "kind": kind,
            "text": text,
        }).execute()
    except Exception as e:
        print(f"Supabase insert_thought error: {e}")


def memory_count() -> int:
    sb = _get_client()
    if not sb:
        return 0
    try:
        res = (
            sb.table("firefly_memories")
            .select("id", count="exact")
            .eq("agent_id", AGENT_ID)
            .execute()
        )
        return res.count or 0
    except Exception:
        return 0


def warmup_async(callback=None):
    """Connect and verify tables in background."""
    global _ready

    def _run():
        global _ready
        if not is_configured():
            print("Supabase not configured (set SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY)")
            _ready = False
            if callback:
                callback(False, "not configured")
            return
        if ping():
            _ready = True
            print("Supabase ready.")
            if callback:
                callback(True, "ready")
        else:
            _ready = False
            print("Supabase ping failed — check migration SQL was applied")
            if callback:
                callback(False, "ping failed")

    threading.Thread(target=_run, daemon=True).start()
