"""
配置文件
Configuration settings for Anki Vocabulary Automation
"""

import os
from pathlib import Path

from .llm_client import (
    DEFAULT_GPT_OSS_REASONING_EFFORT,
    SUPPORTED_GPT_OSS_REASONING_EFFORTS,
    SUPPORTED_LLM_API_MODES,
    SUPPORTED_LLM_PROVIDERS,
    resolve_llm_runtime_config,
)
from .tts_generator import LEGACY_URL_TTS_SERVICES, PRIMARY_TTS_SERVICE, SUPPORTED_TTS_SERVICES

# 加载环境变量
# 首先尝试加载项目根目录下的config.env文件
project_root = Path(__file__).parent.parent.parent
config_env_path = project_root / "config.env"

try:
    from dotenv import load_dotenv

    if config_env_path.exists():
        load_dotenv(config_env_path)
    else:
        # 如果没有config.env，尝试加载.env文件
        load_dotenv(project_root / ".env")
except ImportError:
    # 如果python-dotenv未安装，使用系统环境变量
    print("警告: python-dotenv未安装，无法加载.env文件，将使用系统环境变量")
    print("请运行: pip install python-dotenv")

# 项目根目录
ROOT_DIR = project_root


# 辅助函数：从环境变量获取布尔值
def get_bool_env(key, default=False):
    """从环境变量获取布尔值"""
    value = os.getenv(key, str(default)).lower()
    return value in ("true", "1", "yes", "on")


# 辅助函数：从环境变量获取数字值
def get_int_env(key, default=None):
    """从环境变量获取整数值"""
    value = os.getenv(key)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


# 辅助函数：从环境变量获取浮点数值
def get_float_env(key, default=None):
    """从环境变量获取浮点数值"""
    value = os.getenv(key)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


# Collins Dictionary API配置
# Collins API密钥
_collins_api_key = os.getenv("COLLINS_API_KEY", "")
# 检查是否是占位符
COLLINS_API_KEY = _collins_api_key if _collins_api_key not in ["", "your_collins_api_key_here"] else ""
COLLINS_API_BASE_URL = "https://api.collinsdictionary.com/api/v1"

# 词典优先级配置（支持双重发音）
# english: 提供英式音标（有重音符号）
# learner词典: 作为fallback，同时提供英式和美式发音
DICTIONARIES = [
    "english",  # 主要词典：英式音标（有重音符号）
    "english-learner",  # 英式学习者词典（fallback）
    "american-learner",  # 美式学习者词典（fallback）
    "collins",  # 通用词典（最后fallback）
]

# 双重发音配置
PRONUNCIATION_SOURCES = {
    "british": ["english", "english-learner"],  # 英式发音来源
    "american": ["american-learner"],  # 美式发音来源
}

# Anki Connect配置
ANKI_CONNECT_HOST = os.getenv("ANKI_CONNECT_HOST", "localhost")
ANKI_CONNECT_PORT = get_int_env("ANKI_CONNECT_PORT", 8765)

# Anki设置
DECK_NAME = os.getenv("DECK_NAME", "Vocabulary")
MODEL_NAME = os.getenv("MODEL_NAME", "Vocabulary")

# 文件路径
DATA_DIR = ROOT_DIR / "data"
WORD_LIST_FILE = DATA_DIR / "New_Words.txt"
LOG_FILE = ROOT_DIR / "anki_vocab_automation.log"

# API设置
REQUEST_DELAY = get_int_env("REQUEST_DELAY", 1)  # 请求间隔（秒）
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3

# HTML解析器设置
HEADWORD_SELECTORS = [".headword", ".hw", "h1.headword", "span.headword", ".entry-title", "h1"]

DEFINITION_SELECTORS = [".def", ".definition", ".sense .def", ".collins-definition", ".meaning"]

EXAMPLE_SELECTORS = [".example", ".collins-example", ".quote", ".cit", ".usage-example"]

PRONUNCIATION_SELECTORS = [".pron", ".pronunciation", ".ipa", ".phonetic"]

PART_OF_SPEECH_SELECTORS = [".pos", ".part-of-speech", ".grammar", ".wordtype"]

# 标签设置
TAGS = ["vocabulary", "collins", "automated"]

# LLM配置
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "auto").strip().lower() or "auto"
LLM_API_MODE = os.getenv("LLM_API_MODE", "auto").strip().lower() or "auto"
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:1234").strip()
LLM_API_KEY = os.getenv("LLM_API_KEY", "not-needed")
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "").strip()
LLM_TIMEOUT = get_int_env("LLM_TIMEOUT", 60)
ENABLE_LLM_FALLBACK = get_bool_env("ENABLE_LLM_FALLBACK", True)

