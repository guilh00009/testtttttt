"""LLM engine — MiniCPM5-1B via llama-cpp-python on CPU."""

import gc
import os
import threading
from llama_cpp import Llama
from huggingface_hub import hf_hub_download

MODEL_REPO = os.environ.get("MODEL_REPO", "mradermacher/MiniCPM5-1B-heretic-GGUF")
MODEL_FILE = os.environ.get("MODEL_FILE", "MiniCPM5-1B-heretic.Q4_K_S.gguf")
N_CTX = int(os.environ.get("N_CTX", "2048"))
N_THREADS = int(os.environ.get("N_THREADS", "2"))

IM_START = "<|im_start|>"
IM_END = "<|im_end|>"

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
    parts.append(f"{IM_START}assistant\n<think>\n\n</think>\n\n")
    return "".join(parts)


def get_llm() -> Llama:
    global _llm, _ready, _boot_status
    if _llm is None:
        with _lock:
            if _llm is None:
                _boot_status = "Loading MiniCPM5-1B GGUF..."
                print(f"Loading {MODEL_FILE} from {MODEL_REPO}...")
                path = hf_hub_download(repo_id=MODEL_REPO, filename=MODEL_FILE)
                _llm = Llama(
                    model_path=path,
                    n_ctx=N_CTX,
                    n_threads=N_THREADS,
                    n_gpu_layers=0,
                    n_batch=128,
                    use_mmap=True,
                    use_mlock=False,
                    verbose=False,
                )
                _ready = True
                _boot_status = "Model ready"
                print("Model loaded.")
    return _llm


def generate(
    messages: list[dict],
    max_tokens: int = 150,
    temperature: float = 0.7,
    stream: bool = False,
):
    gc.collect()
    prompt = _format_messages(messages)
    llm = get_llm()
    stops = [IM_END, "</s>", IM_START]
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
        return out["choices"][0]["text"].strip()
