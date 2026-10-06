"""Check every piece of the dev environment and say exactly what is missing.

python scripts/check_setup.py
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import urllib.request

from gui_agent.config import REPO_ROOT, Settings

OK, FAIL = "\033[32m✔\033[0m", "\033[31m✘\033[0m"
failures = 0


def check(name: str, ok: bool, hint: str = "") -> None:
    global failures
    print(f"{OK if ok else FAIL} {name}" + ("" if ok else f"\n    -> {hint}"))
    failures += not ok


s = Settings.from_env()

check("Python >= 3.11", sys.version_info >= (3, 11), "conda activate gui-agent  (see docs/SETUP.md)")
check(".env present", (REPO_ROOT / ".env").exists(), "cp .env.example .env")
for sub in ("android_world", "gelab-zero"):
    sub_dir = REPO_ROOT / "third_party" / sub
    check(
        f"submodule third_party/{sub}",
        sub_dir.exists() and any(sub_dir.iterdir()),
        "git submodule update --init",
    )
check("ffmpeg on PATH", shutil.which("ffmpeg") is not None, "brew install ffmpeg")

try:
    import android_world  # noqa: F401

    check("android_world importable", True)
except Exception as e:  # noqa: BLE001
    check("android_world importable", False, f"{e} -> pip install -e third_party/android_world")

try:
    from gui_agent import gelab  # noqa: F401

    check("gelab-zero parser importable", True)
except Exception as e:  # noqa: BLE001
    check("gelab-zero parser importable", False, f"{e} -> pip install -e '.[dev]'")

adb_ok = shutil.which(s.adb_path) is not None or os.path.isfile(s.adb_path)
check(f"adb at {s.adb_path}", adb_ok, "bash scripts/setup_mac.sh  (installs Android SDK)")
if adb_ok:
    out = subprocess.run([s.adb_path, "devices"], capture_output=True, text=True).stdout
    check(
        f"emulator-{s.emulator_console_port} running",
        f"emulator-{s.emulator_console_port}" in out,
        "bash scripts/start_emulator.sh",
    )

try:
    base = s.llm_base_url.removesuffix("/v1")
    with urllib.request.urlopen(f"{base}/api/tags", timeout=5) as r:
        models = [m["name"] for m in json.load(r)["models"]]
    check("Ollama reachable", True)
    check(
        f"model '{s.llm_model}' available",
        any(m.split(":")[0] == s.llm_model.split(":")[0] for m in models),
        "bash scripts/setup_model.sh",
    )
except Exception as e:  # noqa: BLE001
    check(f"Ollama reachable at {s.llm_base_url}", False, f"{e} -> open the Ollama app / `ollama serve`")

print("\nAll good." if not failures else f"\n{failures} problem(s) found.")
sys.exit(1 if failures else 0)
