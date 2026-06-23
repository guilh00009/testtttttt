"""LLM engine — MiniCPM5-1B via llama-cpp-python on CPU."""

import gc
import os
import threading
from llama_cpp import Llama
from huggingface_hub import hf_hub_download

MODEL_REPO = os.environ.get("MODEL_REPO", "openbmb/MiniCPM5-1B-GGUF")
MODEL_FILE = os.environ.get("MODEL_FILE", "MiniCPM5-1B-Q4_K_M.gguf")
MIN_MODEL_BYTES = int(os.environ.get("MIN_MODEL_BYTES", "650000000"))
N_CTX = int(os.environ.get("N_CTX", "2048"))
N_THREADS = int(os.environ.get("N_THREADS", "2"))

# Construct ChatML tokens at import (avoids editor mangling special token strings).
IM_START = "<|" + "im_start" + "|>"
IM_END = "<|" + "im_end" + "|>"
_THINK_OPEN = "<" + "think" + ">"
_THINK_CLOSE = "</" + "think" + ">"

_lock = threading.Lock()
_llm = None
_ready = False
_boot_status = "Waiting to load model..."


def is_ready() -> bool:
    return _ready


def boot_status() -> str:
    return _boot_status


def preload():
    get_llm()


def _format_messages(messages: list[dict]) -> str:
    """MiniCPM5 ChatML template (nothink mode for speed)."""
    parts = []
    for msg in messages:
        role = msg["role"]
        content = msg["content"].strip()
        parts.append(f"{IM_START}{role}\n{content}{IM_END}\n")
    # Empty thinking block = fast no-think mode per MiniCPM5 docs
    parts.append(
        f"{IM_START}assistant\n{_THINK_OPEN}\n\n{_THINK_CLOSE}\n\n"
    )
    return "".join(parts)


def _model_path(force_download: bool = False) -> str:
    path = hf_hub_download(
        repo_id=MODEL_REPO,
        filename=MODEL_FILE,
        force_download=force_download,
    )
    size = os.path.getsize(path)
    if size < MIN_MODEL_BYTES:
        print(f"Model file looks truncated ({size} bytes); re-downloading...")
        path = hf_hub_download(
            repo_id=MODEL_REPO,
            filename=MODEL_FILE,
            force_download=True,
        )
    return path


def _load_llama(path: str) -> Llama:
    return Llama(
        model_path=path,
        n_ctx=N_CTX,
        n_threads=N_THREADS,
        n_gpu_layers=0,
        n_batch=128,
        use_mmap=True,
        use_mlock=False,
        verbose=False,
    )


def get_llm() -> Llama:
    global _llm, _ready, _boot_status
    if _llm is None:
        with _lock:
            if _llm is None:
                _boot_status = f"Loading {MODEL_FILE} (~0.7GB)..."
                print(f"Loading {MODEL_FILE} from {MODEL_REPO}...")
                last_err = None
                for attempt in range(2):
                    try:
                        path = _model_path(force_download=(attempt > 0))
                        size_mb = os.path.getsize(path) / (1024 * 1024)
                        print(f"GGUF path: {path} ({size_mb:.0f} MB)")
                        _llm = _load_llama(path)
                        _ready = True
                        _boot_status = "Model ready"
                        print("Model loaded.")
                        break
                    except Exception as e:
                        last_err = e
                        print(f"Model load attempt {attempt + 1} failed: {e}")
                        _llm = None
                        _ready = False
                if _llm is None:
                    _boot_status = f"Model load failed: {last_err}"
                    raise RuntimeError(
                        f"Failed to load model from {MODEL_REPO}/{MODEL_FILE}: {last_err}"
                    )
    return _llm


def _clean_output(text: str) -> str:
    import re
    if not text:
        return ""
    think_pat = "<" + "think" + ">.*?</" + "think" + ">"
    text = re.sub(think_pat, "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"```\w*\n?", "", text)
    return text.strip()


def generate(
    messages: list[dict],
    max_tokens: int = 150,
    temperature: float = 0.7,
    stream: bool = False,
):
    gc.collect()
    prompt = _format_messages(messages)
    llm = get_llm()
    stops = [IM_END, "</s>"]
    with _lock:
        if stream:
            return llm(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=0.95,
                repeat_penalty=1.15,
                stop=stops,
                stream=True,
            )
        out = llm(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=0.95,
            repeat_penalty=1.15,
            stop=stops,
        )
        return _clean_output(out["choices"][0]["text"])
