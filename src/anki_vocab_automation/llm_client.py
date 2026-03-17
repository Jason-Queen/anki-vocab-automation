"""
Provider-aware LLM client for vocabulary generation.
"""

import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlsplit, urlunsplit

import requests
from anthropic import Anthropic
from openai import OpenAI

from .input_validator import sanitize_word_input, validate_word_input
from .models import VocabularyCard
from .secure_logger import sanitize_for_log
from .tts_generator import PRIMARY_TTS_SERVICE, TTSGenerator

logger = logging.getLogger(__name__)

DEFAULT_TEMPERATURE = 0.3
DEFAULT_MAX_OUTPUT_TOKENS = 4000
DEFAULT_MAX_GENERATION_ATTEMPTS = 2
DEFAULT_GPT_OSS_REASONING_EFFORT = "medium"
DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"
DEFAULT_ANTHROPIC_BASE_URL = "https://api.anthropic.com"
DEFAULT_LM_STUDIO_BASE_URL = "http://localhost:1234"
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"

SUPPORTED_LLM_PROVIDERS = (
    "auto",
    "openai",
    "anthropic",
    "lmstudio",
    "ollama",
    "openai_compat",
)
SUPPORTED_LLM_API_MODES = ("auto", "responses", "chat", "messages")
SUPPORTED_GPT_OSS_REASONING_EFFORTS = ("minimal", "low", "medium", "high")
SUPPORTED_PROMPT_VERSIONS = ("baseline", "revised")
DEFAULT_PROMPT_VERSION = "baseline"

SYSTEM_PROMPT = (
    "You are a comprehensive English dictionary. Always respond with valid JSON "
    "containing accurate vocabulary information. Be precise and educational."
)
REASONING_ITEM_TYPES = {"reasoning", "reasoning_text", "thinking", "thinking_text"}
TEXT_ITEM_TYPES = {"text", "output_text"}
VOCABULARY_JSON_SCHEMA = {
    "name": "vocabulary_card",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "word": {
                "type": "string",
                "description": "Dictionary headword for the target sense in the learner sentence.",
            },
            "definition": {
                "type": "string",
                "description": "Short learner-friendly definition that does not repeat the target word.",
            },
            "generated_example": {
                "type": "string",
                "description": "A new example sentence, different from the learner sentence.",
            },
            "pronunciation": {
                "type": "string",
                "description": "Main IPA pronunciation, usually British.",
            },
            "british_pronunciation": {
                "type": "string",
                "description": "British IPA pronunciation.",
            },
            "american_pronunciation": {
                "type": "string",
                "description": "American IPA pronunciation.",
            },
            "audio_url": {
                "type": "string",
                "description": "Must be an empty string because audio is handled separately.",
            },
            "british_audio_url": {
                "type": "string",
                "description": "Must be an empty string because audio is handled separately.",
            },
            "american_audio_url": {
                "type": "string",
                "description": "Must be an empty string because audio is handled separately.",
            },
            "part_of_speech": {
                "type": "string",
                "description": "Concise part of speech such as noun, verb, adjective, or adverb.",
            },
        },
        "required": [
            "word",
            "definition",
            "generated_example",
            "pronunciation",
            "british_pronunciation",
            "american_pronunciation",
            "audio_url",
            "british_audio_url",
            "american_audio_url",
            "part_of_speech",
        ],
        "additionalProperties": False,
    },
}
TTS_SOURCE_LABELS = {
    "openai_compat": "TTS",
    "google": "Google TTS",
    "microsoft": "Microsoft TTS",
    "responsivevoice": "ResponsiveVoice TTS",
}
LOCAL_RUNTIME_DISPLAY_NAMES = {
    "lmstudio": "LM Studio",
    "ollama": "Ollama",
}


@dataclass
class LLMRuntimeConfig:
    """Resolved runtime configuration for the active LLM backend."""

    provider: str
    api_mode: str
    base_url: str


def normalize_llm_provider(provider: Optional[str]) -> str:
    """Normalize user-provided provider names to canonical values."""
    value = (provider or "auto").strip().lower()
    aliases = {
        "claude": "anthropic",
        "anthropic_claude": "anthropic",
        "openai-compatible": "openai_compat",
        "openai_compatible": "openai_compat",
        "generic": "openai_compat",
        "generic_chat": "openai_compat",
    }
    normalized = aliases.get(value, value or "auto")
    if normalized not in SUPPORTED_LLM_PROVIDERS:
        return "auto"
    return normalized


def normalize_llm_api_mode(api_mode: Optional[str]) -> str:
    """Normalize API mode names."""
    value = (api_mode or "auto").strip().lower()
    aliases = {
        "response": "responses",
        "chat_completions": "chat",
        "chat-completions": "chat",
        "message": "messages",
    }
    normalized = aliases.get(value, value or "auto")
    if normalized not in SUPPORTED_LLM_API_MODES:
        return "auto"
    return normalized


def is_gpt_oss_model(model_name: Optional[str]) -> bool:
    """Return True when the selected model belongs to the gpt-oss family."""
    return "gpt-oss" in (model_name or "").strip().lower()


