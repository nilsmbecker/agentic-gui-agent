# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

The group project for "Agentic AI in Business" (TUM School of Management): a GUI agent that drives **AndroidWorld** with **GELab-Zero-4B** running locally in Ollama. Private GitHub repo `agentic-gui-agent`, 4 contributors, all on Apple Silicon Macs. Deadline Fri 9 Oct 2026, plan in `docs/PLAN.md`, decisions in `docs/DECISIONS.md`, team workflow in `CONTRIBUTING.md`.

Layout:
- `src/gui_agent/`: project code (see Project architecture below).
- `scripts/`: `setup_mac.sh`, `setup_model.sh`, `start_emulator.sh`, `run_task.py`, `check_setup.py`.
- `tests/`: unit tests that need no emulator or model.
- `configs/tasks.yaml`: the evaluated tasks by tier.
- `results/`: curated runs for submission. `runs/` (raw runs) is gitignored.
- `course/`: lecture slides (`course/slides/`) and D1–D3 labs (`course/labs/`). **Reference only. Never edit, never import from `src/`.**
- `third_party/`: pinned submodules `android_world`, `gelab-zero`, `ai-agent-book` (opt-in, `update = none`). **Never edit.**

## Commands

### Project (conda env `gui-agent`, Python 3.11)
```bash
conda activate gui-agent
ruff check src scripts tests && ruff format --check src scripts tests && pytest -q   # same as CI
pytest tests/test_actions.py::test_click                                            # single test
python scripts/check_setup.py                       # env, adb, emulator, Ollama, model
bash scripts/start_emulator.sh                      # AVD AndroidWorldAvd with -grpc 8554
python scripts/run_task.py --task SystemWifiTurnOff --runs 3 --record
python scripts/run_task.py --perform-emulator-setup # once per fresh emulator
```
Config comes from `.env` (template `.env.example`), loaded by `gui_agent/config.py` without python-dotenv.

### Course labs (reference; run from inside `course/labs/<day>`)

#### D1 — foundations lab (talks to a local Ollama server, stdlib only, no `pip install`)
```bash
ollama serve                              # or open the Ollama app; needs qwen3-vl-4b:latest or qwen3-vl:4b pulled
cd course/labs/D1
python3 -m py_compile *.py && echo "scripts ok"
python3 check_setup.py                    # verify model + context window before running anything else
python3 step1_chat.py                     # terminal chat; /raw /hist /new /quit
python3 step2_temperature.py              # temperature sweep, fixed vs. no seed
python3 step3_context_growth.py           # 5-turn conversation, prompt_eval_count growth
python3 step4_chat_template.py            # chat-template markers + raw-mode injection
```
Useful env vars: `VERBOSE=1` (print every request/reply as JSON), `OLLAMA_MODEL=<tag>` (override model selection), `OLLAMA_HOST=http://host:11434`.

#### D2 — context engineering lab (same Ollama setup, stdlib only)
```bash
cd course/labs/D2
python3 check_setup.py
python3 step1_tool_context.py             # native tool-calling loop; flags: --model, --dry-run, --max-rounds
python3 step2_prefix_cache.py             # stable-prefix vs. changing-prefix prompt_eval_ms comparison
python3 step3_skill_status.py             # Skill loading + agent status bar
python3 step4_memory.py                   # persistent memory extraction/reload across sessions
```
Outputs land in `course/labs/D2/artifacts/` (gitignored) (JSON/CSV) and are overwritten on each run — not hand-maintained files; copy them elsewhere if you need to keep a particular run's output.

#### D3-code-example — hosted agent via OpenAI Responses API (needs the OpenAI SDK, unlike D1/D2)
```bash
python3 -m pip install --upgrade "openai[aiohttp]"
# edit API_KEY, MODEL, TASK at the top of minimal_agent_example.py, then:
cd course/labs/D3-code-example
python3 minimal_agent_example.py
```
Each run writes a new `agent_trace_<timestamp>.txt` next to the script; these accumulate and are safe to delete.

## Course lab architecture

**D1 and D2 share one pattern**: a hand-rolled `common.py` HTTP client (no SDK, plain `urllib`) that POSTs to a local Ollama server at `http://localhost:11434/api/chat` / `/api/show`, plus several `step*.py` scripts that are read/inspect/modify exercises — each prints a "what you should have noticed" lesson at the end rather than asserting anything. Model resolution order (`common.py: resolve_model()`): `$OLLAMA_MODEL` env var → local `qwen3-vl-4b:latest` tag → official `qwen3-vl:4b` tag → hard error if neither is installed.

