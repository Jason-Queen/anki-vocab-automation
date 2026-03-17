"""
TTS音频生成器
Text-to-Speech audio reference generator for vocabulary cards
"""

import hashlib
import json
import logging
import tempfile
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import quote

import requests

from .input_validator import InputValidator

logger = logging.getLogger(__name__)

OPENAI_COMPAT_AUDIO_FORMATS = {"wav", "mp3", "flac", "ogg", "opus"}
DEFAULT_OPENAI_COMPAT_INSTRUCTIONS = "Speak clearly and naturally in English."
PRIMARY_TTS_SERVICE = "openai_compat"
LEGACY_URL_TTS_SERVICES = ("google", "microsoft", "responsivevoice")
SUPPORTED_TTS_SERVICES = LEGACY_URL_TTS_SERVICES + (PRIMARY_TTS_SERVICE,)
USER_FACING_TTS_LABELS = {
    "google": "Google TTS",
    "microsoft": "Microsoft TTS",
    "responsivevoice": "ResponsiveVoice TTS",
}


class TTSGenerator:
    """TTS音频生成器"""

    def __init__(
        self,
        service: str = PRIMARY_TTS_SERVICE,
        voice: str = "en-US",
        base_url: str = "",
        api_key: str = "not-needed",
        model_name: str = "",
        openai_compat_voice: str = "",
        openai_compat_instructions: str = "",
        response_format: str = "wav",
        timeout: int = 60,
        temp_dir: Optional[str] = None,
    ):
        """
        初始化TTS生成器

        Args:
            service: TTS服务提供商
            voice: 语音类型
            base_url: OpenAI兼容TTS服务地址
            api_key: OpenAI兼容TTS服务密钥
            model_name: OpenAI兼容TTS模型名
            openai_compat_voice: OpenAI兼容TTS内置说话人
            openai_compat_instructions: OpenAI兼容TTS音色指令
            response_format: OpenAI兼容TTS返回格式
            timeout: OpenAI兼容TTS请求超时
            temp_dir: 远程TTS临时文件目录
        """
        self.service = service.lower().strip()
        self.voice = voice
        self.base_url = (base_url or "").strip().rstrip("/")
        self.api_key = api_key or "not-needed"
        self.model_name = (model_name or "").strip()
        self.openai_compat_voice = (openai_compat_voice or "").strip()
        self.openai_compat_instructions = (openai_compat_instructions or "").strip()
        self.timeout = timeout

        normalized_format = (response_format or "wav").strip().lower()
        if normalized_format not in OPENAI_COMPAT_AUDIO_FORMATS:
            logger.warning("不支持的OpenAI兼容TTS输出格式: %s，已回退到wav", normalized_format)
            normalized_format = "wav"
        self.response_format = normalized_format

        self.temp_dir = Path(temp_dir) if temp_dir else Path(tempfile.gettempdir()) / "anki_audio_tts"
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Anki-Vocabulary-Automation/2.0 (TTS Generator)",
            }
        )
        if self.api_key and self.api_key != "not-needed":
            self.session.headers.update({"Authorization": "Bearer {0}".format(self.api_key)})

        self._openai_compat_default_model = None
        self._openai_compat_models = None
        self._legacy_warning_emitted = False

    def generate_audio_reference(self, word: str, pronunciation: str = "", language: str = "en-US") -> str:
        """
        生成单词的音频引用。

        返回值可能是远程音频URL，也可能是已生成的本地临时音频文件路径。
        """
        del pronunciation  # 当前实现不直接使用IPA，但保留参数兼容现有调用。

        if not word.strip():
            return ""

        try:
            if self.service in LEGACY_URL_TTS_SERVICES and not self._legacy_warning_emitted:
                logger.warning(
                    "正在使用 legacy URL 型 TTS 兼容层: %s。建议优先配置 OpenAI-compatible TTS 服务。",
                    self.service,
                )
                self._legacy_warning_emitted = True

            if self.service == "google":
                return self._generate_google_tts_url(word, language)
            if self.service == "microsoft":
                return self._generate_microsoft_tts_url(word, language)
            if self.service == "responsivevoice":
                return self._generate_responsivevoice_url(word, language)
            if self.service == PRIMARY_TTS_SERVICE:
                return self._generate_openai_compat_audio(word, language)

            logger.warning("不支持的TTS服务: %s", self.service)
            return ""

        except Exception as exc:
            logger.error("生成TTS音频引用失败 - %s: %s", word, exc)
            return ""

    def generate_audio_url(self, word: str, pronunciation: str = "", language: str = "en-US") -> str:
        """
        兼容旧接口。

        旧调用点仍会把返回值当作“音频引用”处理，因此这里继续返回字符串。
        """
        return self.generate_audio_reference(word, pronunciation, language)

    def get_source_label(self) -> str:
        """Return a user-facing label describing the current TTS source."""
        if self.service == PRIMARY_TTS_SERVICE:
            return self._resolve_openai_compat_model_name() or "TTS"

        return USER_FACING_TTS_LABELS.get(self.service, "TTS")

    def _generate_google_tts_url(self, word: str, language: str = "en-US") -> str:
        """
        生成Google TTS URL

        Args:
            word: 单词
            language: 语言代码

        Returns:
            Google TTS URL
        """
        # 将language转换为Google TTS支持的格式
        if language == "en-GB":
            tl = "en-gb"
        elif language == "en-US":
            tl = "en-us"
        else:
            tl = "en"

        # Google Translate TTS API
        encoded_word = quote(word)
        url = f"https://translate.google.com/translate_tts?ie=UTF-8&tl={tl}&client=tw-ob&q={encoded_word}"
        logger.debug(f"生成Google TTS URL: {word} ({language}) -> {url}")
        return url

    def _generate_microsoft_tts_url(self, word: str, language: str = "en-US") -> str:
        """
        生成Microsoft TTS URL

        Args:
            word: 单词
            language: 语言代码

        Returns:
            Microsoft TTS URL
        """
        # 选择合适的语音
        if language == "en-GB":
            voice = "en-GB-LibbyNeural"
        elif language == "en-US":
            voice = "en-US-JennyNeural"
        else:
            voice = self.voice

        # Microsoft Edge TTS (需要特定的API调用)
        encoded_word = quote(word)
        url = (
            "https://speech.platform.bing.com/synthesize"
            f"?text={encoded_word}&voice={voice}&format=audio-16khz-32kbitrate-mono-mp3"
        )
        logger.debug(f"生成Microsoft TTS URL: {word} ({language}) -> {url}")
        return url

    def _generate_responsivevoice_url(self, word: str, language: str = "en-US") -> str:
        """
        生成ResponsiveVoice TTS URL

        Args:
            word: 单词
            language: 语言代码

        Returns:
            ResponsiveVoice TTS URL
        """
        # 选择合适的语音
        if language == "en-GB":
            voice = "UK English Female"
        elif language == "en-US":
            voice = "US English Female"
        else:
            voice = "US English Female"

        # ResponsiveVoice API
        encoded_word = quote(word)
        encoded_voice = quote(voice)
        url = (
            "https://responsivevoice.org/responsivevoice/getvoice.php"
            f"?t={encoded_word}&tl={language}&sv={encoded_voice}&pitch=0.5&rate=0.5&vol=1"
        )
        logger.debug(f"生成ResponsiveVoice TTS URL: {word} ({language}) -> {url}")
        return url

    def _generate_openai_compat_audio(self, word: str, language: str = "en-US") -> str:
        """调用OpenAI兼容TTS服务并写入本地临时音频文件。"""
        if not self.base_url:
            logger.warning("openai_compat TTS服务缺少 base_url 配置")
            return ""

        model_name = self._resolve_openai_compat_model_name()
        model_metadata = self._get_openai_compat_model_metadata(model_name)

        if model_metadata.get("supports_voice_clone"):
            logger.error("当前TTS模型需要参考音频，不能作为通用单词发音备选: %s", model_name)
            return ""

        payload = {
            "input": word,
            "language": self._map_language_for_openai_compat(language),
            "response_format": self.response_format,
        }
        if model_name:
            payload["model"] = model_name

        voice_name = self.openai_compat_voice
        if model_metadata.get("supports_custom_voice"):
            if not voice_name:
                logger.error("当前TTS模型需要配置 TTS_OPENAI_COMPAT_VOICE: %s", model_name)
                return ""
            payload["voice"] = voice_name
        elif voice_name and not model_metadata:
            payload["voice"] = voice_name

        instructions = self._resolve_openai_compat_instructions(language, model_metadata)
        if instructions:
            payload["instructions"] = instructions

        file_path = self._build_openai_compat_cache_path(word, payload)
        if file_path.exists() and file_path.stat().st_size > 0:
            logger.debug("复用已生成的远程TTS音频: %s", file_path.name)
            return str(file_path)

        endpoint = self._build_openai_compat_endpoint("audio/speech", versioned=True)
        logger.info("开始调用远程TTS服务: %s -> %s", word, endpoint)
        response = self.session.post(endpoint, json=payload, timeout=self.timeout)
        response.raise_for_status()

        content_type = response.headers.get("Content-Type", "")
        if (
            content_type
            and not content_type.startswith("audio/")
            and content_type
            not in (
                "application/octet-stream",
                "binary/octet-stream",
            )
        ):
            logger.warning("远程TTS返回了可疑Content-Type: %s", content_type)

        audio_bytes = response.content
        if not audio_bytes:
            logger.error("远程TTS返回空音频: %s", word)
            return ""

        file_path.write_bytes(audio_bytes)
        if file_path.stat().st_size == 0:
            logger.error("远程TTS生成的音频文件为空: %s", word)
            file_path.unlink()
            return ""

        logger.info("远程TTS生成成功: %s -> %s", word, file_path.name)
        return str(file_path)

    def _resolve_openai_compat_model_name(self) -> str:
        """优先使用显式配置的模型，否则读取服务默认模型。"""
        if self.model_name:
            return self.model_name

        if self._openai_compat_default_model is not None:
            return self._openai_compat_default_model

        try:
            endpoint = self._build_openai_compat_endpoint("health", versioned=False)
            response = self.session.get(endpoint, timeout=self.timeout)
            response.raise_for_status()
            payload = response.json()
            default_model = payload.get("default_model", "")
            self._openai_compat_default_model = default_model.strip() if isinstance(default_model, str) else ""
        except (requests.RequestException, ValueError) as exc:
            logger.warning("读取远程TTS默认模型失败，将依赖服务端默认行为: %s", exc)
            self._openai_compat_default_model = ""

        return self._openai_compat_default_model

    def _load_openai_compat_models(self) -> Dict[str, dict]:
        """拉取远程TTS模型元数据并缓存。"""
        if self._openai_compat_models is not None:
            return self._openai_compat_models

        self._openai_compat_models = {}
        try:
            endpoint = self._build_openai_compat_endpoint("models", versioned=True)
            response = self.session.get(endpoint, timeout=self.timeout)
            response.raise_for_status()
            payload = response.json()
            for item in payload.get("data", []):
                if not isinstance(item, dict):
                    continue
                model_id = item.get("id", "")
                metadata = item.get("metadata") or {}
                if isinstance(model_id, str) and model_id.strip() and isinstance(metadata, dict):
                    self._openai_compat_models[model_id.strip()] = metadata
        except (requests.RequestException, ValueError) as exc:
            logger.warning("读取远程TTS模型列表失败，将使用保守默认值: %s", exc)

        return self._openai_compat_models

    def _get_openai_compat_model_metadata(self, model_name: str) -> Dict[str, object]:
        """返回当前模型的元数据；取不到时返回空字典。"""
        if not model_name:
            return {}
        return self._load_openai_compat_models().get(model_name, {})

    def _resolve_openai_compat_instructions(self, language: str, model_metadata: Dict[str, object]) -> str:
        """根据模型能力决定是否发送 instructions。"""
        custom_instructions = self.openai_compat_instructions
        supports_instruction = bool(model_metadata.get("supports_instruction_control"))

        if custom_instructions:
            if model_metadata and not supports_instruction:
                logger.warning("当前TTS模型不支持 instructions，已忽略自定义音色指令")
                return ""
            return custom_instructions

        if model_metadata and not supports_instruction:
            return ""

        if language == "en-GB":
            return "Speak clearly and naturally with a British English accent."
        if language == "en-US":
            return "Speak clearly and naturally with an American English accent."
        return DEFAULT_OPENAI_COMPAT_INSTRUCTIONS

    def _build_openai_compat_endpoint(self, path: str, versioned: bool) -> str:
        """构建服务端点，兼容传入根地址或 /v1 地址。"""
        base_url = self.base_url
        if base_url.endswith("/v1"):
            root_url = base_url[:-3].rstrip("/")
        else:
            root_url = base_url

        if versioned:
            return "{0}/v1/{1}".format(root_url, path.strip("/"))
        return "{0}/{1}".format(root_url, path.strip("/"))

    def _map_language_for_openai_compat(self, language: str) -> str:
        """把项目里的语言代码映射到Qwen TTS支持的语言名。"""
        normalized = (language or "").strip().lower()
        if normalized.startswith("en"):
            return "english"
        if normalized.startswith("zh"):
            return "chinese"
        return "auto"

    def _build_openai_compat_cache_path(self, word: str, payload: Dict[str, object]) -> Path:
        """根据请求内容构建稳定的临时缓存文件路径。"""
        safe_word = InputValidator.sanitize_filename(word)[:20]
        if not safe_word or safe_word in ("", "sanitized_file"):
            safe_word = "audio"

        payload_fingerprint = json.dumps(
            {
                "base_url": self.base_url,
                "payload": payload,
            },
            ensure_ascii=True,
            sort_keys=True,
        )
        payload_hash = hashlib.md5(payload_fingerprint.encode("utf-8")).hexdigest()[:12]
        filename = "{0}_{1}.{2}".format(safe_word, payload_hash, self.response_format)
        filename = InputValidator.sanitize_filename(filename)
        return self.temp_dir / filename

    def is_available(self) -> bool:
        """
        检查TTS服务是否可用

        Returns:
            True如果服务可用，False否则
        """
        if self.service != PRIMARY_TTS_SERVICE:
            return True

        if not self.base_url:
            return False

        try:
            endpoint = self._build_openai_compat_endpoint("health", versioned=False)
            response = self.session.get(endpoint, timeout=self.timeout)
            response.raise_for_status()
            return True
        except requests.RequestException:
            return False

    @staticmethod
    def get_available_services() -> list:
        """
        获取可用的TTS服务列表

        Returns:
            服务名称列表
        """
        return list(SUPPORTED_TTS_SERVICES)
