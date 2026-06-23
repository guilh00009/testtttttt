"""LLM engine — Firefly-V3 via llama-cpp-python on CPU."""

import os
import threading
from llama_cpp import Llama
from huggingface_hub import hf_hub_download

MODEL_REPO = os.environ.get("MODEL_REPO", "mradermacher/Firefly-V3-i1-GGUF")
MODEL_FILE = os.environ.get("MODEL_FILE", "Firefly-V3.i1-Q4_K_S.gguf")
N_CTX = int(os.environ.get("N_CTX", "2048"))
N_THREADS = int(os.environ.get("N_THREADS", "2"))

_lock = threading.Lock()
_llm = None


def _format_messages(messages: list[dict]) -> str:
    """Llama 3 chat template for Firefly."""
    parts = []
    for i, msg in enumerate(messages):
        role = msg["role"]
        content = msg["content"].strip()
        block = f"<|start_header_id|>{role}<|end_header_id|>\n\n{content}<|eot_id|>"
        if i == 0:
            block = "<|begin_of_text|>" + block
        parts.append(block)
    parts.append("<|start_header_id|>assistant<|end_header_id|>\n\n")
    return "".join(parts)


def get_llm() -> Llama:
    global _llm
    if _llm is None:
        print(f"Loading {MODEL_FILE} from {MODEL_REPO}...")
        path = hf_hub_download(repo_id=MODEL_REPO, filename=MODEL_FILE)
        _llm = Llama(
            model_path=path,
            n_ctx=N_CTX,
            n_threads=N_THREADS,
            n_gpu_layers=0,
            verbose=False,
        )
        print("Model loaded.")
    return _llm


def generate(
    messages: list[dict],
    max_tokens: int = 256,
    temperature: float = 0.85,
    stream: bool = False,
):
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


def generate_stream_text(messages: list[dict], max_tokens: int = 256, temperature: float = 0.85):
    full = ""
    for chunk in generate(messages, max_tokens=max_tokens, temperature=temperature, stream=True):
        token = chunk["choices"][0]["text"]
        full += token
        yield full
