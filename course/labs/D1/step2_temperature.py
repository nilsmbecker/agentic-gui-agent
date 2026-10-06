#!/usr/bin/env python3
"""
STEP 2 — Sweep the temperature from 0 to 1.5 with a fixed seed.
         Find where output stops being reproducible.

Slide: "This afternoon: read the wire", step 2.

Two separate questions, and people confuse them constantly:

  (a) Same temperature, SAME seed, run three times  -> do you get the same text?
  (b) Same temperature, NO seed,   run three times  -> do you get the same text?

(a) tests whether the sampler is deterministic given a starting point.
(b) tests whether your PIPELINE is reproducible, which is the one you
    actually care about on Friday when you report a number.
"""

import sys

import common as C

PROMPT = "In one short sentence: why might a customer return a pair of headphones?"
TEMPERATURES = [0.0, 0.3, 0.7, 1.0, 1.5]
RUNS = 3
SEED = 42
NUM_PREDICT = 512


def run(temperature, seed, label):
    with C.Waiting(label):
        r = C.chat(
            [{"role": "user", "content": PROMPT}],
            temperature=temperature,
            seed=seed,
            num_predict=NUM_PREDICT,
        )
    return C.content(r).strip()


def identical(outputs):
    return len(set(outputs)) == 1


def short(text, width=54):
    text = " ".join(text.split())
    return text if len(text) <= width else text[: width - 1] + "…"


def main():
    C.banner(2, "Temperature and reproducibility",
             "Temperature is not a 'creativity' dial. It is a divisor in a formula.")

    print(f"\nprompt      : {PROMPT}")
    print(f"runs each   : {RUNS}")
    print(f"fixed seed  : {SEED}")
    print(f"num_predict : {NUM_PREDICT}   (kept short so this finishes before the break)")
    print(f"total calls : {len(TEMPERATURES) * RUNS * 2}  — this takes a few minutes, "
          f"the timer tells you it is alive")
    print()
    C.preload()
    print()

    rows = []
    for t in TEMPERATURES:
        print(C.rule(f"temperature {t}"))

        fixed = [run(t, SEED, f"T={t} seed={SEED} run {i + 1}/{RUNS}") for i in range(RUNS)]
        free = [run(t, None, f"T={t} no seed  run {i + 1}/{RUNS}") for i in range(RUNS)]

        f_same, r_same = identical(fixed), identical(free)
        rows.append((t, f_same, r_same, fixed[0]))

        print(f"  seed={SEED}   " + ("identical x3" if f_same else "DIFFERENT"))
        for i, o in enumerate(fixed, 1):
            print(f"      {i}. {short(o)}")
        print(f"  no seed     " + ("identical x3" if r_same else "DIFFERENT"))
        for i, o in enumerate(free, 1):
            print(f"      {i}. {short(o)}")
        print()

    print(C.rule("summary"))
    print(f"  {'temp':>5}  {'fixed seed':<14}{'no seed':<14}first reply")
    for t, f_same, r_same, sample in rows:
        print(f"  {t:>5}  "
              f"{'same' if f_same else 'differs':<14}"
              f"{'same' if r_same else 'differs':<14}"
              f"{short(sample, 40)}")

    first_drift = next((t for t, f, r, _ in rows if not r), None)

    print()
    print(C.rule("what you should have noticed"))
    print(f"""
  * At temperature 0 the sampler always takes the highest-scoring token, so
    the seed makes no difference — there is nothing left to randomise.
  * With a fixed seed, the same temperature should give you the same text.
    That is reproducibility you control.
  * Without a seed, output starts drifting from about temperature
    {first_drift if first_drift is not None else '(look at the table)'} upwards.

  And the warning from the slide, which you may have just seen for real:
  temperature 0 does NOT guarantee byte-identical output on every setup.
  Batching and floating-point arithmetic on a GPU can change it. If your
  temperature-0 rows differ slightly, you have not made a mistake.

  Next:  python3 step3_context_growth.py
""")


if __name__ == "__main__":
    sys.exit(main() or 0)
