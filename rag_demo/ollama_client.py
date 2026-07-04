import json
import os
from typing import Dict, Optional
import urllib.request


def build_ollama_payload(
    prompt: str,
    model: str = "qwen2.5:7b",
    system: Optional[str] = None,
) -> Dict[str, object]:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_ctx": 8192,
            "num_predict": _int_env("RAG_OLLAMA_NUM_PREDICT", 768),
        },
    }
    if system:
        payload["system"] = system
    return payload


def ask_ollama(
    prompt: str,
    model: str = "qwen2.5:7b",
    system: Optional[str] = None,
) -> str:
    payload = build_ollama_payload(prompt=prompt, model=model, system=system)
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        "http://127.0.0.1:11434/api/generate",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=120) as response:
        body = json.loads(response.read().decode("utf-8"))
    return body["response"].strip()


def _int_env(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, str(default)))
    except (TypeError, ValueError):
        return default
