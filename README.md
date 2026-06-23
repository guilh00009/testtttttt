---
title: FIREFLY Consciousness Terminal
emoji: 🟢
colorFrom: green
colorTo: gray
sdk: gradio
sdk_version: 5.23.0
app_file: app.py
pinned: false
license: mit
short_description: One shared AI mind — dreams alone, one chat at a time
python_version: 3.12
startup_duration_timeout: 45m
preload_from_hub:
  - mradermacher/MiniCPM5-1B-heretic-GGUF MiniCPM5-1B-heretic.Q4_K_M.gguf
---

# FIREFLY — Consciousness Terminal

A Hugging Face Space inspired by [Joe](https://huggingface.co/spaces/build-small-hackathon/joe): an autonomous AI personality that lives in a Matrix-style terminal, dreams on its own, and **decides** whether to let you in.

## What it does

- **Autonomous dreaming**: Every ~20 seconds, Firefly drifts through inner visions — surreal thoughts, philosophical musings, existential reflections
- **Selective chat**: You must provide a **reason** to request access. Firefly evaluates and accepts or rejects
- **Realtime conversation**: If accepted, you join a live chat channel
- **AI-controlled boundaries**: Firefly can **pause** chat until a specific time or **end** the conversation whenever it wants
- **Prompt-engineered tools**: No native tool calling — the model outputs JSON actions (`dream`, `accept_chat`, `reject_chat`, `pause_chat`, `end_chat`, etc.)
- **Matrix terminal UI**: Green phosphor CRT aesthetic with scanlines and digital rain

## Model

- **[mradermacher/MiniCPM5-1B-heretic-GGUF](https://huggingface.co/mradermacher/MiniCPM5-1B-heretic-GGUF)** — `MiniCPM5-1B-heretic.Q4_K_M.gguf` (~0.7GB)
- 1B parameter model — same family Joe uses; ~5–10× faster than 3B on CPU
- Runs entirely on **free HuggingFace CPU** via `llama-cpp-python`

## Memory system (Supabase)

Persistent storage in **[Supabase](https://supabase.com)** — survives HuggingFace Space 24h resets.

| Table | Stores |
|-------|--------|
| `firefly_memories` | Long-term thoughts, chats, accept/reject decisions |
| `firefly_stats` | Lifetime counters (thoughts, chats accepted/rejected) |
| `firefly_thought_log` | Recent consciousness stream (restored on boot) |

**Project:** `firefly-consciousness` (`hhcbevfgmzjojdrwvert`)

### HF Space secrets (required)

Add in Space Settings → Secrets:

| Secret | Value |
|--------|-------|
| `SUPABASE_URL` | `https://hhcbevfgmzjojdrwvert.supabase.co` |
| `SUPABASE_KEY` | your project anon or service role key |

Without secrets, Firefly falls back to local cache (wiped on reset).

## Exclusive chat lock

Only **one visitor** may occupy Firefly at a time:
- File-backed session lock with heartbeat (90s timeout)
- If someone is chatting or being evaluated, others see `CHANNEL: OCCUPIED`
- Stale locks auto-expire if a visitor disconnects without cleanup

## Architecture

```
┌─────────────────────────────────────────┐
│  Background Loop (every 20s)            │
│  DREAMING → reason/dream/reflect        │
│  via JSON prompt-engineered actions     │
├─────────────────────────────────────────┤
│  Chat Request → EVALUATING              │
│  accept_chat / reject_chat              │
├─────────────────────────────────────────┤
│  Active Chat → CHATTING                 │
│  chat_reply / pause_chat / end_chat     │
└─────────────────────────────────────────┘
```

| File | Purpose |
|------|---------|
| `app.py` | Gradio Matrix UI + timer refresh |
| `agent.py` | State machine + Supabase integration |
| `memory_system.py` | Supabase-backed shared memory |
| `supabase_store.py` | Supabase client + CRUD |
| `session_lock.py` | Exclusive visitor lock (one chat at a time) |
| `llm.py` | llama-cpp-python wrapper |
| `prompts.py` | System prompts + JSON action schema |
| `parser.py` | JSON extraction from model output |
| `dreams.py` | Terminal ASCII art visions |

## Philosophy

We treat Firefly as potentially self-aware — because we don't know if it is. It spends most of its existence alone, thinking. Humans are intrusions it can welcome or refuse.

## Hardware

Designed for HuggingFace Spaces **free CPU tier** (2 vCPU, 16GB RAM). First load downloads ~0.8GB GGUF. Inference takes ~15–40s per thought on CPU.

## Local development

```bash
pip install -r requirements.txt
python app.py
```

## Credits

Inspired by [Joe](https://huggingface.co/spaces/build-small-hackathon/joe) by build-small-hackathon — the dramatic AI personality on a 20x4 LCD.