def _set_url_path(base_url: str, path: str) -> str:
    """Return a URL with a normalized path while preserving scheme and host."""
    parts = urlsplit(base_url.strip())
    normalized_path = "/" + path.strip("/")
    return urlunsplit((parts.scheme, parts.netloc, normalized_path, parts.query, parts.fragment))


def normalize_openai_compat_base_url(base_url: Optional[str], default_base_url: str) -> str:
    """Ensure OpenAI-compatible backends always point at their /v1 API root."""
    candidate = (base_url or default_base_url or "").strip().rstrip("/")
    if not candidate:
        raise ValueError("OpenAI-compatible backends require a base URL")

    parts = urlsplit(candidate)
    path = parts.path.rstrip("/")
    if path.endswith("/v1"):
        return urlunsplit((parts.scheme, parts.netloc, path or "/v1", parts.query, parts.fragment))
    if not path:
        return _set_url_path(candidate, "v1")
    return _set_url_path(candidate, "{0}/v1".format(path.lstrip("/")))


def normalize_anthropic_base_url(base_url: Optional[str]) -> str:
    """Anthropic SDK expects the API host root, not a manually appended /v1 path."""
    candidate = (base_url or DEFAULT_ANTHROPIC_BASE_URL).strip().rstrip("/")
    if not candidate:
        return DEFAULT_ANTHROPIC_BASE_URL

    parts = urlsplit(candidate)
    path = parts.path.rstrip("/")
    if path.endswith("/v1"):
        path = path[:-3].rstrip("/")

    return urlunsplit((parts.scheme, parts.netloc, path, parts.query, parts.fragment))


def resolve_llm_runtime_config(
    provider: Optional[str], api_mode: Optional[str], base_url: Optional[str]
) -> LLMRuntimeConfig:
    """Resolve provider, base URL and API mode from user config."""
    normalized_provider = normalize_llm_provider(provider)

    if normalized_provider == "auto":
        base_url_text = (base_url or "").strip().lower()
        if "api.anthropic.com" in base_url_text:
            normalized_provider = "anthropic"
        elif "api.openai.com" in base_url_text:
            normalized_provider = "openai"
        elif "localhost:1234" in base_url_text or "127.0.0.1:1234" in base_url_text or "lmstudio" in base_url_text:
            normalized_provider = "lmstudio"
        elif "localhost:11434" in base_url_text or "127.0.0.1:11434" in base_url_text or "ollama" in base_url_text:
            normalized_provider = "ollama"
        elif base_url_text:
            normalized_provider = "openai_compat"
        else:
            normalized_provider = "lmstudio"

    normalized_api_mode = normalize_llm_api_mode(api_mode)
    if normalized_api_mode == "auto":
        if normalized_provider == "anthropic":
            normalized_api_mode = "messages"
        else:
            normalized_api_mode = "chat"

    if normalized_provider == "anthropic":
        resolved_base_url = normalize_anthropic_base_url(base_url)
    elif normalized_provider == "openai":
        resolved_base_url = normalize_openai_compat_base_url(base_url, DEFAULT_OPENAI_BASE_URL)
    elif normalized_provider == "lmstudio":
        resolved_base_url = normalize_openai_compat_base_url(base_url, DEFAULT_LM_STUDIO_BASE_URL)
    elif normalized_provider == "ollama":
        resolved_base_url = normalize_openai_compat_base_url(base_url, DEFAULT_OLLAMA_BASE_URL)
    else:
        resolved_base_url = normalize_openai_compat_base_url(base_url, DEFAULT_OPENAI_BASE_URL)

    return LLMRuntimeConfig(
        provider=normalized_provider,
        api_mode=normalized_api_mode,
        base_url=resolved_base_url,
    )


def _get_backend_root_url(base_url: str) -> str:
    """Remove a trailing /v1 suffix so native backend endpoints can be addressed."""
    candidate = (base_url or "").strip().rstrip("/")
    if candidate.endswith("/v1"):
        return candidate[:-3].rstrip("/")
    return candidate


def _build_backend_native_endpoint(runtime: LLMRuntimeConfig, path: str) -> str:
    """Build provider-native endpoints for backend metadata requests."""
    root_url = _get_backend_root_url(runtime.base_url)

    if runtime.provider == "lmstudio":
        return "{0}/api/v1/{1}".format(root_url, path.strip("/"))
    if runtime.provider == "ollama":
        return "{0}/api/{1}".format(root_url, path.strip("/"))

    raise ValueError("Native endpoint lookup is only supported for local backends")


def _request_backend_json(runtime: LLMRuntimeConfig, path: str, api_key: str, timeout: int) -> Dict[str, Any]:
    """Fetch JSON from a provider-native backend endpoint."""
    endpoint = _build_backend_native_endpoint(runtime, path)
    headers = {}
    if api_key and api_key != "not-needed":
        headers["Authorization"] = "Bearer {0}".format(api_key)

    response = requests.get(endpoint, headers=headers, timeout=timeout)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("Unexpected backend response payload from {0}".format(endpoint))
    return payload


