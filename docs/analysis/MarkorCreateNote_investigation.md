# MarkorCreateNote: why it failed 3/3, and what we changed

Investigation log, 2026-10-08, Nils' Mac (Apple Silicon, arm64 emulator, `gelab-zero-4b-preview`
q8_0, image size 1024). Written for the presentation: every claim below points to a run folder,
screenshot or experiment. Code changes are on branch `fix/type-focus`.

## TL;DR

| | What happened | Root cause | Tag | D4 lever |
|---|---|---|---|---|
| Bug 1 | Agent typed the note text 3×, editor stayed empty → loop guard | Editor had no input focus; `adb input text` went nowhere | `grounding` (action didn't land) | **Actionability** |
| Bug 2 | After fixing bug 1: agent said COMPLETE, file empty | Markor writes the file only when you save/leave the editor | `false_done` | **Goal clarity** (hint) |
| Remaining | After a hint: note saved correctly (checker 1.0), but agent taps the greyed-out save icon 3× → loop guard | A ~240-pixel change is invisible to a 4B model at 1024 px | `loop` symptom of perception limit | **Structured feedback** (not done) |

Not a model planning problem: the model's plan (open Markor → + → name → OK → type) was right
in every run. Both bugs sit at the interface between the model and the phone.

---

## 1. Symptom (graded runs, commit `fce0c3b`)

| Seed | Run | Result | Stop | Steps |
|---|---|---|---|---|
| 0 | `runs/MarkorCreateNote/20261008-164111_r1` | FAIL, score 0.0 | loop | 7 |
| 1 | `runs/MarkorCreateNote/20261008-164258_r2` | FAIL, score 0.0 | loop | 7 |
| 2 | `runs/MarkorCreateNote/20261008-164441_r3` | FAIL, score 0.0 | loop | 7 |

All three identical: `AWAKE Markor → CLICK + → TYPE <name> → CLICK OK → TYPE <text>` ×3. The 3rd
identical TYPE triggered our loop guard (`MAX_REPEATED_ACTIONS = 3`).

![focus bug](img/markor_focus_bug.png)

Panels 2 and 3: the editor is open and the keyboard is up, but there is **no cursor**, and the
text never appears. Note in the log: every body TYPE arrived **without a point**
(`executed: input_text, clear_text: true`, no `x`/`y`), so the agent never tapped the field.

Puzzle: task 3 (`MarkorCreateNoteAndSms`, same app, seed 1, same first 5 actions incl. TYPE
without point) **succeeded**: the text arrived on the first try
(`results/MarkorCreateNoteAndSms/20261008-163147_r2/step_005.png`). Both tasks use the same
setup code (`MarkorCreateNoteAndSms` delegates to `MarkorCreateNote.initialize_task`), so the
difference is not the task setup. Typing into this editor without a tap works *sometimes*.

## 2. Hypotheses and experiments

Tool: `docs/analysis/tools/replay_markor.py` sets up `MarkorCreateNote` with the same seed and
replays the **logged executed actions** (no model), then asks AndroidWorld's checker.

| Exp | Change vs. logged actions | Checker | Finding |
|---|---|---|---|
| A | none (exact replay) | 0.0 | **Reproduces** without the model → deterministic, not sampling noise |
| B | tap into the editor before the body TYPE | 0.0 | **Text arrives** (panel 4 above), but still fails → a 2nd cause |
| D | type name as `…wolf.txt` (we suspected the missing `.txt`) | 0.0 | no effect |
| E2 | B + name `…wolf.txt` + Back | 0.0 | file `qFzW_polite_wolf.txt.txt`, **empty** |
| F | B + original name + Back ×2 (leave editor) | **1.0** | file `qFzW_polite_wolf.txt` = "Actions speak louder than words." |

**Refuted hypothesis (worth showing):** we first blamed the model for leaving out `.txt`. Panel
1 shows Markor's dialog has a separate extension field pre-set to `.txt`, so the model's input
was correct, and typing the extension ourselves produced `.txt.txt` (E2).

**Conclusion:** two independent causes.
1. Text only arrives if the editor holds input focus (B vs. A).
2. Markor only writes the file when you leave the editor or press save; the checker reads the
   file from disk (F vs. B). One Back only hides the keyboard.

## 3. Fix 1: tap a text field before TYPE without a point (commit `692d401`)

`src/gui_agent/actions.py: text_field_target()` picks, from AndroidWorld's accessibility tree
(`state.ui_elements`), the focused editable field, else the largest visible one.
`agent.py` adds its centre as `x/y` to `input_text`, so AndroidWorld taps it before typing
(its normal path when coordinates are given). Logged per step as `focus_tap`. General: no app
names, no Markor coordinates. 3 unit tests.

Verification (seed 0, `runs/MarkorCreateNote/20261008-172101_r1`): `focus_tap` at both TYPEs,
text arrives on the first try, then **COMPLETE → score 0.0**: the note was still unsaved
(save icon active, `step_005.png`). That is cause 2: `false_done`.

## 4. Fix 2: hint to save before COMPLETE (commits `256658a`, `89c4f63`)

GELab's prompt has a hint slot: `env2messages4ask(..., hints=[...])`.
**Finding:** upstream builds the hint text but never inserts it into the prompt
(`make_status_prompt` drops `hint_str`). A unit test caught this before any run.
`gelab.py: with_hints()` therefore appends the hint to the task text; a test pins down the
upstream behaviour.

| Version | Hint | Run (seed 0) | Checker | Result |
|---|---|---|---|---|
| v1 `256658a` | "…if you are still in an editor or the app shows a save icon, save or leave the editor first." | `20261008-172726_r1` | **1.0** | FAIL: save tapped 3× → loop |
| v2 `89c4f63` | "…Tap the save icon once: a greyed-out save icon means the changes are already saved, so then output COMPLETE…" | `20261008-173309_r1` | **1.0** | FAIL: save tapped 3× → loop |

![save steps](img/markor_save_steps.png)

The note is now saved correctly, but the agent doesn't see that it is done. Measured screen
change (excluding status bar): typing 58,009 px; 1st save tap 244 px (icon turns grey); 2nd and
3rd tap 240 px (cursor blink only). The only feedback is a small icon colour change:

![save icon](img/markor_save_icon.png)

Lesson: v1 was taken literally (a grey icon is still "a save icon"). v2 describes the grey
state, but the model can't perceive it at 1024 px. Prompting has reached its limit here.

**Not done (next lever, D4 structured feedback):** if the screen barely changed after the last
action, tell the model "your last action had no visible effect" in the next prompt. General
for all tasks; we stopped here for time.

## 5. Graded re-run (commit `89c4f63`)

Decided: re-run **task 2 only** with the fixed code. Tasks 1 and 3 keep their runs on
`fce0c3b`, so **task 2 uses different agent code than tasks 1/3**; say so on the slide.

| Seed | Run | Result | Checker | Stop | Steps | Time |
|---|---|---|---|---|---|---|
| 0 | `results/MarkorCreateNote/20261008-173712_r1` | FAIL | **1.0** | loop | 8 | 1:58 |
| 1 | `results/MarkorCreateNote/20261008-173920_r2` | FAIL | **1.0** | loop | 8 | 1:53 |
| 2 | `results/MarkorCreateNote/20261008-174124_r3` | FAIL | **1.0** | loop | 8 | 2:05 |

Same pattern in all three: name and text arrive (`focus_tap` logged), the note is saved at
step 5 (checker 1.0), then the agent taps the greyed-out save icon at steps 6 and 7 and the loop
guard ends the episode. `success` stays False because the agent never said COMPLETE.

**Before vs. after the fix (same seeds 0–2):**

| | Text arrives | Note saved (checker) | Agent says done | Counted success |
|---|---|---|---|---|
| Before (`fce0c3b`) | 0/3 | 0/3 (0.0) | 0/3 | 0/3 |
| After (`89c4f63`) | 3/3 | **3/3 (1.0)** | 0/3 | 0/3 |

The success *rate* is unchanged, but the failure moved from "the action has no effect" to
"the model doesn't recognise it has finished": one level closer to the goal, and a different
D4 lever.

**Label in `results/labels.csv`:** `grounding`, first wrong step 6. None of the five D1 classes
fits exactly: the taps land correctly, the model misreads the screen state (grey icon = saved).
We chose `grounding` in the broad sense of linking the screenshot to what is going on; a team
decision may prefer another class. The loop itself is only the symptom.

## 6. Side findings

- **Flaky startup download:** twice today, AndroidWorld failed before step 1 with
  `URLError: SSL UNEXPECTED_EOF_WHILE_READING` while downloading its accessibility forwarder
  APK (`android_env/wrappers/a11y_grpc_wrapper.py`). Not agent-related; retrying works. No step
  ran, so no run was recorded.
- **Harmless reset error:** between graded runs 1 and 2, AndroidWorld logged a traceback for
  `adb shell am stack remove <id>` (`SIGTRAP`) while resetting the phone. The next run started
  and finished normally.
- Old failed graded runs (`fce0c3b`) stay in `runs/` as the "before" evidence; the verification
  runs (`692d401`, `256658a`, `89c4f63`, seed 0) stay there too. Neither is handed in.

## Slide outline

1. Symptom: 3/3 identical failures, loop on TYPE (panel 2–3).
2. Reproduce without the model (Exp A): it's the interface, not the model.
3. One tap fixes it (panel 4). Refuted `.txt` hypothesis (panel 1).
4. Second cause appears: `false_done` (unsaved note).
5. Hint fixes saving, but the model can't see "done" (save icon strip, 240 px).
6. D4 levers: actionability ✔, goal clarity ✔ (partially), structured feedback → next.