# TTS音频生成配置
ENABLE_TTS_FALLBACK = get_bool_env("ENABLE_TTS_FALLBACK", True)
TTS_SERVICE = os.getenv("TTS_SERVICE", "").strip().lower()
TTS_VOICE = os.getenv("TTS_VOICE", "en-US")
TTS_OPENAI_COMPAT_BASE_URL = os.getenv("TTS_OPENAI_COMPAT_BASE_URL", "").strip()
TTS_OPENAI_COMPAT_API_KEY = os.getenv("TTS_OPENAI_COMPAT_API_KEY", "not-needed")
TTS_OPENAI_COMPAT_MODEL = os.getenv("TTS_OPENAI_COMPAT_MODEL", "").strip()
TTS_OPENAI_COMPAT_VOICE = os.getenv("TTS_OPENAI_COMPAT_VOICE", "").strip()
TTS_OPENAI_COMPAT_INSTRUCTIONS = os.getenv("TTS_OPENAI_COMPAT_INSTRUCTIONS", "").strip()
TTS_OPENAI_COMPAT_RESPONSE_FORMAT = os.getenv("TTS_OPENAI_COMPAT_RESPONSE_FORMAT", "wav").strip().lower() or "wav"
TTS_OPENAI_COMPAT_TIMEOUT = get_int_env("TTS_OPENAI_COMPAT_TIMEOUT", 60)


def build_tts_service_priority(tts_service=None, openai_compat_base_url=None):
    """Return TTS services in preferred fallback order."""
    normalized_service = (TTS_SERVICE if tts_service is None else tts_service or "").strip().lower()
    normalized_openai_compat_base_url = (
        TTS_OPENAI_COMPAT_BASE_URL if openai_compat_base_url is None else openai_compat_base_url or ""
    ).strip()
    services = []

    if normalized_openai_compat_base_url:
        services.append(PRIMARY_TTS_SERVICE)

    if normalized_service in LEGACY_URL_TTS_SERVICES and normalized_service not in services:
        services.append(normalized_service)
    elif (
        normalized_service == PRIMARY_TTS_SERVICE
        and normalized_openai_compat_base_url
        and PRIMARY_TTS_SERVICE not in services
    ):
        services.append(PRIMARY_TTS_SERVICE)

    return services


TTS_SERVICE_PRIORITY = tuple(build_tts_service_priority())

# 数据源优先级设置
DATA_SOURCE_STRATEGY = os.getenv("DATA_SOURCE_STRATEGY", "collins_first")

# 高级LLM配置
LLM_AUTO_DETECT_CAPABILITIES = get_bool_env("LLM_AUTO_DETECT_CAPABILITIES", True)
LLM_FORCE_THINKING_MODE = None
_thinking_mode_env = os.getenv("LLM_FORCE_THINKING_MODE", "").lower()
if _thinking_mode_env in ("true", "1", "yes", "on"):
    LLM_FORCE_THINKING_MODE = True
elif _thinking_mode_env in ("false", "0", "no", "off"):
    LLM_FORCE_THINKING_MODE = False

LLM_GPT_OSS_REASONING_EFFORT = (
    os.getenv("LLM_GPT_OSS_REASONING_EFFORT", DEFAULT_GPT_OSS_REASONING_EFFORT).strip().lower()
    or DEFAULT_GPT_OSS_REASONING_EFFORT
)
LLM_CUSTOM_TEMPERATURE = get_float_env("LLM_CUSTOM_TEMPERATURE")
LLM_CUSTOM_MAX_TOKENS = get_int_env("LLM_CUSTOM_MAX_TOKENS")

# 日志设置
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"

# 用户代理
USER_AGENT = "Anki Vocabulary Automation/1.0"


