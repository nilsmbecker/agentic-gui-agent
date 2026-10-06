# Decision log

Short record of decisions, so nobody has to re-discuss them. Newest at the bottom.

| Date | Decision | Why |
|---|---|---|
| 2026-10-06 | Private GitHub repo `agentic-gui-agent` under Nils' account, 4 collaborators | Simple; course slides are committed, so the repo must not be public |
| 2026-10-06 | Course slides + labs live in `course/` (committed, read-only) | Same reference for everyone; clearly separated from project code |
| 2026-10-06 | External repos as **pinned git submodules** in `third_party/`; `ai-agent-book` opt-in | Identical versions on all machines; the book is 1.2 GB reference only |
| 2026-10-06 | GELab-Zero runs **locally in Ollama** (q8_0 default); **no cloud models** | GELab-Zero isn't offered by Ollama Cloud or OpenRouter; a cloud planner/verifier is out of scope for a 3-day timeline. The endpoint stays configurable in `.env` |
| 2026-10-06 | Python 3.11 conda env `gui-agent` | android_world pins numpy 1.26 / matplotlib 3.6 (no wheels for 3.13) |
| 2026-10-06 | Reuse GELab's own `Parser0920Summary` for prompt + parsing (not a re-implementation) | Prompt must match what the model was trained on |
| 2026-10-06 | Minimal stdlib HTTP client, no agent framework | Course convention (D1/D2): auditable, every request visible in logs |
| 2026-10-06 | No fixed roles; work is split via issues/workstreams | Team preference |
| 2026-10-06 | Recordings on a shared drive, not in git | Video size |
| 2026-10-06 | `main` protected by team convention only (PR + 1 review), not by GitHub settings | Branch protection needs GitHub Pro for private repos |
