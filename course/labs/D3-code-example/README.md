# Minimal Agent with a Built-in Tool

## Quick start

1. Add API credits through the official [OpenAI API billing page](https://platform.openai.com/account/billing/overview).
2. Install the SDK in the Python environment you will use:

   ```bash
   python3 -m pip install --upgrade "openai[aiohttp]"
   ```

3. Edit the settings at the top of `minimal_agent.py`:

   ```python
   API_KEY = "PASTE_YOUR_API_KEY_HERE"
   BASE_URL = "https://api.openai.com/v1"
   MODEL = "gpt-5-mini"
   TASK = "Find the latest stable Python release and its release date. Verify with official sources."
   ```

4. Run from the script's folder:

   ```bash
   python3 minimal_agent.py
   ```

The script prints the answer and saves a TXT trace beside the script. Use the same Python interpreter for installation and execution.

## Available models

Change `MODEL` to choose a model:

| Model ID | Suggested use |
| --- | --- |
| `gpt-5-mini` | Current default for this demo. |
| `gpt-5.6-luna` | Lower-cost demonstrations. |
| `gpt-5.6-terra` | Balance capability and cost. |
| `gpt-5.6-sol` | More demanding research tasks. |
| `gpt-6-astra` | Complex reasoning tasks. |

Keep `reasoning={"effort": "low"}` for these options. Access depends on your API account and provider. Check the [official model catalog](https://developers.openai.com/api/docs/models) for current support. Model information checked on September 21, 2026.

## How the hosted ReAct-style loop works

The hosted runtime handles tool execution and feedback within one API request. No custom tool functions or local `while` loop are needed.

```text
Instructions + task + enabled tool
                 |
                 v
       +----> Model decides
       |         |
       |         +--- Enough evidence ---> Final answer
       |         |
       |    Need more evidence
       |         |
       |         v
       |     Web search
       |         |
       +--- Observations
```

- `web_search`: retrieves information through a hosted tool.
- `tool_choice="auto"`: lets the model decide whether to search.
- `max_tool_calls=4`: allows up to four built-in tool calls, not four guaranteed rounds.

The script receives the response, prints the answer, and saves the visible trace. See the [web search guide](https://developers.openai.com/api/docs/guides/tools-web-search).

## What the TXT trace contains

The `agent_trace_<timestamp>.txt` file records:

- **Request:** instructions, task, enabled tools, and settings.
- **Response:** metadata, usage, API-visible output items, search actions, included sources, and final answer.
- **Errors:** exception details when a request fails.

Output items are not complete internal ReAct rounds. The log does not expose hidden reasoning, every internal context, or full search observations. The configured API key is redacted.

`agent_trace_sample.txt` is an offline mock, not a live search result.

## API requirements and troubleshooting

The script uses the **Responses API** at `https://api.openai.com/v1/responses`. Keep `BASE_URL` as `https://api.openai.com/v1`. A third-party provider must support Responses and built-in `web_search`; Chat Completions support alone is insufficient.

- **`No module named 'openai'`:** install the SDK with the interpreter used to run the script.
- **No `responses` attribute / `aiohttp.SocketTimeoutError`:** upgrade the SDK and dependencies with the installation command above.
- **`Request failed`:** open the TXT trace path printed in the terminal for the specific error.
- **Model or parameter rejected:** check account access, the model ID, and supported tools and parameters.
