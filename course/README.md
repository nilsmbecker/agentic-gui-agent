# 📚 Course material (reference only)

**This folder is NOT project code.** It holds the lecture material of *Agentic AI in Business*
as handed out, so the whole team has the same reference. Don't edit it, and don't import from it
in `src/`.

| Path | Content |
|---|---|
| `slides/D1-Intro.pdf` | Model as stateless sampler; agent = model + context + tools; **failure taxonomy** (`grounding`, `too_early`, `lost_value`, `wrong_app`, `false_done`) |
| `slides/D2-Context engineering.pdf` | Context window, KV-cache/stable prefix, Skills, memory |
| `slides/D3-Tools.pdf` | ReAct loop, tool design as Agent–Computer Interface |
| `slides/D4-Coding.pdf` | **Reliability checklist**: goal clarity, observable state, actionability, structured feedback, independent verification, bounded recovery |
| `slides/D5-RL-slides.pdf` | SFT vs. RL (not needed for the project) |
| `labs/D1/` | Ollama chat / sampling lab (stdlib only), see its README |
| `labs/D2/` | Context-engineering lab: tools, prefix cache, skills, memory |
| `labs/D3-code-example/` | OpenAI Responses API hosted-tool example |

The labs' commands are in the root `CLAUDE.md`. Run them from inside their folder (`cd course/labs/D1`).
