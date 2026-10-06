"""Run one AndroidWorld task N times with the GELab-Zero agent and log everything.

Examples:
  python scripts/run_task.py --task SystemWifiTurnOff --runs 3 --record
  python scripts/run_task.py --task ContactsAddContact --runs 1 --max-steps 15
  python scripts/run_task.py --perform-emulator-setup   # ONCE per fresh emulator

Outputs (gitignored):  runs/<task>/<run_id>/{steps.jsonl, step_*.png, summary.json, recording.webm}
                       runs/results.csv  (one row per run, appended)
"""

from __future__ import annotations

import argparse
import contextlib
import csv
import os
import random
import subprocess
import time
from pathlib import Path

os.environ.setdefault("GRPC_VERBOSITY", "ERROR")

from android_world import registry  # noqa: E402
from android_world.env import env_launcher  # noqa: E402

from gui_agent.agent import GelabAgent  # noqa: E402
from gui_agent.config import Settings  # noqa: E402
from gui_agent.trajectory import TrajectoryLogger  # noqa: E402


class EmulatorRecorder:
    """Records the emulator screen via the emulator console (max 180 s per file)."""

    def __init__(self, adb: str, port: int, out: Path):
        self.base = [adb, "-s", f"emulator-{port}", "emu", "screenrecord"]
        self.out = out

    def __enter__(self):
        subprocess.run([*self.base, "start", "--time-limit", "180", str(self.out)], check=False)
        return self

    def __exit__(self, *exc):
        subprocess.run([*self.base, "stop"], check=False)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--task", help="AndroidWorld task class name, e.g. SystemWifiTurnOff")
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

        start, steps, agent_done = time.time(), 0, False
        recorder = EmulatorRecorder(s.adb_path, s.emulator_console_port, logger.dir / "recording.webm")
        with recorder if args.record else contextlib.nullcontext():
            for steps in range(1, max_steps + 1):
                result = agent.step(task.goal)
                a = result.data.get("action", {})
                print(f"  [{steps:02d}] {a.get('action', 'PARSE_ERROR')}: {a.get('explain', '')[:80]}")
                if result.done:
                    agent_done = True
                    break

        score = task.is_successful(env)
        summary = {
            "task": args.task,
            "run": i + 1,
            "seed": args.seed + i,
            "goal": task.goal,
            "success": bool(agent_done and score == 1),
            "score": score,
            "agent_said_done": agent_done,
            "steps": steps,
            "max_steps": max_steps,
            "seconds": round(time.time() - start, 1),
            "model": s.llm_model,
            "commit": _git_commit(),
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
    return sha.strip() + ("-dirty" if dirty.strip() else "")


def _append_csv(path: Path, row: dict) -> None:
    new = not path.exists()
    with path.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(row))
        if new:
            w.writeheader()
        w.writerow(row)


if __name__ == "__main__":
    main()
