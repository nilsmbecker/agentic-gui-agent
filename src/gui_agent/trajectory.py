"""Per-run trajectory logging: one JSONL line per step + the screenshot it saw.

Layout:  runs/<task>/<run_id>/steps.jsonl, step_000.png, ..., summary.json
These logs are the raw material for the failure analysis (docs/analysis/).
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
from PIL import Image


class TrajectoryLogger:
    def __init__(self, runs_dir: Path, task_name: str, run_id: str | None = None):
        self.run_id = run_id or time.strftime("%Y%m%d-%H%M%S")
        self.dir = runs_dir / task_name / self.run_id
        self.dir.mkdir(parents=True, exist_ok=True)
        self._steps = self.dir / "steps.jsonl"

    def log_step(self, step: int, record: dict, pixels: np.ndarray | None = None) -> None:
        if pixels is not None:
            shot = f"step_{step:03d}.png"
            Image.fromarray(pixels.astype("uint8")).save(self.dir / shot)
            record = {**record, "screenshot": shot}
        with self._steps.open("a") as f:
            f.write(json.dumps({"step": step, "t": time.time(), **record}, ensure_ascii=False) + "\n")

    def write_summary(self, summary: dict) -> None:
        (self.dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))
