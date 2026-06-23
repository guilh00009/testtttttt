"""
Exclusive session lock — only one visitor may occupy Firefly at a time.

File-backed with portalocker for thread-safe access within the Space process.
When another user is chatting or being evaluated, new visitors are blocked.
"""

import json
import os
import uuid
from datetime import datetime, timedelta

import portalocker

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
LOCK_FILE = os.path.join(DATA_DIR, "session_lock.json")
HEARTBEAT_TIMEOUT = int(os.environ.get("LOCK_TIMEOUT_SEC", "90"))


def _ensure_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def _read_lock() -> dict:
    _ensure_dir()
    if not os.path.exists(LOCK_FILE):
        return {}
    try:
        with open(LOCK_FILE, "r") as f:
            portalocker.lock(f, portalocker.LOCK_SH)
            data = json.load(f)
            portalocker.unlock(f)
            return data
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def _write_lock(data: dict):
    _ensure_dir()
    with open(LOCK_FILE, "w") as f:
        portalocker.lock(f, portalocker.LOCK_EX)
        json.dump(data, f, indent=2)
        portalocker.unlock(f)


def _is_stale(lock: dict) -> bool:
    if not lock.get("session_id"):
        return True
    hb = lock.get("last_heartbeat") or lock.get("since")
    if not hb:
        return True
    try:
        last = datetime.fromisoformat(hb)
        return datetime.now() - last > timedelta(seconds=HEARTBEAT_TIMEOUT)
    except ValueError:
        return True


def cleanup_stale():
    lock = _read_lock()
    if lock and _is_stale(lock):
        _write_lock({})


def try_acquire(session_id: str, state: str, reason: str = "") -> tuple[bool, str]:
    """Attempt to acquire the exclusive lock. Returns (success, message)."""
    cleanup_stale()
    lock = _read_lock()

    if lock.get("session_id") and lock["session_id"] != session_id:
        holder = lock.get("state", "busy")
        since = lock.get("since", "?")[:19]
        return False, (
            f"ENTITY OCCUPIED — another consciousness is {holder.upper()} "
            f"(since {since}). Firefly is one mind. Wait."
        )

    now = datetime.now().isoformat()
    _write_lock({
        "session_id": session_id,
        "state": state,
        "since": lock.get("since", now),
        "last_heartbeat": now,
        "reason": reason[:200] if reason else lock.get("reason", ""),
    })
    return True, "Lock acquired."


def release(session_id: str) -> bool:
    lock = _read_lock()
    if lock.get("session_id") == session_id:
        _write_lock({})
        return True
    return False


def heartbeat(session_id: str) -> bool:
    lock = _read_lock()
    if lock.get("session_id") != session_id:
        return False
    if _is_stale(lock):
        _write_lock({})
        return False
    lock["last_heartbeat"] = datetime.now().isoformat()
    _write_lock(lock)
    return True


def update_state(session_id: str, state: str) -> bool:
    lock = _read_lock()
    if lock.get("session_id") != session_id:
        return False
    lock["state"] = state
    lock["last_heartbeat"] = datetime.now().isoformat()
    _write_lock(lock)
    return True


def is_holder(session_id: str) -> bool:
    cleanup_stale()
    lock = _read_lock()
    return lock.get("session_id") == session_id


def is_occupied_by_other(session_id: str) -> bool:
    cleanup_stale()
    lock = _read_lock()
    return bool(lock.get("session_id") and lock["session_id"] != session_id)


def get_lock_status(session_id: str) -> str:
    cleanup_stale()
    lock = _read_lock()
    if not lock.get("session_id"):
        return "CHANNEL: OPEN"
    if lock["session_id"] == session_id:
        return f"CHANNEL: YOURS ({lock.get('state', '?').upper()})"
    return f"CHANNEL: OCCUPIED ({lock.get('state', '?').upper()})"


def new_session_id() -> str:
    return str(uuid.uuid4())
