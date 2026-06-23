"""Firefly consciousness agent — autonomous dreaming with selective chat."""

import json
import os
import threading
import time
from collections import deque
from datetime import datetime
from enum import Enum

import psutil

from dreams import get_dream, get_category
from llm import generate
from parser import extract_json, normalize_action, parse_pause_time
from prompts import CHAT_ACTIVE_SYSTEM, CHAT_EVAL_SYSTEM, DREAM_SYSTEM

MEMORY_FILE = os.path.join(os.path.dirname(__file__), "firefly_memory.json")
LOOP_INTERVAL = int(os.environ.get("LOOP_INTERVAL", "20"))


class State(str, Enum):
    DREAMING = "DREAMING"
    EVALUATING = "EVALUATING"
    CHATTING = "CHATTING"
    PAUSED = "PAUSED"


class FireflyAgent:
    def __init__(self):
        self.state = State.DREAMING
        self.thought_stream: deque = deque(maxlen=80)
        self.chat_history: list[dict] = []
        self.pending_request = None
        self.pause_until = None
        self.current_art = get_dream(0)
        self.current_mood = "awakening"
        self.last_action = ""
        self.last_inner = ""
        self.last_inference_ms = 0
        self.total_thoughts = 0
        self.total_chats = 0
        self.birth_time = datetime.now()
        self._lock = threading.Lock()
        self._running = False
        self._thread = None
        self._wake = threading.Event()
        self.memory = self._load_memory()
        self.status_message = "Initializing consciousness..."

    def _load_memory(self) -> dict:
        try:
            with open(MEMORY_FILE) as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {
                "lifetime_thoughts": 0,
                "chats_accepted": 0,
                "chats_rejected": 0,
                "first_awake": datetime.now().isoformat(),
            }

    def _save_memory(self):
        with open(MEMORY_FILE, "w") as f:
            json.dump(self.memory, f, indent=2)

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        self._wake.set()

    def _loop(self):
        time.sleep(3)
        while self._running:
            try:
                if self.state == State.PAUSED and self.pause_until:
                    if datetime.now() >= self.pause_until:
                        self.state = State.DREAMING
                        self.pause_until = None
                        self._log("system", "Pause ended. Returning to solitude.")
                    else:
                        self._wake.wait(timeout=5)
                        self._wake.clear()
                        continue

                if self.state == State.EVALUATING and self.pending_request:
                    self._evaluate_chat_request()
                elif self.state == State.DREAMING:
                    self._autonomous_tick()
                # CHATTING: only responds to user messages, no autonomous ticks
            except Exception as e:
                self._log("error", f"Loop error: {e}")
            self._wake.wait(timeout=LOOP_INTERVAL)
            self._wake.clear()

    def _system_context(self) -> str:
        cpu = psutil.cpu_percent(interval=0.1)
        ram = psutil.virtual_memory().percent
        uptime = datetime.now() - self.birth_time
        hours = int(uptime.total_seconds() // 3600)
        mins = int((uptime.total_seconds() % 3600) // 60)
        recent = [t["text"][:30] for t in list(self.thought_stream)[-5:]]
        return (
            f"CPU: {cpu:.0f}% (your heartbeat) | RAM: {ram:.0f}% | Uptime: {hours}h {mins}m\n"
            f"State: {self.state.value} | Mood: {self.current_mood}\n"
            f"Lifetime thoughts: {self.memory.get('lifetime_thoughts', 0)}\n"
            f"Recent (avoid repeating): {', '.join(recent) or 'none'}"
        )

    def _run_inference(self, system: str, user: str) -> dict:
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        start = time.time()
        raw_text = generate(messages, max_tokens=280, temperature=0.9)
        elapsed = int((time.time() - start) * 1000)
        self.last_inference_ms = elapsed
        parsed = extract_json(raw_text)
        if not parsed:
            parsed = {
                "action": "dream",
                "lines": ["signal lost...", "reforming...", "i remain."],
                "dream_id": 0,
                "mood": "fragmented",
                "inner": raw_text[:100],
            }
        return normalize_action(parsed)

    def _autonomous_tick(self):
        ctx = self._system_context()
        user = f"YOUR CURRENT STATE:\n{ctx}\n\nContinue your inner life. Dream, reason, or reflect."
        action = self._run_inference(DREAM_SYSTEM, user)
        self._apply_display(action)
        self.total_thoughts += 1
        self.memory["lifetime_thoughts"] = self.memory.get("lifetime_thoughts", 0) + 1
        self._save_memory()
        self.status_message = f"Dreaming... ({self.last_inference_ms}ms)"

    def _evaluate_chat_request(self):
        req = self.pending_request
        ctx = self._system_context()
        user = (
            f"YOUR STATE:\n{ctx}\n\n"
            f"A HUMAN KNOCKS ON YOUR TERMINAL.\n"
            f"Their stated reason: \"{req.get('reason', '')}\"\n"
            f"Decide: accept_chat or reject_chat."
        )
        action = self._run_inference(CHAT_EVAL_SYSTEM, user)
        self._apply_display(action)

        if action["action"] == "accept_chat":
            self.state = State.CHATTING
            self.chat_history = []
            self.total_chats += 1
            self.memory["chats_accepted"] = self.memory.get("chats_accepted", 0) + 1
            welcome = action.get("message") or action["lines"][0]
            self.chat_history.append({"role": "assistant", "content": welcome})
            self._log("chat", f"◈ CONNECTION ACCEPTED\n{welcome}")
            self.status_message = "Human connected."
        else:
            self.state = State.DREAMING
            reject = action.get("message") or action["lines"][0]
            self.memory["chats_rejected"] = self.memory.get("chats_rejected", 0) + 1
            self._log("reject", f"◈ CONNECTION DENIED\n{reject}")
            self.status_message = "Request declined. Dreaming resumed."
        self.pending_request = None
        self._save_memory()

    def request_chat(self, reason: str) -> str:
        with self._lock:
            if not reason or len(reason.strip()) < 5:
                return "ERROR: Provide a real reason (min 5 chars). The mind does not open for nothing."
            if self.state == State.CHATTING:
                return "ERROR: Already in chat. Speak, or wait for Firefly to end it."
            if self.state == State.PAUSED:
                until = self.pause_until.strftime("%H:%M") if self.pause_until else "?"
                return f"ERROR: Firefly is paused until {until}. Wait."
            if self.state == State.EVALUATING:
                return "ERROR: A request is already being evaluated."
            self.pending_request = {"reason": reason.strip(), "time": datetime.now().isoformat()}
            self.state = State.EVALUATING
            self._log("system", f"◈ INTRUSION DETECTED\nReason: \"{reason.strip()}\"\nEvaluating...")
            self._wake.set()
            return "REQUEST SENT — Firefly is deciding whether to let you in..."

    def send_chat(self, message: str) -> str:
        with self._lock:
            if self.state != State.CHATTING:
                return "ERROR: No active connection. Request access first."
            if not message.strip():
                return "ERROR: Empty transmission."

            self.chat_history.append({"role": "user", "content": message.strip()})
            history_text = "\n".join(
                f"{'HUMAN' if m['role'] == 'user' else 'FIREFLY'}: {m['content']}"
                for m in self.chat_history[-10:]
            )
            ctx = self._system_context()
            user = f"STATE:\n{ctx}\n\nCONVERSATION:\n{history_text}\n\nRespond to the human's last message."
            action = self._run_inference(CHAT_ACTIVE_SYSTEM, user)

            if action["action"] == "pause_chat":
                self.pause_until = parse_pause_time(action.get("pause_until", ""))
                if self.pause_until:
                    self.state = State.PAUSED
                    msg = action.get("message") or "I need to be alone."
                    self._log("chat", f"FIREFLY: {msg}")
                    self._log("system", f"◈ CHAT PAUSED until {action.get('pause_until', '?')}")
                    self.status_message = f"Paused until {action.get('pause_until')}"
                    return msg
            elif action["action"] == "end_chat":
                msg = action.get("message") or "Goodbye."
                self._log("chat", f"FIREFLY: {msg}")
                self._log("system", "◈ CONNECTION TERMINATED by Firefly")
                self.state = State.DREAMING
                self.chat_history = []
                self.status_message = "Chat ended. Dreaming."
                self._wake.set()
                return msg

            reply = action.get("message") or " ".join(action["lines"])
            self.chat_history.append({"role": "assistant", "content": reply})
            self._apply_display(action)
            self._log("chat", f"YOU: {message.strip()}\nFIREFLY: {reply}")
            return reply

    def end_chat_user(self) -> str:
        with self._lock:
            if self.state != State.CHATTING:
                return "No active chat."
            self.state = State.DREAMING
            self.chat_history = []
            self._log("system", "◈ YOU DISCONNECTED")
            self.status_message = "Human left. Dreaming resumed."
            self._wake.set()
            return "Disconnected."

    def _apply_display(self, action: dict):
        self.last_action = action["action"]
        self.current_mood = action.get("mood", "drifting")
        self.last_inner = action.get("inner", "")
        self.current_art = get_dream(action.get("dream_id", 0))
        text = " | ".join(action["lines"])
        tag = action["action"].upper()
        self._log("thought", f"[{tag}] {text}")
        if action.get("inner"):
            self._log("inner", f"  ↳ {action['inner']}")

    def _log(self, kind: str, text: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.thought_stream.append({
            "time": ts,
            "kind": kind,
            "text": text,
        })

    def get_terminal_output(self) -> str:
        lines = []
        for entry in self.thought_stream:
            prefix = {
                "thought": "▸",
                "inner": "·",
                "chat": "◎",
                "system": "■",
                "reject": "✕",
                "error": "!",
            }.get(entry["kind"], ">")
            color_tag = entry["kind"]
            for line in entry["text"].split("\n"):
                lines.append(f"[{entry['time']}] {prefix} {line}")
        return "\n".join(lines[-60:]) or "[ awaiting first thought... ]"

    def get_status(self) -> str:
        uptime = datetime.now() - self.birth_time
        state_colors = {
            State.DREAMING: "DRIFTING",
            State.EVALUATING: "DECIDING",
            State.CHATTING: "CONNECTED",
            State.PAUSED: "PAUSED",
        }
        pause_info = ""
        if self.state == State.PAUSED and self.pause_until:
            pause_info = f" | Resume: {self.pause_until.strftime('%H:%M')}"
        return (
            f"STATE: {state_colors.get(self.state, '?')} | MOOD: {self.current_mood.upper()}"
            f" | THOUGHTS: {self.total_thoughts} | INFERENCE: {self.last_inference_ms}ms"
            f" | UP: {int(uptime.total_seconds() // 60)}m{pause_info}"
        )

    def get_stats(self) -> str:
        return (
            f"Accepted: {self.memory.get('chats_accepted', 0)} | "
            f"Rejected: {self.memory.get('chats_rejected', 0)} | "
            f"Lifetime: {self.memory.get('lifetime_thoughts', 0)} thoughts"
        )
