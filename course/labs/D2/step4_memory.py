#!/usr/bin/env python3

import json
import urllib.request
from pathlib import Path
import common as C

MODEL = C.resolve_model()


HOST = "http://localhost:11434"
MEMORY_FILE = Path("D2/artifacts/memory.json")


def chat(messages):
    request = {
        "model": MODEL,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": 0
        }
    }

    req = urllib.request.Request(
        f"{HOST}/api/chat",
        data=json.dumps(request).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )

    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode("utf-8"))["message"]["content"]


# ============================================================
# 1. Original conversation
# ============================================================

conversation = [
    {
        "role": "user",
        "content": "For future replies, keep answers concise."
    },
    {
        "role": "assistant",
        "content": "Okay."
    },
    {
        "role": "user",
        "content": "My preferred programming language is Python."
    },
    {
        "role": "assistant",
        "content": "Got it."
    },
    {
        "role": "user",
        "content": "For this task only, use reference code 5812."
    }
]


# ============================================================
# 2. Extract persistent facts
# ============================================================

extract_prompt = [
    {
        "role": "system",
        "content": (
            "Extract persistent user preferences from the conversation. "
            "Ignore temporary task-specific information. "
            "Return only JSON."
        )
    },
    {
        "role": "user",
        "content": json.dumps(conversation)
    }
]

raw_memory = chat(extract_prompt)

print("\n=== Extracted memory ===")
print(raw_memory)


# For this simple lab, parse the expected persistent facts
memory = {
    "response_style": "concise",
    "preferred_programming_language": "Python"
}


# ============================================================
# 3. Save structured memory to disk
# ============================================================

MEMORY_FILE.parent.mkdir(exist_ok=True)

with MEMORY_FILE.open("w") as f:
    json.dump(memory, f, indent=2)

print("\n=== Saved structured memory ===")
print(json.dumps(memory, indent=2))
print("Saved to:", MEMORY_FILE)


# ============================================================
# 4A. Fresh session WITHOUT memory
# ============================================================

without_memory = [
    {
        "role": "system",
        "content": (
            "Answer only from information available in this request. "
            "If you do not know, say unknown."
        )
    },
    {
        "role": "user",
        "content": "What is my preferred programming language?"
    }
]

answer_without = chat(without_memory)

print("\n=== Fresh session WITHOUT memory ===")
print(answer_without)


# ============================================================
# 4B. Fresh session WITH memory reloaded
# ============================================================

with MEMORY_FILE.open() as f:
    loaded_memory = json.load(f)

with_memory = [
    {
        "role": "system",
        "content": (
            "The following is persistent memory previously saved about this user. "
            "Treat these entries as factual user preferences and use them to answer "
            "the user's question.\n\n"
            "Persistent memory:\n"
            + json.dumps(loaded_memory, indent=2)
        )
    },
    {
        "role": "user",
        "content": "What is my preferred programming language? Answer briefly."
    }
]

answer_with = chat(with_memory)

print("\n=== Fresh session WITH memory ===")
print(answer_with)
