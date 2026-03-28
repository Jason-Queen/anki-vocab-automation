# Anki 词汇自动化工具

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

> 语言: [English](README.md) | [中文](README_CN.md)

把你自己的单词和原句自动整理成适合初学者的英语词汇卡片，并直接导入 Anki进行学习。你还可以通过Agent调用**study-coach** Skill来进行交互式学习。

## 功能

- 多种内容来源：Collins 词典 API、LLM（OpenAI / Anthropic / LM Studio / Ollama / 其他 OpenAI 兼容后端），或按优先级组合回退
- 英式/美式双发音，优先使用词典音频；缺失时 TTS 自动补位
- 自动跳过重复笔记
- 通过 AnkiConnect 直接导入
- 四种使用方式：agent 工具、CLI、文件批量导入、交互式 launcher

## 环境要求

| 必需 | 可选 |
| --- | --- |
| Python 3.9+ | Collins Dictionary API 密钥 |
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | Agent 工具（Codex、Claude Code、Gemini CLI 等） |
| Anki Desktop + [AnkiConnect](https://ankiweb.net/shared/info/2055492159) | |

> [!NOTE]
> 如果使用 **agent-authored** 工作流，agent 自身的模型负责生成卡片内容，不需要额外的 LLM 后端或 Collins API 密钥。CLI、文件批量导入、launcher 和 repo-llm 工作流则需要至少一个 LLM 后端**或** Collins API 密钥。

## 安装

```bash
git clone https://github.com/Jason-Queen/anki-vocab-automation.git
cd anki-vocab-automation
uv sync
```

## 配置

复制示例配置文件，然后只修改你需要的字段：

```bash
cp config.env.example config.env
```

一个最小的本地模型配置：

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

也可以用交互式 launcher（`uv run python app.py`）通过引导菜单创建和编辑 `config.env`。

## 快速开始

### Agent 工具模式（推荐）

如果你在使用 Codex、Claude Code、Gemini CLI 或类似的 agent 工具，这是最简单的入口。根据任务选择入口：用 **agent-authored** 新建卡片，用 **repo-llm** 复现仓库自己的本地 LLM 流程，用 **study-coach** 针对已有卡片做互动练习。

在 agent 工具中打开仓库根目录，然后调用以下入口：

| 工具 | 入口 |
| --- | --- |
| Codex / OpenCode | `anki-card-repo-llm`、`anki-card-agent-authored` 或 `anki-card-study-coach` |
| Claude Code | `/anki-card-repo-llm`、`/anki-card-agent-authored` 或 `/anki-card-study-coach` |
| Gemini CLI | `/anki-card:repo-llm`、`/anki-card:agent-authored` 或 `/anki-card:study-coach` |

- **agent-authored** — agent 用自身模型直接编写卡片内容。不需要本地 LLM 或 API 密钥。
- **repo-llm** — agent 调用仓库自带的 LLM 流程生成卡片内容。需要先配置 LLM 后端（见[配置](#配置)）。
- **study-coach** — agent 读取你现有的 Anki 卡片和复习记录，进行只读的互动学习；题型会变化，默认优先使用卡片里已有的例句作为语境，并在答案接近时先给分级提示而不是直接揭晓。需要正在运行的 Anki Desktop、已启用的 AnkiConnect，以及一个已有卡片的 deck。

`study-coach` 示例请求：

- `Practice my 5 weakest words in Vocabulary.`
- `Use study-coach on Vocabulary and give hints before revealing answers.`

如果这些 skill 文件是在 agent 会话启动后才加入的，需要重启会话让工具重新扫描项目。

### CLI

适合脚本、shell 自动化和手工命令行导入。需要先配置 LLM 后端。

导入一条：

```bash
uv run anki-vocab --entry 'clarify｜I asked the teacher to clarify the lesson.'
```

通过 stdin 批量导入：

```bash
printf 'clarify｜I asked the teacher to clarify the lesson.\nschedule|We need to change the meeting schedule again.\n' | \
  uv run anki-vocab --stdin --concurrent
```

调整并发参数：

```bash
printf 'clarify｜…\n' | \
  uv run anki-vocab --stdin --concurrent --max-workers 4 --rate-limit 2.0
```

> [!NOTE]
> CLI 模式（`--entry` / `--stdin`）始终以 `llm_only` 运行，忽略 `DATA_SOURCE_STRATEGY`，也不需要 `COLLINS_API_KEY`。

### 文件批量导入

把单词写入 `data/New_Words.txt`，然后运行：

```bash
uv run anki-vocab
```

这个模式会遵守你配置的 `DATA_SOURCE_STRATEGY`。

### 交互式 launcher

```bash
uv run python app.py
```

菜单式本地工作流，提供配置、环境检查和导入功能。

## 输入格式

每行一条，支持以下格式：

| 格式 | 示例 |
| --- | --- |
| `单词<TAB>原句` | `clarify`\t`I asked the teacher to clarify the lesson.` |
| `单词｜原句` | `schedule｜We need to change the meeting schedule again.` |
| `单词\|原句` | `present\|The present plan is easier to explain.` |
| `单词`（无原句） | `implementation` |

提供原句可以显著提升词义和词性判断的准确度。

## 卡片字段

每张导入的笔记包含以下字段：

| 字段 | 说明 |
| --- | --- |
| `Word` | 目标单词 |
| `PartOfSpeech` | 词性（如 verb、noun） |
| `Definition` | 面向初学者的释义 |
| `Example` | 你的原句（如提供） |
| `GeneratedExample` | 新生成的例句 |
| `Pronunciation` | 音标 |
| `AudioFilename` / `AudioSource` | 主音频 |
| `BritishPronunciation` / `BritishAudioFilename` / `BritishAudioSource` | 英式发音 |
| `AmericanPronunciation` / `AmericanAudioFilename` / `AmericanAudioSource` | 美式发音 |

## 数据源策略

`DATA_SOURCE_STRATEGY` 控制文件批量导入和 launcher 模式下的内容来源：

| 值 | 行为 |
| --- | --- |
| `collins_only` | 仅 Collins API |
| `llm_only` | 仅 LLM |
| `collins_first` | 先尝试 Collins，失败后回退到 LLM |
| `llm_first` | 先尝试 LLM，失败后回退到 Collins |

CLI 模式（`--entry` / `--stdin`）始终覆盖为 `llm_only`。

## Prompt 版本

`LLM_PROMPT_VERSION` 控制 LLM 如何判断词义和词性：

| 值 | 行为 |
| --- | --- |
| `revised`（默认） | 以用户原句为词义和词性判断的主要依据。推荐使用。 |
| `baseline` | 较旧的提示词，用于向后兼容。 |

## Provider 配置示例

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

### 使用 gpt-oss 的 LM Studio

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

### 第三方 OpenAI 兼容后端

```env
LLM_PROVIDER=openai_compat
LLM_API_MODE=chat
LLM_BASE_URL=https://your-provider.example.com
LLM_API_KEY=your_provider_key
LLM_MODEL_NAME=your-model-name
```

> [!TIP]
> 对 `lmstudio` 和 `ollama`，`LLM_MODEL_NAME` 留空时会自动使用当前已加载的模型——但前提是恰好只加载了一个模型。零个或多个模型都会报错。

## 音频行为

1. 有词典音频时优先保留。
2. 只有卡片仍然缺少可用音频且 `ENABLE_TTS_FALLBACK=true` 时才会走 TTS。
3. `TTS_OPENAI_COMPAT_BASE_URL` 是推荐的 TTS 路径。
4. `TTS_SERVICE` 是 legacy URL 风格回退（Google / Microsoft / ResponsiveVoice）。

## Anki 提醒

- 运行时 note type 名称基于 `DECK_NAME` 生成，而不是 `MODEL_NAME`。
- `MODEL_NAME` 仍出现在配置中以保持兼容，但运行时创建模板时不使用它。
- 除非你明确要做破坏性迁移，否则不要删除并重建 note type。

## 常见问题

| 问题 | 解决方法 |
| --- | --- |
| 连不上 Anki | 启动 Anki Desktop → 确认 AnkiConnect 已安装 → 检查 `ANKI_CONNECT_HOST` / `ANKI_CONNECT_PORT` → 运行 launcher 的 `9` |
| CLI 提示没有输入 | 使用 `--entry 'word｜sentence'` 或通过 `--stdin` 管道传入 |
| 本地后端找不到模型 | 显式设置 `LLM_MODEL_NAME`，或确保只加载了一个模型 |
| 没有音频 | 检查词典音频是否存在 → 设置 `ENABLE_TTS_FALLBACK=true` → 配置 `TTS_OPENAI_COMPAT_BASE_URL` |

## 给开发者：本地 Anki 验收测试

```bash
uv sync --extra test
```

1. 默认保持 `ANKI_LOCAL_TEST_RUN=false`。
2. 把 `ANKI_LOCAL_TEST_PROFILE` 设为专用测试账户。
3. 把 `ANKI_LOCAL_TEST_DECK` 设为可清空的专用牌组（如 `Vocabulary_LocalSmoke`），确保与主 `DECK_NAME` 不同。
4. 用该测试账户启动 Anki，并开启 AnkiConnect。
5. 运行：

```bash
ANKI_LOCAL_TEST_RUN=1 uv run pytest tests/test_local_anki_import.py -m local_anki -s
```

测试结果快照保存在 `tests/.artifacts/local_anki_import_latest.json`。

## 声明

本仓库主要通过 AI 驱动的方式迭代开发，仓库主人不具备编程经验。请在实际用于学习之前自行审查代码和运行行为。AI 生成的卡片内容应视为学习参考，而非绝对权威——词义准确性很重要时，请提供原句并进行人工确认。

## License

GPL-3.0。详见 [LICENSE](LICENSE)。
