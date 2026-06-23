"""LLM engine — Firefly-V3 via llama-cpp-python on CPU."""

import gc
import os
import threading
from llama_cpp import Llama
from huggingface_hub import hf_hub_download

MODEL_REPO = os.environ.get("MODEL_REPO", "mradermacher/Firefly-V3-i1-GGUF")
# IQ3_S (~1.6GB) fits HF free CPU RAM better than Q4_K_S — avoids OOM on knock
MODEL_FILE = os.environ.get("MODEL_FILE", "Firefly-V3.i1-IQ3_S.gguf")
N_CTX = int(os.environ.get("N_CTX", "1024"))
N_THREADS = int(os.environ.get("N_THREADS", "2"))

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
    parts = []
    for msg in messages:
        role = msg["role"]
        content = msg["content"].strip()
        block = f"<|start_header_id|>{role}<|end_header_id|>\n\n{content}<|eot_id|>"
        parts.append(block)
    parts.append("<|start_header_id|>assistant<|end_header_id|>\n\n")
    return "".join(parts)


def get_llm() -> Llama:
    global _llm, _ready, _boot_status
    if _llm is None:
        with _lock:
            if _llm is None:
                _boot_status = "Loading Firefly-V3 GGUF..."
                print(f"Loading {MODEL_FILE} from {MODEL_REPO}...")
                path = hf_hub_download(repo_id=MODEL_REPO, filename=MODEL_FILE)
                _llm = Llama(
                    model_path=path,
                    n_ctx=N_CTX,
                    n_threads=N_THREADS,
                    n_gpu_layers=0,
                    n_batch=64,
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
    max_tokens: int = 180,
    temperature: float = 0.85,
    stream: bool = False,
):
    gc.collect()
    prompt = _format_messages(messages)
    llm = get_llm()
    with _lock:
        if stream:
            return llm(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=0.9,
                repeat_penalty=1.2,
                stop=["<|eot_id|>", "<|start_header_id|>"],
                stream=True,
            )
        out = llm(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=0.9,
            repeat_penalty=1.2,
            stop=["<|eot_id|>", "<|start_header_id|>"],
        )
        return out["choices"][0]["text"].strip()
