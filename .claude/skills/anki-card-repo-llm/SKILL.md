---
name: anki-card-repo-llm
description: Reproduce this anki-card repository's direct CLI and local-LLM workflow, including `uv run anki-vocab --entry` or `--stdin`, connectivity checks, post-import localization, and the local Anki smoke test.
argument-hint: "[word｜sentence, batch task, or validation task]"
---

Use the canonical repo skill at `.agents/skills/anki-card-repo-llm/SKILL.md` as the source of truth for this workflow.

When this skill is invoked:

1. Read `.agents/skills/anki-card-repo-llm/SKILL.md`.
2. Read only the specific files you need under `.agents/skills/anki-card-repo-llm/references/`.
3. Reuse scripts from `.agents/skills/anki-card-repo-llm/scripts/` for AnkiConnect checks and model-localization steps.
4. If slash arguments were provided, treat them as the requested import, troubleshooting, localization, or smoke-test task.
5. Keep smoke tests on dedicated profiles and disposable decks only.

If the user wants the agent to skip the repo LLM and directly author the card content itself, do not continue here. Use `anki-card-agent-authored` instead.
