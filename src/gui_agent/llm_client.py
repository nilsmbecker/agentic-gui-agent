"""Minimal client for any OpenAI-compatible /v1/chat/completions endpoint.

Plain urllib, no SDK -- same idea as course/labs/D1/common.py, so every
request is easy to inspect. Works with local Ollama (default), vLLM, etc.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

from gui_agent.config import Settings


@dataclass
class ChatResult:
    text: str
    latency_s: float
    usage: dict


class LLMClient:
    def __init__(self, settings: Settings):
        self.s = settings

    def chat(self, messages: list[dict]) -> ChatResult:
        body = {
            "model": self.s.llm_model,
            "messages": messages,
            # Sampling args mirror gelab-zero's local_server.py defaults.
            "temperature": self.s.llm_temperature,
            "top_p": 1.0,
            "max_tokens": 512,
            "stream": False,
        }
        req = urllib.request.Request(
            f"{self.s.llm_base_url}/chat/completions",
            data=json.dumps(body).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.s.llm_api_key}",
            },
        )
        start = time.monotonic()
        try:
            with urllib.request.urlopen(req, timeout=self.s.llm_timeout_s) as resp:
                data = json.load(resp)
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"LLM HTTP {e.code}: {e.read().decode()[:500]}") from e
        return ChatResult(
            text=data["choices"][0]["message"]["content"] or "",
            latency_s=time.monotonic() - start,
            usage=data.get("usage", {}),
        )
