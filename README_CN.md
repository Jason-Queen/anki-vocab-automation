# 🚀 Anki 词汇学习自动化工具

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![GitLab issues](https://img.shields.io/badge/GitLab-issues-blue.svg)](https://gitlab.com/jason853/anki-automation/-/issues)
[![GitLab stars](https://img.shields.io/badge/GitLab-stars-blue.svg)](https://gitlab.com/jason853/anki-automation)

> **语言选择:** [English](README.md) | [中文](README_CN.md)

**使用柯林斯词典API和AI语言模型自动创建Anki词汇卡片。**

通过智能自动化工具，批量将单词列表转换为简洁的Anki记忆卡片。

## 🎯 项目初衷

我希望在阅读英语内容时可以及时收集自己专属的生词本，并利用Anki卡牌进行强化学习。

## ✨ 核心功能

### 📚 **全面的词汇数据**
- **多数据源支持：** 柯林斯词典API + AI语言模型
- **基础信息：** 定义、例句、IPA发音、音频URL
- **智能词汇匹配：** 自动查找标准词典形式
- **双重发音支持：** 英式和美式发音

### 🤖 **AI驱动的灵活性**
- **通用LLM支持：** 兼容OpenAI、Claude、LM Studio、Ollama等
- **动态模型检测：** 自动检测本地LLM服务的可用模型
- **自定义TTS生成：** 在词典音频不可用时创建音频

### 🎯 **Anki集成**
- **直接导入：** 使用AnkiConnect无缝创建卡片
- **重复检测：** 自动跳过已存在的卡片
- **统一命名：** 卡片模板与牌组使用相同名称，保持一致性

## 🚀 快速开始

### 1. 环境要求

- **Python 3.8+** 
- **Anki桌面版** (安装AnkiConnect插件)
- **柯林斯词典API密钥** (可选) 或 **AI服务** (OpenAI、Claude或本地LLM)

### 2. 安装

```bash
# 克隆仓库
git clone https://gitlab.com/jason853/anki-automation.git
cd anki-vocab-automation

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
```

## 📖 工作原理

### 输入格式
创建一个简单的文本文件，每行一个单词：
```
investigation
bidirectional
fundamental
consequence
```

### 处理流程
1. **单词分析：** 确定标准词典形式
2. **数据获取：** 从柯林斯API获取或用AI生成
3. **音频处理：** 使用词典的音频或生成TTS
4. **卡片创建：** 直接导入Anki

### 生成的卡片
每张卡片包含：
- **单词：** 标准词典形式
- **定义：** 清晰、适合学习者的解释
- **例句：** 实用的上下文用法
- **发音：** IPA音标转录（英式和美式）
- **音频：** 发音音频文件
- **词性：** 语法分类

## 🛠️ 高级配置

### 数据源策略
- `collins_first`: 使用柯林斯API，备选AI
- `llm_first`: 使用AI，备选柯林斯API
- `collins_only`: 仅柯林斯API
- `llm_only`: 仅AI

### 支持的AI服务

#### 云端服务
- **OpenAI:** GPT-4, GPT-3.5-turbo
- **Anthropic:** Claude 3.5 Sonnet, Claude 3 Opus

#### 本地LLM服务
- **LM Studio:** 本地模型，OpenAI兼容API
- **Ollama:** 简单的本地模型部署
- **Text Generation WebUI:** 高级本地模型管理

#### 配置示例
```env
# OpenAI
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL_NAME=gpt-4o-mini
LLM_API_KEY=your_openai_api_key

# Anthropic Claude
LLM_BASE_URL=https://api.anthropic.com/v1
LLM_MODEL_NAME=claude-3-5-sonnet-20241022
LLM_API_KEY=your_anthropic_api_key

# LM Studio (本地)
LLM_BASE_URL=http://localhost:1234
LLM_MODEL_NAME=llama3.2-3b-instruct
LLM_API_KEY=not-needed

# Ollama (本地)
LLM_BASE_URL=http://localhost:11434
LLM_MODEL_NAME=llama3
LLM_API_KEY=not-needed
```

### TTS音频生成
- **Google TTS:** 高质量、可靠
- **Microsoft TTS:** 自然语音
- **ResponsiveVoice:** 额外语音选项

## 📊 输出示例

**终端显示：**
```
Processing: 3/10 - sophisticated
✓ Found in american-learner dictionary
✓ Successfully added card: sophisticated
✓ Audio: Real pronunciation available
```

**Anki卡片：**
```
正面: sophisticated
例句: The software uses sophisticated algorithms to analyze data.

背面: 
定义: having great knowledge or experience; complex and refined
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

3. **模板创建失败**
   - 如果模板存在但字段不完整，在Anki中手动删除该模板
   - 程序将创建具有正确字段的新模板

4. **柯林斯API问题**
   - 验证API密钥是否有效
   - 检查网络连接
   - 考虑切换到仅LLM策略

### 获取帮助

- 查看 `anki_vocab_automation.log` 中的日志
- 使用选项6查看当前配置
- 使用选项9运行综合测试

---

<div align="center">
  <strong>学习愉快！ 📚✨</strong>
  <br><br>
</div>