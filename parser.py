"""Extract structured actions from model output via prompt-engineered JSON."""

import json
import re
from datetime import datetime
from typing import Optional

LINE_MAX = int(__import__("os").environ.get("LINE_MAX", "72"))

# Placeholder text the 1B model copies from bad prompts — treat as empty.
_PLACEHOLDER_LINES = frozenset({
    "line1", "line2", "line3", "...", "…", "short line 1", "short line 2", "short line 3",
})
_PLACEHOLDER_INNER = frozenset({
    "private thought", "thought", "thinking about the visitor's words",
})
_PLACEHOLDER_MESSAGE = frozenset({"...", "…", ""})
_GARBAGE_LINE = re.compile(
    r"^(\[?(dream|reason|reflect|inner|mood|action|haunted)\]?|inner|mood)$",
    re.I,
)


def _finish_line(text: str, max_len: int = LINE_MAX) -> str:
    """Keep full sentences; only trim at word boundary if over limit."""
    text = re.sub(r"\s+", " ", str(text).strip())
    if not text:
        return ""
    if len(text) <= max_len:
        return text
    cut = text[:max_len]
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return cut.rstrip(".,;:- ")


def _is_placeholder_line(text: str) -> bool:
    t = str(text).strip().lower()
    if not t or t in _PLACEHOLDER_LINES or t.startswith("..."):
        return True
    if _GARBAGE_LINE.match(t):
        return True
    if re.search(r"\[(DREAM|REASON|REFLECT)\]", t, re.I):
        return True
    return False


def _clean_lines(lines: list) -> list[str]:
    if isinstance(lines, str):
        lines = [lines]
    cleaned = []
    for line in lines[:3]:
        s = _finish_line(str(line))
        if not _is_placeholder_line(s):
            cleaned.append(s)
    return cleaned


def _clean_message(msg: str) -> str:
    s = str(msg or "").strip()
    if s.lower() in _PLACEHOLDER_MESSAGE:
        return ""
    return s[:500]


def _clean_inner(inner: str) -> str:
    s = _finish_line(str(inner or ""), max_len=200)
    if s.lower() in _PLACEHOLDER_INNER:
        return ""
    return s


def extract_json(text: str) -> Optional[dict]:
    if not text:
        return None
    text = text.strip()
    # Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Find JSON object in text
    for match in re.finditer(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", text, re.DOTALL):
        try:
            obj = json.loads(match.group())
            if "action" in obj:
                return obj
        except json.JSONDecodeError:
            continue
    # Fallback: regex fields
    action_m = re.search(r'"action"\s*:\s*"([^"]+)"', text)
    if not action_m:
        return None
    result = {"action": action_m.group(1)}
    for key in ("message", "mood", "inner", "pause_until"):
        m = re.search(rf'"{key}"\s*:\s*"([^"]*)"', text)
        if m:
            result[key] = m.group(1)
    lines_m = re.search(r'"lines"\s*:\s*\[(.*?)\]', text, re.DOTALL)
    if lines_m:
        result["lines"] = re.findall(r'"([^"]*)"', lines_m.group(1))[:3]
    dream_m = re.search(r'"dream_id"\s*:\s*(\d+)', text)
    if dream_m:
        result["dream_id"] = int(dream_m.group(1))
    return result


def normalize_action(raw: dict) -> dict:
    action = raw.get("action", "dream").lower().strip()
    valid = {
        "dream", "reason", "reflect",
        "accept_chat", "reject_chat",
        "chat_reply", "pause_chat", "end_chat",
    }
    if action not in valid:
        action = "dream"

    lines = _clean_lines(raw.get("lines", []))
    message = _clean_message(raw.get("message", ""))
    inner = _clean_inner(raw.get("inner", ""))

    # Chat actions: message is primary; backfill lines from message if needed.
    if message and len(lines) < 3:
        parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+|[|]", message) if p.strip()]
        for p in parts:
            if len(lines) >= 3:
                break
            finished = _finish_line(p)
            if finished and not _is_placeholder_line(finished):
                lines.append(finished)
    if not lines and message:
        chunk = _finish_line(message)
        lines = [chunk] if chunk else []
    while len(lines) < 3:
        lines.append("...")

    result = {
        "action": action,
        "lines": lines[:3],
        "mood": str(raw.get("mood", "drifting"))[:20],
        "inner": inner,
        "message": message,
        "dream_id": int(raw.get("dream_id", 0)) % 30,
        "pause_until": raw.get("pause_until", ""),
        "raw": raw,
    }
    return result


def action_speech(action: dict, fallback: str = "...") -> str:
    """Best text for chat display — prefers message over placeholder lines."""
    msg = _clean_message(action.get("message", ""))
    if msg:
        return msg
    lines = _clean_lines(action.get("lines", []))
    if lines:
        return " | ".join(lines)
    return fallback


def parse_pause_time(pause_until: str) -> Optional[datetime]:
    if not pause_until:
        return None
    try:
        parts = pause_until.strip().split(":")
        h, m = int(parts[0]), int(parts[1]) if len(parts) > 1 else 0
        now = datetime.now()
        target = now.replace(hour=h % 24, minute=m % 60, second=0, microsecond=0)
        if target <= now:
            from datetime import timedelta
            target += timedelta(days=1)
        return target
    except (ValueError, IndexError):
        return None
