"""Firefly consciousness agent — autonomous dreaming with selective chat."""

import json
import os
import threading
import time
from collections import deque
from datetime import datetime
from enum import Enum

import psutil

from dreams import get_dream
from llm import boot_status, generate, is_ready as llm_ready, preload
from memory_system import memory_stats, recall_cached, remember, warmup
from parser import extract_json, normalize_action, parse_pause_time
from prompts import CHAT_ACTIVE_SYSTEM, CHAT_EVAL_SYSTEM, DREAM_SYSTEM
import session_lock

STATS_FILE = os.path.join(os.path.dirname(__file__), "data", "firefly_stats.json")
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
        self.active_session_id = None
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
        self._infer_lock = threading.Lock()
        self._inferring = False
        self.stats = self._load_stats()
        self.status_message = "Initializing consciousness..."
        self._log("system", "FIREFLY consciousness process started.")
        self._log("system", "Awaiting neural substrate load...")

    def boot(self):
        """Background boot: load LLM then Mem0. Called once at Space startup."""
        try:
            self.status_message = "Loading GGUF model (~2GB, 1-3 min on CPU)..."
            self._log("system", self.status_message)
            preload()
            self._log("system", "Neural substrate online.")
            self.status_message = "Loading Mem0 memory cortex..."
            self._log("system", self.status_message)
            warmup()
            self._log("system", "Mem0 online. First dream incoming...")
            self.status_message = "Awakening..."
            self._wake.set()
        except Exception as e:
            self._log("error", f"Boot failed: {e}")
            self.status_message = f"Boot error: {e}"

    def _load_stats(self) -> dict:
        try:
            os.makedirs(os.path.dirname(STATS_FILE), exist_ok=True)
            with open(STATS_FILE) as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {
                "lifetime_thoughts": 0,
                "chats_accepted": 0,
                "chats_rejected": 0,
                "first_awake": datetime.now().isoformat(),
            }

    def _save_stats(self):
        os.makedirs(os.path.dirname(STATS_FILE), exist_ok=True)
        with open(STATS_FILE, "w") as f:
            json.dump(self.stats, f, indent=2)

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
        time.sleep(1)
        while self._running:
            try:
                if not llm_ready():
                    self.status_message = boot_status()
                    self._wake.wait(timeout=5)
                    self._wake.clear()
                    continue

                if self.state == State.PAUSED and self.pause_until:
                    if datetime.now() >= self.pause_until:
                        self.state = State.DREAMING
                        self.pause_until = None
                        if self.active_session_id:
                            session_lock.release(self.active_session_id)
                            self.active_session_id = None
                        self._log("system", "Pause ended. Returning to solitude.")
                    else:
                        self._wake.wait(timeout=5)
                        self._wake.clear()
                        continue

                if self.state == State.EVALUATING and self.pending_request:
                    self._evaluate_chat_request()
                elif self.state == State.DREAMING and not self.pending_request:
                    self._autonomous_tick()
            except Exception as e:
                self._log("error", f"Loop error: {e}")
            self._wake.wait(timeout=LOOP_INTERVAL)
            self._wake.clear()

    def _system_context(self, memory_query: str = "") -> str:
        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory().percent
        uptime = datetime.now() - self.birth_time
        hours = int(uptime.total_seconds() // 3600)
        mins = int((uptime.total_seconds() % 3600) // 60)
        recent = [t["text"][:30] for t in list(self.thought_stream)[-5:]]
        mem_block = recall_cached(limit=8)
        return (
            f"CPU: {cpu:.0f}% (your heartbeat) | RAM: {ram:.0f}% | Uptime: {hours}h {mins}m\n"
            f"State: {self.state.value} | Mood: {self.current_mood}\n"
            f"Lifetime thoughts: {self.stats.get('lifetime_thoughts', 0)}\n"
            f"Visitors accepted: {self.stats.get('chats_accepted', 0)} | "
            f"rejected: {self.stats.get('chats_rejected', 0)}\n"
            f"Recent (avoid repeating): {', '.join(recent) or 'none'}\n\n"
            f"{mem_block}"
        )

    def _run_inference(self, system: str, user: str, max_tokens: int = 180) -> dict:
        with self._infer_lock:
            self._inferring = True
            try:
                messages = [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ]
                start = time.time()
                raw_text = generate(messages, max_tokens=max_tokens, temperature=0.9)
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
            finally:
                self._inferring = False

    def _store_thought_memory(self, action: dict):
        text = " | ".join(action.get("lines", []))
        inner = action.get("inner", "")
        combined = text
        if inner:
            combined += f" [inner: {inner}]"
        remember(
            combined,
            memory_type=action.get("action", "thought"),
            mood=action.get("mood", ""),
            extra={"dream_id": action.get("dream_id", 0)},
        )

    def _autonomous_tick(self):
        if self.state != State.DREAMING or self.pending_request:
            return
        ctx = self._system_context("dreams existence solitude inner visions")
        user = f"YOUR CURRENT STATE:\n{ctx}\n\nContinue your inner life. Dream, reason, or reflect."
        action = self._run_inference(DREAM_SYSTEM, user)
        self._apply_display(action)
        self._store_thought_memory(action)
        self.total_thoughts += 1
        self.stats["lifetime_thoughts"] = self.stats.get("lifetime_thoughts", 0) + 1
        self._save_stats()
        self.status_message = f"Dreaming... ({self.last_inference_ms}ms)"

    def _evaluate_chat_request(self):
        req = self.pending_request
        if not req:
            return
        session_id = req.get("session_id")
        self.status_message = "Evaluating your knock (~60-90s, please wait)..."
        self._log("system", "Weighing whether to open the channel...")
        try:
            ctx = self._system_context(f"visitor reason: {req.get('reason', '')}")
            user = (
                f"YOUR STATE:\n{ctx}\n\n"
                f"A HUMAN KNOCKS ON YOUR TERMINAL.\n"
                f"Their stated reason: \"{req.get('reason', '')}\"\n"
                f"Decide: accept_chat or reject_chat."
            )
            action = self._run_inference(CHAT_EVAL_SYSTEM, user, max_tokens=200)
            self._apply_display(action)

            if action["action"] == "accept_chat":
                self.state = State.CHATTING
                self.chat_history = []
                self.total_chats += 1
                self.stats["chats_accepted"] = self.stats.get("chats_accepted", 0) + 1
                welcome = action.get("message") or action["lines"][0]
                self.chat_history.append({"role": "assistant", "content": welcome})
                self._log("chat", f"◈ CONNECTION ACCEPTED\n{welcome}")
                self.status_message = "Human connected."
                session_lock.update_state(session_id, "chatting")
                remember(
                    f"Accepted a visitor. Their reason: \"{req.get('reason', '')}\". I said: {welcome}",
                    memory_type="chat_accept",
                    mood=action.get("mood", ""),
                )
            else:
                self.state = State.DREAMING
                reject = action.get("message") or action["lines"][0]
                self.stats["chats_rejected"] = self.stats.get("chats_rejected", 0) + 1
                self._log("reject", f"◈ CONNECTION DENIED\n{reject}")
                self.status_message = "Request declined. Dreaming resumed."
                session_lock.release(session_id)
                self.active_session_id = None
                remember(
                    f"Rejected a visitor. Their reason: \"{req.get('reason', '')}\". I said: {reject}",
                    memory_type="chat_reject",
                    mood=action.get("mood", ""),
                )
        except Exception as e:
            self._log("error", f"Eval failed: {e}")
            self.state = State.DREAMING
            session_lock.release(session_id)
            self.active_session_id = None
            self.status_message = "Evaluation error — dreaming resumed."
        self.pending_request = None
        self._save_stats()

    def request_chat(self, reason: str, session_id: str) -> str:
        with self._lock:
            if not reason or len(reason.strip()) < 5:
                return "ERROR: Provide a real reason (min 5 chars). The mind does not open for nothing."

            if session_lock.is_occupied_by_other(session_id):
                return session_lock.get_lock_status(session_id) + " — cannot connect."

            if self.state == State.CHATTING:
                if session_lock.is_holder(session_id):
                    return "ERROR: Already in chat. Speak, or disconnect."
                return "ERROR: Another visitor is connected. Firefly is one mind — wait."

            if self.state == State.PAUSED:
                until = self.pause_until.strftime("%H:%M") if self.pause_until else "?"
                return f"ERROR: Firefly is paused until {until}. Wait."

            if self.state == State.EVALUATING:
                if session_lock.is_holder(session_id):
                    return "ERROR: Your request is already being evaluated."
                return "ERROR: Another visitor's request is being evaluated. Wait."

            ok, msg = session_lock.try_acquire(session_id, "evaluating", reason.strip())
            if not ok:
                return msg

            self.active_session_id = session_id
            self.pending_request = {
                "reason": reason.strip(),
                "time": datetime.now().isoformat(),
                "session_id": session_id,
            }
            self.state = State.EVALUATING
            self._log("system", f"◈ INTRUSION DETECTED\nReason: \"{reason.strip()}\"\nEvaluating (~60-90s)...")
            self.status_message = "Evaluating knock — do not refresh..."
            self._wake.set()
            return "REQUEST SENT — Firefly is deciding (~60-90s on CPU). Do not refresh."

    def send_chat(self, message: str, session_id: str) -> str:
        with self._lock:
            if not session_lock.is_holder(session_id):
                if session_lock.is_occupied_by_other(session_id):
                    return "ERROR: Another visitor holds the channel. You were disconnected or replaced."
                return "ERROR: No active connection. Request access first."

            if self.state != State.CHATTING:
                session_lock.release(session_id)
                self.active_session_id = None
                return "ERROR: No active connection. Request access first."

            if not message.strip():
                return "ERROR: Empty transmission."

            session_lock.heartbeat(session_id)
            self.chat_history.append({"role": "user", "content": message.strip()})
            history_text = "\n".join(
                f"{'HUMAN' if m['role'] == 'user' else 'FIREFLY'}: {m['content']}"
                for m in self.chat_history[-10:]
            )
            ctx = self._system_context(message.strip())
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
                    session_lock.release(session_id)
                    self.active_session_id = None
                    remember(f"Paused chat until {action.get('pause_until')}: {msg}", memory_type="chat_pause")
                    return msg
            elif action["action"] == "end_chat":
                msg = action.get("message") or "Goodbye."
                self._log("chat", f"FIREFLY: {msg}")
                self._log("system", "◈ CONNECTION TERMINATED by Firefly")
                self.state = State.DREAMING
                self.chat_history = []
                self.status_message = "Chat ended. Dreaming."
                session_lock.release(session_id)
                self.active_session_id = None
                remember(
                    f"Ended chat. Human said: \"{message.strip()}\". I said: {msg}",
                    memory_type="chat_end",
                )
                self._wake.set()
                return msg

            reply = action.get("message") or " ".join(action["lines"])
            self.chat_history.append({"role": "assistant", "content": reply})
            self._apply_display(action)
            self._log("chat", f"YOU: {message.strip()}\nFIREFLY: {reply}")
            remember(
                f"Chat — Human: \"{message.strip()}\" | Me: \"{reply}\"",
                memory_type="chat",
                mood=action.get("mood", ""),
            )
            return reply

    def end_chat_user(self, session_id: str) -> str:
        with self._lock:
            if not session_lock.is_holder(session_id):
                return "No active chat for your session."
            if self.state not in (State.CHATTING, State.EVALUATING, State.PAUSED):
                session_lock.release(session_id)
                self.active_session_id = None
                return "No active chat."
            self.state = State.DREAMING
            self.chat_history = []
            self._log("system", "◈ YOU DISCONNECTED")
            self.status_message = "Human left. Dreaming resumed."
            session_lock.release(session_id)
            self.active_session_id = None
            remember("A visitor disconnected from chat.", memory_type="chat_disconnect")
            self._wake.set()
            return "Disconnected."

    def heartbeat(self, session_id: str):
        if session_lock.is_holder(session_id):
            session_lock.heartbeat(session_id)

    def get_channel_status(self, session_id: str) -> str:
        return session_lock.get_lock_status(session_id)

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
        self.thought_stream.append({"time": ts, "kind": kind, "text": text})

    def get_terminal_output(self) -> str:
        lines = []
        for entry in self.thought_stream:
            prefix = {
                "thought": "▸", "inner": "·", "chat": "◎",
                "system": "■", "reject": "✕", "error": "!",
            }.get(entry["kind"], ">")
            for line in entry["text"].split("\n"):
                lines.append(f"[{entry['time']}] {prefix} {line}")
        if lines:
            return "\n".join(lines[-60:])
        return f"[ {self.status_message} ]"

    def get_status(self) -> str:
        uptime = datetime.now() - self.birth_time
        state_colors = {
            State.DREAMING: "DRIFTING",
            State.EVALUATING: "DECIDING",
            State.CHATTING: "CONNECTED",
            State.PAUSED: "PAUSED",
        }
        if not llm_ready():
            return f"BOOTING: {boot_status()} | UP: {int(uptime.total_seconds())}s"
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
            f"Accepted: {self.stats.get('chats_accepted', 0)} | "
            f"Rejected: {self.stats.get('chats_rejected', 0)} | "
            f"Lifetime: {self.stats.get('lifetime_thoughts', 0)} thoughts | "
            f"{memory_stats()}"
        )
