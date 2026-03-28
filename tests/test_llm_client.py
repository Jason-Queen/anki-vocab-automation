from types import SimpleNamespace

import pytest

from anki_vocab_automation.llm_client import (
    DEFAULT_PROMPT_VERSION,
    DEFAULT_GPT_OSS_REASONING_EFFORT,
    LLMClient,
    list_loaded_models_for_backend,
    list_models_for_backend,
    resolve_llm_runtime_config,
)
from anki_vocab_automation.models import VocabularyCard

JSON_RESPONSE = """
{
  "word": "clarify",
  "definition": "to make something easier to understand",
  "generated_example": "Please clarify the final step for me.",
  "pronunciation": "/ˈklær.ɪ.faɪ/",
  "british_pronunciation": "/ˈklær.ɪ.faɪ/",
  "american_pronunciation": "/ˈkler.ə.faɪ/",
  "audio_url": "",
  "british_audio_url": "",
  "american_audio_url": "",
  "part_of_speech": "verb"
}
""".strip()


def test_resolve_llm_runtime_config_normalizes_backend_defaults() -> None:
    lmstudio_runtime = resolve_llm_runtime_config("lmstudio", "responses", "http://localhost:1234")
    ollama_runtime = resolve_llm_runtime_config("ollama", "chat", "http://localhost:11434")
    anthropic_runtime = resolve_llm_runtime_config("anthropic", "messages", "https://api.anthropic.com/v1")
    custom_runtime = resolve_llm_runtime_config("openai_compat", "auto", "https://example.com/proxy")

    assert lmstudio_runtime.base_url == "http://localhost:1234/v1"
    assert lmstudio_runtime.api_mode == "responses"
    assert ollama_runtime.base_url == "http://localhost:11434/v1"
    assert anthropic_runtime.base_url == "https://api.anthropic.com"
    assert custom_runtime.api_mode == "chat"
    assert custom_runtime.base_url == "https://example.com/proxy/v1"


def test_gpt_oss_models_use_responses_api_with_reasoning_effort(monkeypatch) -> None:
    captured = {}

    class FakeOpenAI:
        def __init__(self, **kwargs):
            captured["init"] = kwargs
            self.responses = SimpleNamespace(create=self._create_response)
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=lambda **kwargs: None))
            self.models = SimpleNamespace(list=lambda: [])

        def _create_response(self, **kwargs):
            captured["request"] = kwargs
            return SimpleNamespace(output_text=JSON_RESPONSE)

    monkeypatch.setattr("anki_vocab_automation.llm_client.OpenAI", FakeOpenAI)

    client = LLMClient(
        provider="openai",
        api_mode="auto",
        base_url="https://api.openai.com",
        api_key="sk-test",
        model_name="openai/gpt-oss-20b",
        enable_tts=False,
    )

    card = client.generate_vocabulary_card("clarify")

    assert card is not None
    assert card.word == "clarify"
    assert card.part_of_speech == "verb"
    assert card.generated_example == "Please clarify the final step for me."
    assert captured["init"]["base_url"] == "https://api.openai.com/v1"
    assert captured["request"]["model"] == "openai/gpt-oss-20b"
    assert captured["request"]["instructions"]
    assert captured["request"]["reasoning"] == {"effort": DEFAULT_GPT_OSS_REASONING_EFFORT}


