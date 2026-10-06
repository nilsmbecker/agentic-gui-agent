"""
Agentic AI — Day 1 client, reused for Day 2
A very small Ollama client, written with the standard library only.

There is no SDK here on purpose. The point of today is that nothing between
you and the model is a black box, so every request is a dict you can print
and every response is a dict you can inspect.

Ollama speaks plain HTTP on http://localhost:11434.
"""

import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request

HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")

# Override with:  export OLLAMA_MODEL=qwen3-vl-4b:latest
MODEL_ENV = os.environ.get("OLLAMA_MODEL")
MODEL_DEFAULT = "qwen3-vl-4b:latest"

# Set VERBOSE=1 to print the exact JSON going out and coming back.
VERBOSE = os.environ.get("VERBOSE", "") not in ("", "0", "false", "False")


# --------------------------------------------------------------------------
# transport
# --------------------------------------------------------------------------

def post(path, payload, timeout=600):
    """POST a JSON body to Ollama and return the decoded JSON reply."""
    url = f"{HOST}{path}"
    body = json.dumps(payload).encode("utf-8")

    if VERBOSE:
        print(f"\n--- POST {url}", file=sys.stderr)
        print(_pretty(payload), file=sys.stderr)

    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            out = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        die(f"Ollama returned HTTP {exc.code} at {url}\n{detail}")
    except urllib.error.URLError as exc:
        die(
            f"Could not reach Ollama at {HOST}  ({exc})\n"
            "Is it running?  Try:   ollama serve      (or just open the Ollama app)"
        )

    if VERBOSE:
        print(f"--- reply", file=sys.stderr)
        print(_pretty(out), file=sys.stderr)
    return out


def get(path, timeout=30):
    url = f"{HOST}{path}"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        die(
            f"Could not reach Ollama at {HOST}  ({exc})\n"
            "Is it running?  Try:   ollama serve      (or just open the Ollama app)"
        )


def _pretty(obj, limit=900):
    """Dump JSON, but shorten base64 images so the terminal stays readable."""
    def shorten(o):
        if isinstance(o, dict):
            return {k: (["<base64 image, %d chars>" % len(v[0])] if k == "images" and v
                        else shorten(v)) for k, v in o.items()}
        if isinstance(o, list):
            return [shorten(v) for v in o]
        if isinstance(o, str) and len(o) > limit:
            return o[:limit] + f"… (+{len(o) - limit} chars)"
        return o
    return json.dumps(shorten(obj), indent=2, ensure_ascii=False)


# --------------------------------------------------------------------------
# the two calls this lab uses
# --------------------------------------------------------------------------

def chat(messages, model=None, temperature=None, seed=None, fmt=None,
         tools=None, num_predict=None, timeout=600, think=None):
    """
    POST /api/chat, non-streaming.

    Returns the whole response dict. The interesting keys are:
        ["message"]["content"]   the text that came back
        ["message"]["thinking"]  present only on thinking models
        ["prompt_eval_count"]    server-reported prompt counter (version/cache dependent)
        ["eval_count"]           how many tokens came back
        ["total_duration"]       nanoseconds
        ["done_reason"]          "stop" = it finished; "length" = it ran out of room
    """
    payload = {
        "model": model or resolve_model(),
        "messages": messages,
        "stream": False,
    }
    options = {}
    if temperature is not None:
        options["temperature"] = temperature
    if seed is not None:
        options["seed"] = seed
    if num_predict is not None:
        options["num_predict"] = num_predict
    if options:
        payload["options"] = options
    if fmt is not None:
        payload["format"] = fmt
    if tools is not None:
        payload["tools"] = tools

    # Thinking models spend their token budget reasoning before they answer,
    # which would leave most of this lab printing empty strings. Switch it
    # off by default, but only if the model actually supports the flag.
    if think is None:
        think = False if "thinking" in capabilities(payload["model"]) else None
    if think is not None:
        payload["think"] = think

    return post("/api/chat", payload, timeout=timeout)


