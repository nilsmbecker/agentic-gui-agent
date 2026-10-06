#!/usr/bin/env python3
"""
STEP 1 — Run a small model locally and chat with it in the terminal.

Slide: "This afternoon: read the wire", step 1.

The point is not that you can chat with a model. You have all done that.
The point is that a chat is a POST request with a list of messages in it,
and that YOU are holding the conversation, not the server.

Type /raw to see the exact JSON of the next exchange.
Type /new to throw the history away and watch the token count collapse.
Type /quit to leave.
"""

import sys

import common as C

SYSTEM = "You are a support agent. Answer in at most three sentences."

# Cap the reply length. Without this a small model can ramble for minutes and
# the terminal looks frozen.
MAX_TOKENS = 200


def main():
    C.banner(1, "Chat in the terminal",
             "A conversation is a list of messages that YOU keep and resend.")

    print()
    C.preload()

    print("\nThe system message below is sent at the start of every single request:")
    print(f'   {{"role": "system", "content": "{SYSTEM}"}}')
    print("\nCommands:  /raw  show the next request+reply as JSON")
    print("           /hist show the message list as it stands")
    print("           /new  clear the history")
    print("           /quit")
    print("\nReplies stream in token by token. A 4B model on a laptop runs at a")
    print("few tokens a second, so give it a moment — it is working, not stuck.")
    print()

    messages = [{"role": "system", "content": SYSTEM}]
    show_raw = False

    while True:
        try:
            user = input("you > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user:
            continue
        if user == "/quit":
            break
        if user == "/new":
            messages = [{"role": "system", "content": SYSTEM}]
            print("   history cleared — you are back to 1 message\n")
            continue
        if user == "/raw":
            show_raw = True
            print("   next exchange will be printed as JSON\n")
            continue
        if user == "/hist":
            print()
            print(C._pretty(messages))
            print(f"\n   {len(messages)} messages in the list\n")
            continue

        messages.append({"role": "user", "content": user})

        if show_raw:
            print("\n" + C.rule("what goes out over HTTP"))
            print(C._pretty({
                "model": C.resolve_model(),
                "messages": messages,
                "stream": False,
                "options": {"temperature": 0.7},
            }))

        if show_raw:
            # non-streaming, so the reply arrives as one printable object
            with C.Waiting("waiting for the whole reply"):
                response = C.chat(messages, temperature=0.7, num_predict=MAX_TOKENS)
            print("\n" + C.rule("what comes back"))
            print(C._pretty(response))
            print()
            show_raw = False
            reply = C.content(response).strip()
            print(f"bot > {reply}")
        else:
            print("bot > ", end="", flush=True)
            response = C.chat_stream(messages, temperature=0.7, num_predict=MAX_TOKENS)
            reply = C.content(response).strip()
            print()

        print(f"      ({C.stats(response)})\n")

        # This line is the whole lesson: the model has no memory, so we keep it.
        messages.append({"role": "assistant", "content": reply})

    print("\n" + C.rule("what you should have noticed"))
    print("""
  * You appended every reply to `messages` yourself. Nothing on the server
    remembered anything between requests.
  * "sent N tokens" grew every turn, even when your question was short.
    You are paying for the whole conversation, every single time.
  * /new dropped it back to almost nothing — because the history IS the memory.

  Next:  python3 step2_temperature.py
""")


if __name__ == "__main__":
    sys.exit(main() or 0)
