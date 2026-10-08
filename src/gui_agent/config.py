"""Settings loaded from environment variables, with an optional `.env` file.

No python-dotenv dependency: `.env` is parsed by hand (KEY=VALUE lines).
Real environment variables always win over `.env`.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def default_android_sdk(platform: str | None = None) -> str:
    """Where the Android SDK lives by default (what Android Studio / our setup scripts use)."""
    platform = platform or sys.platform
    if platform.startswith("win"):
        local = os.environ.get("LOCALAPPDATA", os.path.expanduser(r"~\AppData\Local"))
        return os.path.join(local, "Android", "Sdk")
    if platform == "darwin":
        return os.path.expanduser("~/Library/Android/sdk")
    return os.path.expanduser("~/Android/Sdk")


def default_adb_path(platform: str | None = None) -> str:
    platform = platform or sys.platform
    exe = "adb.exe" if platform.startswith("win") else "adb"
    sdk = os.environ.get("ANDROID_HOME") or default_android_sdk(platform)
    return os.path.join(sdk, "platform-tools", exe)


def _load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


@dataclass(frozen=True)
class Settings:
    llm_base_url: str
    llm_model: str
    llm_quant: str
    llm_api_key: str
    llm_temperature: float
    llm_timeout_s: float
    llm_image_size: int
    adb_path: str
    emulator_console_port: int
    transition_pause_s: float
    runs_dir: Path

    @classmethod
    def from_env(cls) -> Settings:
        _load_dotenv(REPO_ROOT / ".env")
        env = os.environ.get
        return cls(
            llm_base_url=env("LLM_BASE_URL", "http://localhost:11434/v1").rstrip("/"),
            llm_model=env("LLM_MODEL", "gelab-zero-4b-preview"),
            # Only logged (summary.json): Ollama doesn't report the quant it was created with.
            llm_quant=env("LLM_QUANT", "q8_0"),
            llm_api_key=env("LLM_API_KEY", "ollama"),
            llm_temperature=float(env("LLM_TEMPERATURE", "0.1")),
            llm_timeout_s=float(env("LLM_TIMEOUT_S", "180")),
            # Screenshot sent to the model, squashed to N x N as gelab-zero's deployment does
            # (mcp_server_config.yaml uses 728). Ollama never uses fewer than ~1024 image tokens
            # (it upscales smaller images), so 1024 costs the same as 728 but keeps more detail.
            # 0 = full-resolution PNG: ~2x the prompt tokens and step time (scripts/bench_image_size.py).
            llm_image_size=int(env("LLM_IMAGE_SIZE", "1024")),
            adb_path=os.path.expanduser(env("ADB_PATH") or default_adb_path()),
            emulator_console_port=int(env("EMULATOR_CONSOLE_PORT", "5554")),
            transition_pause_s=float(env("TRANSITION_PAUSE_S", "1.5")),
            runs_dir=REPO_ROOT / env("RUNS_DIR", "runs"),
        )
