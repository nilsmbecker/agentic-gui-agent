#!/usr/bin/env python3
"""
STEP 0 — is this machine ready?

Run this first. It answers the only question that matters before the lab
starts: will step 1 work on your laptop, or do you need help now rather
than at half past two.
"""

import sys

import common as C


def main():
    ok = True

    print(C.rule("1. Is the Ollama server reachable?"))
    try:
        version = C.get("/api/version")
        print(f"   yes — Ollama {version.get('version', '?')} at {C.HOST}")
    except SystemExit:
        raise
    print()

    print(C.rule("2. What is installed on this machine?"))
    models = C.tags()
    if not models:
        print("   nothing. Pull the course model:   ollama pull qwen3-vl:4b")
        ok = False
    for m in models:
        size_gb = m.get("size", 0) / 1e9
        det = m.get("details", {})
        print(f"   {m.get('name'):<34} {size_gb:5.1f} GB   "
              f"{det.get('parameter_size', '?'):>6}  {det.get('quantization_level', '?')}")
    print()

    print(C.rule("3. Which model will the lab use?"))
    model = C.resolve_model()
    print(f"   {model}")
    print("   (override any time with:  export OLLAMA_MODEL=<tag>)")
    print()

    print(C.rule("4. What can it do?"))
    info = C.show(model)
    caps = info.get("capabilities", [])
    print(f"   capabilities: {', '.join(caps) if caps else '(not reported)'}")
    ctx = None
    for k, v in (info.get("model_info") or {}).items():
        if k.endswith(".context_length"):
            ctx = v
    print(f"   context window: {ctx if ctx else '(not reported)'} tokens")
    if "vision" not in caps:
        print("   note: no vision capability reported — step 5 will not work.")
    print()

    print(C.rule("5. Can it actually answer?"))
    print("   (first call loads the model off disk — a minute is normal)")
    with C.Waiting("loading and answering"):
        r = C.chat([{"role": "user", "content": "Reply with exactly one word: ready"}],
                   temperature=0, num_predict=1052)
    reply = C.content(r).strip()
    print(f"   reply: {reply!r}")
    print(f"   {C.stats(r)}")
    if "thinking" in caps:
        print("   note: this is a thinking model — the lab sends think=false so")
        print("         the token budget goes to the answer, not the reasoning.")
    if not reply:
        print("   WARNING: empty reply. Raise num_predict, or check `ollama ps`.")
        ok = False
    print()

    print("=" * 78)
    if ok:
        print("  You are ready. Start with:   python3 step1_chat.py")
    else:
        print("  Not ready yet — fix the lines above, then run this again.")
    print("=" * 78)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
