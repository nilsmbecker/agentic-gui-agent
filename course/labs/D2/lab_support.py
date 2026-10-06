"""Small printing/logging helpers. Model transport remains in Day 1 common.py."""

import copy
import json
import os
from pathlib import Path
import time

import common as C

ROOT = Path(__file__).resolve().parent


def pretty(value):
    return json.dumps(value, indent=2, ensure_ascii=False)


class Lab:
    def __init__(self, step, title, dry_run=False, verbose=False, model=None):
        self.step = step
        self.dry_run = dry_run
        self.verbose = verbose or C.VERBOSE
        self.records = []
        self.think = None
        print(f"\n{'=' * 76}\nSTEP {step} — {title}\n{'=' * 76}")
        if dry_run:
            self.model = model or os.environ.get("OLLAMA_MODEL", C.MODEL_DEFAULT)
            print("DRY RUN: requests only; no model output or performance measurements.")
        else:
            self.model = model or C.resolve_model()
            self.think = False if "thinking" in C.capabilities(self.model) else None
            print(f"model: {self.model}    host: {C.HOST}")
            C.preload(self.model)

    def request(self, messages, tools=None, fmt=None, num_predict=140):
        payload = {
            "model": self.model, "messages": copy.deepcopy(messages),
            "stream": False, "keep_alive": "30m",
            "options": {"temperature": 0, "seed": 42,
                        "num_predict": num_predict, "num_ctx": 4096},
        }
        if self.think is not None:
            payload["think"] = self.think
        if tools is not None:
            payload["tools"] = copy.deepcopy(tools)
        if fmt is not None:
            payload["format"] = fmt
        return payload

    def call(self, payload, label, show=False):
        # Snapshot before appending future turns to the original message list.
        record = {"label": label, "request": copy.deepcopy(payload)}
        print("\n" + C.rule(label))
        if show or self.verbose:
            print(pretty(payload))
        else:
            roles = [m["role"] for m in payload["messages"]]
            print(f"roles: {roles}; request JSON: {len(pretty(payload))} characters")
        self.records.append(record)
        if self.dry_run:
            return None
        start = time.perf_counter()
        try:
            with C.Waiting(label):
                response = C.post("/api/chat", payload, timeout=300)
        except (Exception, SystemExit) as exc:
            record["error"] = str(exc)
            self.save(stopped_on_error=True)
            raise
        record["wall_seconds"] = time.perf_counter() - start
        record["response"] = response
        # Keep malformed replies inspectable; the experiment validates them.
        if not isinstance(response, dict):
            print("reply:", pretty(response))
            return response
        message = response.get("message", {})
        print("reply:", (message.get("content") if isinstance(message, dict) else None)
              or pretty(message))
        print("prompt_eval_count:", response.get("prompt_eval_count", "unavailable"),
              " cached:", response.get("prompt_eval_cached_count", "unavailable"),
              " prompt_eval_ms:",
              round(response["prompt_eval_duration"] / 1e6, 3)
              if response.get("prompt_eval_duration") is not None else "unavailable")
        if response.get("done_reason") == "length":
            print("Output hit num_predict. This reply may be incomplete.")
        return response

    def save(self, **extra):
        path = ROOT / "artifacts" / f"step{self.step}.json"
        path.parent.mkdir(exist_ok=True)
        path.write_text(pretty({"step": self.step, "dry_run": self.dry_run,
                               "records": self.records, **extra}) + "\n", encoding="utf-8")
        print("\nFull requests and responses:", path)
        return path
