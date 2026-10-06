"""Minimal hosted agent: built-in web search, an editable task, and a TXT trace."""

import json
from datetime import datetime
from pathlib import Path
from openai import OpenAI

# Configuration: fill in your key and change the task.
API_KEY == "PASTE_YOUR_API_KEY_HERE"
BASE_URL = "https://api.openai.com/v1"  # Uses /responses, not /chat/completions.
MODEL = "gpt-5-mini"
TASK = "Find the latest stable Python release and its release date. Verify with official sources."


def main():
    if not API_KEY.strip() or API_KEY == "PASTE_YOUR_API_KEY_HERE":
        raise SystemExit("Fill API_KEY at the top of this script first.")

    # Enable a hosted tool; no custom function or JSON Schema is needed.
    request = {
        "model": MODEL,
        "instructions": "Use web search when needed. Check the evidence, search again if needed, and answer concisely with Markdown source links.",
        "input": TASK,
        "tools": [{"type": "web_search"}],
        "tool_choice": "auto",
        "reasoning": {"effort": "low"},
        "max_tool_calls": 4,
        "include": ["web_search_call.action.sources"],
    }
    path = Path(__file__).with_name(f"agent_trace_{datetime.now():%Y%m%d_%H%M%S_%f}.txt")
    with path.open("x", encoding="utf-8") as file:
        def log(title, data):
            text = json.dumps(data, ensure_ascii=False, indent=2).replace(API_KEY, "[REDACTED]")
            file.write(f"\n--- {title} ---\n{text}\n")
            file.flush()

        print(f"Trace log: {path}")
        log("LOG GUIDE", "Initial context and API-visible output only. Internal contexts and full search observations are not exposed here.")
        log("INITIAL CONTEXT / API REQUEST", request)

        # OpenAI runs the model -> search -> observation -> model loop.
        try:
            # Avoid incompatible optional decompressors in older Conda environments.
            with OpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=120, max_retries=0,
                        default_headers={"Accept-Encoding": "identity"}) as client:
                response = client.responses.create(**request)
        except Exception as error:
            log("API ERROR", {"type": type(error).__name__, "message": str(error)})
            detail = f"{type(error).__name__}: {error}".replace(API_KEY, "[REDACTED]")
            raise SystemExit(f"{detail}\nSee the trace log for details.") from None

        # Output items are visible trace items, not complete internal rounds.
        data = response.model_dump(mode="json")
        log("RESPONSE METADATA", {k: v for k, v in data.items() if k != "output"})
        for index, item in enumerate(data.get("output", []), 1):
            log(f"VISIBLE TRACE ITEM {index}: {item['type']}", item)
        log("RESPONSE TEXT", response.output_text)
        print(f"Status: {response.status}\n{response.output_text}")


if __name__ == "__main__":
    main()
