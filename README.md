# 🚀 Anki Vocabulary Automation

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![GitLab issues](https://img.shields.io/badge/GitLab-issues-blue.svg)](https://gitlab.com/jason853/anki-automation/-/issues)
[![GitLab stars](https://img.shields.io/badge/GitLab-stars-blue.svg)](https://gitlab.com/jason853/anki-automation)

> **Language:** [English](README.md) | [中文](README_CN.md)

**Automated vocabulary card creation for Anki using Collins Dictionary API and AI-powered language models.**

Transform your vocabulary learning with intelligent automation that creates comprehensive Anki flashcards from simple word lists.

## 🎯 Project Motivation

I wanted to efficiently collect my personal vocabulary while reading English content and use Anki cards for reinforced learning.

## ✨ Key Features

### 📚 **Comprehensive Vocabulary Data**
- **Multi-source support:** Collins Dictionary API + AI language models
- **Complete information:** Definitions, examples, IPA pronunciation, audio URLs
- **Smart word matching:** Automatically finds standard dictionary forms
- **Dual pronunciation:** British and American pronunciation support

### 🤖 **AI-Powered Flexibility**
- **Universal LLM support:** Compatible with OpenAI, Claude, LM Studio, Ollama, etc.
- **Dynamic model detection:** Automatically detects available models for local LLM services
- **Custom TTS generation:** Creates audio when dictionary audio isn't available

### 🎯 **Anki Integration**
- **Direct import:** Uses AnkiConnect for seamless card creation
- **Duplicate prevention:** Automatically skips existing cards
- **Unified naming:** Card templates use the same name as deck for consistency

## 🚀 Quick Start

### 1. Prerequisites

- **Python 3.8+** 
- **Anki Desktop** (with AnkiConnect plugin)
- **Collins Dictionary API key** (optional) OR **AI service** (OpenAI, Claude, or local LLM)

### 2. Installation

```bash
# Clone the repository
git clone https://gitlab.com/jason853/anki-automation.git
cd anki-vocab-automation

# Run setup script to create virtual environment and install dependencies
python setup.py

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

### 3. Configuration

```bash
# Start the interactive configuration
python app.py

# Follow the setup wizard:
# 1. Choose option 7: Create config file (if needed)
# 2. Choose option 8: Check Anki environment
# 3. Choose option 4: Configure LLM service
# 4. Choose option 3: Configure Collins API (optional)
# 5. Choose option 5: Set data source priority
# 6. Choose option 6: View current configuration
```

### 4. Usage

```bash
# Add words to your list
echo -e "sophisticated\nimplementation\noptimization" > data/New_Words.txt

# Start the application
python app.py

# Choose option 1: Run automation script
```

## 📖 How It Works

### Input Format
Create a simple text file with one word per line:
```
investigation
bidirectional
fundamental
consequence
```

### Processing Flow
1. **Word Analysis:** Determines standard dictionary form
2. **Data Retrieval:** Fetches from Collins API or generates with AI
3. **Audio Processing:** Uses real audio or generates TTS
4. **Card Creation:** Imports directly into Anki

### Generated Cards
Each card includes:
- **Word:** Standard dictionary form
- **Definition:** Clear, learner-friendly explanation
- **Example:** Practical usage in context
- **Pronunciation:** IPA phonetic transcription (British and American)
- **Audio:** Pronunciation audio files
- **Part of Speech:** Grammatical category

## 🛠️ Advanced Configuration

### Data Source Strategies
- `collins_first`: Use Collins API, fallback to AI
- `llm_first`: Use AI, fallback to Collins API
- `collins_only`: Collins API only
- `llm_only`: AI only

### Supported AI Services

#### Cloud Services
- **OpenAI:** GPT-4, GPT-3.5-turbo
- **Anthropic:** Claude 3.5 Sonnet, Claude 3 Opus

#### Local LLM Services
- **LM Studio:** Local models with OpenAI-compatible API
- **Ollama:** Easy local model deployment
- **Text Generation WebUI:** Advanced local model management

#### Configuration Examples
```env
# OpenAI
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL_NAME=gpt-4o-mini
LLM_API_KEY=your_openai_api_key

# Anthropic Claude
LLM_BASE_URL=https://api.anthropic.com/v1
LLM_MODEL_NAME=claude-3-5-sonnet-20241022
LLM_API_KEY=your_anthropic_api_key

# LM Studio (local)
LLM_BASE_URL=http://localhost:1234
LLM_MODEL_NAME=llama3.2-3b-instruct
LLM_API_KEY=not-needed

# Ollama (local)
LLM_BASE_URL=http://localhost:11434
LLM_MODEL_NAME=llama3
LLM_API_KEY=not-needed
```

### TTS Audio Generation
- **Google TTS:** High-quality, reliable
- **Microsoft TTS:** Natural-sounding voices
- **ResponsiveVoice:** Additional voice options

## 📊 Example Output

**Terminal:**
```
Processing: 3/10 - sophisticated
✓ Found in american-learner dictionary
✓ Successfully added card: sophisticated
✓ Audio: Real pronunciation available
```

**Anki Card:**
```
Front: sophisticated
Example: The software uses sophisticated algorithms to analyze data.

Back: 
Definition: having great knowledge or experience; complex and refined
Pronunciation: 
🇬🇧 British: /səˈfɪstɪkeɪtɪd/
🇺🇸 American: /səˈfɪstɪkeɪtɪd/
🔊 [Audio players]
Part of Speech: adjective
```

## 🔧 Troubleshooting

### Common Issues

1. **Anki Connection Failed**
   - Ensure Anki is running
   - Install and enable AnkiConnect plugin
   - Use option 8 to check Anki environment

2. **LLM Service Not Working**
   - Check your API keys and base URLs
   - For local services, ensure they're running
   - Use option 4 to reconfigure LLM service

3. **Template Creation Failed**
   - If template exists but fields are incomplete, manually delete the template in Anki
   - The program will create a new template with the correct fields

4. **Collins API Issues**
   - Verify your API key is valid
   - Check network connectivity
   - Consider switching to LLM-only strategy

### Getting Help

- Check the logs in `anki_vocab_automation.log`
- Use option 6 to view current configuration
- Use option 9 to run comprehensive tests

---

<div align="center">
  <strong>Happy Learning! 📚✨</strong>
  <br><br>
</div> 