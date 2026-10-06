# How we work together (4 people, 3 days)

## Branches & PRs
- `main` is always runnable. **No direct pushes to `main`.** Everything goes through a PR. (GitHub Free can't enforce this on a private repo, so it relies on all of us.)
- Branch names: `<type>/<short-topic>`, e.g. `fix/awake-app-names`, `feat/verify-before-done`,
  `docs/failure-markor`, `runs/contacts-add`.
- Small PRs (< ~200 lines). Link the issue: `Closes #12`.
- **1 approval from someone else** before merge. Squash merge.
- Before opening a PR:
  ```bash
  ruff check src scripts tests && ruff format --check src scripts tests && pytest -q
  ```
  CI runs the same on every PR.

## Commits
Imperative, short: `Map AWAKE app names to AndroidWorld names`. One topic per commit.

## Issues
Every piece of work is an issue with a workstream label (`env`, `agent`, `eval`, `reliability`,
`analysis`). Assign yourself when you start, so nobody duplicates work. See docs/PLAN.md §3.

## Folders: what goes where
| You produced… | Put it in |
|---|---|
| Code | `src/gui_agent/` (+ a test in `tests/` for anything not needing the emulator) |
| A raw run | stays in `runs/` (gitignored) |
| A run we submit | `results/<task>/<run_id>/` via a `runs/...` PR |
| A screen recording | team drive, link in the analysis doc |
| A setup problem + fix | `docs/SETUP.md` troubleshooting table |
| A decision | one line in `docs/DECISIONS.md` |
| A failure analysis | `docs/analysis/<task>_r<n>.md` from `TEMPLATE.md` |

## Never
- edit `third_party/` (submodules) or `course/` (lecture material)
- commit `.env`, model weights, or videos
- run evaluation runs from a dirty working tree. `summary.json` records the commit, and `-dirty` runs don't count

## Updating a submodule (rare, needs team agreement)
```bash
cd third_party/android_world && git fetch && git checkout <sha> && cd ../..
git add third_party/android_world && git commit -m "Bump android_world to <sha>"
```
