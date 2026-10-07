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

## Quick start

Works on **macOS (Apple Silicon)** and **Windows 10/11 (x86_64)**. Same 7 steps, different scripts.

**Prerequisites (both):** git, conda (Miniforge or Anaconda), the [Ollama app](https://ollama.com/download)
running, ~15 GB free disk, 16 GB+ RAM.
- macOS: also [Homebrew](https://brew.sh).
- Windows: also `winget` (built into Windows 11), and **Windows Hypervisor Platform** enabled
  (*Turn Windows features on or off*, then reboot) so the emulator is hardware-accelerated.

### macOS (bash / zsh)
```bash
git clone --recurse-submodules <repo-url> && cd agentic-gui-agent
bash scripts/setup_mac.sh            # 1. Android SDK, arm64 emulator, AVD, conda env (~30 min, once)
conda activate gui-agent
bash scripts/setup_model.sh          # 2. GELab-Zero → Ollama (once)
bash scripts/start_emulator.sh       # 3. separate terminal, keep open
python scripts/run_task.py --perform-emulator-setup   # 4. installs task apps (once per emulator)
python scripts/check_setup.py        # 5. everything should be ✔
python scripts/run_task.py --task SystemWifiTurnOn --runs 1   # 6. first run
python scripts/run_task.py --task SystemWifiTurnOn --runs 3 --record   # 7. evaluation run
```

### Windows (PowerShell)
```powershell
git clone --recurse-submodules <repo-url>; cd agentic-gui-agent
powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1   # 1. SDK, x86_64 emulator, AVD, conda env (once)
# open a NEW terminal (PATH changed), then:
conda activate gui-agent
powershell -ExecutionPolicy Bypass -File scripts\setup_model.ps1     # 2. GELab-Zero → Ollama (once)
powershell -ExecutionPolicy Bypass -File scripts\start_emulator.ps1  # 3. separate terminal, keep open
python scripts\run_task.py --perform-emulator-setup   # 4. installs task apps (once per emulator)
python scripts\check_setup.py        # 5. everything should be ✔
python scripts\run_task.py --task SystemWifiTurnOn --runs 1   # 6. first run
python scripts\run_task.py --task SystemWifiTurnOn --runs 3 --record   # 7. evaluation run
```

Downloaded the repo as a ZIP? The `third_party/` folders will be empty and the commit can't be
recorded. Clone with `--recurse-submodules` instead.

### Comparing results across machines
Results are only comparable with the **same commit, seed and quant** (`LLM_QUANT` in `.env`).
Macs run the arm64 emulator image and Windows runs x86_64, so `summary.json` records `platform` too.
Mention it in the analysis if a failure only shows up on one platform.

Details and troubleshooting: [docs/SETUP.md](docs/SETUP.md). How we work together: [CONTRIBUTING.md](CONTRIBUTING.md).

## Deliverables (course requirements, D1 slides)

| Requirement | Where |
|---|---|
| One agent class with a single `step()` | `src/gui_agent/agent.py` |
| ≥ 3 tasks, one from each slide box, 3 runs each | `configs/tasks.yaml` → `results/<task>/<run_id>/` |
| Screen recording of every run | `recording*.webm` per run (team drive, linked in the analysis) |
| Model name | `summary.json` (`model`, `quant`) |
| Trajectory logs | `results/<task>/<run_id>/steps.jsonl` + screenshots |
| Analysis of ≥ 1 failure | `docs/analysis/` |
| Demo + presentation (10–30 min) | slides + backup demo video |