def test_openai_chat_mode_uses_chat_completions(monkeypatch) -> None:
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "models": [
                    {
                        "type": "llm",
                        "key": "qwen/qwen3.5-9b",
                        "loaded_instances": [{"identifier": "loaded"}],
                    }
                ]
            }

    class FakeOpenAI:
        def __init__(self, **kwargs):
            captured["init"] = kwargs
            self.responses = SimpleNamespace(create=lambda **kwargs: None)
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create_chat))
            self.models = SimpleNamespace(list=lambda: [SimpleNamespace(id="qwen/qwen3.5-9b")])

        def _create_chat(self, **kwargs):
            captured["request"] = kwargs
            message = SimpleNamespace(content=JSON_RESPONSE)
            choice = SimpleNamespace(message=message)
            return SimpleNamespace(choices=[choice])

    monkeypatch.setattr("anki_vocab_automation.llm_client.requests.get", lambda *args, **kwargs: FakeResponse())
    monkeypatch.setattr("anki_vocab_automation.llm_client.OpenAI", FakeOpenAI)

    client = LLMClient(
        provider="lmstudio",
        api_mode="chat",
        base_url="http://localhost:1234",
        api_key="not-needed",
        model_name="qwen/qwen3.5-9b",
        enable_tts=False,
    )

    card = client.generate_vocabulary_card("clarify")

    assert card is not None
    assert card.definition == "to make something easier to understand"
    assert card.generated_example == "Please clarify the final step for me."
    assert captured["init"]["base_url"] == "http://localhost:1234/v1"
    assert captured["request"]["messages"][0]["role"] == "system"
    assert captured["request"]["messages"][1]["role"] == "user"
    assert captured["request"]["response_format"]["type"] == "json_schema"
    assert captured["request"]["response_format"]["json_schema"]["name"] == "vocabulary_card"


def test_anthropic_messages_mode_uses_sdk_messages_api(monkeypatch) -> None:
    captured = {}

    class FakeAnthropic:
        def __init__(self, **kwargs):
            captured["init"] = kwargs
            self.messages = SimpleNamespace(create=self._create_message)
            self.models = SimpleNamespace(list=lambda limit=100: [])

        def _create_message(self, **kwargs):
            captured["request"] = kwargs
            return SimpleNamespace(content=[SimpleNamespace(type="text", text=JSON_RESPONSE)])

    monkeypatch.setattr("anki_vocab_automation.llm_client.Anthropic", FakeAnthropic)

    client = LLMClient(
        provider="anthropic",
        api_mode="messages",
        base_url="https://api.anthropic.com/v1",
        api_key="sk-ant-test",
        model_name="claude-3-5-sonnet-20241022",
        enable_tts=False,
    )

    card = client.generate_vocabulary_card("clarify")

    assert card is not None
    assert card.generated_example == "Please clarify the final step for me."
    assert captured["init"]["base_url"] == "https://api.anthropic.com"
    assert captured["request"]["messages"][0]["role"] == "user"
    assert captured["request"]["system"]


def test_llm_client_keeps_user_example_on_front_and_generated_example_on_back(monkeypatch) -> None:
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "models": [
                    {
                        "type": "llm",
                        "key": "qwen/qwen3.5-9b",
                        "loaded_instances": [{"identifier": "loaded"}],
                    }
                ]
            }

    class FakeOpenAI:
        def __init__(self, **kwargs):
            self.responses = SimpleNamespace(create=lambda **kwargs: SimpleNamespace(output_text=JSON_RESPONSE))
            self.chat = SimpleNamespace(
                completions=SimpleNamespace(
                    create=lambda **kwargs: SimpleNamespace(
                        choices=[SimpleNamespace(message=SimpleNamespace(content=JSON_RESPONSE))]
                    )
                )
            )
            self.models = SimpleNamespace(list=lambda: [SimpleNamespace(id="openai/gpt-oss-20b")])

    monkeypatch.setattr("anki_vocab_automation.llm_client.requests.get", lambda *args, **kwargs: FakeResponse())
    monkeypatch.setattr("anki_vocab_automation.llm_client.OpenAI", FakeOpenAI)

    client = LLMClient(
        provider="lmstudio",
        api_mode="responses",
        base_url="http://localhost:1234",
        api_key="not-needed",
        model_name="openai/gpt-oss-20b",
        enable_tts=False,
    )

    card = client.generate_vocabulary_card(
        "clarify",
        source_example="I asked the teacher to clarify the lesson.",
    )

    assert card is not None
    assert card.example == "I asked the teacher to clarify the lesson."
    assert card.generated_example == "Please clarify the final step for me."