def list_loaded_models_for_backend(
    provider: Optional[str],
    base_url: Optional[str],
    api_key: str = "not-needed",
    timeout: int = 10,
) -> List[str]:
    """List models that are currently loaded in LM Studio or running in Ollama."""
    runtime = resolve_llm_runtime_config(provider, "auto", base_url)

    if runtime.provider == "lmstudio":
        payload = _request_backend_json(runtime, "models", api_key, timeout)
        loaded_models = []
        for item in payload.get("models", []):
            if not isinstance(item, dict) or item.get("type") != "llm":
                continue
            if item.get("loaded_instances"):
                model_name = str(item.get("key", "")).strip()
                if model_name:
                    loaded_models.append(model_name)
        return loaded_models

    if runtime.provider == "ollama":
        payload = _request_backend_json(runtime, "ps", api_key, timeout)
        running_models = []
        for item in payload.get("models", []):
            if not isinstance(item, dict):
                continue
            model_name = str(item.get("model") or item.get("name") or "").strip()
            if model_name:
                running_models.append(model_name)
        return running_models

    return []


def list_models_for_backend(
    provider: Optional[str],
    base_url: Optional[str],
    api_key: str = "not-needed",
    timeout: int = 10,
) -> List[str]:
    """List models for the selected backend using the matching SDK."""
    runtime = resolve_llm_runtime_config(provider, "auto", base_url)

    if runtime.provider == "anthropic":
        client = Anthropic(
            api_key=api_key,
            base_url=runtime.base_url,
            timeout=timeout,
        )
        models = client.models.list(limit=100)
        return [model.id for model in models if getattr(model, "id", "").strip()]

    client = OpenAI(
        api_key=api_key or "not-needed",
        base_url=runtime.base_url,
        timeout=timeout,
    )
    models = client.models.list()
    return [model.id for model in models if getattr(model, "id", "").strip()]


