# GELab-Zero on AndroidWorld

Group project for the course Agentic AI in Modern Business at the TUM School of Management.

We took [GELab-Zero-4B-preview](https://github.com/stepfun-ai/gelab-zero), a small vision-language model from StepFun that was trained to operate phone apps, and turned it into an agent for [AndroidWorld](https://github.com/google-research/android_world), Google's benchmark of tasks on an Android emulator. Everything runs on our own laptops: the model is served by Ollama on the CPU, and the emulator is a Pixel 6 image with Android 13.

The model only sees screenshots and answers with actions like `CLICK 512,830` or `TYPE "hello"`. Most of the work in this repo is the code around it: building the prompt the way GELab expects, translating its actions into AndroidWorld actions, catching loops, and telling the model when an action had no effect.

## Results

We evaluated one task from each of the three difficulty tiers, three runs each, with seeds 0, 1 and 2. A run counts as a success when the agent says COMPLETE and AndroidWorld's checker returns 1.0.

| Task | Tier | Success | Steps | Time per run | Where it ran |
|---|---|---|---|---|---|
| SystemWifiTurnOn | warm-up | 2 / 3 | 4 to 5 | 4 to 5 min | Windows laptop |
| MarkorCreateNote | real work | 3 / 3 | 7 to 8 | about 2 min | Nils' Mac |
| MarkorCreateNoteAndSms | multi-app and memory | 3 / 3 | 13 to 16 | 3 to 4 min | Nils' Mac |

That is 8 of 9 runs. A few things worth knowing about these numbers:

- The failed Wi-Fi run (run 1) was stopped by our loop guard: the model sent the same tap on the "Internet" tile three times in a row. The tap itself was right, but the panel opened only after our 1.5 s wait, so the next screenshot showed no change, and the repeated tap closed the panel again.
- MarkorCreateNote failed all three runs on our first version of the code. The typed text never reached the editor, and later the model kept tapping an already greyed-out save icon. Four rounds of fixes brought it to 3 / 3. The graded runs use the fixed code (commit `06af22e`); the other two tasks were recorded before these fixes. The whole investigation is in [docs/analysis/MarkorCreateNote_investigation.md](docs/analysis/MarkorCreateNote_investigation.md).
- Sending a smaller screenshot made the agent about 2.2 times faster. The emulator's screenshot is 1080 × 2400. Sent as a full PNG it costs 3,193 prompt tokens; squashed to 1024 × 1024 JPEG (as GELab's own deployment does) it costs 1,667. On the Windows laptop the model call went from 131 s to 59 s per step, and a Wi-Fi run from about 16 minutes to 4 or 5. The full-resolution baseline run is kept in `runs/SystemWifiTurnOn/20261008-134620_r1`. `scripts/bench_image_size.py` repeats the measurement.

## How one step works

`GelabAgent.step()` in [src/gui_agent/agent.py](src/gui_agent/agent.py) does four things:

1. Observe: take the screenshot and the accessibility tree from AndroidWorld.
2. Decide: build the prompt with GELab's own prompt builder (`Parser0920Summary` from the upstream repo, so the prompt matches training) and send it to the model through an OpenAI-compatible API ([llm_client.py](src/gui_agent/llm_client.py)). Only the newest screenshot is attached.
3. Act: parse the reply and map GELab's 0 to 1000 coordinates to screen pixels ([actions.py](src/gui_agent/actions.py)). Most actions become AndroidWorld `JSONAction`s. A swipe is sent as an exact adb swipe, because `JSONAction` only knows scroll directions.
4. Report: return whether the episode is over (COMPLETE, ABORT, or a stop by one of the guards below) and log the step.

The agent also has these guards and fixes:

- A loop guard ends the episode when the model sends the identical action three times in a row.
- After three failed steps in a row (unparseable reply or model error) the agent gives up.
- When GELab sends TYPE without a position, the agent first taps the focused or largest text field. Without this, `adb input text` can type into nothing.
- A short hint in every prompt reminds the model to save before it says COMPLETE ([gelab.py](src/gui_agent/gelab.py)).
- When an action barely changed the screen, the next prompt says so, names the action, and says if the tapped element is disabled ([feedback.py](src/gui_agent/feedback.py)). The message goes through GELab's `user_comment` field, the channel the model was trained to treat as a user speaking mid-task. Appending the same text to the task description had no effect.

Every step is written to `runs/<task>/<run_id>/steps.jsonl` with the raw model output, the parsed action, what was executed, the model's latency and any feedback, next to the screenshot the model saw. `summary.json` holds the result of the run.

## Getting started

The full replication guide, including the Windows and macOS setup, is in [SETUP.md](SETUP.md). In short, on Windows:

```powershell
git clone --recurse-submodules https://github.com/nilsmbecker/agentic-gui-agent
cd agentic-gui-agent
powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1
conda activate gui-agent
powershell -ExecutionPolicy Bypass -File scripts\setup_model.ps1
powershell -ExecutionPolicy Bypass -File scripts\start_emulator.ps1      # in a second terminal
python scripts\run_task.py --perform-emulator-setup                      # once per emulator
python scripts\check_setup.py
python scripts\run_task.py --task SystemWifiTurnOn --runs 3 --seed 0 --record
```

The unit tests need neither the emulator nor the model:

```bash
python -m pytest
```

## What is where

| Path | Contents |
|---|---|
| `src/gui_agent/` | The agent: `agent.py` (`GelabAgent.step()`), action mapping, feedback, prompt bridge to GELab, model client, logging |
| `scripts/` | Setup scripts for Windows and macOS, emulator start, `run_task.py` (runs a task N times and logs everything), `check_setup.py`, `bench_image_size.py` |
| `tests/` | Unit tests for the action mapping, the feedback and the prompt |
| `configs/tasks.yaml` | The three evaluated tasks and the backups we had picked for each tier |
| `docs/analysis/` | The MarkorCreateNote failure analysis, its figures and the two scripts used for it |
| `runs/` | Logs, screenshots and recordings of the submitted runs (in the ZIP; not tracked in git) |
| `third_party/` | `android_world` and `gelab-zero` as pinned git submodules, fetched during setup |
| `models/` | The model weights, downloaded by `setup_model` (not in git) |

Each run folder in `runs/` contains `steps.jsonl`, the screenshots `step_000.png` and up, `summary.json` and `recording.mp4`. The emulator records WebM files of at most 170 s each. For the submission we joined each run's parts into one MP4 and scaled it to 540 × 1200, which is why `summary.json` still lists `recording_part1.webm` and so on. `runs/results.csv` has one row per run. `runs/MarkorCreateNote_fix_history/` holds Nils' log of every MarkorCreateNote run across the four fix rounds.

## Team

Eric Schoof, Nils Becker, Raouf Tadros, Tobias Lösch

## Credits

- [AndroidWorld](https://github.com/google-research/android_world) by Google Research: the emulator environment, the tasks and their checkers.
- [GELab-Zero](https://github.com/stepfun-ai/gelab-zero) by StepFun: the model, its prompt format and the output parser we reuse.
