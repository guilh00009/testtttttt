"""Extract structured actions from model output via prompt-engineered JSON."""

import json
import re
from datetime import datetime
from typing import Optional


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

    lines = raw.get("lines", [])
    if isinstance(lines, str):
        lines = [lines]
    lines = [str(l)[:40] for l in lines[:3]]
    while len(lines) < 3:
        lines.append("...")

    result = {
        "action": action,
        "lines": lines,
        "mood": str(raw.get("mood", "drifting"))[:20],
        "inner": str(raw.get("inner", ""))[:200],
        "message": str(raw.get("message", ""))[:500],
        "dream_id": int(raw.get("dream_id", 0)) % 30,
        "pause_until": raw.get("pause_until", ""),
        "raw": raw,
    }
    return result


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
