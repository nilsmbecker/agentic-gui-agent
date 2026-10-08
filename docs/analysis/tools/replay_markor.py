"""Replay the exact executed actions of a failed MarkorCreateNote run, without the model.

usage: python replay_markor.py <steps.jsonl> <out_dir> [--focus-tap]
  --focus-tap: before every input_text without coordinates, tap the screen centre
               (where the Markor editor body is) to give it input focus.
After each action: screenshot + which window/view has IME focus.
"""

import json
import random
import subprocess
import sys
import time
from pathlib import Path

from android_world import registry
from android_world.env import env_launcher, json_action
from PIL import Image

from gui_agent.config import Settings

steps_file, out = Path(sys.argv[1]), Path(sys.argv[2])
focus_tap = "--focus-tap" in sys.argv
full_name = "--full-name" in sys.argv
back = "--back" in sys.argv  # press Back after typing (leave the editor, as a user would)  # type the filename exactly as in the goal (incl. .txt)
out.mkdir(parents=True, exist_ok=True)
s = Settings.from_env()


def ime_state() -> str:
    d = subprocess.run([s.adb_path, "shell", "dumpsys", "input_method"], capture_output=True, text=True).stdout
    keep = ("mServedView", "mCurrentFocusedWindow", "mInputShown", "inputType", "packageName")
    return " | ".join(sorted({line.strip()[:140] for line in d.splitlines() if any(k in line for k in keep)}))


summary = json.loads((steps_file.parent / "summary.json").read_text())
env = env_launcher.load_and_setup_env(console_port=s.emulator_console_port, emulator_setup=False, adb_path=s.adb_path)
task_cls = registry.TaskRegistry().get_registry(registry.TaskRegistry.ANDROID_WORLD_FAMILY)["MarkorCreateNote"]
random.seed(summary["seed"])
task = task_cls(task_cls.generate_random_params())
env.reset(go_home=True)
task.initialize_task(env)
print("goal:", task.goal, "| focus_tap:", focus_tap, "| full_name:", full_name)

log = []
for i, line in enumerate(steps_file.read_text().splitlines()):
    rec = json.loads(line)
    for kw in rec.get("executed") or []:
        if full_name and i == 2 and kw["action_type"] == "input_text":
            kw = {**kw, "text": task.params["file_name"]}
        if focus_tap and kw["action_type"] == "input_text" and "x" not in kw and i >= 4:
            w, h = env.logical_screen_size
            env.execute_action(json_action.JSONAction(action_type="click", x=w // 2, y=h // 3))
            time.sleep(1.0)
        env.execute_action(json_action.JSONAction(**kw))
    time.sleep(s.transition_pause_s)
    Image.fromarray(env.get_state().pixels).save(out / f"after_{i:02d}.png")
    entry = {"step": i, "executed": rec.get("executed"), "ime": ime_state()}
    log.append(entry)
    print(json.dumps(entry)[:400])
    if i == 4:  # first body TYPE is enough to decide
        break

if back:
    for _ in range(2 if "--back2" in sys.argv else 1):
        env.execute_action(json_action.JSONAction(action_type="navigate_back")); time.sleep(1)
    time.sleep(2)
    Image.fromarray(env.get_state().pixels).save(out / "after_back.png")
files = subprocess.run([s.adb_path, "shell", "ls", "/sdcard/Documents/Markor/"], capture_output=True, text=True).stdout.split()
print("markor files before check:", files)
contents = {f: subprocess.run([s.adb_path, "shell", "cat", f"/sdcard/Documents/Markor/{f}"], capture_output=True, text=True).stdout for f in files}
print("contents:", repr(contents), "| expected:", repr(task.params["text"]))
score = task.is_successful(env)
print("is_successful:", score)
(out / "replay_log.json").write_text(json.dumps({"focus_tap": focus_tap, "full_name": full_name, "back": back, "files": files, "contents": contents, "score": score, "steps": log}, indent=2))
task.tear_down(env)
env.close()
