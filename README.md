# 🚀 Anki Vocabulary Learning Automation Tool

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
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
- **Universal LLM Support:** Compatible with OpenAI, Claude, LM Studio, Ollama, and all OpenAI API-compatible services
- **Intelligent Model Detection:** Automatically detect model capabilities (such as thinking tag support) and optimize prompts
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

- **Python 3.8+**
- **Anki Desktop** (with AnkiConnect plugin installed)
- **Collins Dictionary API Key** (optional) or **AI Service** (OpenAI, Claude, or local LLM)

### 2. Installation

```bash
# Clone repository
git clone https://gitlab.com/jason853/anki-automation.git
cd anki-automation

# Run setup script to create virtual environment and install dependencies
python setup.py

# Activate virtual environment
# macOS/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate
```

### 3. Configuration

```bash
# Start interactive configuration wizard
python app.py

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
python app.py

# Select option 1: Run automation script
# Select option 2: Use concurrent processing (recommended for large vocabularies)
```

## 📖 How It Works

### Input Format
Create a simple text file with one word per line:
```
Apple
Cat
Yellow
Train
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
- **Example:** Daily situations, 8-15 words, simple sentence structure, highlighting usage
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

#### Cloud Services
- **OpenAI:** GPT-4, GPT-4O, GPT-3.5-turbo
- **Anthropic:** Claude 3.5 Sonnet, Claude 3 Opus, Claude 3 Haiku
- **OpenAI O1 Series:** O1-preview, O1-mini (supports thinking capability)

#### Local LLM Services
- **LM Studio:** Local models, fully OpenAI compatible
- **Ollama:** Simple local model deployment
- **Text Generation WebUI:** Advanced local model management
- **Any OpenAI API-compatible service**

#### Intelligent Model Configuration
Program automatically detects model capabilities and optimizes:
```env
# OpenAI
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL_NAME=gpt-4o-mini
LLM_API_KEY=your_openai_api_key

# Anthropic Claude (supports thinking)
LLM_BASE_URL=https://api.anthropic.com/v1
LLM_MODEL_NAME=claude-3-5-sonnet-20241022
LLM_API_KEY=your_anthropic_api_key

# LM Studio (local)
LLM_BASE_URL=http://localhost:1234
LLM_MODEL_NAME=qwen2.5-7b-instruct
LLM_API_KEY=not-needed

# Ollama (local)
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL_NAME=llama3.2
LLM_API_KEY=not-needed
```

### TTS Audio Generation
- **Google TTS:** High quality, reliable (default recommended)
- **Microsoft TTS:** Natural speech synthesis
- **ResponsiveVoice:** Additional voice options

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