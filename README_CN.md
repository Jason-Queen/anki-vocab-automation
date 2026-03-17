# 🚀 Anki 词汇学习自动化工具

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![GitLab issues](https://img.shields.io/badge/GitLab-issues-blue.svg)](https://gitlab.com/jason853/anki-automation/-/issues)
[![GitLab stars](https://img.shields.io/badge/GitLab-stars-blue.svg)](https://gitlab.com/jason853/anki-automation)

> **语言选择:** [English](README.md) | [中文](README_CN.md)

**使用柯林斯词典API和AI语言模型自动创建专为英语学习者优化的Anki词汇卡片。**

通过智能自动化工具，批量将单词列表转换为学习者友好的、简洁高效的Anki记忆卡片。

请注意，本程序完全由AI开发，未经人类开发者的验证，请谨慎使用。

## 🎯 项目初衷

我希望在阅读英语内容时可以及时收集自己专属的生词本，并利用Anki卡牌进行强化学习。程序专门为中级英语学习者设计，提供易于理解的定义和实用的例句。

## ✨ 核心功能

### 📚 **学习者友好的词汇内容**
- **优化的定义：** 使用简单常见词汇解释，避免循环定义，15词以内的简洁表达
- **实用例句：** 8-15词长度，日常情境，简单句式结构，突出目标词汇用法
- **多数据源支持：** 柯林斯词典API + AI语言模型智能生成
- **双重发音支持：** 英式和美式IPA音标及音频

### 🤖 **AI驱动的智能生成**
- **按提供商适配的 LLM 支持：** OpenAI 和 Anthropic 走官方 SDK，LM Studio、Ollama 和第三方兼容后端走兼容接口
- **可选接口模式：** 支持 Responses API、Chat Completions API 和 Anthropic Messages API
- **学习导向优化：** AI专门针对英语学习者需求调教，生成易懂内容
- **自定义TTS生成：** 在词典音频不可用时智能创建发音音频

### 🚀 **高性能处理**
- **并发处理：** 多线程批量处理，显著提升大词汇表处理速度
- **智能重试：** 自动重试机制，确保处理成功率
- **速率限制：** 可配置的API调用频率控制，避免超出服务限制
- **进度追踪：** 实时显示处理进度和成功率统计

### 🔒 **安全性增强**
- **输入验证：** 全面的用户输入安全验证，防止注入攻击
- **安全日志：** 自动过滤敏感信息的安全日志记录系统
- **依赖安全：** 使用最新版本依赖，修复已知安全漏洞(CVE)

### 🎯 **Anki完美集成**
- **直接导入：** 使用AnkiConnect无缝创建卡片，无需手动导入
- **媒体管理：** 完美的Anki媒体库集成，音频文件自动管理
- **重复检测：** 智能跳过已存在的卡片，避免重复创建
- **模板一致性：** 卡片模板与牌组使用相同名称，保持整洁

## 🚀 快速开始

### 1. 环境要求

- **Python 3.9+**
- **uv**（[安装指南](https://docs.astral.sh/uv/getting-started/installation/)）
- **Anki桌面版** (安装AnkiConnect插件)
- **柯林斯词典API密钥** (可选) 或 **AI服务** (OpenAI、Claude或本地LLM)

### 2. 安装

```bash
# 克隆仓库
git clone https://gitlab.com/jason853/anki-automation.git
cd anki-automation

# 安装运行依赖
uv sync

# 如果需要跑测试或代码检查
uv sync --extra dev --extra test
```

### 3. 配置

```bash
# 启动交互式配置向导
uv run python app.py

# 按照设置向导操作：
# 1. 选择选项7: 创建配置文件（如需要）
# 2. 选择选项8: 检查Anki环境
# 3. 选择选项4: 配置LLM服务
# 4. 选择选项3: 配置柯林斯API（可选）
# 5. 选择选项5: 设置数据源优先级
# 6. 选择选项6: 查看当前配置
```

### 4. 使用方法

```bash
# 添加单词到列表
echo -e "sophisticated\nimplementation\noptimization" > data/New_Words.txt

# 启动应用程序
uv run python app.py

# 选择选项1: 运行自动化脚本
# 选择选项2: 使用并发处理（推荐用于大词汇表）
```

### 5. 本地 Anki 验收测试

当你想在每次开发开始时第一时间看到当前导入效果，可以先跑这个本地验收测试。

如果还没安装测试依赖，先执行一次 `uv sync --extra test`。

1. 在 `config.env` 里保持 `ANKI_LOCAL_TEST_RUN=false`。
2. 把 `ANKI_LOCAL_TEST_PROFILE` 设成专用的 Anki 测试账户。
3. 把 `ANKI_LOCAL_TEST_DECK` 设成可清空的专用牌组，例如 `Vocabulary_LocalSmoke`。这个测试会先删除该牌组里的旧样例，再导入 1 张新卡。
4. 可选：设置 `ANKI_LOCAL_TEST_SOURCE_EXAMPLE`，用于验证新的“正面原句 / 背面新例句”流程。
5. 用该测试账户启动 Anki，并确认 AnkiConnect 已启用。
6. 运行：

```bash
ANKI_LOCAL_TEST_RUN=1 uv run pytest tests/test_local_anki_import.py -m local_anki -s
```

测试会把最新一次导入的字段和媒体快照写到 `tests/.artifacts/local_anki_import_latest.json`，方便你快速比对效果。

### 6. 开发检查

如果你是在维护这个项目，先安装维护者依赖：

```bash
uv sync --extra dev --extra test
```

然后用 `uv` 运行常用检查：

```bash
uv run pytest tests/ -v --cov=src/anki_vocab_automation --cov-report=xml
uv run flake8 src/
uv run --with safety safety check --json > safety-report.json
uv run --with bandit bandit -r src/ -f json -o bandit-report.json
```

## 📖 工作原理

### 输入格式
推荐格式：`单词<TAB>你看到这个单词时的原句`。

旧的“每行只写一个单词”仍然兼容，但如果同时提供原句，生成的释义通常会更准确。

示例：
```
clarify	I asked the teacher to clarify the lesson.
fundamental	The report explains the fundamental problem in the design.
schedule | We need to change the meeting schedule again.
implementation
```

### 智能处理流程
1. **输入验证：** 安全验证和清理用户输入
2. **单词分析：** 自动确定标准词典形式
3. **内容生成：** 从柯林斯API获取或用AI生成学习者友好的内容
4. **音频处理：** 优先使用词典音频，备选智能TTS生成
5. **并发优化：** 多线程并行处理，提升效率
6. **卡片创建：** 直接导入Anki，完美媒体集成

### 生成的学习者友好卡片
每张卡片专为英语学习者优化：
- **单词：** 标准词典形式
- **定义：** 使用简单词汇，避免循环，15词以内
- **正面例句：** 优先显示用户提供的原句
- **背面例句：** 额外显示一个新生成的例句，并且该例句会明确包含目标词
- **发音：** 清晰的IPA音标（英式和美式）
- **音频：** 高质量发音音频文件
- **词性：** 简洁的语法分类

## 🛠️ 高级配置

### 数据源策略
- `collins_first`: 使用柯林斯API，备选AI（质量优先）
- `llm_first`: 使用AI，备选柯林斯API（速度优先）
- `collins_only`: 仅柯林斯API
- `llm_only`: 仅AI（适合离线使用）

### 并发处理配置
```env
# 并发处理设置
MAX_WORKERS=4              # 最大并发线程数
RATE_LIMIT_PER_SECOND=2.0  # API调用频率限制
RETRY_ATTEMPTS=2           # 失败重试次数
TIMEOUT_PER_WORD=60        # 单词处理超时时间
```

**⚠️ 重要提醒：并发处理可能导致TTS文件下载失败**
- 当并发速度过快时，TTS服务可能无法及时响应，导致音频文件下载失败
- 如果遇到TTS下载问题，建议使用单线程模式（选项1）确保稳定性
- 单线程模式虽然速度较慢，但能确保所有音频文件正确下载

### 支持的AI服务

#### 官方云端提供商
- **OpenAI：** 使用官方 OpenAI SDK；`gpt-oss` 模型走 Responses API，其他模型走 Chat Completions + JSON Schema
- **Anthropic：** 使用官方 Anthropic SDK，走 Messages API

#### 本地与自建后端
- **LM Studio：** 自动把 `gpt-oss` 模型路由到 Responses API，把其他模型路由到 Chat Completions + JSON Schema
- **Ollama：** 自动把 `gpt-oss` 模型路由到 Responses API，把其他模型路由到 Chat Completions + JSON Schema
- **第三方 OpenAI 兼容后端：** 先支持 Chat Completions 兼容模式，并在可用时使用 JSON Schema

#### 推荐配置示例
```env
# OpenAI 官方
LLM_PROVIDER=openai
LLM_API_MODE=chat
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL_NAME=gpt-4o-mini
LLM_API_KEY=your_openai_api_key

# OpenAI / LM Studio 的 gpt-oss
LLM_PROVIDER=lmstudio
LLM_API_MODE=responses
LLM_BASE_URL=http://localhost:1234
LLM_MODEL_NAME=openai/gpt-oss-20b
LLM_API_KEY=not-needed
LLM_GPT_OSS_REASONING_EFFORT=medium

# Anthropic 官方
LLM_PROVIDER=anthropic
LLM_API_MODE=messages
LLM_BASE_URL=https://api.anthropic.com
LLM_MODEL_NAME=claude-3-5-sonnet-20241022
LLM_API_KEY=your_anthropic_api_key

# LM Studio 自动路由
LLM_PROVIDER=lmstudio
LLM_API_MODE=auto
LLM_BASE_URL=http://localhost:1234
# 留空时自动使用当前已加载模型
LLM_MODEL_NAME=
LLM_API_KEY=not-needed

# LM Studio 显式 Chat API
LLM_PROVIDER=lmstudio
LLM_API_MODE=chat
LLM_BASE_URL=http://localhost:1234
# 如果你不想使用“当前已加载模型”，也可以显式指定模型名
LLM_MODEL_NAME=qwen/qwen3.5-9b
LLM_API_KEY=not-needed

# Ollama 自动路由
LLM_PROVIDER=ollama
LLM_API_MODE=auto
LLM_BASE_URL=http://localhost:11434
# 留空时自动使用当前正在运行的模型
LLM_MODEL_NAME=
LLM_API_KEY=not-needed

# 第三方 OpenAI 兼容后端
LLM_PROVIDER=openai_compat
LLM_API_MODE=chat
LLM_BASE_URL=https://your-provider.example.com
LLM_MODEL_NAME=your-model-name
LLM_API_KEY=your_provider_key
```

对于 LM Studio 和 Ollama：
- 当 `LLM_MODEL_NAME` 留空时，程序会自动使用当前已加载/正在运行的模型。
- 如果本地后端里同时加载了多个模型，程序会停止并要求你显式设置 `LLM_MODEL_NAME`。
- 如果当前没有已加载/正在运行的模型，程序会直接报错并停止生成，不再猜测默认模型。
- 如果你手动填写了 `LLM_MODEL_NAME`，程序会优先使用该值，但现在会先检查该模型是否真实存在。
- 当选中的模型属于 `gpt-oss` 家族时，程序会使用 Responses API，并默认 `LLM_GPT_OSS_REASONING_EFFORT=medium`。
- 其他本地模型会使用 Chat Completions + JSON Schema，减少只输出 reasoning、不输出最终 JSON 的情况。

维护说明：
- 当前这一轮本地模型 benchmark 和 prompt 对比的阶段性结论见 [docs/llm-benchmark-phase-summary-2026-03.md](docs/llm-benchmark-phase-summary-2026-03.md)。

### TTS音频生成
- **OpenAI 兼容远程 TTS：** 新配置的推荐主路径，可接入本地或远程的 `/v1/audio/speech` 服务，例如 `Qwen3-TTS-MLX-Server`
- **Google TTS / Microsoft TTS / ResponsiveVoice：** 只有在你显式开启时才会使用的 legacy URL 兼容回退

OpenAI 兼容远程 TTS 配置示例：

```env
ENABLE_TTS_FALLBACK=true
TTS_OPENAI_COMPAT_BASE_URL=http://127.0.0.1:8000
TTS_OPENAI_COMPAT_API_KEY=not-needed
TTS_OPENAI_COMPAT_MODEL=mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-bf16
TTS_OPENAI_COMPAT_RESPONSE_FORMAT=wav
```

说明：
- 只要配置了 `TTS_OPENAI_COMPAT_BASE_URL`，程序就会把 `openai_compat` 当作主 TTS 路径
- `TTS_SERVICE` 现在只表示“可选的 legacy URL 兼容回退”；如果你完全不想碰这些脆弱的公开 URL，就保持留空
- 如果不设置 `TTS_OPENAI_COMPAT_MODEL`，程序会先读取服务 `/health` 返回的 `default_model`
- 默认会按 `en-GB` / `en-US` 自动生成英式或美式英语口音指令
- 如果你改用 `CustomVoice` 模型，需要额外设置 `TTS_OPENAI_COMPAT_VOICE`
- `Base` 声音克隆模型需要 `ref_audio`，不适合作为当前的通用单词读音备选
- 卡片背面会显示音频来源，明确区分 `Dictionary` 和 `TTS`

如果你确实想显式启用 legacy 兼容回退，可以这样写：

```env
TTS_SERVICE=google
```

### 数据源与音频回退决策表

先记住一个原则：
- `DATA_SOURCE_STRATEGY` 决定“词卡内容从哪里来”
- 音频回退规则只在“当前卡片缺少音频”时才生效

内容来源决策：

| 配置 | 词卡内容默认顺序 |
| --- | --- |
| `collins_only` | `Collins` |
| `collins_first` | `Collins -> LLM` |
| `llm_only` | `LLM` |
| `llm_first` | `LLM -> Collins` |

单词音频决策：

| 条件 | 单词音频默认顺序 |
| --- | --- |
| 卡片已有词典音频 | `Dictionary` |
| 卡片缺少音频，且配置了 `TTS_OPENAI_COMPAT_BASE_URL` | `openai_compat TTS -> 可选 legacy TTS_SERVICE` |
| 卡片缺少音频，且只配置了 `TTS_SERVICE` | `legacy TTS_SERVICE` |
| 卡片缺少音频，且两者都没配置 | `不做 TTS 回退` |

常见组合示例：

| 配置 | 实际常见路径 |
| --- | --- |
| `collins_first` + 本地 TTS | `Collins 内容/词典音频 -> 缺失时 openai_compat TTS -> 可选 legacy TTS` |
| `llm_only` + 本地 TTS | `LLM 内容 -> openai_compat TTS -> 可选 legacy TTS` |
| `llm_first` + 本地 TTS | `LLM 内容 -> 若 LLM 失败则 Collins -> 缺失时 openai_compat TTS -> 可选 legacy TTS` |

## 📊 输出示例

**终端显示（并发处理）：**
```
开始批量处理 10 个单词 (并发度: 4)
✅ [3/10] sophisticated (2.1s)
✅ [4/10] implementation (1.8s)  
❌ [5/10] xyz - 输入验证失败: 单词包含不允许的字符 (0.1s)
进度: 5/10 (成功: 4, 失败: 1)
批量处理完成: 总耗时 15.2s, 平均 1.5s/词, 成功 9/10
```

**Anki卡片（学习者优化）：**
```
正面: sophisticated
例句: This software uses sophisticated methods to solve problems.

背面: 
定义: having great knowledge or experience; advanced and complex
发音: 
🇬🇧 英式: /səˈfɪstɪkeɪtɪd/
🇺🇸 美式: /səˈfɪstɪkeɪtɪd/
🔊 [发音播放器]
词性: adjective
```

## 🔧 故障排除

### 常见问题

1. **Anki连接失败**
   - 确保Anki正在运行
   - 安装并启用AnkiConnect插件
   - 使用选项8检查Anki环境

2. **LLM服务不工作**
   - 检查API密钥和基础URL
   - 对于本地服务，确保它们正在运行
   - 使用选项4重新配置LLM服务
   - 查看安全日志了解详细错误信息

3. **并发处理问题**
   - 降低MAX_WORKERS数值（建议2-4）
   - 增加RATE_LIMIT_PER_SECOND间隔
   - 检查网络稳定性和API限制
   - **TTS下载失败：** 如果遇到音频文件下载失败，建议切换到单线程模式（选项1）

4. **模板创建失败**
   - 如果模板存在但字段不完整，在Anki中手动删除该模板
   - 程序将创建具有正确字段的新模板

5. **安全警告**
   - 程序会自动验证和清理输入
   - 查看日志文件了解被过滤的内容
   - 确保单词文件来源可信

### 获取帮助

- 查看 `anki_vocab_automation.log` 中的安全日志
- 使用选项6查看当前配置
- 使用选项9运行综合测试
- 检查依赖版本是否为最新安全版本

### 性能优化建议

- **小词汇表（<50词）：** 使用默认单线程处理
- **中等词汇表（50-200词）：** 启用并发处理，设置max_workers=4
- **大词汇表（>200词）：** 使用并发处理，适当调整速率限制
- **本地LLM：** 可以提高并发度和降低速率限制
- **⚠️ TTS稳定性优先：** 如果音频文件下载失败，建议使用单线程模式确保所有音频正确下载

---

<div align="center">
  <strong>本程序完全由Cursor程序以及背后的LLM AI驱动生成，请注意AI可能犯错！ 📚✨</strong>
  <br><br>
  <em>现在支持并发处理、安全验证、智能优化等高级特性</em>
</div>