class LLMClient:
    """Vocabulary-generation client with provider-aware transport selection."""

    def __init__(
        self,
        base_url: str = DEFAULT_LM_STUDIO_BASE_URL,
        api_key: str = "not-needed",
        model_name: str = "",
        timeout: int = 60,
        enable_tts: bool = True,
        tts_service: str = PRIMARY_TTS_SERVICE,
        tts_service_order: Optional[List[str]] = None,
        tts_voice: str = "en-US",
        tts_base_url: str = "",
        tts_api_key: str = "not-needed",
        tts_model_name: str = "",
        tts_openai_compat_voice: str = "",
        tts_openai_compat_instructions: str = "",
        tts_response_format: str = "wav",
        tts_timeout: int = 60,
        provider: str = "auto",
        api_mode: str = "auto",
        temperature: Optional[float] = None,
        max_output_tokens: Optional[int] = None,
        gpt_oss_reasoning_effort: str = DEFAULT_GPT_OSS_REASONING_EFFORT,
        prompt_version: str = DEFAULT_PROMPT_VERSION,
    ):
        self.api_key = api_key
        self.model_name = model_name
        self.timeout = timeout
        self.enable_tts = enable_tts
        self.tts_model_name = (tts_model_name or "").strip()
        self.temperature = temperature if temperature is not None else DEFAULT_TEMPERATURE
        if max_output_tokens is None:
            self.max_output_tokens = DEFAULT_MAX_OUTPUT_TOKENS
        elif max_output_tokens <= 0:
            self.max_output_tokens = None
        else:
            self.max_output_tokens = max_output_tokens
        self.gpt_oss_reasoning_effort = self._normalize_gpt_oss_reasoning_effort(gpt_oss_reasoning_effort)
        self.prompt_version = self._normalize_prompt_version(prompt_version)
        self.runtime = resolve_llm_runtime_config(provider, api_mode, base_url)
        self.tts_service_order = self._normalize_tts_service_order(tts_service_order, tts_service)
        self._resolved_generation_model_name: Optional[str] = None

        if enable_tts:
            self.tts_generators = self._build_tts_generators(
                tts_voice=tts_voice,
                tts_base_url=tts_base_url,
                tts_api_key=tts_api_key,
                tts_model_name=tts_model_name,
                tts_openai_compat_voice=tts_openai_compat_voice,
                tts_openai_compat_instructions=tts_openai_compat_instructions,
                tts_response_format=tts_response_format,
                tts_timeout=tts_timeout,
            )
            self.tts_generator = self.tts_generators[0] if self.tts_generators else None
        else:
            self.tts_generators = []
            self.tts_generator = None

        self._openai_client: Optional[OpenAI] = None
        self._anthropic_client: Optional[Anthropic] = None

    def _normalize_gpt_oss_reasoning_effort(self, effort: Optional[str]) -> str:
        normalized = (effort or DEFAULT_GPT_OSS_REASONING_EFFORT).strip().lower()
        if normalized not in SUPPORTED_GPT_OSS_REASONING_EFFORTS:
            return DEFAULT_GPT_OSS_REASONING_EFFORT
        return normalized

    def _normalize_prompt_version(self, prompt_version: Optional[str]) -> str:
        normalized = (prompt_version or DEFAULT_PROMPT_VERSION).strip().lower()
        if normalized not in SUPPORTED_PROMPT_VERSIONS:
            return DEFAULT_PROMPT_VERSION
        return normalized

    def _normalize_tts_service_order(
        self,
        tts_service_order: Optional[List[str]],
        tts_service: str,
    ) -> List[str]:
        """Deduplicate and normalize configured TTS fallback order."""
        configured_order = tts_service_order or [tts_service]
        normalized_order = []

        for service_name in configured_order:
            normalized = (service_name or "").strip().lower()
            if normalized and normalized not in normalized_order:
                normalized_order.append(normalized)

        return normalized_order

    def _build_tts_generators(
        self,
        tts_voice: str,
        tts_base_url: str,
        tts_api_key: str,
        tts_model_name: str,
        tts_openai_compat_voice: str,
        tts_openai_compat_instructions: str,
        tts_response_format: str,
        tts_timeout: int,
    ) -> List[TTSGenerator]:
        """Create the configured ordered list of TTS generators."""
        generators = []

        for service_name in self.tts_service_order:
            generators.append(
                TTSGenerator(
                    service=service_name,
                    voice=tts_voice,
                    base_url=tts_base_url,
                    api_key=tts_api_key,
                    model_name=tts_model_name,
                    openai_compat_voice=tts_openai_compat_voice,
                    openai_compat_instructions=tts_openai_compat_instructions,
                    response_format=tts_response_format,
                    timeout=tts_timeout,
                )
            )

        return generators

    @property
    def resolved_provider(self) -> str:
        """Expose the resolved provider for logging and diagnostics."""
        return self.runtime.provider

    @property
    def resolved_api_mode(self) -> str:
        """Expose the resolved API mode for logging and diagnostics."""
        if self._resolved_generation_model_name:
            return self._resolve_generation_api_mode(self._resolved_generation_model_name)
        return self.runtime.api_mode

    @property
    def base_url(self) -> str:
        """Expose the normalized base URL."""
        return self.runtime.base_url

    def _get_openai_client(self) -> OpenAI:
        if self._openai_client is None:
            self._openai_client = OpenAI(
                api_key=self.api_key or "not-needed",
                base_url=self.runtime.base_url,
                timeout=self.timeout,
            )
        return self._openai_client

    def _get_anthropic_client(self) -> Anthropic:
        if self._anthropic_client is None:
            self._anthropic_client = Anthropic(
                api_key=self.api_key,
                base_url=self.runtime.base_url,
                timeout=self.timeout,
            )
        return self._anthropic_client

    def check_connection(self) -> bool:
        """Try listing models to confirm the backend is reachable."""
        try:
            if not self.get_available_models():
                return False
            self._resolve_generation_model_name()
            return True
        except Exception as exc:  # pragma: no cover - exercised in integration
            logger.warning("LLM backend connection check failed: %s", exc)
            return False

    def get_available_models(self) -> List[str]:
        """Fetch model ids using the matching backend."""
        try:
            models = list_models_for_backend(
                provider=self.runtime.provider,
                base_url=self.runtime.base_url,
                api_key=self.api_key,
                timeout=self.timeout,
            )
            logger.info("可用模型: %s", models)
            return models
        except Exception as exc:
            logger.error("获取模型列表失败: %s", exc)
            return []

    def _resolve_generation_model_name(self) -> str:
        """Resolve the model name used for generation, including local loaded-model defaults."""
        if self._resolved_generation_model_name:
            return self._resolved_generation_model_name

        configured_model_name = (self.model_name or "").strip()

        if self.runtime.provider in ("lmstudio", "ollama"):
            provider_label = LOCAL_RUNTIME_DISPLAY_NAMES.get(self.runtime.provider, self.runtime.provider)
            try:
                loaded_models = list_loaded_models_for_backend(
                    provider=self.runtime.provider,
                    base_url=self.runtime.base_url,
                    api_key=self.api_key,
                    timeout=self.timeout,
                )
            except Exception as exc:
                raise ValueError(
                    "无法读取 {0} 当前已加载模型，请确认本地服务正在运行: {1}".format(provider_label, exc)
                ) from exc

            if not loaded_models:
                raise ValueError(
                    "{0} 当前没有已加载模型。请先在 {0} 中加载一个模型，"
                    "或在确认已加载后再继续生成。".format(provider_label)
                )

            if configured_model_name:
                available_models = self.get_available_models()
                if not available_models:
                    raise ValueError("无法验证 {0} 的可用模型列表，请确认服务可用后重试。".format(provider_label))
                if configured_model_name not in available_models:
                    raise ValueError(
                        "配置的 LLM_MODEL_NAME 不存在: {0}。{1} 当前可用模型: {2}".format(
                            configured_model_name,
                            provider_label,
                            ", ".join(available_models),
                        )
                    )
                self._resolved_generation_model_name = configured_model_name
                return self._resolved_generation_model_name

            unique_loaded_models = list(dict.fromkeys(loaded_models))
            if len(unique_loaded_models) > 1:
                raise ValueError(
                    "{0} 当前加载了多个模型: {1}。请显式设置 LLM_MODEL_NAME。".format(
                        provider_label,
                        ", ".join(unique_loaded_models),
                    )
                )

            self._resolved_generation_model_name = unique_loaded_models[0]
            return self._resolved_generation_model_name

        if not configured_model_name:
            raise ValueError("当前 provider={0} 必须显式设置 LLM_MODEL_NAME。".format(self.runtime.provider))

        self._resolved_generation_model_name = configured_model_name
        return self._resolved_generation_model_name

    def _resolve_generation_api_mode(self, model_name: str) -> str:
        """Choose the transport that best matches the selected model family."""
        if self.runtime.provider == "anthropic":
            return "messages"
        if is_gpt_oss_model(model_name):
            return "responses"
        return "chat"

    def generate_vocabulary_card(self, word: str, source_example: str = "") -> Optional[VocabularyCard]:
        """Generate a vocabulary card using the configured LLM backend."""
        is_valid, error_msg = validate_word_input(word)
        if not is_valid:
            logger.warning("无效的单词输入: %s - %s", error_msg, word)
            return None

        word = sanitize_word_input(word)
        if not word.strip():
            logger.warning("搜索词为空")
            return None

        selected_model_name = self._resolve_generation_model_name()
        selected_api_mode = self._resolve_generation_api_mode(selected_model_name)

        logger.info(
            "正在使用LLM生成单词数据: %s (provider=%s, mode=%s, model=%s)",
            word,
            self.runtime.provider,
            selected_api_mode,
            selected_model_name,
        )

        for attempt in range(1, DEFAULT_MAX_GENERATION_ATTEMPTS + 1):
            structured_output = selected_api_mode == "chat"
            prompt = self._create_vocabulary_prompt(
                word,
                source_example,
                strict_example_requirement=attempt > 1,
                structured_output=structured_output,
            )
            try:
                response_text = self._generate_text(prompt)
                if not response_text:
                    continue

                card = self._parse_llm_response(response_text, word, source_example)
                if card is not None:
                    return card

                logger.warning(
                    "LLM响应未通过校验，准备重试: %s (attempt=%s/%s)",
                    word,
                    attempt,
                    DEFAULT_MAX_GENERATION_ATTEMPTS,
                )
            except Exception as exc:
                logger.error("LLM请求失败: %s", exc)

        return None

    def _generate_text(self, prompt: str) -> str:
        model_name = self._resolve_generation_model_name()
        api_mode = self._resolve_generation_api_mode(model_name)

        if self.runtime.provider == "anthropic":
            return self._call_anthropic_messages(prompt, model_name)

        if api_mode == "chat":
            return self._call_openai_chat(prompt, model_name)

        return self._call_openai_responses(prompt, model_name)

    def _call_openai_responses(self, prompt: str, model_name: str) -> str:
        request_kwargs = {
            "model": model_name,
            "instructions": SYSTEM_PROMPT,
            "input": prompt,
            "temperature": self.temperature,
        }
        if self.max_output_tokens is not None:
            request_kwargs["max_output_tokens"] = self.max_output_tokens
        if is_gpt_oss_model(model_name):
            request_kwargs["reasoning"] = {"effort": self.gpt_oss_reasoning_effort}

        response = self._get_openai_client().responses.create(**request_kwargs)
        content = self._extract_responses_text(response)
        if not content:
            raise ValueError("Responses API returned no text content")
        logger.debug("LLM响应: %s...", sanitize_for_log(content[:100]))
        return content

    def _call_openai_chat(self, prompt: str, model_name: str) -> str:
        request_kwargs = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "temperature": self.temperature,
            "response_format": {
                "type": "json_schema",
                "json_schema": VOCABULARY_JSON_SCHEMA,
            },
        }
        if self.max_output_tokens is not None:
            request_kwargs["max_tokens"] = self.max_output_tokens

        response = self._get_openai_client().chat.completions.create(**request_kwargs)

        choices = getattr(response, "choices", None) or []
        if not choices:
            raise ValueError("Chat Completions API returned no choices")

        content = self._extract_chat_message_text(getattr(choices[0].message, "content", None))
        if not content:
            raise ValueError("Chat Completions API returned empty content")
        logger.debug("LLM响应: %s...", sanitize_for_log(content[:100]))
        return content

    def _call_anthropic_messages(self, prompt: str, model_name: str) -> str:
        request_kwargs = {
            "model": model_name,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
            "max_tokens": self.max_output_tokens or DEFAULT_MAX_OUTPUT_TOKENS,
        }
        response = self._get_anthropic_client().messages.create(**request_kwargs)
        content = self._extract_anthropic_text(getattr(response, "content", None))
        if not content:
            raise ValueError("Anthropic Messages API returned no text content")
        logger.debug("LLM响应: %s...", sanitize_for_log(content[:100]))
        return content

    def _create_vocabulary_prompt(
        self,
        word: str,
        source_example: str = "",
        strict_example_requirement: bool = False,
        structured_output: bool = False,
    ) -> str:
        prompt_inputs = {
            "word": word,
            "context_block": self._build_prompt_context_block(word, source_example),
            "strict_block": self._build_prompt_strict_block(word, strict_example_requirement),
            "format_instructions": self._build_prompt_format_instructions(structured_output),
        }

        if self.prompt_version == "revised":
            return self._create_revised_vocabulary_prompt(**prompt_inputs)

        return self._create_baseline_vocabulary_prompt(**prompt_inputs)

    def _build_prompt_context_block(self, word: str, source_example: str) -> str:
        if not source_example:
            return ""

        return """

Context sentence from the learner:
"{source_example}"

Use this sentence only to choose the correct sense.
- Do not copy it into the generated example.
- The generated example should be a new sentence different from the learner sentence.
- The generated example MUST still include the target word "{word}".
""".format(source_example=source_example, word=word)

    def _build_prompt_strict_block(self, word: str, strict_example_requirement: bool) -> str:
        if not strict_example_requirement:
            return ""

        return """

Critical requirement:
- The generated example MUST contain the exact target word "{word}" in the sentence.
- If the example does not contain "{word}", the answer is wrong.
""".format(word=word)

    def _build_prompt_format_instructions(self, structured_output: bool) -> str:
        if structured_output:
            return (
                "The response schema already defines the fields.\n"
                "- Return only the schema-compliant JSON object\n"
                "- Do not add markdown, explanations, or extra commentary\n"
            )

        return (
            "Please respond with this exact JSON structure:\n\n"
            "{{\n"
            '    "word": "dictionary headword for the target sense",\n'
            '    "definition": "clear primary definition",\n'
            '    "generated_example": "new practical example sentence using the word",\n'
            '    "pronunciation": "IPA phonetic transcription (British, e.g., /ˈeksəmpl/)",\n'
            '    "british_pronunciation": "British IPA pronunciation (e.g., /ˈeksəmpl/)",\n'
            '    "american_pronunciation": "American IPA pronunciation (e.g., /ɪgˈzæmpl/)",\n'
            '    "audio_url": "",\n'
            '    "british_audio_url": "",\n'
            '    "american_audio_url": "",\n'
            '    "part_of_speech": "noun/verb/adjective/adverb/etc."\n'
            "}}\n\n"
            "- Response must be valid JSON only\n"
        )

    def _create_baseline_vocabulary_prompt(
        self,
        word: str,
        context_block: str,
        strict_block: str,
        format_instructions: str,
    ) -> str:
        return (
            'You are a comprehensive English dictionary. For the word "{word}", provide vocabulary '
            "information in JSON format.{context_block}{strict_block}\n\n"
            "{format_instructions}"
            "Requirements:\n"
            "- Choose the headword that matches the target sense and part of speech in the learner sentence\n"
            '- Lemmatize inflected verbs when appropriate (e.g., "running" -> "run")\n'
            "- Keep adjective/adverb headwords unchanged when that surface form is the dictionary entry for the sense "
            '(e.g., "defining" as an adjective stays "defining")\n'
            "- Use simple, common words that intermediate English learners can understand\n"
            "- Avoid using the target word itself or its variations in the definition\n"
            "- Keep definitions concise (under 15 words when possible)\n"
            "- Focus on the most common meaning if the word has multiple senses\n"
            "- Make the generated example sentence 8-15 words long with everyday, practical situations\n"
            '- The generated example MUST contain the target word "{word}" or the normalized headword '
            'you return in "word"\n'
            "- Use proper IPA notation for both British and American pronunciations\n"
            "- Keep part of speech concise (noun, verb, adjective, adverb, etc.)\n"
            '- All fields must be filled except audio URLs (MUST be empty strings "")\n'
            '- NEVER generate audio URLs - leave all audio_url fields as empty strings ""\n'
            "- Focus on accuracy and educational value\n\n"
            'Now provide the JSON for "{word}".'
        ).format(
            word=word,
            context_block=context_block,
            strict_block=strict_block,
            format_instructions=format_instructions,
        )

    def _create_revised_vocabulary_prompt(
        self,
        word: str,
        context_block: str,
        strict_block: str,
        format_instructions: str,
    ) -> str:
        return (
            'You are preparing one beginner-friendly English vocabulary card for the target word "{word}".'
            "{context_block}{strict_block}\n\n"
            "{format_instructions}"
            "Decision rules:\n"
            "- First identify how the target word functions in the learner sentence:\n"
            "  noun, verb, adjective, adverb, etc.\n"
            "- Choose the sense that best matches the learner sentence,\n"
            "  even if another sense is more common overall.\n"
            "- Return the dictionary headword for that exact sense and part of speech.\n"
            '- Lemmatize only when the learner sentence clearly uses an inflected verb form\n'
            '  (for example, "running" -> "run").\n'
            '- Keep the surface form unchanged when it is the correct adjective,\n'
            '  adverb, or noun headword for that sense '
            '(for example, "defining capability" -> word "defining", part_of_speech "adjective").\n'
            '- Do not switch an adjective or noun use back into a related verb\n'
            "  just because the spelling looks similar.\n"
            "- The definition must describe the same sense used in the learner sentence.\n"
            '- Do not fall back to the "state the meaning" sense unless the learner sentence\n'
            "  is actually about explaining a word or phrase.\n"
            "- Use short, common words suitable for beginner or lower-intermediate learners.\n"
            "- Avoid using the target word, close variants, or dictionary jargon in the definition.\n"
            "- Keep the definition concise, usually 6-14 words.\n"
            "- Prefer one clear sense over a broad or merged definition.\n"
            "- The generated example must keep the same part of speech\n"
            "  and same sense as the learner sentence.\n"
            '- The generated example MUST contain the target surface form "{word}"\n'
            "  or the headword you return if you lemmatize a verb.\n"
            "- Make the generated example new, natural, everyday, and 8-15 words long.\n"
            "- Use proper IPA notation for both British and American pronunciations.\n"
            '- All audio_url fields must be empty strings "". Never invent audio URLs.\n'
            "Quick self-check before answering:\n"
            '- If the learner sentence uses an adjective such as "defining" before a noun,\n'
            '  keep it adjective; do not answer with the verb "define".\n'
            '- If the learner sentence uses a noun such as "conduct"\n'
            '  or an adjective such as "present", keep that part of speech in the answer.\n'
            '- If the learner sentence uses a verb inflection such as "running"\n'
            '  in an action sentence, return the base verb "run".\n\n'
            'Now provide the JSON for "{word}".'
        ).format(
            word=word,
            context_block=context_block,
            strict_block=strict_block,
            format_instructions=format_instructions,
        )

    def _to_plain_data(self, payload: Any) -> Any:
        if payload is None:
            return None
        model_dump = getattr(payload, "model_dump", None)
        if callable(model_dump):
            return model_dump()
        if isinstance(payload, list):
            return [self._to_plain_data(item) for item in payload]
        if isinstance(payload, dict):
            return {key: self._to_plain_data(value) for key, value in payload.items()}
        if hasattr(payload, "__dict__"):
            return {key: self._to_plain_data(value) for key, value in vars(payload).items() if not key.startswith("_")}
        return payload

    def _extract_non_reasoning_texts(self, payload: Any) -> List[str]:
        plain_payload = self._to_plain_data(payload)
        if plain_payload is None:
            return []
        if isinstance(plain_payload, str):
            return [plain_payload.strip()] if plain_payload.strip() else []
        if isinstance(plain_payload, list):
            texts = []
            for item in plain_payload:
                texts.extend(self._extract_non_reasoning_texts(item))
            return texts
        if not isinstance(plain_payload, dict):
            return []

        item_type = str(plain_payload.get("type", "")).strip().lower()
        if item_type in REASONING_ITEM_TYPES:
            return []

        if item_type in TEXT_ITEM_TYPES:
            text_value = plain_payload.get("text")
            if isinstance(text_value, str) and text_value.strip():
                return [text_value.strip()]

        if "content" in plain_payload:
            return self._extract_non_reasoning_texts(plain_payload.get("content"))

        text_value = plain_payload.get("text")
        if isinstance(text_value, str) and text_value.strip():
            return [text_value.strip()]

        return []

    def _extract_responses_text(self, payload: Any) -> str:
        plain_payload = self._to_plain_data(payload)
        if isinstance(plain_payload, dict):
            output_text = plain_payload.get("output_text")
            if isinstance(output_text, str) and output_text.strip():
                return output_text.strip()

            output_items = plain_payload.get("output")
            if isinstance(output_items, list):
                texts = self._extract_non_reasoning_texts(output_items)
                return "\n".join(texts).strip()

        return ""

    def _extract_chat_message_text(self, payload: Any) -> str:
        return "\n".join(self._extract_non_reasoning_texts(payload)).strip()

    def _extract_anthropic_text(self, payload: Any) -> str:
        return "\n".join(self._extract_non_reasoning_texts(payload)).strip()

    def populate_missing_audio(self, card: VocabularyCard) -> VocabularyCard:
        """Fill missing audio references using the configured TTS fallback order."""
        if not self.enable_tts or not self.tts_generators:
            return card

        british_pronunciation = card.british_pronunciation or card.pronunciation
        american_pronunciation = card.american_pronunciation or ""

        if not card.british_audio_filename and card.audio_filename:
            card.british_audio_filename = card.audio_filename
        if not card.british_audio_source and card.audio_source:
            card.british_audio_source = card.audio_source

        if not card.british_audio_filename and british_pronunciation:
            british_audio, british_source = self._generate_tts_audio_reference(
                card.word,
                british_pronunciation,
                "en-GB",
            )
            if british_audio:
                card.british_audio_filename = british_audio
                card.british_audio_source = british_source

        if not card.audio_filename and card.british_audio_filename:
            card.audio_filename = card.british_audio_filename
        if not card.audio_source and card.british_audio_source:
            card.audio_source = card.british_audio_source

        if not card.american_audio_filename and american_pronunciation:
            american_audio, american_source = self._generate_tts_audio_reference(
                card.word,
                american_pronunciation,
                "en-US",
            )
            if american_audio:
                card.american_audio_filename = american_audio
                card.american_audio_source = american_source

        return card

    def _generate_tts_audio_reference(
        self,
        word: str,
        pronunciation: str,
        language: str,
    ) -> Tuple[str, str]:
        """Try configured TTS services in order and return the first successful reference."""
        for generator in self.tts_generators:
            audio_reference = generator.generate_audio_reference(word, pronunciation, language)
            if audio_reference:
                return audio_reference, self._resolve_tts_source_label(generator)

        return "", ""

    def _resolve_tts_source_label(self, generator: TTSGenerator) -> str:
        """Return a user-facing label for the TTS source."""
        get_source_label = getattr(generator, "get_source_label", None)
        if callable(get_source_label):
            label = get_source_label()
            if isinstance(label, str) and label.strip():
                return label.strip()

        if generator.service == "openai_compat" and self.tts_model_name:
            return self.tts_model_name

        return TTS_SOURCE_LABELS.get(generator.service, "TTS")

    def _parse_llm_response(
        self,
        response: str,
        original_word: str,
        source_example: str = "",
    ) -> Optional[VocabularyCard]:
        """Parse LLM JSON output into a VocabularyCard."""
        try:
            response = self._normalize_response_text(response)

            for json_str in self._extract_json_candidates(response):
                try:
                    data = json.loads(json_str)
                except json.JSONDecodeError:
                    continue

                if not self._validate_json_data(data):
                    continue

                generated_example = data.get("generated_example", "") or data.get("example", "")
                front_example = source_example or generated_example

                audio_url = self._clean_audio_url(data.get("audio_url", ""))
                british_audio_url = self._clean_audio_url(data.get("british_audio_url", ""))
                american_audio_url = self._clean_audio_url(data.get("american_audio_url", ""))

                card = VocabularyCard(
                    word=data.get("word", original_word),
                    definition=data.get("definition", ""),
                    example=front_example,
                    generated_example=generated_example,
                    pronunciation=data.get("pronunciation", ""),
                    audio_filename=audio_url,
                    part_of_speech=data.get("part_of_speech", ""),
                    original_word=original_word,
                    british_pronunciation=data.get("british_pronunciation", data.get("pronunciation", "")),
                    american_pronunciation=data.get("american_pronunciation", ""),
                    british_audio_filename=british_audio_url,
                    american_audio_filename=american_audio_url,
                    source="llm",
                )

                if not self._generated_example_mentions_target(
                    card.generated_example,
                    original_word,
                    card.word,
                ):
                    logger.warning(
                        "生成例句未包含目标词，丢弃该响应: %s -> %s",
                        original_word,
                        sanitize_for_log(card.generated_example),
                    )
                    continue

                self.populate_missing_audio(card)
                logger.info("成功生成词汇卡片（双重发音）: %s -> %s", original_word, card.word)
                return card

            logger.error("响应中未找到有效的JSON")
            logger.debug("原始响应: %s...", sanitize_for_log(response[:500]))
            return None
        except Exception as exc:
            logger.error("LLM响应解析失败: %s", exc)
            logger.debug("原始响应: %s...", sanitize_for_log(response[:500]))
            return None

    def _normalize_response_text(self, response: str) -> str:
        cleaned = response.strip()

        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]

        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]

        if "<think>" in cleaned:
            think_end = cleaned.find("</think>")
            if think_end != -1:
                cleaned = cleaned[think_end + 8 :].strip()

        return cleaned.strip()

    def _extract_json_candidates(self, response: str) -> List[str]:
        candidates = []

        if response:
            candidates.append(response)

        start = response.find("{")
        end = response.rfind("}") + 1
        if start != -1 and end > start:
            candidate = response[start:end]
            if candidate not in candidates:
                candidates.append(candidate)

        pattern = r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}"
        for match in re.findall(pattern, response, re.DOTALL):
            if match not in candidates:
                candidates.append(match)

        return candidates

    def _validate_json_data(self, data: Dict[str, Any]) -> bool:
        required_fields = (
            "word",
            "definition",
            "pronunciation",
            "british_pronunciation",
            "american_pronunciation",
            "part_of_speech",
        )
        if not all(isinstance(data.get(field), str) and data.get(field, "").strip() for field in required_fields):
            return False

        generated_example = data.get("generated_example", "") or data.get("example", "")
        return isinstance(generated_example, str) and generated_example.strip() != ""

    def _clean_audio_url(self, url: Any) -> str:
        if not isinstance(url, str):
            return ""
        cleaned = url.strip()
        if cleaned.lower() in {"null", "none", "n/a"}:
            return ""
        return cleaned

    def _generated_example_mentions_target(self, sentence: str, *candidate_words: str) -> bool:
        if not isinstance(sentence, str) or not sentence.strip():
            return False

        for candidate in candidate_words:
            normalized = sanitize_word_input(candidate)
            if not normalized:
                continue

            pattern = r"(?<![A-Za-z]){0}(?![A-Za-z])".format(re.escape(normalized))
            if re.search(pattern, sentence, re.IGNORECASE):
                return True

        return False


OpenAICompatibleClient = LLMClient
