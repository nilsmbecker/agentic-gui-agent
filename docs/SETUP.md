# Setup guide (Apple Silicon Mac)

Total: ~30–45 min and ~15 GB disk. Do it once per machine.

## 0. Prerequisites
- Homebrew, conda (Anaconda/Miniforge), git
- **Ollama app** from https://ollama.com/download (keep it running)
- GitHub access to the repo (ask Nils for an invite). `gh auth login` makes cloning easy

## 1. Clone
```bash
git clone --recurse-submodules https://github.com/<owner>/agentic-gui-agent.git
cd agentic-gui-agent
```
Already cloned without submodules? Run `git submodule update --init`.
The 1.2 GB reference book is skipped. Get it only if you want it:
`git submodule update --init --checkout third_party/ai-agent-book`

## 2. Android SDK, emulator, conda env
```bash
bash scripts/setup_mac.sh
conda activate gui-agent
```
This installs ffmpeg, JDK 17, the Android command-line tools, the **API 33 arm64** system image,
an AVD called `AndroidWorldAvd` (Pixel 6), and the Python 3.11 env with `android_world` and our
package in editable mode.

Already have Android Studio? Fine. The script reuses `~/Library/Android/sdk`.

## 3. Model
```bash
bash scripts/setup_model.sh             # downloads ~8 GB, registers q8_0 (~4.4 GB) in Ollama
```
Low on RAM or too slow? `QUANT=Q4_K_M bash scripts/setup_model.sh` (2.2 GB, less accurate).
Tell the team if you switch: results are only comparable with the same quant.

## 4. Emulator + one-time app install
```bash
bash scripts/start_emulator.sh          # terminal 1, keep open
python scripts/run_task.py --perform-emulator-setup   # terminal 2, ONCE per new emulator
python scripts/check_setup.py           # everything should be ✔
```

## 5. First run
```bash
python scripts/run_task.py --task SystemWifiTurnOff --runs 1
```
Look at `runs/SystemWifiTurnOff/<run_id>/steps.jsonl` and the `step_*.png` screenshots.

---

## Troubleshooting (add what you run into!)

| Symptom | Fix |
|---|---|
| `adb not found` | `ADB_PATH` in `.env`, or re-run `setup_mac.sh` |
| `emulator-5554` not in `adb devices` | Emulator not started or still booting. Wait for the home screen |
| AndroidWorld hangs on connect | Emulator must be started with `-grpc 8554` (the script does this) |
| Model call times out | First call loads the model (~30 s). Raise `LLM_TIMEOUT_S`; check `ollama ps` |
| Mac runs out of memory | Close browser/IDE, start emulator with `-no-window`, use `Q4_K_M` |
| Setup crashes: `monkey ... exit status 251`, "SYS_KEYS has no physical keys" | Set `hw.keyboard=yes` in `~/.android/avd/AndroidWorldAvd.avd/config.ini`, restart the emulator, re-run setup (`setup_mac.sh` now does this) |
| `avdmanager`: "Valid system image paths are: null" | Use `~/Library/Android/sdk/cmdline-tools/latest/bin/avdmanager`, not Homebrew's (`setup_mac.sh` now does this) |
| Recording stops after 3 min | Emulator limit. Use macOS screen recording (⌘⇧5) on the emulator window |