def test_chat_content_extraction_ignores_reasoning_items(monkeypatch) -> None:
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "models": [
                    {
                        "type": "llm",
                        "key": "qwen/qwen3.5-9b",
                        "loaded_instances": [{"identifier": "loaded"}],
                    }
                ]
            }

    class FakeOpenAI:
        def __init__(self, **kwargs):
            self.responses = SimpleNamespace(create=lambda **kwargs: None)
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create_chat))
            self.models = SimpleNamespace(list=lambda: [SimpleNamespace(id="qwen/qwen3.5-9b")])

        def _create_chat(self, **kwargs):
            del kwargs
            message = SimpleNamespace(
                content=[
                    {"type": "reasoning_text", "text": "internal chain of thought"},
                    {"type": "text", "text": JSON_RESPONSE},
                ]
            )
            choice = SimpleNamespace(message=message)
            return SimpleNamespace(choices=[choice])

    monkeypatch.setattr("anki_vocab_automation.llm_client.requests.get", lambda *args, **kwargs: FakeResponse())
    monkeypatch.setattr("anki_vocab_automation.llm_client.OpenAI", FakeOpenAI)

    client = LLMClient(
        provider="lmstudio",
        api_mode="auto",
        base_url="http://localhost:1234",
        api_key="not-needed",
        model_name="qwen/qwen3.5-9b",
        enable_tts=False,
    )

    card = client.generate_vocabulary_card("clarify")

    assert card is not None
    assert card.word == "clarify"


def test_responses_extraction_ignores_reasoning_only_payload(monkeypatch) -> None:
    attempts = {"count": 0}

    class FakeOpenAI:
        def __init__(self, **kwargs):
            self.responses = SimpleNamespace(create=self._create_response)
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=lambda **kwargs: None))
            self.models = SimpleNamespace(list=lambda: [SimpleNamespace(id="openai/gpt-oss-20b")])

        def _create_response(self, **kwargs):
            del kwargs
            attempts["count"] += 1
            return {
                "output": [
                    {
                        "type": "reasoning",
                        "content": [{"type": "reasoning_text", "text": "reasoning only"}],
                    }
                ]
            }

    monkeypatch.setattr("anki_vocab_automation.llm_client.OpenAI", FakeOpenAI)

    client = LLMClient(
        provider="openai",
        api_mode="auto",
        base_url="https://api.openai.com",
        api_key="sk-test",
        model_name="openai/gpt-oss-20b",
        enable_tts=False,
    )

    card = client.generate_vocabulary_card("clarify")

    assert card is None
    assert attempts["count"] == 2


def test_gpt_oss_reasoning_effort_can_be_overridden(monkeypatch) -> None:
    captured = {}

    class FakeOpenAI:
        def __init__(self, **kwargs):
            self.responses = SimpleNamespace(create=self._create_response)
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=lambda **kwargs: None))
            self.models = SimpleNamespace(list=lambda: [])

        def _create_response(self, **kwargs):
            captured["request"] = kwargs
            return SimpleNamespace(output_text=JSON_RESPONSE)

    monkeypatch.setattr("anki_vocab_automation.llm_client.OpenAI", FakeOpenAI)

    client = LLMClient(
        provider="openai",
        api_mode="auto",
        base_url="https://api.openai.com",
        api_key="sk-test",
        model_name="openai/gpt-oss-20b",
        enable_tts=False,
        gpt_oss_reasoning_effort="high",
    )

    card = client.generate_vocabulary_card("clarify")

    assert card is not None
    assert captured["request"]["reasoning"] == {"effort": "high"}


def test_zero_max_output_tokens_disables_request_limit() -> None:
    client = LLMClient(
        provider="lmstudio",
        api_mode="auto",
        base_url="http://localhost:1234",
        api_key="not-needed",
        model_name="qwen/qwen3.5-9b",
        enable_tts=False,
        max_output_tokens=0,
    )

    assert client.max_output_tokens is None


def test_llm_client_defaults_prompt_version_to_revised() -> None:
    client = LLMClient(
        provider="openai",
        api_mode="auto",
        base_url="https://api.openai.com",
        api_key="sk-test",
        model_name="openai/gpt-oss-20b",
        enable_tts=False,
    )

    assert client.prompt_version == DEFAULT_PROMPT_VERSION
    assert client.prompt_version == "revised"


def test_revised_prompt_adds_lemma_and_part_of_speech_guardrails() -> None:
    client = LLMClient(
        provider="openai",
        api_mode="auto",
        base_url="https://api.openai.com",
        api_key="sk-test",
        model_name="openai/gpt-oss-20b",
        enable_tts=False,
        prompt_version="revised",
    )

    prompt = client._create_vocabulary_prompt(
        "defining",
        source_example="Code execution is the defining capability that makes agentic engineering possible.",
        structured_output=True,
    )

    assert client.prompt_version == "revised"
    assert 'keep it adjective; do not answer with the verb "define"' in prompt
    assert "same part of speech" in prompt
    assert "same sense as the learner sentence" in prompt
    assert "primary sense-selection evidence" in prompt


def test_list_models_for_backend_uses_matching_sdk(monkeypatch) -> None:
    class FakeOpenAI:
        def __init__(self, **kwargs):
            self.models = SimpleNamespace(list=lambda: [SimpleNamespace(id="qwen"), SimpleNamespace(id="llama")])

    class FakeAnthropic:
        def __init__(self, **kwargs):
            self.models = SimpleNamespace(list=lambda limit=100: [SimpleNamespace(id="claude-3-5-sonnet")])

    monkeypatch.setattr("anki_vocab_automation.llm_client.OpenAI", FakeOpenAI)
    monkeypatch.setattr("anki_vocab_automation.llm_client.Anthropic", FakeAnthropic)

    assert list_models_for_backend("lmstudio", "http://localhost:1234", "not-needed") == ["qwen", "llama"]
    assert list_models_for_backend("anthropic", "https://api.anthropic.com", "sk-ant-test") == ["claude-3-5-sonnet"]


def test_list_loaded_models_for_backend_uses_provider_native_endpoints(monkeypatch) -> None:
    class FakeResponse:
        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    def fake_get(url, headers=None, timeout=0):
        del headers, timeout
        if url == "http://localhost:1234/api/v1/models":
            return FakeResponse(
                {
                    "models": [
                        {"type": "llm", "key": "qwen/qwen3.5-9b", "loaded_instances": [{"identifier": "loaded"}]},
                        {"type": "llm", "key": "qwen/qwen3-8b", "loaded_instances": []},
                    ]
                }
            )
        if url == "http://localhost:11434/api/ps":
            return FakeResponse({"models": [{"model": "llama3.2:latest"}]})
        raise AssertionError("Unexpected URL: {0}".format(url))

    monkeypatch.setattr("anki_vocab_automation.llm_client.requests.get", fake_get)

    assert list_loaded_models_for_backend("lmstudio", "http://localhost:1234", "not-needed") == ["qwen/qwen3.5-9b"]
    assert list_loaded_models_for_backend("ollama", "http://localhost:11434", "not-needed") == ["llama3.2:latest"]


def test_llm_client_uses_loaded_lmstudio_model_when_model_name_is_blank(monkeypatch) -> None:
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "models": [
                    {
                        "type": "llm",
                        "key": "qwen/qwen3.5-9b",
                        "loaded_instances": [{"identifier": "loaded"}],
                    }
                ]
            }

    class FakeOpenAI:
        def __init__(self, **kwargs):
            self.responses = SimpleNamespace(create=lambda **kwargs: None)
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create_chat))
            self.models = SimpleNamespace(list=lambda: [SimpleNamespace(id="qwen/qwen3.5-9b")])

        def _create_chat(self, **kwargs):
            captured["request"] = kwargs
            message = SimpleNamespace(content=JSON_RESPONSE)
            choice = SimpleNamespace(message=message)
            return SimpleNamespace(choices=[choice])

    monkeypatch.setattr("anki_vocab_automation.llm_client.requests.get", lambda *args, **kwargs: FakeResponse())
    monkeypatch.setattr("anki_vocab_automation.llm_client.OpenAI", FakeOpenAI)

    client = LLMClient(
        provider="lmstudio",
        api_mode="responses",
        base_url="http://localhost:1234",
        api_key="not-needed",
        model_name="",
        enable_tts=False,
    )

    card = client.generate_vocabulary_card("clarify")

    assert card is not None
    assert captured["request"]["model"] == "qwen/qwen3.5-9b"
    assert captured["request"]["response_format"]["type"] == "json_schema"


@pytest.mark.parametrize(
    ("provider", "base_url"),
    [
        ("lmstudio", "http://localhost:1234"),
        ("ollama", "http://localhost:11434"),
    ],
)
def test_llm_client_skips_loaded_model_discovery_for_explicit_local_model(
    monkeypatch, provider: str, base_url: str
) -> None:
    native_endpoint_calls = []

    def fake_get(*args, **kwargs):
        native_endpoint_calls.append(args[0])
        raise AssertionError("explicit local model should not trigger provider-native loaded-model discovery")

    class FakeOpenAI:
        def __init__(self, **kwargs):
            self.responses = SimpleNamespace(create=lambda **kwargs: SimpleNamespace(output_text=JSON_RESPONSE))
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=lambda **kwargs: None))
            self.models = SimpleNamespace(list=lambda: [SimpleNamespace(id="openai/gpt-oss-20b")])

    monkeypatch.setattr("anki_vocab_automation.llm_client.requests.get", fake_get)
    monkeypatch.setattr("anki_vocab_automation.llm_client.OpenAI", FakeOpenAI)

    client = LLMClient(
        provider=provider,
        api_mode="responses",
        base_url=base_url,
        api_key="not-needed",
        model_name="openai/gpt-oss-20b",
        enable_tts=False,
    )

    card = client.generate_vocabulary_card("clarify")

    assert card is not None
    assert card.word == "clarify"
    assert native_endpoint_calls == []


def test_llm_client_rejects_generation_when_no_local_model_is_loaded(monkeypatch) -> None:
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"models": []}

    monkeypatch.setattr("anki_vocab_automation.llm_client.requests.get", lambda *args, **kwargs: FakeResponse())

    client = LLMClient(
        provider="ollama",
        api_mode="responses",
        base_url="http://localhost:11434",
        api_key="not-needed",
        model_name="",
        enable_tts=False,
    )

    with pytest.raises(ValueError, match="当前没有已加载模型"):
        client.generate_vocabulary_card("clarify")


def test_llm_client_rejects_unknown_explicit_local_model(monkeypatch) -> None:
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "models": [
                    {
                        "type": "llm",
                        "key": "qwen/qwen3.5-9b",
                        "loaded_instances": [{"identifier": "loaded"}],
                    }
                ]
            }

    class FakeOpenAI:
        def __init__(self, **kwargs):
            self.responses = SimpleNamespace(create=lambda **kwargs: None)
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=lambda **kwargs: None))
            self.models = SimpleNamespace(list=lambda: [SimpleNamespace(id="qwen/qwen3.5-9b")])

    monkeypatch.setattr("anki_vocab_automation.llm_client.requests.get", lambda *args, **kwargs: FakeResponse())
    monkeypatch.setattr("anki_vocab_automation.llm_client.OpenAI", FakeOpenAI)

    client = LLMClient(
        provider="lmstudio",
        api_mode="responses",
        base_url="http://localhost:1234",
        api_key="not-needed",
        model_name="missing-model",
        enable_tts=False,
    )

    with pytest.raises(ValueError, match="LLM_MODEL_NAME 不存在"):
        client.generate_vocabulary_card("clarify")


def test_llm_client_passes_openai_compat_tts_configuration(monkeypatch) -> None:
    captured = {}

    class FakeTTSGenerator:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr("anki_vocab_automation.llm_client.TTSGenerator", FakeTTSGenerator)

    LLMClient(
        provider="lmstudio",
        api_mode="responses",
        base_url="http://localhost:1234",
        api_key="not-needed",
        model_name="qwen/qwen3.5-9b",
        enable_tts=True,
        tts_service="openai_compat",
        tts_voice="en-US",
        tts_base_url="http://127.0.0.1:8000",
        tts_api_key="not-needed",
        tts_model_name="mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-bf16",
        tts_openai_compat_voice="Ryan",
        tts_openai_compat_instructions="Speak clearly.",
        tts_response_format="wav",
        tts_timeout=75,
    )

    assert captured["service"] == "openai_compat"
    assert captured["base_url"] == "http://127.0.0.1:8000"
    assert captured["model_name"] == "mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-bf16"
    assert captured["openai_compat_voice"] == "Ryan"
    assert captured["openai_compat_instructions"] == "Speak clearly."
    assert captured["response_format"] == "wav"
    assert captured["timeout"] == 75


