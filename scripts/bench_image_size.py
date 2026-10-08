"""A/B test: how the screenshot size sent to GELab changes prompt tokens, latency and the action.

Replays one saved screenshot as a step-0 prompt (same goal, same GELab prompt, no history),
so the only thing that changes between rows is the image. Needs Ollama only, no emulator.

Example:
  python scripts/bench_image_size.py --image runs/SystemWifiTurnOn/<run_id>/step_000.png \
      --goal "Turn wifi on." --sizes 0 728 --repeat 1

Size 0 = full-resolution PNG (what we sent before), 728 = gelab-zero's own deployment size.
Result on our CPU (2026-10-08): full res 3,193 prompt tokens / 116 s; 1024, 728 and 512 all
1,667 tokens / 51-55 s, because Ollama upscales images below ~1024x1024. Same action in every row.
"""

from __future__ import annotations

import argparse

import numpy as np
from PIL import Image

from gui_agent.config import Settings
from gui_agent.gelab import Parser0920Summary, parse_action, pixels_to_data_url
from gui_agent.llm_client import LLMClient


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--image", required=True, help="a saved screenshot, e.g. runs/<task>/<run>/step_000.png")
    ap.add_argument("--goal", required=True, help="the task goal shown in that run's summary.json")
    ap.add_argument("--sizes", type=int, nargs="+", default=[0, 728], help="0 = full resolution")
    ap.add_argument("--repeat", type=int, default=1)
    args = ap.parse_args()

    s = Settings.from_env()
    llm, parser = LLMClient(s), Parser0920Summary()
    pixels = np.asarray(Image.open(args.image).convert("RGB"))
    height, width = pixels.shape[:2]

    calls = 0

    def ask(size: int):
        # Ollama reuses its cache for an identical prompt prefix, image included. Like in a real
        # step, only the text before the screenshot may be cached, so every call gets an image it
        # has not seen yet: a 16x16 corner patch (status bar) with a different gray value.
        nonlocal calls
        calls += 1
        img = pixels.copy()
        img[:16, :16] = (calls * 37) % 256
        env = [{"image": pixels_to_data_url(img, size), "user_comment": ""}]
        return llm.chat(parser.env2messages4ask(task=args.goal, environments=env, actions=[]))

    # Not measured: loads the model and caches the shared text prefix.
    print("warm-up call (not measured) ...", flush=True)
    ask(min(args.sizes, key=lambda x: x or 10**9))

    print(f"\nscreenshot {width}x{height} | model {s.llm_model} ({s.llm_quant})\n")
    print("| image sent | prompt tokens | completion tokens | latency s | action |")
    print("|---|---|---|---|---|")
    for size in args.sizes:
        for _ in range(args.repeat):
            reply = ask(size)
            try:
                a = parse_action(parser, reply.text)
                act = " ".join(str(a.get(k)) for k in ("action", "point", "point1", "point2") if k in a)
            except (AssertionError, ValueError, KeyError) as e:
                act = f"PARSE_ERROR: {e}"
            sent = f"{size}x{size} JPEG" if size else f"{width}x{height} PNG"
            u = reply.usage
            print(
                f"| {sent} | {u.get('prompt_tokens')} | {u.get('completion_tokens')} "
                f"| {reply.latency_s:.1f} | {act} |",
                flush=True,
            )


if __name__ == "__main__":
    main()
