"""Settings loaded from environment variables, with an optional `.env` file.

No python-dotenv dependency: `.env` is parsed by hand (KEY=VALUE lines).
Real environment variables always win over `.env`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


@dataclass(frozen=True)
class Settings:
    llm_base_url: str
    llm_model: str
    llm_api_key: str
    llm_temperature: float
    llm_timeout_s: float
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
            llm_api_key=env("LLM_API_KEY", "ollama"),
            llm_temperature=float(env("LLM_TEMPERATURE", "0.1")),
            llm_timeout_s=float(env("LLM_TIMEOUT_S", "180")),
            adb_path=os.path.expanduser(env("ADB_PATH", "~/Library/Android/sdk/platform-tools/adb")),
            emulator_console_port=int(env("EMULATOR_CONSOLE_PORT", "5554")),
            transition_pause_s=float(env("TRANSITION_PAUSE_S", "1.5")),
            runs_dir=REPO_ROOT / env("RUNS_DIR", "runs"),
        )
