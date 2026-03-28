---
name: anki-card-study-coach
description: Practice existing Anki vocabulary cards in this anki-card repository by inspecting review history and running a short read-only study session.
argument-hint: "[deck or study request]"
---

Use the canonical repo skill at `.agents/skills/anki-card-study-coach/SKILL.md` as the source of truth for this workflow.

When this skill is invoked:

1. Read `.agents/skills/anki-card-study-coach/SKILL.md`.
2. Read only the specific files you need under `.agents/skills/anki-card-study-coach/references/`.
3. Execute scripts from `.agents/skills/anki-card-study-coach/scripts/` instead of retyping their logic.
4. If slash arguments were provided, treat them as the requested deck, study length, session style, or seed.
5. Keep the workflow read-only unless the user explicitly asks for a risky Anki action.
6. When the learner is stuck or gives a near-miss on a form-sensitive prompt, prefer `.agents/skills/anki-card-study-coach/scripts/study_turn_assist.py` over ad-hoc judging.

If the request is actually about creating new cards or reproducing the repository's `uv run anki-vocab --entry/--stdin` workflow, do not continue here. Use `anki-card-agent-authored` or `anki-card-repo-llm` instead.
