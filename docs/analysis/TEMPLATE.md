# Failure analysis: <Task> run <n>

Copy this file to `docs/analysis/<task>_r<n>.md`.

## 1. Facts
- **Task / tier:** `<TaskName>` / warm-up | real-work | multi-app
- **Goal (as given to the agent):** "…"
- **Run:** `results/<task>/<run_id>/`, recording: <drive link>
- **Outcome:** success=false, agent_said_done=…, steps=…/max …
- **Commit / model / quant:** `<sha>` / gelab-zero-4b-preview / q8_0

## 2. What happened (step by step, only the relevant steps)
| Step | Screen (what was visible) | Model `explain` / `action` | Effect |
|---|---|---|---|
| 3 | … | … | … |

## 3. Root cause
- **First wrong step:** #…
- **Taxonomy tag:** `grounding` | `too_early` | `lost_value` | `wrong_app` | `false_done` | `parse_error` | `loop` | `env`
- **Evidence:** quote the log line or screenshot that proves it

## 4. Which reliability lever (D4) would have prevented it?
goal clarity · observable state · actionability · structured feedback · independent verification · bounded recovery

What a concrete fix would look like in `step()`:

## 5. Did we try it? (optional)
Before/after over 3 runs:
