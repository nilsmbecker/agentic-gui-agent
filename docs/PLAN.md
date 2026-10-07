# Project plan: GELab-Zero agent on AndroidWorld

**Team:** 4 people on Apple Silicon Macs and Windows PCs · **No fixed roles:** work is split by GitHub issues
**Deadline:** Friday 9 Oct 2026 (demo + presentation) · **Plan written:** Tue 6 Oct 2026

---

## 1. Goal

> Build one auditable GUI agent (`GelabAgent.step()`) that drives AndroidWorld with a locally
> running GELab-Zero-4B. Run it on 3 tasks across all difficulty tiers, 3 times each, and explain
> **why** it fails, using the course's failure taxonomy and D4's reliability levers.

Grading context: group project 40% (demo, trajectory logs, written failure analysis) + presentation 20%.

### Goals by priority (MoSCoW)

| | Goal | Measurable as |
|---|---|---|
| **Must** | Agent class with a single `step()`: observe → decide → act → done | `src/gui_agent/agent.py`, runs end-to-end |
| **Must** | ≥ 3 tasks, one per tier (warm-up / real-work / multi-app & memory) | `configs/tasks.yaml` |
| **Must** | 3 runs per task, each with screen recording + trajectory log | 9 folders in `results/`, 9 videos on team drive |
| **Must** | Written analysis of ≥ 1 failure, tagged with taxonomy + D4 lever | `docs/analysis/*.md` |
| **Must** | Presentation 10–30 min + live or recorded demo | slides + backup video |
| **Should** | Results table: success rate, steps, time per step, per task | `results/results.csv` + slide |
| **Should** | One targeted improvement, measured before/after (e.g. verify before `COMPLETE`) | 3 extra runs on the affected task |
| **Could** | More tasks / backups from `configs/tasks.yaml` | more rows in results |
| **Could** | q8_0 vs Q4_K_M quantization: speed vs. success | small comparison table |
| **Won't** | Cloud models, fine-tuning/RL (D5), multi-agent architectures | (out of scope, see DECISIONS.md) |

**We don't aim for a high success rate.** A 4B model will fail on harder tasks. What gets graded
is showing *why* it fails, with evidence from the logs. A well-explained failure is worth as much
as a success.

---

## 2. Milestones

Critical path: **emulator + AndroidWorld running on our Macs and PCs**. Everything else waits on it,
so all 4 people do M0 in parallel tonight and the first machine that works becomes the reference.

### M0: Environment works (Tue 6 Oct, evening)
- [ ] Repo pushed to GitHub (private), all 4 added as collaborators, everyone cloned
- [ ] Everyone: `scripts/setup_mac.sh` → `setup_model.sh` → `start_emulator.sh`
- [ ] Everyone: `run_task.py --perform-emulator-setup` (installs task apps, slow, once)
- [ ] Everyone: `check_setup.py` all green, post the result in the team chat
- [ ] **Exit criterion:** ≥ 2 machines fully green. If nobody gets there by Wed 10:00 → see Risk R1.

### M1: First end-to-end run (Wed 7 Oct, by 14:00)
- [ ] `run_task.py --task SystemWifiTurnOn --runs 1` completes with a logged trajectory
- [ ] Fix mapping bugs in `actions.py`. Likely issues: AWAKE app names, TYPE focus, SLIDE direction
- [ ] Measure seconds per step → decide max steps per task and q8 vs. Q4
- [ ] Try each `primary` task in `configs/tasks.yaml` once. Swap in a backup if a task can't run on ARM
- [ ] **Exit criterion:** task selection frozen (PR changing `configs/tasks.yaml` merged)