def chat_stream(messages, model=None, temperature=None, seed=None,
                num_predict=None, timeout=600, think=None, out=None):
    """
    Same request as chat(), but with "stream": true.

    Ollama then replies with one JSON object per line. We print the tokens as
    they arrive — partly so you can see that generation really is one token
    at a time, and partly so a slow laptop does not look like a crash.

    Returns the final object, which carries the same counters as chat().
    """
    out = out or sys.stdout
    payload = {
        "model": model or resolve_model(),
        "messages": messages,
        "stream": True,
    }
    options = {}
    if temperature is not None:
        options["temperature"] = temperature
    if seed is not None:
        options["seed"] = seed
    if num_predict is not None:
        options["num_predict"] = num_predict
    if options:
        payload["options"] = options
    if think is None:
        think = False if "thinking" in capabilities(payload["model"]) else None
    if think is not None:
        payload["think"] = think

    if VERBOSE:
        print(f"\n--- POST {HOST}/api/chat  (streaming)", file=sys.stderr)
        print(_pretty(payload), file=sys.stderr)

    req = urllib.request.Request(
        f"{HOST}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    pieces, final = [], {}
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            for line in resp:
                line = line.strip()
                if not line:
                    continue
                chunk = json.loads(line.decode("utf-8"))
                token = (chunk.get("message") or {}).get("content", "")
                if token:
                    pieces.append(token)
                    out.write(token)
                    out.flush()
                if chunk.get("done"):
                    final = chunk
    except urllib.error.URLError as exc:
        die(f"Could not reach Ollama at {HOST}  ({exc})")

    final.setdefault("message", {})["content"] = "".join(pieces)
    return final


def preload(model=None):
    """
    Load the model into memory before the first real question.

    An empty messages array tells Ollama to load and return. Without this the
    first request looks frozen for however long it takes to read a few GB off
    disk, and everyone assumes the script has hung.
    """
    model = model or resolve_model()
    print(f"  loading {model} into memory (first run can take a minute)... ",
          end="", flush=True)
    t0 = time.time()
    post("/api/chat", {"model": model, "messages": [], "keep_alive": "30m"}, timeout=900)
    print(f"ready in {time.time() - t0:.1f}s")


class Waiting:
    """
    Print elapsed seconds while a blocking call runs.

    Used by the non-streaming steps so a slow generation never looks like a
    crash. Nothing clever — a thread and a carriage return.
    """

    def __init__(self, label="thinking"):
        self.label = label
        self._stop = threading.Event()
        self._thread = None

    def __enter__(self):
        def tick():
            t0 = time.time()
            while not self._stop.wait(0.25):
                sys.stdout.write(f"\r  {self.label}... {time.time() - t0:4.1f}s")
                sys.stdout.flush()
        self._thread = threading.Thread(target=tick, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *exc):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1)
        sys.stdout.write("\r" + " " * 40 + "\r")
        sys.stdout.flush()
        return False


def show(model=None):
    """POST /api/show — the model's prompt template, parameters and metadata."""
    return post("/api/show", {"model": model or resolve_model()}, timeout=60)


def tags():
    """GET /api/tags — every model installed on this machine."""
    return get("/api/tags").get("models", [])


_caps_cache = {}


def capabilities(model=None):
    """What this model can do: e.g. ['completion', 'vision', 'thinking']."""
    model = model or resolve_model()
    if model not in _caps_cache:
        try:
            _caps_cache[model] = show(model).get("capabilities", []) or []
        except SystemExit:
            raise
        except Exception:
            _caps_cache[model] = []
    return _caps_cache[model]


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

_resolved = None


def resolve_model():
    """
    Work out which model tag to use.

    Order: $OLLAMA_MODEL, the local 4B course tag, then the official 4B tag.
    Other models require an explicit override; a missing 4B model is an error.
    """
    global _resolved
    if _resolved:
        return _resolved
    if MODEL_ENV:
        _resolved = MODEL_ENV
        return _resolved

    installed = [m.get("name", "") for m in tags()]
    for want in (MODEL_DEFAULT, "qwen3-vl:4b"):
        if want in installed:
            _resolved = want
            return _resolved
    die(
        f"No default 4B course model found ({MODEL_DEFAULT} or qwen3-vl:4b).\n"
        f"Installed: {', '.join(installed) or '(none)'}\n\n"
        "Pull it with:   ollama pull qwen3-vl:4b\n"
        "Or point the lab at another model:   export OLLAMA_MODEL=<tag>"
    )


def content(response):
    """The reply text. Thinking models put their reasoning in a separate field."""
    return (response.get("message") or {}).get("content", "")


def thinking(response):
    return (response.get("message") or {}).get("thinking") or ""


def stats(response):
    """One line of the numbers that matter, for printing under a reply."""
    sent = response.get("prompt_eval_count", 0)
    back = response.get("eval_count", 0)
    secs = response.get("total_duration", 0) / 1e9
    tps = (back / (response.get("eval_duration", 1) / 1e9)) if response.get("eval_duration") else 0
    return (f"prompt_eval_count {sent} · got {back} back · {secs:.1f}s · "
            f"{tps:.1f} tok/s · done_reason={response.get('done_reason', '?')}")


def rule(title=""):
    width = 78
    if not title:
        return "-" * width
    return f"--- {title} " + "-" * max(0, width - len(title) - 5)


def die(msg):
    print("\n" + msg + "\n", file=sys.stderr)
    raise SystemExit(1)


def banner(step, title, purpose):
    print()
    print("=" * 78)
    print(f"  STEP {step} — {title}")
    print(f"  {purpose}")
    print(f"  model: {resolve_model()}    host: {HOST}")
    print("=" * 78)
