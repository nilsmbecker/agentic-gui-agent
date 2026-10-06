# agentic-gui-agent

Group project for **Agentic AI in Business** (TUM School of Management): a GUI agent that
drives an Android emulator through [AndroidWorld](https://github.com/google-research/android_world)
tasks using the vision-language model [GELab-Zero-4B](https://github.com/stepfun-ai/gelab-zero),
running **locally** in Ollama.

> **Deadline: Friday 9 Oct 2026.** Plan, milestones and goals: [docs/PLAN.md](docs/PLAN.md)

## Repository map

| Path | What it is | Who edits it |
|---|---|---|
| `src/gui_agent/` | **Our project code**: the agent (`agent.py` → `GelabAgent.step()`), action mapping, model client, logging | team |
| `scripts/` | Setup, emulator start, `run_task.py` (runs a task N times + logs), `check_setup.py` | team |
| `tests/` | Unit tests (no emulator/model needed) | team |
| `configs/tasks.yaml` | The AndroidWorld tasks we evaluate, by difficulty tier | team |
| `docs/` | Plan, setup guide, decisions, failure-analysis write-ups | team |
| `results/` | **Curated** runs we submit (logs + summaries). Raw runs go to `runs/` (gitignored) | team |
| `course/` | 📚 **Lecture slides and D1–D3 labs from the course. Reference only, not project code.** | nobody (read-only) |
| `third_party/` | Pinned git submodules: `android_world`, `gelab-zero`, `ai-agent-book` (opt-in) | nobody (never edit) |
| `models/` | Downloaded model weights (gitignored) | scripts |

## How it works

```
AndroidWorld task ──goal──▶ GelabAgent.step()
                              1. observe   screenshot from emulator
                              2. decide    GELab-Zero (local Ollama) → "CLICK 512,830"
                              3. act       map 0-1000 coords → pixels → adb on emulator
                              4. report    done? (COMPLETE / ABORT / too many parse errors)
                            ◀─ AgentInteractionResult(done, data) ─ logged to runs/<task>/<run>/
```

## Quick start (Apple Silicon Mac)

```bash
git clone --recurse-submodules <repo-url> && cd agentic-gui-agent
bash scripts/setup_mac.sh            # Android SDK, emulator, AVD, conda env (~30 min, once)
conda activate gui-agent
bash scripts/setup_model.sh          # GELab-Zero → Ollama (once)
bash scripts/start_emulator.sh       # separate terminal, keep open
python scripts/run_task.py --perform-emulator-setup   # installs task apps (once per emulator)
python scripts/check_setup.py
python scripts/run_task.py --task SystemWifiTurnOff --runs 1
```

Details and troubleshooting: [docs/SETUP.md](docs/SETUP.md). How we work together: [CONTRIBUTING.md](CONTRIBUTING.md).
