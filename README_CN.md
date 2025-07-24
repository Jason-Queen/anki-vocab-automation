# 🚀 Anki 词汇学习自动化工具

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
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
- **通用LLM支持：** 兼容OpenAI、Claude、LM Studio、Ollama等所有OpenAI API兼容服务
- **智能模型检测：** 自动识别模型能力（如thinking标签支持）并优化提示词
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

- **Python 3.8+** 
- **Anki桌面版** (安装AnkiConnect插件)
- **柯林斯词典API密钥** (可选) 或 **AI服务** (OpenAI、Claude或本地LLM)

### 2. 安装

```bash
# 克隆仓库
git clone https://gitlab.com/jason853/anki-automation.git
cd anki-automation

# 运行设置脚本创建虚拟环境并安装依赖
python setup.py

# 激活虚拟环境
# macOS/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate
```

### 3. 配置

```bash
# 启动交互式配置向导
python app.py

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
python app.py

# 选择选项1: 运行自动化脚本
# 选择选项2: 使用并发处理（推荐用于大词汇表）
```

## 📖 工作原理

### 输入格式
创建一个简单的文本文件，每行一个单词：
```
Apple
Cat
Yellow
Train
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
- **例句：** 日常情境，8-15词，简单句式，突出用法
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

#### 云端服务
- **OpenAI:** GPT-4, GPT-4O, GPT-3.5-turbo
- **Anthropic:** Claude 3.5 Sonnet, Claude 3 Opus, Claude 3 Haiku
- **OpenAI O1系列:** O1-preview, O1-mini (支持thinking能力)

#### 本地LLM服务
- **LM Studio:** 本地模型，完全OpenAI兼容
- **Ollama:** 简单的本地模型部署
- **Text Generation WebUI:** 高级本地模型管理
- **任何OpenAI API兼容服务**

#### 智能模型配置
程序自动检测模型能力并优化：
```env
# OpenAI
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL_NAME=gpt-4o-mini
LLM_API_KEY=your_openai_api_key

# Anthropic Claude (支持thinking)
LLM_BASE_URL=https://api.anthropic.com/v1
LLM_MODEL_NAME=claude-3-5-sonnet-20241022
LLM_API_KEY=your_anthropic_api_key

# LM Studio (本地)
LLM_BASE_URL=http://localhost:1234
LLM_MODEL_NAME=qwen2.5-7b-instruct
LLM_API_KEY=not-needed

# Ollama (本地)
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL_NAME=llama3.2
LLM_API_KEY=not-needed
```

### TTS音频生成
- **Google TTS:** 高质量、可靠（默认推荐）
- **Microsoft TTS:** 自然语音合成
- **ResponsiveVoice:** 额外语音选项

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