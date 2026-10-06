#!/usr/bin/env python3
"""
STEP 3 — Hold a five-turn conversation by hand, re-sending the full history.
         Plot prompt tokens per turn.

Slide: "This afternoon: read the wire", step 3.

Nothing here is automatic. We build the message list ourselves, send the
WHOLE thing every turn, and watch prompt_eval_count climb.

The chart is drawn in the terminal so it works on every machine. If you
happen to have matplotlib installed it also writes context_growth.png.
"""

import sys

import common as C

SYSTEM = (
    "You are a support agent for an online electronics shop. "
    "The refund window for electronics is 45 days. Answer in at most two sentences."
)

TURNS = [
    "Hi — I bought a pair of headphones from you.",
    "It was order 41, placed on 2 August for 89.00 euros.",
    "They arrived with a crackling left earcup.",
    "Can I still return them?",
    "What was my order number again?",   # <- the memory test
]


def bar(n, scale):
    return "#" * max(1, int(round(n / scale)))


def main():
    C.banner(3, "Five turns, by hand",
             "The model has no memory. The history in your variable IS the memory.")

    print()
    C.preload()
    print()

    messages = [{"role": "system", "content": SYSTEM}]
    sent, back = [], []

    for i, user_text in enumerate(TURNS, 1):
        messages.append({"role": "user", "content": user_text})

        print(C.rule(f"turn {i}  —  messages in the list: {len(messages)}"))
        print(f"  you > {user_text}")

        with C.Waiting(f"turn {i} of {len(TURNS)}"):
            r = C.chat(messages, temperature=0.2, num_predict=800)
        reply = C.content(r).strip()
        messages.append({"role": "assistant", "content": reply})

        p = r.get("prompt_eval_count", 0)
        e = r.get("eval_count", 0)
        sent.append(p)
        back.append(e)

        print(f"  bot > {reply}")
        print(f"        prompt_eval_count = {p} tokens sent, eval_count = {e} back")
        print()

    # ---------------------------------------------------------------- chart
    scale = max(1, max(sent) / 50.0)
    print(C.rule("prompt tokens sent, per turn"))
    print()
    for i, p in enumerate(sent, 1):
        print(f"  turn {i}  {bar(p, scale):<52} {p:>5}")
    print()
    print(f"  total tokens sent across 5 turns : {sum(sent)}")
    print(f"  tokens you actually typed        : ~{sum(len(t.split()) for t in TURNS)} words")
    print(f"  growth from turn 1 to turn 5     : {sent[-1] / max(1, sent[0]):.1f}x")
    print()

    # --------------------------------------------------- optional PNG
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(6, 3.4), dpi=150)
        ax.bar(range(1, len(sent) + 1), sent, color="#0065BD")
        ax.set_xlabel("turn")
        ax.set_ylabel("prompt tokens sent")
        ax.set_title("Every turn re-sends the whole conversation")
        for i, v in enumerate(sent, 1):
            ax.text(i, v, str(v), ha="center", va="bottom", fontsize=8)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        fig.tight_layout()
        fig.savefig("context_growth.png")
        print("  wrote context_growth.png")
        print()
    except Exception:
        print("  (no matplotlib — the terminal chart above is the deliverable)")
        print()

    # ---------------------------------------------------- the memory test
    print(C.rule("the memory test"))
    print("""
  Turn 5 asked "what was my order number again?" and the model answered it.
  Now prove to yourself where that answer came from: run the same question
  on its own, with no history at all.
""")
    with C.Waiting("asking with no history"):
        alone = C.chat(
            [{"role": "system", "content": SYSTEM},
             {"role": "user", "content": TURNS[-1]}],
            temperature=0.2, num_predict=120,
        )
    print(f"  with no history > {C.content(alone).strip()}")
    print(f"  ({C.stats(alone)})")

    print()
    print(C.rule("what you should have noticed"))
    print(f"""
  * The bars grow every turn even though your messages stayed short. That is
    the linear cost of a stateless model: turn 5 re-sent turns 1 to 4 in full.
  * On turn 5 the model "remembered" order 41. It did not. You sent it again.
  * With the history removed it cannot answer, and — watch this closely — it
    usually does not say "I don't know". It invents something, confidently.

  That last point is the reason the rest of this week exists.

  Next:  python3 step4_chat_template.py
""")


if __name__ == "__main__":
    sys.exit(main() or 0)