**D2 adds**:
- `lab_support.py` — a `RequestLog`-style helper that builds requests, times them, and writes the `artifacts/*.json` / `*.csv` records the step scripts rely on for before/after comparisons.
- `skills/<name>/SKILL.md` — Agent Skills: YAML frontmatter + a trigger description, loaded into the system message on demand by an explicit `should_load_skill()`-style keyword check in the step script, not auto-discovered or always-loaded.

**D3-Code Example is architecturally different from D1/D2**: it calls OpenAI's **Responses API** (not Ollama) via the official `openai` SDK, using a hosted `web_search` tool. There is no local tool-execution loop here — the model↔tool loop runs entirely server-side inside one `client.responses.create(...)` call; the script only logs the request and the visible output items/trace.

The PDFs in `course/slides/` (`D1-Intro.pdf`, `D2-Context engineering.pdf`, `D3-Tools.pdf`, `D4-Coding.pdf`, `D5-RL-slides.pdf`) are the lecture decks; each lab's README under `course/labs/` documents that day's lab in more detail than this file does and should be treated as the source of truth for lab mechanics.

## Course arc (background for anything built on top of this repo)

The week moves "inside out": model → context → tools → coding reliability → training.
- **D1**: a model is a stateless next-token sampler; temperature/top-p control *how* it samples, not whether it's correct; agent = model (rarely changed) + context (fills the memory gap) + tools (fills the action gap).
- **D2**: the context window is the model's whole world; KV-cache reuse requires a stable prefix (dynamic data goes at the end, never reorder tools, never hand-format roles); Skills supply know-how, tools supply capability; memory is episodic/semantic/procedural and must be compressed to stay cheap.
- **D3**: ReAct loop (reason → act → observe); tool design is an Agent–Computer Interface (clear inputs + useful observations/errors); tool granularity trades off call count against mixed effects.
- **D4**: an agentic loop is reliable only if it has goal clarity, observable state, actionability, structured feedback, independent verification, and bounded recovery (retry/revise/rollback/escalate) — this is the design checklist for any agent built here.
- **D5**: SFT memorizes, RL generalizes the procedure; training is the last resort after knowledge (retrieval) and instructions (prompts/Skills) fail — not expected to be used in the group project.

## Group project requirements

Drive **AndroidWorld** (116-task Android benchmark) with **GELab-Zero** (vision-language GUI model), groups of 3–5.

- Required shape: one agent class with a single `step()` method: read the screen, choose an action, report whether it is done.
- Task selection: at least 3 AndroidWorld tasks covering all three tiers (warm-up / real-work / multi-app-and-memory), 3 runs per task, a screen recording of each run.
- Grading: group project 40% (demo, trajectory logs, written analysis of at least one failure), presentation 20% (10–30 min + 5–10 min Q&A).
- Failure taxonomy: `grounding`, `too_early`, `lost_value`, `wrong_app`, `false_done` (D1), plus our own `parse_error`, `loop`, `env`, read against D4's reliability levers.

## Project architecture

`GelabAgent(EnvironmentInteractingAgent)` in `src/gui_agent/agent.py`: each `step(goal)` takes a screenshot, builds GELab's prompt, calls the model, parses the reply, maps it to AndroidWorld actions, executes them, and returns `AgentInteractionResult(done, data)`.

- `gelab.py` puts `third_party/gelab-zero` on `sys.path` and reuses upstream `Parser0920Summary` (prompt + parser) unchanged, so the prompt matches the model's training. Its `env2messages4ask` requires `len(environments) == len(actions) + 1`. The agent pops the environment again on a parse failure to keep that invariant.
- `actions.py` is the only place that maps GELab actions (0–1000 normalized coords) to AndroidWorld `JSONAction` kwargs (pixels). It is pure (no android_world import) so it's unit-testable. `SLIDE` becomes an exact adb swipe; `COMPLETE` becomes `answer` (fills `interaction_cache` for information-retrieval tasks) + `status complete`; `INFO` is not executed (no user in the loop).
- `llm_client.py` is a stdlib-only client for any OpenAI-compatible `/v1/chat/completions` (default: local Ollama). Sampling mirrors gelab-zero's `local_server.py` (temp 0.1, top_p 1, max_tokens 512).
- `trajectory.py` writes `runs/<task>/<run_id>/steps.jsonl` + `step_NNN.png` + `summary.json`. `scripts/run_task.py` also appends `runs/results.csv` and records the git commit (`-dirty` if `src/` has local changes).
- Bounded recovery: 3 consecutive unparseable replies end the episode (`MAX_CONSECUTIVE_PARSE_FAILURES`).

Conventions: keep a minimal, auditable client over the model API, not an agent framework. Every new behaviour should leave evidence in the step `record`, since the logs are graded deliverables.
