#!/usr/bin/env python3
"""Load a Skill on demand and include a code-maintained status snapshot."""

import json
from pathlib import Path
import urllib.error
import urllib.request

import common as C


SKILL_PATH = Path(__file__).resolve().parent / "skills" / "three-bullet-summary" / "SKILL.md"

user_text = """
Summarize this text in three bullet points:

A model request contains the context assembled for that call.
A stable prefix may allow cached computations to be reused.
Persistent memory has to be stored outside the model.
""".strip()


def should_load_skill(user_text):
    text = user_text.lower()
    return "three bullet" in text or "3 bullet" in text


def build_request(model, user_text, loaded_skill, status):
    """Build a request without changing status or contacting the model."""
    system_content = "Answer the user's request."
    if loaded_skill is not None:
        system_content += (
            "\n\nThe following Skill is procedural guidance. "
            "Follow it when answering the user's request:\n"
            "<skill>\n" + loaded_skill + "\n</skill>"
        )

    # Serialize now: later status changes must not rewrite this snapshot.
    status_snapshot = json.dumps(status, indent=2, ensure_ascii=False)
    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_text},
        {
            "role": "user",
            "content": (
                "Current agent status maintained by Python:\n"
                "<agent_status>\n" + status_snapshot + "\n</agent_status>"
            ),
        },
    ]
    return {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0},
    }


def call_model(model, user_text, loaded_skill, status, timeout=60):
    """Count attempted chat requests; update phase on both success and failure."""
    status["phase"] = "preparing_request"
    status.pop("error", None)
    try:
        # Prepare the state the model should see, without counting a call yet.
        call_status = {
            **status,
            "model_calls": status["model_calls"] + 1,
            "phase": "calling_model",
        }
        request = build_request(model, user_text, loaded_skill, call_status)
        req = urllib.request.Request(
            f"{C.HOST}/api/chat",
            data=json.dumps(request).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        print("\n" + "=" * 70)
        print("NEXT REQUEST")
        print("=" * 70)
        print(json.dumps(request, indent=2, ensure_ascii=False))

        # Only count once construction succeeded and a send is being attempted.
        status.update(call_status)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))

        if not isinstance(data, dict):
            raise ValueError("Ollama response must be a JSON object.")
        if data.get("error"):
            raise ValueError(f"Ollama error: {data['error']}")
        message = data.get("message")
        if not isinstance(message, dict):
            raise ValueError("Ollama response is missing an assistant message.")
        answer = message.get("content")
        if (message.get("role") != "assistant"
                or not isinstance(answer, str) or not answer.strip()):
            raise ValueError("Ollama response is missing a non-empty assistant answer.")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        error = f"Ollama returned HTTP {exc.code} at {exc.url}\n{detail}"
    except urllib.error.URLError as exc:
        error = f"Could not reach Ollama at {C.HOST}: {exc.reason}"
    except Exception as exc:
        error = str(exc)
    else:
        status["phase"] = "completed"
        return answer

    status.update(phase="failed", error=error)
    raise RuntimeError(error)


def main():
    status = {
        "skill_loaded": False,
        "skill_name": None,
        # Attempted generation requests, including failed sends; not previews.
        "model_calls": 0,
        "phase": "waiting",
    }

    try:
        loaded_skill = None
        if should_load_skill(user_text):
            loaded_skill = SKILL_PATH.read_text(encoding="utf-8")
            status.update(skill_loaded=True, skill_name="three-bullet-summary")
            print("Trigger matched.")
            print("Loaded Skill:", SKILL_PATH)
        else:
            print("Trigger did not match.")
            print("Skill was not loaded.")

        # Resolve only when running the experiment, not when importing helpers.
        model = C.resolve_model()
        answer = call_model(model, user_text, loaded_skill, status)
        print("\n" + "=" * 70)
        print("MODEL RESPONSE")
        print("=" * 70)
        print(answer)
        return 0
    except SystemExit:
        # common.py already prints the model setup error before exiting.
        status.update(phase="failed", error="Model setup failed; see the error above.")
        return 1
    except Exception as exc:
        status.update(phase="failed", error=str(exc))
        print(f"\nError: {exc}")
        return 1
    except KeyboardInterrupt:
        status["phase"] = "interrupted"
        print("\nInterrupted.")
        return 130
    finally:
        print("\nFinal status:")
        print(json.dumps(status, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    raise SystemExit(main())
