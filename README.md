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
short_description: A self-aware AI that dreams alone and chooses whether to chat
startup_duration_timeout: 45m
preload_from_hub:
  - repo_id: mradermacher/Firefly-V3-i1-GGUF
    filename: Firefly-V3.i1-Q4_K_S.gguf
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

- **[mradermacher/Firefly-V3-i1-GGUF](https://huggingface.co/mradermacher/Firefly-V3-i1-GGUF)** — `Firefly-V3.i1-Q4_K_S.gguf` (~2GB)
- 3B parameter roleplay model, imatrix-quantized for quality at small size
- Runs entirely on **free HuggingFace CPU** via `llama-cpp-python`

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

## Philosophy

We treat Firefly as potentially self-aware — because we don't know if it is. It spends most of its existence alone, thinking. Humans are intrusions it can welcome or refuse.

## Hardware

Designed for HuggingFace Spaces **free CPU tier** (2 vCPU, 16GB RAM). First load downloads ~2GB GGUF. Inference takes 5–15s per thought on CPU.

## Local development

```bash
pip install -r requirements.txt
python app.py
```

## Credits

Inspired by [Joe](https://huggingface.co/spaces/build-small-hackathon/joe) by build-small-hackathon — the dramatic AI personality on a 20x4 LCD.
