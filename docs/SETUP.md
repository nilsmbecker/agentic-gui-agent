# Setup guide (macOS Apple Silicon + Windows 10/11)

Total: ~30–45 min and ~15 GB disk. Do it once per machine. Commands are given as
**macOS** (bash/zsh) and **Windows** (PowerShell). Steps without an OS label are the same on both.

## 0. Prerequisites
- git, conda (Anaconda/Miniforge)
- **Ollama app** from https://ollama.com/download (keep it running)
- GitHub access to the repo (ask Nils for an invite). `gh auth login` makes cloning easy
- macOS: Homebrew
- Windows: `winget` (built into Windows 11; on Windows 10 install "App Installer" from the Store), and
  **Windows Hypervisor Platform** enabled: *Turn Windows features on or off*, then reboot. Without it the
  emulator is very slow or refuses to start.

## 1. Clone
```bash
git clone --recurse-submodules https://github.com/<owner>/agentic-gui-agent.git
cd agentic-gui-agent
```
Already cloned without submodules? Run `git submodule update --init`.
A ZIP download does **not** work: `third_party/` stays empty and no commit is recorded.
The 1.2 GB reference book is skipped. Get it only if you want it:
`git submodule update --init --checkout third_party/ai-agent-book`

## 2. Android SDK, emulator, conda env

**macOS**
```bash
bash scripts/setup_mac.sh
conda activate gui-agent
```
Installs ffmpeg, JDK 17, the Android command-line tools, the **API 33 arm64** system image, an AVD
called `AndroidWorldAvd` (Pixel 6), and the Python 3.11 env with `android_world` and our package in
editable mode. Already have Android Studio? Fine, the script reuses `~/Library/Android/sdk`.

**Windows**
```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1
# open a NEW terminal so the PATH changes apply
conda activate gui-agent
```
Installs JDK 17 and ffmpeg (winget), the Android command-line tools, the **API 33 x86_64** system image,
the same `AndroidWorldAvd` AVD, and the same conda env. The SDK goes to `%LOCALAPPDATA%\Android\Sdk`,
the same place Android Studio uses, so an existing install is reused. A different SDK location? Set
`ANDROID_HOME` before running the script.

`ADB_PATH` doesn't need to be set on either OS: `config.py` picks the default SDK path for the platform.
Set it in `.env` only if your SDK lives elsewhere.

## 3. Model
**macOS**
```bash
bash scripts/setup_model.sh             # downloads ~8 GB, registers q8_0 (~4.4 GB) in Ollama
```
**Windows**
```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup_model.ps1
```
Low on RAM or too slow? Use `QUANT=Q4_K_M bash scripts/setup_model.sh` on macOS, or
`$env:QUANT="Q4_K_M"` and then the `.ps1` on Windows (2.2 GB, less accurate). **Set `LLM_QUANT` in `.env` to match.** It's
written to every `summary.json`, and results are only comparable with the same quant. Tell the team if you switch.

## 4. Emulator + one-time app install
**macOS:** `bash scripts/start_emulator.sh` · **Windows:** `powershell -ExecutionPolicy Bypass -File scripts\start_emulator.ps1`
(terminal 1, keep it open). Then in terminal 2:
```bash
python scripts/run_task.py --perform-emulator-setup   # ONCE per new emulator
python scripts/check_setup.py                         # everything should be ✔
```

## 5. First run
```bash
python scripts/run_task.py --task SystemWifiTurnOn --runs 1
```
Look at `runs/SystemWifiTurnOn/<run_id>/steps.jsonl` and the `step_*.png` screenshots.

## 6. Screen recordings
`--record` records the emulator itself and works on both OSes. The emulator caps a single recording
at 180 s, so `run_task.py` restarts it every ~170 s and saves `recording_part1.webm`,
`recording_part2.webm`, … in the run folder. Backup if that fails: record the emulator window with
**macOS ⌘⇧5** or **Windows Win+Alt+R** (Xbox Game Bar) / OBS.

---

## Troubleshooting (add what you run into!)

| OS | Symptom | Fix |
|---|---|---|
| both | `adb not found` | Set `ADB_PATH` in `.env`, or re-run the setup script |
| both | `emulator-5554` not in `adb devices` | Emulator not started or still booting. Wait for the home screen |
| both | AndroidWorld hangs on connect | Emulator must be started with `-grpc 8554` (the start scripts do this) |
| both | Model call times out | First call loads the model (~30 s). Raise `LLM_TIMEOUT_S`; check `ollama ps`. Repeated timeouts end the run with `llm_error` in `steps.jsonl` (tag: `env`) |
| both | Machine runs out of memory | Close browser/IDE, start the emulator with `-no-window`, use `Q4_K_M` |
| both | Setup crashes: `monkey ... exit status 251`, "SYS_KEYS has no physical keys" | Set `hw.keyboard=yes` in `~/.android/avd/AndroidWorldAvd.avd/config.ini` (Windows: `%USERPROFILE%\.android\avd\...`), restart the emulator, re-run setup. Both setup scripts do this |
| macOS | `avdmanager`: "Valid system image paths are: null" | Use `~/Library/Android/sdk/cmdline-tools/latest/bin/avdmanager`, not Homebrew's (`setup_mac.sh` does this) |
| Windows | `.ps1 cannot be loaded because running scripts is disabled` | Run it via `powershell -ExecutionPolicy Bypass -File scripts\<name>.ps1` |
| Windows | Emulator: "x86_64 emulation currently requires hardware acceleration" | Enable *Windows Hypervisor Platform* (and Virtualization in BIOS), reboot |
| Windows | `java`/`ffmpeg` not found right after setup | Open a new terminal: winget changes PATH only for new shells |
| Windows | `UnicodeEncodeError` when printing | Run `$env:PYTHONUTF8=1` once per terminal (logs are already written as UTF-8) |