# 配置验证函数
def validate_config():
    """验证配置是否有效"""
    errors = []

    # 验证数据源策略
    valid_strategies = ["collins_only", "llm_only", "collins_first", "llm_first"]
    if DATA_SOURCE_STRATEGY not in valid_strategies:
        errors.append(f"无效的数据源策略: {DATA_SOURCE_STRATEGY}，有效选项: {valid_strategies}")

    # 验证Collins API密钥
    if DATA_SOURCE_STRATEGY in ["collins_only", "collins_first"] and not COLLINS_API_KEY:
        errors.append("Collins API密钥未配置，但数据源策略需要使用Collins API")

    valid_tts_services = [""] + list(SUPPORTED_TTS_SERVICES)
    if TTS_SERVICE not in valid_tts_services:
        errors.append(f"无效的TTS_SERVICE: {TTS_SERVICE}，有效选项: {valid_tts_services}")

    valid_tts_formats = ["wav", "mp3", "flac", "ogg", "opus"]
    if TTS_OPENAI_COMPAT_RESPONSE_FORMAT not in valid_tts_formats:
        errors.append(
            f"无效的TTS_OPENAI_COMPAT_RESPONSE_FORMAT: {TTS_OPENAI_COMPAT_RESPONSE_FORMAT}，有效选项: {valid_tts_formats}"
        )

    if ENABLE_TTS_FALLBACK and TTS_SERVICE == PRIMARY_TTS_SERVICE and not TTS_OPENAI_COMPAT_BASE_URL:
        errors.append("启用 openai_compat TTS 时必须配置 TTS_OPENAI_COMPAT_BASE_URL")

    if LLM_PROVIDER not in SUPPORTED_LLM_PROVIDERS:
        errors.append(f"无效的LLM_PROVIDER: {LLM_PROVIDER}，有效选项: {SUPPORTED_LLM_PROVIDERS}")

    if LLM_API_MODE not in SUPPORTED_LLM_API_MODES:
        errors.append(f"无效的LLM_API_MODE: {LLM_API_MODE}，有效选项: {SUPPORTED_LLM_API_MODES}")

    if LLM_GPT_OSS_REASONING_EFFORT not in SUPPORTED_GPT_OSS_REASONING_EFFORTS:
        errors.append(
            "无效的LLM_GPT_OSS_REASONING_EFFORT: "
            f"{LLM_GPT_OSS_REASONING_EFFORT}，有效选项: {SUPPORTED_GPT_OSS_REASONING_EFFORTS}"
        )

    try:
        llm_runtime = resolve_llm_runtime_config(LLM_PROVIDER, LLM_API_MODE, LLM_BASE_URL)
    except ValueError as exc:
        errors.append(f"LLM配置无效: {exc}")
        llm_runtime = None

    # 验证LLM配置
    if DATA_SOURCE_STRATEGY in ["llm_only", "llm_first"]:
        resolved_provider = llm_runtime.provider if llm_runtime else LLM_PROVIDER

        if resolved_provider == "openai" and not LLM_API_KEY.startswith("sk-"):
            errors.append("OpenAI provider 需要有效的 LLM_API_KEY")

        if resolved_provider == "anthropic" and not LLM_API_KEY:
            errors.append("Anthropic provider 需要有效的 LLM_API_KEY")

        if resolved_provider == "openai_compat" and not LLM_BASE_URL:
            errors.append("openai_compat provider 需要显式配置 LLM_BASE_URL")

        if resolved_provider == "anthropic" and LLM_API_MODE not in ("auto", "messages"):
            errors.append("Anthropic provider 仅支持 messages 模式")

        if resolved_provider == "openai_compat" and LLM_API_MODE == "messages":
            errors.append("openai_compat provider 不支持 messages 模式")

        if resolved_provider in ("openai", "anthropic", "openai_compat") and not LLM_MODEL_NAME:
            errors.append(
                "当前 LLM provider 需要显式配置 LLM_MODEL_NAME；"
                "只有 LM Studio / Ollama 支持在留空时自动使用当前已加载模型"
            )

    return errors


# 配置显示函数
def display_config():
    """显示当前配置"""
    resolved_runtime = resolve_llm_runtime_config(LLM_PROVIDER, LLM_API_MODE, LLM_BASE_URL)
    print("=" * 50)
    print("当前配置:")
    print("=" * 50)
    print(f"Collins API密钥: {'已配置' if COLLINS_API_KEY else '未配置'}")
    print(f"LLM Provider: {LLM_PROVIDER} -> {resolved_runtime.provider}")
    print(f"LLM API Mode: {LLM_API_MODE} -> {resolved_runtime.api_mode}")
    print(f"LLM Base URL: {LLM_BASE_URL} -> {resolved_runtime.base_url}")
    if LLM_MODEL_NAME:
        print(f"LLM Model: {LLM_MODEL_NAME}")
    elif resolved_runtime.provider in ("lmstudio", "ollama"):
        print("LLM Model: (自动使用当前已加载模型)")
    else:
        print("LLM Model: (未设置)")
    print(f"GPT-OSS Reasoning Effort: {LLM_GPT_OSS_REASONING_EFFORT}")
    print(f"数据源策略: {DATA_SOURCE_STRATEGY}")
    print(f"启用LLM备选: {ENABLE_LLM_FALLBACK}")
    if TTS_OPENAI_COMPAT_BASE_URL:
        print("TTS主服务: openai_compat")
        legacy_fallback = TTS_SERVICE if TTS_SERVICE in LEGACY_URL_TTS_SERVICES else "(未启用)"
        print(f"TTS Legacy回退: {legacy_fallback}")
    else:
        print(f"TTS主服务: {TTS_SERVICE or '(未配置)'}")
    print(f"TTS优先级: {list(TTS_SERVICE_PRIORITY)}")
    if PRIMARY_TTS_SERVICE in TTS_SERVICE_PRIORITY:
        print(f"TTS Base URL: {TTS_OPENAI_COMPAT_BASE_URL}")
        print(f"TTS Model: {TTS_OPENAI_COMPAT_MODEL or '(使用服务默认模型)'}")
        print(f"TTS Voice: {TTS_OPENAI_COMPAT_VOICE or '(未配置)'}")
        print(f"TTS Audio Format: {TTS_OPENAI_COMPAT_RESPONSE_FORMAT}")
    print(f"Anki Connect: {ANKI_CONNECT_HOST}:{ANKI_CONNECT_PORT}")
    print(f"卡牌模板: {MODEL_NAME}")
    print(f"目标牌组: {DECK_NAME}")
    print("=" * 50)


# 在模块导入时验证配置
if __name__ == "__main__":
    errors = validate_config()
    if errors:
        print("配置错误:")
        for error in errors:
            print(f"❌ {error}")
    else:
        print("✅ 配置验证通过")

    display_config()
