"""Run one AndroidWorld task N times with the GELab-Zero agent and log everything.

Examples:
  python scripts/run_task.py --task SystemWifiTurnOn --runs 3 --record
  python scripts/run_task.py --task ContactsAddContact --runs 1 --max-steps 15
  python scripts/run_task.py --perform-emulator-setup   # ONCE per fresh emulator

Outputs (gitignored):  runs/<task>/<run_id>/{steps.jsonl, step_*.png, summary.json, recording_part*.webm}
                       runs/results.csv  (one row per run, appended)
"""

from __future__ import annotations

import argparse
import contextlib
import csv
import os
import random
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

os.environ.setdefault("GRPC_VERBOSITY", "ERROR")

from android_world import registry  # noqa: E402
from android_world.env import env_launcher  # noqa: E402

from gui_agent.agent import GelabAgent  # noqa: E402
from gui_agent.config import Settings  # noqa: E402
from gui_agent.trajectory import TrajectoryLogger  # noqa: E402


class EmulatorRecorder:
    """Records the emulator screen via the emulator console (works on macOS and Windows).

    The emulator caps one recording at 180 s, so a background thread rotates to a new
    part every PART_S seconds: recording_part1.webm, recording_part2.webm, ...
    Parts are written to a temp dir first because the console command splits on spaces
    (our repo path may contain some), then moved into the run folder.
    """

    PART_S = 170

    def __init__(self, adb: str, port: int, out_dir: Path):
        self.base = [adb, "-s", f"emulator-{port}", "emu", "screenrecord"]
        self.out_dir = out_dir
        self.tmp = Path(tempfile.mkdtemp(prefix="gui_agent_rec_"))
        self.parts: list[str] = []
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._rotate, daemon=True)

    def _start_part(self) -> None:
        name = f"recording_part{len(self.parts) + 1}.webm"
        subprocess.run([*self.base, "start", "--time-limit", "180", str(self.tmp / name)], check=False)
        self.parts.append(name)

    def _rotate(self) -> None:
        self._start_part()
        while not self._stop.wait(self.PART_S):
            subprocess.run([*self.base, "stop"], check=False)
            self._start_part()

    def __enter__(self):
        self._thread.start()
        return self

    def __exit__(self, *exc):
        self._stop.set()
        self._thread.join()
        subprocess.run([*self.base, "stop"], check=False)
        for name in self.parts:
            for _ in range(10):  # the emulator may still be finalising the file
                try:
                    shutil.move(self.tmp / name, self.out_dir / name)
                    break
                except (PermissionError, FileNotFoundError):
                    time.sleep(1)
            else:
                print(f"  ! recording {name} not found in {self.tmp}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--task", help="AndroidWorld task class name, e.g. SystemWifiTurnOn")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--max-steps", type=int, default=None, help="default: 10 x task complexity")
    ap.add_argument("--seed", type=int, default=0, help="run i uses seed+i for task params")
    ap.add_argument("--record", action="store_true", help="save a screen recording per run")
    ap.add_argument("--perform-emulator-setup", action="store_true", help="install task apps (once)")
    args = ap.parse_args()

    s = Settings.from_env()
    env = env_launcher.load_and_setup_env(
        console_port=s.emulator_console_port,
        emulator_setup=args.perform_emulator_setup,
        adb_path=s.adb_path,
    )
    if not args.task:
        print("Emulator ready." if args.perform_emulator_setup else "No --task given.")
        env.close()
        return

    aw = registry.TaskRegistry().get_registry(registry.TaskRegistry.ANDROID_WORLD_FAMILY)
    if args.task not in aw:
        raise SystemExit(f"Unknown task {args.task!r}. Some valid names: {sorted(aw)[:10]} ...")
    task_cls = aw[args.task]

    results_csv = s.runs_dir / "results.csv"
    s.runs_dir.mkdir(parents=True, exist_ok=True)
    for i in range(args.runs):
        random.seed(args.seed + i)
        task = task_cls(task_cls.generate_random_params())
        logger = TrajectoryLogger(s.runs_dir, args.task, run_id=f"{time.strftime('%Y%m%d-%H%M%S')}_r{i + 1}")
        agent = GelabAgent(env, s, logger=logger)
        max_steps = args.max_steps or int(task.complexity * 10)

        agent.reset(go_home=True)
        task.initialize_task(env)
        print(f"\n=== {args.task} run {i + 1}/{args.runs} | max {max_steps} steps\nGoal: {task.goal}")

        start, steps, stop_reason = time.time(), 0, "max_steps"
        recorder = EmulatorRecorder(s.adb_path, s.emulator_console_port, logger.dir) if args.record else None
        with recorder or contextlib.nullcontext():
            for steps in range(1, max_steps + 1):
                result = agent.step(task.goal)
                a = result.data.get("action", {})
                kind = a.get("action") or ("LLM_ERROR" if "llm_error" in result.data else "PARSE_ERROR")
                print(f"  [{steps:02d}] {kind}: {a.get('explain', '')[:80]}")
                if result.done:
                    stop_reason = result.data.get("stop_reason", "unknown")
                    break

        score = task.is_successful(env)
        # Only COMPLETE counts as "the agent said it's done" (false_done = said done, but score != 1).
        # Episodes ended by ABORT, loop detection or repeated errors are not.
        agent_done = stop_reason == "complete"
        summary = {
            "task": args.task,
            "run": i + 1,
            "seed": args.seed + i,
            "goal": task.goal,
            "success": bool(agent_done and score == 1),
            "score": score,
            "agent_said_done": agent_done,
            "stop_reason": stop_reason,
            "steps": steps,
            "max_steps": max_steps,
            "seconds": round(time.time() - start, 1),
            "model": s.llm_model,
            "quant": s.llm_quant,
            "platform": sys.platform,
            "commit": _git_commit(),
            "recordings": ";".join(recorder.parts) if recorder else "",
            "run_dir": str(logger.dir.relative_to(s.runs_dir)),
        }
        logger.write_summary(summary)
        _append_csv(results_csv, summary)
        print(f"  -> {'SUCCESS' if summary['success'] else 'FAIL'} (score={score}, {steps} steps)")
        task.tear_down(env)

    env.close()


def _git_commit() -> str:
    """Short commit hash (+ '-dirty'), so results from different machines are comparable."""
    sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout
    dirty = subprocess.run(
        ["git", "status", "--porcelain", "--", "src"], capture_output=True, text=True
    ).stdout
    return (sha.strip() or "no-git") + ("-dirty" if dirty.strip() else "")


def _append_csv(path: Path, row: dict) -> None:
    new = not path.exists()
    with path.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(row))
        if new:
            w.writeheader()
        w.writerow(row)


if __name__ == "__main__":
    main()
