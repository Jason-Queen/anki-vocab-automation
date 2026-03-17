# 🚀 Anki Vocabulary Learning Automation Tool

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![GitLab issues](https://img.shields.io/badge/GitLab-issues-blue.svg)](https://gitlab.com/jason853/anki-automation/-/issues)
[![GitLab stars](https://img.shields.io/badge/GitLab-stars-blue.svg)](https://gitlab.com/jason853/anki-automation)

> **Language Selection:** [English](README.md) | [中文](README_CN.md)

**Automatically create Anki vocabulary cards optimized for English learners using Collins Dictionary API and AI language models.**

Transform word lists into learner-friendly, concise, and efficient Anki memory cards through intelligent automation tools.

**Note:** This program is entirely developed by AI and has not been verified by human developers. Please use with caution.

## 🎯 Project Motivation

I wanted to collect my own personalized vocabulary list while reading English content and use Anki cards for reinforcement learning. The program is specifically designed for intermediate English learners, providing easy-to-understand definitions and practical example sentences.

## ✨ Core Features

### 📚 **Learner-Friendly Vocabulary Content**
- **Optimized Definitions:** Use simple common vocabulary for explanations, avoid circular definitions, concise expressions within 15 words
- **Practical Examples:** 8-15 word length, daily situations, simple sentence structures, highlighting target vocabulary usage
- **Multi-Data Source Support:** Collins Dictionary API + AI language model intelligent generation
- **Dual Pronunciation Support:** British and American IPA phonetic transcription and audio

### 🤖 **AI-Driven Intelligent Generation**
- **Provider-Aware LLM Support:** Official SDK paths for OpenAI and Anthropic, plus LM Studio, Ollama, and third-party OpenAI-compatible backends
- **Selectable API Modes:** Responses API, Chat Completions API, and Anthropic Messages API
- **Learning-Oriented Optimization:** AI specifically tuned for English learner needs, generating easy-to-understand content
- **Custom TTS Generation:** Intelligently create pronunciation audio when dictionary audio is unavailable

### 🚀 **High-Performance Processing**
- **Concurrent Processing:** Multi-threaded batch processing, significantly improving large vocabulary processing speed
- **Intelligent Retry:** Automatic retry mechanism, ensuring processing success rate
- **Rate Limiting:** Configurable API call frequency control, avoiding service limits
- **Progress Tracking:** Real-time display of processing progress and success rate statistics

### 🔒 **Enhanced Security**
- **Input Validation:** Comprehensive user input security validation, preventing injection attacks
- **Secure Logging:** Automatic filtering of sensitive information in secure logging system
- **Dependency Security:** Use latest version dependencies, fixing known security vulnerabilities (CVE)

### 🎯 **Perfect Anki Integration**
- **Direct Import:** Seamlessly create cards using AnkiConnect, no manual import required
- **Media Management:** Perfect Anki media library integration, automatic audio file management
- **Duplicate Detection:** Intelligently skip existing cards, avoiding duplicate creation
- **Template Consistency:** Card templates use the same name as the deck, maintaining cleanliness

## 🚀 Quick Start

### 1. Requirements

- **Python 3.9+**
- **uv** ([installation guide](https://docs.astral.sh/uv/getting-started/installation/))
- **Anki Desktop** (with AnkiConnect plugin installed)
- **Collins Dictionary API Key** (optional) or **AI Service** (OpenAI, Claude, or local LLM)

### 2. Installation

```bash
# Clone repository
git clone https://gitlab.com/jason853/anki-automation.git
cd anki-automation

# Install runtime dependencies
uv sync

# If you plan to run tests or lint checks
uv sync --extra dev --extra test
```

### 3. Configuration

```bash
# Start interactive configuration wizard
uv run python app.py

# Follow the setup wizard:
# 1. Select option 7: Create configuration file (if needed)
# 2. Select option 8: Check Anki environment
# 3. Select option 4: Configure LLM service
# 4. Select option 3: Configure Collins API (optional)
# 5. Select option 5: Set data source priority
# 6. Select option 6: View current configuration
```

### 4. Usage

```bash
# Add words to list
echo -e "sophisticated\nimplementation\noptimization" > data/New_Words.txt

# Start application
uv run python app.py

# Select option 1: Run automation script
# Select option 2: Use concurrent processing (recommended for large vocabularies)
```

### 5. Local Anki Smoke Test

Use this as the first check in a coding session when you want to see the current import result in Anki immediately.

If you have not installed test dependencies yet, run `uv sync --extra test` once first.

1. Keep `ANKI_LOCAL_TEST_RUN=false` in `config.env`.
2. Set `ANKI_LOCAL_TEST_PROFILE` to your dedicated Anki test profile.
3. Keep `ANKI_LOCAL_TEST_DECK` on a disposable deck such as `Vocabulary_LocalSmoke`. The smoke test deletes old notes in that deck before importing a fresh sample.
4. Optional: set `ANKI_LOCAL_TEST_SOURCE_EXAMPLE` if you want to verify the new front-side context sentence flow.
5. Start Anki with that test profile and AnkiConnect enabled.
6. Run:

```bash
ANKI_LOCAL_TEST_RUN=1 uv run pytest tests/test_local_anki_import.py -m local_anki -s
```

The test writes the latest imported note snapshot to `tests/.artifacts/local_anki_import_latest.json` so you can compare fields and media quickly after each run.

### 6. Development Checks

If you are working on the project itself, install maintainer dependencies first:

```bash
uv sync --extra dev --extra test
```

Then run the common checks with `uv`:

```bash
uv run pytest tests/ -v --cov=src/anki_vocab_automation --cov-report=xml
uv run flake8 src/
uv run --with safety safety check --json > safety-report.json
uv run --with bandit bandit -r src/ -f json -o bandit-report.json
```

## 📖 How It Works

### Input Format
Recommended format: `word<TAB>sentence where you saw the word`.

Plain word-only lines still work, but if you provide the sentence context the generated definition is usually more accurate.

Examples:
```
clarify	I asked the teacher to clarify the lesson.
fundamental	The report explains the fundamental problem in the design.
schedule | We need to change the meeting schedule again.
implementation
```

### Intelligent Processing Flow
1. **Input Validation:** Secure validation and cleaning of user input
2. **Word Analysis:** Automatically determine standard dictionary form
3. **Content Generation:** Get learner-friendly content from Collins API or generate with AI
4. **Audio Processing:** Prioritize dictionary audio, fallback to intelligent TTS generation
5. **Concurrent Optimization:** Multi-threaded parallel processing, improving efficiency
6. **Card Creation:** Direct import to Anki, perfect media integration

### Generated Learner-Friendly Cards
Each card is optimized for English learners:
- **Word:** Standard dictionary form
- **Definition:** Use simple vocabulary, avoid circular definitions, within 15 words
- **Front Example:** The learner-provided sentence when available
- **Back Example:** A new generated sentence distinct from the learner sentence and explicitly containing the target word
- **Pronunciation:** Clear IPA phonetic transcription (British and American)
- **Audio:** High-quality pronunciation audio files
- **Part of Speech:** Concise grammatical classification

## 🛠️ Advanced Configuration

### Data Source Strategy
- `collins_first`: Use Collins API, fallback to AI (quality priority)
- `llm_first`: Use AI, fallback to Collins API (speed priority)
- `collins_only`: Collins API only
- `llm_only`: AI only (suitable for offline use)

### Concurrent Processing Configuration
```env
# Concurrent processing settings
MAX_WORKERS=4              # Maximum concurrent threads
RATE_LIMIT_PER_SECOND=2.0  # API call frequency limit
RETRY_ATTEMPTS=2           # Failure retry attempts
TIMEOUT_PER_WORD=60        # Word processing timeout
```

**⚠️ Important Notice: Concurrent processing may cause TTS file download failures**
- When concurrent speed is too fast, TTS services may not respond in time, causing audio file download failures
- If you encounter TTS download issues, it's recommended to use single-threaded mode (option 1) for stability
- Single-threaded mode is slower but ensures all audio files are downloaded correctly

### Supported AI Services

#### Official Cloud Providers
- **OpenAI:** Uses the official OpenAI SDK; `gpt-oss` models use the Responses API, other models use Chat Completions + JSON Schema
- **Anthropic:** Uses the official Anthropic SDK and the Messages API

#### Local and Self-Hosted Providers
- **LM Studio:** Auto-routes `gpt-oss` models to Responses API and other models to Chat Completions + JSON Schema
- **Ollama:** Auto-routes `gpt-oss` models to Responses API and other models to Chat Completions + JSON Schema
- **Third-party OpenAI-compatible backends:** Supported in Chat Completions compatibility mode, with JSON Schema when available

#### Recommended Configuration Examples
```env
# OpenAI official
LLM_PROVIDER=openai
LLM_API_MODE=chat
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL_NAME=gpt-4o-mini
LLM_API_KEY=your_openai_api_key

# OpenAI / LM Studio gpt-oss
LLM_PROVIDER=lmstudio
LLM_API_MODE=responses
LLM_BASE_URL=http://localhost:1234
LLM_MODEL_NAME=openai/gpt-oss-20b
LLM_API_KEY=not-needed
LLM_GPT_OSS_REASONING_EFFORT=medium

# Anthropic official
LLM_PROVIDER=anthropic
LLM_API_MODE=messages
LLM_BASE_URL=https://api.anthropic.com
LLM_MODEL_NAME=claude-3-5-sonnet-20241022
LLM_API_KEY=your_anthropic_api_key

# LM Studio auto-routing
LLM_PROVIDER=lmstudio
LLM_API_MODE=auto
LLM_BASE_URL=http://localhost:1234
# Leave blank to use the currently loaded model automatically
LLM_MODEL_NAME=
LLM_API_KEY=not-needed

# LM Studio explicit Chat API
LLM_PROVIDER=lmstudio
LLM_API_MODE=chat
LLM_BASE_URL=http://localhost:1234
# Or set an explicit model name when you do not want the loaded-model default
LLM_MODEL_NAME=qwen/qwen3.5-9b
LLM_API_KEY=not-needed

# Ollama auto-routing
LLM_PROVIDER=ollama
LLM_API_MODE=auto
LLM_BASE_URL=http://localhost:11434
# Leave blank to use the currently running model automatically
LLM_MODEL_NAME=
LLM_API_KEY=not-needed

# Third-party OpenAI-compatible backend
LLM_PROVIDER=openai_compat
LLM_API_MODE=chat
LLM_BASE_URL=https://your-provider.example.com
LLM_MODEL_NAME=your-model-name
LLM_API_KEY=your_provider_key
```

For LM Studio and Ollama:
- If `LLM_MODEL_NAME` is blank, the app uses the currently loaded/running model.
- If multiple models are currently loaded/running, the app stops and asks you to set `LLM_MODEL_NAME` explicitly.
- If no model is currently loaded/running, generation stops with an error instead of guessing.
- If you set `LLM_MODEL_NAME` manually, that value is used, but the app now checks that the model exists first.
- When the selected model is in the `gpt-oss` family, generation uses the Responses API and defaults `LLM_GPT_OSS_REASONING_EFFORT=medium`.
- Other local models use Chat Completions + JSON Schema to reduce reasoning-only outputs and improve structured JSON reliability.

Maintainer note:
- The current local-model benchmark conclusion and prompt-comparison summary are recorded in [docs/llm-benchmark-phase-summary-2026-03.md](docs/llm-benchmark-phase-summary-2026-03.md).

### TTS Audio Generation
- **OpenAI-compatible remote TTS:** Preferred path for new setups; works with local or remote `/v1/audio/speech` servers such as `Qwen3-TTS-MLX-Server`
- **Google TTS / Microsoft TTS / ResponsiveVoice:** Legacy URL-based compatibility fallbacks for users who explicitly opt in

Example configuration for an OpenAI-compatible TTS server:

```env
ENABLE_TTS_FALLBACK=true
TTS_OPENAI_COMPAT_BASE_URL=http://127.0.0.1:8000
TTS_OPENAI_COMPAT_API_KEY=not-needed
TTS_OPENAI_COMPAT_MODEL=mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-bf16
TTS_OPENAI_COMPAT_RESPONSE_FORMAT=wav
```

Notes:
- If `TTS_OPENAI_COMPAT_BASE_URL` is configured, the app uses `openai_compat` as the primary TTS path
- `TTS_SERVICE` now means an optional legacy URL-based compatibility fallback; leave it blank if you do not want those brittle public URL paths at all
- If `TTS_OPENAI_COMPAT_MODEL` is unset, the app reads the server `default_model` from `/health`
- The fallback automatically asks for British or American English accents for `en-GB` and `en-US`
- If you switch to a `CustomVoice` model, also set `TTS_OPENAI_COMPAT_VOICE`
- `Base` voice-clone models require `ref_audio`, so they are not suitable for the generic pronunciation fallback
- The card back now shows the audio source so learners can tell `Dictionary` audio from `TTS`

Example if you explicitly want a legacy compatibility fallback:

```env
TTS_SERVICE=google
```

### Source And Audio Fallback Matrix

Keep one rule in mind:
- `DATA_SOURCE_STRATEGY` controls where the card content comes from
- The audio fallback chain only runs when the current card is missing audio

Content-source behavior:

| Setting | Default card-content order |
| --- | --- |
| `collins_only` | `Collins` |
| `collins_first` | `Collins -> LLM` |
| `llm_only` | `LLM` |
| `llm_first` | `LLM -> Collins` |

Word-audio behavior:

| Condition | Default word-audio order |
| --- | --- |
| Card already has dictionary audio | `Dictionary` |
| Card is missing audio and `TTS_OPENAI_COMPAT_BASE_URL` is configured | `openai_compat TTS -> optional legacy TTS_SERVICE` |
| Card is missing audio and only `TTS_SERVICE` is configured | `legacy TTS_SERVICE` |
| Card is missing audio and neither is configured | `no TTS fallback` |

Common combinations:

| Configuration | Typical effective path |
| --- | --- |
| `collins_first` + local TTS | `Collins content/dictionary audio -> if missing, openai_compat TTS -> optional legacy TTS` |
| `llm_only` + local TTS | `LLM content -> openai_compat TTS -> optional legacy TTS` |
| `llm_first` + local TTS | `LLM content -> if LLM fails, Collins -> if audio is missing, openai_compat TTS -> optional legacy TTS` |

## 📊 Output Examples

**Terminal Display (Concurrent Processing):**
```
Starting batch processing of 10 words (concurrency: 4)
✅ [3/10] sophisticated (2.1s)
✅ [4/10] implementation (1.8s)  
❌ [5/10] xyz - Input validation failed: Word contains disallowed characters (0.1s)
Progress: 5/10 (Success: 4, Failed: 1)
Batch processing completed: Total time 15.2s, Average 1.5s/word, Success 9/10
```

**Anki Card (Learner Optimized):**
```
Front: sophisticated
Example: This software uses sophisticated methods to solve problems.

Back: 
Definition: having great knowledge or experience; advanced and complex
Pronunciation: 
🇬🇧 British: /səˈfɪstɪkeɪtɪd/
🇺🇸 American: /səˈfɪstɪkeɪtɪd/
🔊 [Audio Player]
Part of Speech: adjective
```

## 🔧 Troubleshooting

### Common Issues

1. **Anki Connection Failed**
   - Ensure Anki is running
   - Install and enable AnkiConnect plugin
   - Use option 8 to check Anki environment

2. **LLM Service Not Working**
   - Check API key and base URL
   - For local services, ensure they are running
   - Use option 4 to reconfigure LLM service
   - Check secure logs for detailed error information

3. **Concurrent Processing Issues**
   - Reduce MAX_WORKERS value (recommended 2-4)
   - Increase RATE_LIMIT_PER_SECOND interval
   - Check network stability and API limits
   - **TTS Download Failures:** If you encounter audio file download failures, it's recommended to switch to single-threaded mode (option 1)

4. **Template Creation Failed**
   - If template exists but fields are incomplete, manually delete the template in Anki
   - Program will create a new template with correct fields

5. **Security Warnings**
   - Program automatically validates and cleans input
   - Check log files for filtered content
   - Ensure word file sources are trustworthy

### Getting Help

- Check secure logs in `anki_vocab_automation.log`
- Use option 6 to view current configuration
- Use option 9 to run comprehensive tests
- Check if dependency versions are latest secure versions

### Performance Optimization Tips

- **Small Vocabulary (<50 words):** Use default single-threaded processing
- **Medium Vocabulary (50-200 words):** Enable concurrent processing, set max_workers=4
- **Large Vocabulary (>200 words):** Use concurrent processing, adjust rate limits appropriately
- **Local LLM:** Can increase concurrency and lower rate limits
- **⚠️ TTS Stability Priority:** If audio file download failures occur, it's recommended to use single-threaded mode to ensure all audio is downloaded correctly

---

<div align="center">
  <strong>This program is entirely driven by Cursor program and the LLM AI behind it. Please note that AI may make mistakes! 📚✨</strong>
  <br><br>
  <em>Now supports concurrent processing, security validation, intelligent optimization and other advanced features</em>
</div>
