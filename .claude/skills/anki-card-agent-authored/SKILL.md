---
name: anki-card-agent-authored
description: Directly author beginner-friendly vocabulary card content in this anki-card repository and write it into Anki through AnkiConnect, with optional back-language localization and Google TTS fallback when no local TTS is available.
argument-hint: "[word｜sentence or card task]"
---

Use the canonical repo skill at `.agents/skills/anki-card-agent-authored/SKILL.md` as the source of truth for this workflow.

When this skill is invoked:

1. Read `.agents/skills/anki-card-agent-authored/SKILL.md`.
2. Read only the specific files you need under `.agents/skills/anki-card-agent-authored/references/`.
3. Execute scripts from `.agents/skills/anki-card-agent-authored/scripts/` instead of retyping their logic.
4. If slash arguments were provided, treat them as the requested word, sentence, deck, back-language, or verification task.
5. Keep `Vocabulary` and the user's main Anki profile protected unless they explicitly confirm a risky change.

If the request is actually about reproducing the repository's `uv run anki-vocab --entry/--stdin` local-LLM workflow, do not continue here. Use `anki-card-repo-llm` instead.