def test_populate_missing_audio_prefers_openai_compat_and_marks_source(monkeypatch) -> None:
    class FakeTTSGenerator:
        def __init__(self, **kwargs):
            self.service = kwargs["service"]

        def generate_audio_reference(self, word, pronunciation="", language="en-US"):
            if self.service == "openai_compat":
                return "/tmp/{0}-{1}.wav".format(word, language)
            return "https://legacy.example/{0}-{1}.mp3".format(word, language)

    monkeypatch.setattr("anki_vocab_automation.llm_client.TTSGenerator", FakeTTSGenerator)

    client = LLMClient(
        provider="lmstudio",
        api_mode="responses",
        base_url="http://localhost:1234",
        api_key="not-needed",
        model_name="qwen/qwen3.5-9b",
        enable_tts=True,
        tts_service="google",
        tts_service_order=["openai_compat", "google"],
        tts_base_url="http://127.0.0.1:8000",
        tts_model_name="mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-bf16",
    )

    card = VocabularyCard(
        word="clarify",
        definition="to make something easier to understand",
        example="I asked the teacher to clarify the lesson.",
        generated_example="Please clarify the final step for me.",
        pronunciation="/ˈklær.ɪ.faɪ/",
        audio_filename="",
        part_of_speech="verb",
        original_word="clarify",
        british_pronunciation="/ˈklær.ɪ.faɪ/",
        american_pronunciation="/ˈkler.ə.faɪ/",
        source="llm",
    )

    client.populate_missing_audio(card)

    assert card.audio_filename == "/tmp/clarify-en-GB.wav"
    assert card.audio_source == "mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-bf16"
    assert card.british_audio_filename == "/tmp/clarify-en-GB.wav"
    assert card.british_audio_source == "mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-bf16"
    assert card.american_audio_filename == "/tmp/clarify-en-US.wav"
    assert card.american_audio_source == "mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-bf16"


def test_populate_missing_audio_falls_back_to_legacy_tts_when_openai_compat_fails(monkeypatch) -> None:
    class FakeTTSGenerator:
        def __init__(self, **kwargs):
            self.service = kwargs["service"]

        def generate_audio_reference(self, word, pronunciation="", language="en-US"):
            if self.service == "openai_compat":
                return ""
            return "https://legacy.example/{0}-{1}.mp3".format(word, language)

    monkeypatch.setattr("anki_vocab_automation.llm_client.TTSGenerator", FakeTTSGenerator)

    client = LLMClient(
        provider="lmstudio",
        api_mode="responses",
        base_url="http://localhost:1234",
        api_key="not-needed",
        model_name="qwen/qwen3.5-9b",
        enable_tts=True,
        tts_service="google",
        tts_service_order=["openai_compat", "google"],
        tts_base_url="http://127.0.0.1:8000",
    )

    card = VocabularyCard(
        word="clarify",
        definition="to make something easier to understand",
        example="I asked the teacher to clarify the lesson.",
        generated_example="Please clarify the final step for me.",
        pronunciation="/ˈklær.ɪ.faɪ/",
        audio_filename="",
        part_of_speech="verb",
        original_word="clarify",
        british_pronunciation="/ˈklær.ɪ.faɪ/",
        american_pronunciation="/ˈkler.ə.faɪ/",
        source="llm",
    )

    client.populate_missing_audio(card)

    assert card.audio_filename == "https://legacy.example/clarify-en-GB.mp3"
    assert card.audio_source == "Google TTS"
    assert card.american_audio_filename == "https://legacy.example/clarify-en-US.mp3"
    assert card.american_audio_source == "Google TTS"