### M2: Evaluation runs (Wed afternoon → Thu 8 Oct, 18:00)
- [ ] 3 runs × 3 tasks with `--record`, split across machines (same commit, same seed, same quant)
- [ ] Copy each run into `results/<task>/<run_id>/`. Recordings go to the team drive
- [ ] Label every failed run with a taxonomy tag in `results/labels.csv`
- [ ] *Should:* one improvement (pick the most frequent failure tag), +3 runs to show its effect
- [ ] **Code freeze Thu 18:00.** After that, only docs and slides change

### M3: Analysis + presentation (Fri 9 Oct)
- [ ] ≥ 1 failure write-up from `docs/analysis/TEMPLATE.md` (ideally one per tier)
- [ ] Slides: problem → architecture → results table → failure deep-dive → lessons (D4 levers)
- [ ] Backup demo video, in case the live emulator fails
- [ ] Rehearse once with timing; everyone can explain `step()` (expect Q&A on it)

---

## 3. Workstreams (become GitHub issues; anyone picks one up)

| # | Workstream | First issues |
|---|---|---|
| A | **Environment** | ARM emulator quirks; document fixes in SETUP.md troubleshooting |
| B | **Agent core** | Action mapping fixes; app-name mapping for `AWAKE`; prompt/history handling |
| C | **Evaluation** | Runner, recordings, `results/` curation, results table |
| D | **Reliability** (D4) | Verify-before-done; bounded retries; loop detection (same action 3×) |
| E | **Analysis & story** | Failure labels, write-ups, slides, demo video |

Rule of thumb: A and B are urgent on Tue/Wed, C on Thu, D is optional, E runs from Thu to Fri.

---

## 4. How we analyse failures

For each failed run, open `steps.jsonl` and the screenshots, find the **first step that went
wrong**, and tag it:

| Tag (D1) | Meaning | Typical evidence in our logs | D4 lever that would help |
|---|---|---|---|
| `grounding` | Right intent, wrong place on screen | `explain` names the right button, but the click coordinates miss it | structured feedback (did the screen change?) |
| `too_early` | Acts before the UI is ready | action on a loading screen | observable state / wait |
| `lost_value` | Forgets a value across steps or apps | `summary` no longer contains the value | memory / explicit state |
| `wrong_app` | Opens or works in the wrong app | `AWAKE` value ≠ target app | goal clarity / constraints |
| `false_done` | Says `COMPLETE`, but the task checker says fail | `agent_said_done=true, success=false` | independent verification |

Plus our own: `parse_error` (output not in GELab format, `parse_error` in the step), `loop` (repeats an action, `loop_detected=true` / `stop_reason=loop`), `env` (an emulator/infra problem, not the agent's fault, e.g. `llm_error` in the step).

---

## 5. Risks

| ID | Risk | Likelihood | Mitigation |
|---|---|---|---|
| R1 | AndroidWorld on an ARM emulator: some task apps or `perform_emulator_setup` fail | medium | Try on all 4 Macs at once. Choose tasks whose apps work. Fallback: AndroidWorld's x86 Docker image (slow) |
| R2 | Slow inference (emulator + 4B model in 18 GB RAM) | high | q8_0 → Q4_K_M; close other apps; `-no-window` emulator; split runs across machines |
| R3 | GELab is trained on Chinese apps/prompts, so app names don't match | medium | Map `AWAKE` names to AndroidWorld app names in `actions.py`; log mismatches |
| R4 | Emulator screenrecord is capped at 180 s | high for long tasks | Fallback: macOS screen recording (⌘⇧5) of the emulator window |
| R5 | Results not comparable across machines | medium | Same commit, seed, quant. `summary.json` records model; compare commits in PR |
| R6 | Time: 3 days | high | MoSCoW above; code freeze Thu 18:00; analysis can start from the first failed run on Wed |

---

## 6. Daily rhythm

- **Stand-up, 10 min, 09:30 + 18:00:** what works, what's blocked, who takes which issue.
- Blockers go into the team chat immediately, not at the next stand-up.
- Every finding about the environment goes into `docs/SETUP.md`, so the next person doesn't hit it again.
