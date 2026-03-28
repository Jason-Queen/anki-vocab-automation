# Anki Vocabulary Automation

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

> Language: [English](README.md) | [中文](README_CN.md)

Turn your own words and sentences into beginner-friendly English vocabulary cards and import them into Anki automatically.

## Features

- Multiple content sources: Collins Dictionary API, LLM (OpenAI / Anthropic / LM Studio / Ollama / any OpenAI-compatible backend), or both in fallback order
- British and American pronunciations with dictionary audio preferred; TTS fills gaps when needed
- Duplicate detection — existing notes are skipped
- Direct import through AnkiConnect
- Four usage modes: agent tool, CLI, file-driven batch, and interactive launcher

## Requirements

| Required | Optional |
| --- | --- |
| Python 3.9+ | Collins Dictionary API key |
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | Agent tool (Codex, Claude Code, Gemini CLI, etc.) |
| Anki Desktop with [AnkiConnect](https://ankiweb.net/shared/info/2055492159) | |

> [!NOTE]
> If you use the **agent-authored** workflow, the agent's own model provides card content — you do not need a separate LLM provider or Collins API key. For CLI, file-driven, launcher, and repo-llm workflows, at least one LLM provider **or** Collins API key is required.

## Installation

```bash
git clone https://github.com/Jason-Queen/anki-vocab-automation.git
cd anki-vocab-automation
uv sync
```

## Configuration

Copy the example config and edit only the fields you need:

```bash
cp config.env.example config.env
```

A minimal local-model setup:

```env
LLM_PROVIDER=lmstudio
LLM_API_MODE=auto
LLM_BASE_URL=http://localhost:1234
LLM_API_KEY=not-needed
LLM_MODEL_NAME=
DATA_SOURCE_STRATEGY=llm_only
ENABLE_TTS_FALLBACK=true
DECK_NAME=Vocabulary
```

Alternatively, use the interactive launcher (`uv run python app.py`) to create and edit `config.env` through guided menus.

## Quick Start

### Agent tool mode (recommended)

If you use Codex, Claude Code, Gemini CLI, or a similar agent tool, this is the easiest way to get started. Choose the **agent-authored** entrypoint and the agent handles everything — LLM calls, audio generation, and Anki import — with no local LLM, no API key, and no `config.env` editing required.

Open the repository root in your agent tool, then invoke one of these entrypoints:

| Tool | Entrypoints |
| --- | --- |
| Codex / OpenCode | `anki-card-repo-llm` or `anki-card-agent-authored` |
| Claude Code | `/anki-card-repo-llm` or `/anki-card-agent-authored` |
| Gemini CLI | `/anki-card:repo-llm` or `/anki-card:agent-authored` |

- **agent-authored** — the agent writes card content directly using its own model. No local LLM or API key required.
- **repo-llm** — the agent follows the repository's own LLM workflow. Requires a configured LLM provider (see [Configuration](#configuration)).

If the skill files were added after your agent session started, restart the session so it rescans the project.

### CLI

Use this for scripts, shell automation, or quick manual imports. Requires a configured LLM provider.

Single entry:

```bash
uv run anki-vocab --entry 'clarify｜I asked the teacher to clarify the lesson.'
```

Batch via stdin:

```bash
printf 'clarify｜I asked the teacher to clarify the lesson.\nschedule|We need to change the meeting schedule again.\n' | \
  uv run anki-vocab --stdin --concurrent
```

Tune concurrency:

```bash
printf 'clarify｜…\n' | \
  uv run anki-vocab --stdin --concurrent --max-workers 4 --rate-limit 2.0
```

> [!NOTE]
> CLI mode (`--entry` / `--stdin`) always runs as `llm_only` regardless of `DATA_SOURCE_STRATEGY`, and does not require `COLLINS_API_KEY`.

### File-driven batch

Put your words in `data/New_Words.txt`, then run:

```bash
uv run anki-vocab
```

This mode follows your configured `DATA_SOURCE_STRATEGY`.

### Interactive launcher

```bash
uv run python app.py
```

A menu-driven local workflow for setup, environment checks, and import runs.

## Input Format

Each line is one of:

| Format | Example |
| --- | --- |
| `word<TAB>sentence` | `clarify`\t`I asked the teacher to clarify the lesson.` |
| `word｜sentence` | `schedule｜We need to change the meeting schedule again.` |
| `word\|sentence` | `present\|The present plan is easier to explain.` |
| `word` (no sentence) | `implementation` |

Providing a sentence improves sense and part-of-speech selection.

## Card Fields

Each imported note contains:

| Field | Description |
| --- | --- |
| `Word` | Target word |
| `PartOfSpeech` | e.g. verb, noun |
| `Definition` | Beginner-friendly definition |
| `Example` | Your original sentence (when provided) |
| `GeneratedExample` | A new example sentence |
| `Pronunciation` | IPA |
| `AudioFilename` / `AudioSource` | Primary audio |
| `BritishPronunciation` / `BritishAudioFilename` / `BritishAudioSource` | British variant |
| `AmericanPronunciation` / `AmericanAudioFilename` / `AmericanAudioSource` | American variant |

## Content Source Strategy

`DATA_SOURCE_STRATEGY` controls how card content is obtained in file-driven and launcher modes:

| Value | Behavior |
| --- | --- |
| `collins_only` | Collins API only |
| `llm_only` | LLM only |
| `collins_first` | Try Collins first, fall back to LLM |
| `llm_first` | Try LLM first, fall back to Collins |

CLI mode (`--entry` / `--stdin`) always overrides this to `llm_only`.

## Prompt Version

`LLM_PROMPT_VERSION` controls how the LLM selects word sense and part of speech:

| Value | Behavior |
| --- | --- |
| `revised` (default) | Uses the learner sentence as the primary evidence for sense and part-of-speech selection. Recommended. |
| `baseline` | Older prompt for backward compatibility. |

## LLM Provider Examples

### OpenAI

```env
LLM_PROVIDER=openai
LLM_API_MODE=chat
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=your_openai_api_key
LLM_MODEL_NAME=gpt-4o-mini
```

### Anthropic

```env
LLM_PROVIDER=anthropic
LLM_API_MODE=messages
LLM_BASE_URL=https://api.anthropic.com
LLM_API_KEY=your_anthropic_api_key
LLM_MODEL_NAME=claude-3-5-sonnet-20241022
```

### LM Studio

```env
LLM_PROVIDER=lmstudio
LLM_API_MODE=auto
LLM_BASE_URL=http://localhost:1234
LLM_API_KEY=not-needed
LLM_MODEL_NAME=
```

### LM Studio with gpt-oss

```env
LLM_PROVIDER=lmstudio
LLM_API_MODE=responses
LLM_BASE_URL=http://localhost:1234
LLM_API_KEY=not-needed
LLM_MODEL_NAME=openai/gpt-oss-20b
LLM_GPT_OSS_REASONING_EFFORT=medium
```

### Ollama

```env
LLM_PROVIDER=ollama
LLM_API_MODE=auto
LLM_BASE_URL=http://localhost:11434
LLM_API_KEY=not-needed
LLM_MODEL_NAME=
```

### Third-party OpenAI-compatible backend

```env
LLM_PROVIDER=openai_compat
LLM_API_MODE=chat
LLM_BASE_URL=https://your-provider.example.com
LLM_API_KEY=your_provider_key
LLM_MODEL_NAME=your-model-name
```

> [!TIP]
> For `lmstudio` and `ollama`, leaving `LLM_MODEL_NAME` blank will auto-select the currently loaded model — but only when exactly one model is loaded. Zero or multiple loaded models will cause an error.

## Audio Behavior

1. Dictionary audio is kept when available.
2. TTS only runs when a card still has no usable audio and `ENABLE_TTS_FALLBACK=true`.
3. `TTS_OPENAI_COMPAT_BASE_URL` is the recommended TTS path.
4. `TTS_SERVICE` is a legacy URL-style fallback (Google / Microsoft / ResponsiveVoice).

## Anki Notes

- The runtime note type name is derived from `DECK_NAME`, not `MODEL_NAME`.
- `MODEL_NAME` still appears in config for compatibility but is not used at runtime for model creation.
- Do not delete and recreate the note type unless you intend a destructive migration.

## Troubleshooting

| Problem | Solution |
| --- | --- |
| Cannot connect to Anki | Start Anki Desktop → verify AnkiConnect is installed → check `ANKI_CONNECT_HOST` / `ANKI_CONNECT_PORT` → run launcher option `9` |
| CLI says no entries | Use `--entry 'word｜sentence'` or pipe text into `--stdin` |
| Local backend cannot find model | Set `LLM_MODEL_NAME` explicitly, or ensure exactly one model is loaded |
| Audio missing | Check dictionary audio availability → set `ENABLE_TTS_FALLBACK=true` → configure `TTS_OPENAI_COMPAT_BASE_URL` |

## For Developers: Local Anki Smoke Test

```bash
uv sync --extra test
```

1. Keep `ANKI_LOCAL_TEST_RUN=false` in `config.env` by default.
2. Set `ANKI_LOCAL_TEST_PROFILE` to a dedicated Anki test profile.
3. Set `ANKI_LOCAL_TEST_DECK` to a disposable deck (e.g. `Vocabulary_LocalSmoke`), different from your main `DECK_NAME`.
4. Start Anki with the test profile and AnkiConnect enabled.
5. Run:

```bash
ANKI_LOCAL_TEST_RUN=1 uv run pytest tests/test_local_anki_import.py -m local_anki -s
```

Results are saved to `tests/.artifacts/local_anki_import_latest.json`.

## Disclaimer

This repository is primarily iterated through AI-driven development. The repository owner does not have a programming background. Please review the code and behavior before relying on it in real study workflows. Treat AI-generated card content as learning material, not authoritative lexical data — provide a learner sentence and do a manual review when sense accuracy matters.

## License

GPL-3.0. See [LICENSE](LICENSE).
