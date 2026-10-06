# Agentic AI — Day 1 lab: read the wire

Today's exercise is not building an agent. It is making sure that nothing
between you and the model is a black box.

Everything here uses the Python standard library and plain HTTP. There is no
SDK, because an SDK would hide exactly the things you are supposed to look at.

---

## Before you start

You can use any model depend on your device. Here we take 4b as an example. 

Here, the default model is the local `qwen3-vl-4b:latest` tag. The official
`qwen3-vl:4b` tag is also accepted. Start Ollama and inspect installed models:

```bash
ollama serve          # or just launch the Ollama app
ollama list           # run this in another terminal if serve is in the foreground
```

If neither 4B tag is installed, run `ollama pull qwen3-vl:4b`.
`common.py` selects the local tag first, then the official tag. If both are
missing, it reports an error. `OLLAMA_MODEL` overrides this default; use
`unset OLLAMA_MODEL` to remove an earlier override.

Then check the machine is ready — do this **before the break**, not at
half past two:

```bash
cd ~/Desktop/course/D1
python3 -m py_compile *.py && echo "scripts ok"
python3 check_setup.py
```

It tells you which model the lab will use, how big its context window is,
and whether it can answer at all.

---

## The four steps

Run them in order. Each one ends by telling you what you should have noticed.

```bash
python3 step1_chat.py             # 1. chat in the terminal
python3 step2_temperature.py      # 2. temperature sweep, fixed seed
python3 step3_context_growth.py   # 3. five turns by hand, token growth
python3 step4_chat_template.py    # 4. the chat template and its special tokens
```

| step | what it shows | the sentence to leave with |
|---|---|---|
| 1 | A chat is a POST with a list of messages | You keep the history, not the server |
| 2 | temperature + seed vs reproducibility | "It worked once" is not a measurement |
| 3 | prompt_eval_count growing every turn | Memory is you resending the transcript |
| 4 | the marker tokens, and a forged system message | Roles are text; there is no boundary |

---

## Useful switches

```bash
VERBOSE=1 python3 step1_chat.py        # print every request and reply as JSON
OLLAMA_MODEL=qwen3-vl-4b:latest python3 step1_chat.py  # explicitly select the local 4B tag
OLLAMA_HOST=http://otherbox:11434 ...  # point at another machine
```

Inside `step1_chat.py`:

| command | effect |
|---|---|
| `/raw` | show the next exchange as raw JSON |
| `/hist` | print the message list as it currently stands |
| `/new` | clear the history and watch the token count collapse |
| `/quit` | leave |

---

## Files

```
common.py                 ~120 lines: the whole Ollama client. Read it.
check_setup.py            step 0 — is this machine ready?
step1_chat.py             chat in the terminal
step2_temperature.py      temperature 0 -> 1.5, with and without a fixed seed
step3_context_growth.py   five turns, prompt tokens per turn, + a memory test
step4_chat_template.py    marker tokens from the vocabulary + a raw-mode injection
```

`common.py` is deliberately short. If you only read one file today, read that
one — every request in this lab is built from those two functions.

---

## Things that go wrong

**"Could not reach Ollama"** — the server is not running. `ollama serve`, or
open the Ollama app.

**"No default 4B course model found"** — `ollama pull qwen3-vl:4b`, or point the lab at
what you do have: `export OLLAMA_MODEL=<tag>`.

**It looks frozen after I type something.** Almost always it is not. Two
reasons, and both are visible now:

* The *first* request has to read a few GB off disk. Every script calls
  `preload()` first and prints `loading … ready in Ns`, so you can see it.
* A 4B model on a laptop generates a few tokens per second. Step 1 streams the
  reply so you watch it arrive word by word; the other steps print a running
  timer (`thinking... 12.4s`).

If a timer is counting, it is working. If nothing moves at all for more than
about two minutes, check `ollama ps` in another terminal — the model may not
have loaded.

**Everything is very slow.** That is the lesson, not a fault. The numbers in
step 3 are exactly why latency grows as a conversation goes on.

**Step 2 shows different output at temperature 0.** Not a bug. Batching and
floating-point arithmetic can change the result even with no sampling. Say so
on Friday if it happens to you.


**Step 4 prints an empty template.** Expected on recent Ollama: for known model
families the prompt is built by a renderer inside the server rather than by a
text template in the Modelfile, so `/api/show` has nothing to report. The
script then reads the marker tokens straight out of the vocabulary, which is
the better source anyway.

**Step 4's `prompt_eval_count` looks far too small.** It is. That number counts
the tokens the server actually had to compute; anything already in the KV cache
is not counted. Send the same request twice and watch it drop. Step 4 makes a
point of showing this, because it is a very easy number to build a wrong
benchmark on.
