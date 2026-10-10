# Setup and replication

This guide takes a fresh Windows or macOS machine to the point where you can rerun our nine evaluation runs. The setup scripts do most of the work. Plan for about an hour, most of it downloads.

## 1. What you need

- Windows 10 or 11 on x86_64, or a Mac with Apple Silicon. We ran the Wi-Fi task on a Windows laptop and both Markor tasks on an Apple Silicon Mac.
- 16 GB of RAM and about 25 GB of free disk space (Android SDK and emulator image about 8 GB, model download about 9 GB, the Ollama copy of the model about 4.5 GB).
- Hardware virtualization. On Windows, turn on "Windows Hypervisor Platform" under *Turn Windows features on or off* and reboot.
- [git](https://git-scm.com/), conda (we use [Miniforge](https://github.com/conda-forge/miniforge)) and the [Ollama](https://ollama.com/download) app, running.
- On Windows, `winget` (built into Windows 11). On macOS, [Homebrew](https://brew.sh).

## 2. Get the code

From GitHub (the submodules come along):

```bash
git clone --recurse-submodules https://github.com/nilsmbecker/agentic-gui-agent
cd agentic-gui-agent
```

From the submitted ZIP: unzip it and open a terminal in the `agentic-gui-agent` folder. The ZIP leaves out the two upstream projects in `third_party/`. The setup script in step 3 notices the missing `.git` folder and downloads them at the commits we used. To do it by hand:

```bash
git init third_party/android_world
git -C third_party/android_world fetch --depth 1 https://github.com/google-research/android_world 2dfc5ca3dc590efe9c72ce768f2b04182f2f75c7
git -C third_party/android_world checkout FETCH_HEAD

git init third_party/gelab-zero
git -C third_party/gelab-zero fetch --depth 1 https://github.com/stepfun-ai/gelab-zero 7b619f6f67d2b1101021fc453cb27bd48a29e4f2
git -C third_party/gelab-zero checkout FETCH_HEAD
```

## 3. Run the setup script

Windows (PowerShell):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1
```

macOS:

```bash
bash scripts/setup_mac.sh
```

The script is safe to run again and skips what is already there. It installs JDK 17 and ffmpeg, the Android SDK with the Android 13 (API 33) system image, and creates an emulator called `AndroidWorldAvd` (Pixel 6) with the hardware keyboard switched on. AndroidWorld needs that keyboard to launch apps. Then it fetches the third-party code, creates the conda environment `gui-agent` (Python 3.11, AndroidWorld and this package) and copies `.env.example` to `.env`.

On Windows, open a new terminal afterwards so the PATH changes apply.

## 4. Download the model

```powershell
conda activate gui-agent
powershell -ExecutionPolicy Bypass -File scripts\setup_model.ps1     # Windows
bash scripts/setup_model.sh                                          # macOS
```

This downloads `stepfun-ai/GELab-Zero-4B-preview` from Hugging Face into `models/` and registers it in Ollama as `gelab-zero-4b-preview`, quantized to q8_0. All our runs used q8_0. For another quantization, set `QUANT` before running the script (for example `QUANT=Q4_K_M`) and put the same value into `LLM_QUANT` in `.env`.

## 5. Start the emulator

In a second terminal, which stays open while you run tasks:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start_emulator.ps1  # Windows
bash scripts/start_emulator.sh                                       # macOS
```

The first boot takes a few minutes. Then, once per new emulator, install the apps the tasks use. This also needs a few minutes and an internet connection:

```bash
python scripts/run_task.py --perform-emulator-setup
```

## 6. Check everything

```bash
python scripts/check_setup.py
```

Every line should show a green tick. For anything that is missing, the script prints the command that fixes it.

## 7. Reproduce the evaluation

```bash
python scripts/run_task.py --task SystemWifiTurnOn --runs 3 --seed 0 --record
python scripts/run_task.py --task MarkorCreateNote --runs 3 --seed 0 --record
python scripts/run_task.py --task MarkorCreateNoteAndSms --runs 3 --seed 0 --record
```

Run *i* uses seed 0 + *i*, so you get the same task instances we did. For example, MarkorCreateNote with seed 0 always asks for a note called `qFzW_polite_wolf.txt`. The step limit defaults to ten times AndroidWorld's complexity score: 10, 16 and 18 steps for the three tasks.

Each run writes a folder `runs/<task>/<run_id>/` with `steps.jsonl`, one screenshot per step, `summary.json` and the screen recording, and appends a row to `runs/results.csv`. Our own runs are in the same layout in the ZIP's `runs/` folder, so you can compare them directly.

What to expect:

- On a laptop CPU one model call takes about a minute, so a Wi-Fi run takes 4 to 5 minutes. On Apple Silicon a call takes about 12 seconds.
- The seed fixes the task, not the agent. The model samples at temperature 0.1 and Ollama has no sampling seed set, and screen timing differs between machines. A single run can therefore end differently from ours. In our own Wi-Fi runs, the same tap opened the Internet panel in time in runs 2 and 3, but too late in run 1.
- The MarkorCreateNote runs were made on this code. The Wi-Fi and SMS runs were recorded earlier, before the Markor fixes (focus tap, save hint and screen-change feedback). Rerunning them on this code includes those fixes. To rerun the SMS task on exactly the code we used, check out commit `fce0c3b` in a git clone.

To measure the screenshot-size speed-up yourself (needs only Ollama, no emulator):

```bash
python scripts/bench_image_size.py --image runs/SystemWifiTurnOn/20261008-160508_r3/step_000.png --goal "Turn wifi on." --sizes 0 1024
```

Size 0 sends the full-resolution PNG. To run whole tasks at full resolution, set `LLM_IMAGE_SIZE=0` in `.env`.

## Configuration

Everything is read from `.env` (copied from `.env.example`) or from environment variables, and every value has a default that works for the local setup:

| Variable | Default | Meaning |
|---|---|---|
| `LLM_BASE_URL` | `http://localhost:11434/v1` | Any OpenAI-compatible endpoint; the default is the local Ollama app |
| `LLM_MODEL` | `gelab-zero-4b-preview` | Model name as registered in Ollama |
| `LLM_TEMPERATURE` | `0.1` | Sampling temperature |
| `LLM_IMAGE_SIZE` | `1024` | Screenshot size sent to the model (N × N JPEG); 0 means full-resolution PNG |
| `LLM_QUANT` | `q8_0` | Only written to `summary.json` |
| `ADB_PATH` | the Android SDK's `platform-tools` for your OS | Set it if adb lives somewhere else |
| `EMULATOR_CONSOLE_PORT` | `5554` | Port of the first emulator (`adb devices` shows `emulator-5554`) |
| `TRANSITION_PAUSE_S` | `1.5` | Wait after each action before the next screenshot |

## Troubleshooting

- The emulator is very slow or does not start (Windows): Windows Hypervisor Platform is probably off. Turn it on and reboot.
- `check_setup.py` cannot find adb: set `ADB_PATH` in `.env` to the full path of `adb` or `adb.exe`.
- `--perform-emulator-setup` aborts with "SYS_KEYS has no physical keys": the emulator was created without a hardware keyboard. Set `hw.keyboard=yes` in `~/.android/avd/AndroidWorldAvd.avd/config.ini` (the setup scripts do this) and restart the emulator.
- "model not found": `ollama list` must show `gelab-zero-4b-preview`, and `LLM_MODEL` in `.env` must match it.
- A run fails right at the start with `SSL UNEXPECTED_EOF`: AndroidWorld downloads a small helper app when it connects, and that download sometimes breaks. Start the run again.
- The emulator crashed once during our Mac runs (exit code 139). Restart it with the start script and rerun the task.
- On Windows with Python 3.11, AndroidWorld's APK install fails because Windows locks a temporary file. `run_task.py` works around this automatically.

The scripts in `docs/analysis/tools/` replay logged runs from the MarkorCreateNote investigation. They need a running emulator and the run folders from Nils' machine, which are not part of the submission.
