"""Does the accessibility tree say that Markor's save icon is disabled after saving?

Replays the executed actions of a round-3 run up to the typed text, then dumps the UI
elements around the save icon before the save tap, after the 1st and after the 2nd tap.
usage: python probe_save_a11y.py <steps.jsonl>
"""

import json
import random
import sys
import time
from pathlib import Path

from android_world import registry
from android_world.env import env_launcher, json_action

from gui_agent.config import Settings

steps_file = Path(sys.argv[1])
s = Settings.from_env()
summary = json.loads((steps_file.parent / "summary.json").read_text())
env = env_launcher.load_and_setup_env(console_port=s.emulator_console_port, emulator_setup=False, adb_path=s.adb_path)
task_cls = registry.TaskRegistry().get_registry(registry.TaskRegistry.ANDROID_WORLD_FAMILY)["MarkorCreateNote"]
random.seed(summary["seed"])
task = task_cls(task_cls.generate_random_params())
env.reset(go_home=True)
task.initialize_task(env)

recs = [json.loads(line) for line in steps_file.read_text().splitlines()]
for rec in recs[:5]:  # AWAKE, +, name, OK, body text
    for kw in rec.get("executed") or []:
        env.execute_action(json_action.JSONAction(**kw))
    time.sleep(s.transition_pause_s)
save = recs[5]["executed"][0]  # the first save tap, in pixels


def dump(label: str) -> None:
    els = env.get_state().ui_elements
    near = [
        e for e in els
        if e.bbox_pixels and e.bbox_pixels.y_max < 400 and (e.is_clickable or e.content_description)
    ]
    print(f"--- {label}")
    for e in near:
        b = e.bbox_pixels
        hit = b.x_min <= save["x"] <= b.x_max and b.y_min <= save["y"] <= b.y_max
        print(
            f"  {'>>' if hit else '  '} desc={e.content_description!r} text={e.text!r} "
            f"enabled={e.is_enabled} clickable={e.is_clickable} res={e.resource_name} "
            f"box=({int(b.x_min)},{int(b.y_min)},{int(b.x_max)},{int(b.y_max)})"
        )


dump("before save")
for n in (1, 2):
    env.execute_action(json_action.JSONAction(**save))
    time.sleep(s.transition_pause_s)
    dump(f"after save tap {n}")
print("checker:", task.is_successful(env))
task.tear_down(env)
env.close()
