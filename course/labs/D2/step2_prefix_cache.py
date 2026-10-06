#!/usr/bin/env python3
"""STEP 2 — Move changing information and measure prompt processing."""

import argparse
import csv
import os
from pathlib import Path
import statistics
import time

import common as C
from lab_support import Lab, pretty


def messages_for(layout, pair_id, revision, lines):
    stable = "Read the reference text below, then answer the final instruction.\n" + "\n".join(
        f"Reference {i:03d}: context contains instructions, observations, previous messages and current state."
        for i in range(lines)
    )
    dynamic = f"Current status revision: {revision:04d}.\n"
    # The pair ID prevents earlier pairs having an identical complete prefix.
    start = f"Measurement pair {pair_id}.\n"
    system = start + (dynamic + stable if layout == "early" else stable + "\n" + dynamic)
    # print(stable)
    # print(dynamic)
    return [{"role": "system", "content": system},
            {"role": "user", "content": "Reply with the single word OK."}]


def common_prefix_characters(a, b):
    return len(os.path.commonprefix([pretty(a), pretty(b)]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--prefix-lines", type=int, default=48)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.repeats <= 20 or not 8 <= args.prefix_lines <= 80:
        parser.error("Use 1–20 repeats and 8–80 prefix lines.")
    lab = Lab(2, "Stable prefix and changing state", args.dry_run, args.verbose)
    rows = []
    run_id = time.time_ns()
    print("Each condition has a warm request immediately followed by a measured request.")
    print("Only the status revision changes within a pair. Condition order alternates.")

    for repeat in range(args.repeats):
        for layout in (("early", "late") if repeat % 2 == 0 else ("late", "early")):
            pair_id = f"{run_id}-{repeat}-{layout}"
            warm = messages_for(layout, pair_id, 1, args.prefix_lines)
            measured = messages_for(layout, pair_id, 2, args.prefix_lines)
            shared = common_prefix_characters(warm, measured)
            print(f"\n{layout}: shared serialized prefix = {shared} characters (not a token count)")
            lab.call(lab.request(warm, num_predict=4), f"{layout} pair {repeat + 1}: warm")
            response = lab.call(lab.request(measured, num_predict=4),
                                f"{layout} pair {repeat + 1}: measured")
            if response is not None:
                duration = response.get("prompt_eval_duration")
                rows.append({"layout": layout, "repeat": repeat + 1,
                             "prompt_eval_ms": duration / 1e6 if duration is not None else None,
                             "prompt_eval_count": response.get("prompt_eval_count"),
                             "prompt_eval_cached_count": response.get("prompt_eval_cached_count"),
                             "wall_seconds": lab.records[-1]["wall_seconds"],
                             "shared_json_prefix_characters": shared})

    lab.save(measurements=rows)
    if rows:
        path = Path(__file__).resolve().parent / "artifacts" / "step2_measurements.csv"
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        print("\nMeasured prompt-processing medians:")
        for layout in ("early", "late"):
            values = [r["prompt_eval_ms"] for r in rows
                      if r["layout"] == layout and r["prompt_eval_ms"] is not None]
            print(f"  {layout:5}: {statistics.median(values):.3f} ms" if values
                  else f"  {layout:5}: server did not expose prompt_eval_duration")
        print("CSV:", path)
    print(C.rule("what you should have noticed"))
    print("""  * Moving the changing field later leaves a longer prefix unchanged.
  * Compare prompt_eval_duration, not just total request time or output tokens.
  * Cache fields and counter semantics vary by Ollama version. Missing is not zero.
  * A shared text prefix shows reuse potential; it does not prove a cache hit.
  * No measurable speedup is a valid observation. Do not invent one.

  Check: compare the measured rows, not the warm-up rows.
  Next: python3 step3_skill_status.py""")


if __name__ == "__main__":
    main()
