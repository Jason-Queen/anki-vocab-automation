from pathlib import Path

import requests

from anki_vocab_automation.config import build_tts_service_priority
from anki_vocab_automation.tts_generator import TTSGenerator

VOICE_DESIGN_MODEL = "mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-bf16"
CUSTOM_VOICE_MODEL = "mlx-community/Qwen3-TTS-12Hz-0.6B-CustomVoice-bf16"


class FakeResponse:
    def __init__(self, json_data=None, content=b"", headers=None, status_code=200):
        self._json_data = json_data
        self.content = content
        self.headers = headers or {}
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError("HTTP {0}".format(self.status_code))

    def json(self):
        if self._json_data is None:
            raise ValueError("Response does not contain JSON")
        return self._json_data


class FakeSession:
    def __init__(self, responses):
        self.responses = responses
        self.headers = {}
        self.get_calls = []
        self.post_calls = []

    def get(self, url, timeout=None):
        self.get_calls.append({"url": url, "timeout": timeout})
        response = self.responses.get(url)
        if response is None:
            raise AssertionError("Unexpected GET {0}".format(url))
        return response

    def post(self, url, json=None, timeout=None):
        self.post_calls.append({"url": url, "json": json, "timeout": timeout})
        response = self.responses.get(("POST", url))
        if response is None:
            raise AssertionError("Unexpected POST {0}".format(url))
        return response


def test_openai_compat_tts_uses_default_model_metadata_and_caches_audio(monkeypatch, tmp_path) -> None:
    base_url = "http://127.0.0.1:8000"
    session = FakeSession(
        {
            "{0}/health".format(base_url): FakeResponse(
                json_data={"status": "ok", "default_model": VOICE_DESIGN_MODEL}
            ),
            "{0}/v1/models".format(base_url): FakeResponse(
                json_data={
                    "data": [
                        {
                            "id": VOICE_DESIGN_MODEL,
                            "metadata": {
                                "supports_instruction_control": True,
                                "supports_custom_voice": False,
                                "supports_voice_clone": False,
                                "supports_voice_design": True,
                            },
                        }
                    ]
                }
            ),
            ("POST", "{0}/v1/audio/speech".format(base_url)): FakeResponse(
                content=b"RIFFtest-audio",
                headers={"Content-Type": "audio/wav"},
            ),
        }
    )

    monkeypatch.setattr("anki_vocab_automation.tts_generator.requests.Session", lambda: session)

    generator = TTSGenerator(
        service="openai_compat",
        base_url=base_url,
        temp_dir=str(tmp_path),
    )

    first_path = generator.generate_audio_reference("agentic", language="en-GB")
    second_path = generator.generate_audio_reference("agentic", language="en-GB")

    assert first_path == second_path
    assert Path(first_path).exists()
    assert Path(first_path).suffix == ".wav"
    assert len(session.post_calls) == 1
    assert session.post_calls[0]["json"]["model"] == VOICE_DESIGN_MODEL
    assert session.post_calls[0]["json"]["language"] == "english"
    assert session.post_calls[0]["json"]["instructions"] == "Speak clearly and naturally with a British English accent."


def test_openai_compat_tts_omits_instructions_for_models_without_instruction_support(
    monkeypatch,
    tmp_path,
) -> None:
    base_url = "http://127.0.0.1:8000"
    session = FakeSession(
        {
            "{0}/v1/models".format(base_url): FakeResponse(
                json_data={
                    "data": [
                        {
                            "id": CUSTOM_VOICE_MODEL,
                            "metadata": {
                                "supports_instruction_control": False,
                                "supports_custom_voice": True,
                                "supports_voice_clone": False,
                                "supports_voice_design": False,
                            },
                        }
                    ]
                }
            ),
            ("POST", "{0}/v1/audio/speech".format(base_url)): FakeResponse(
                content=b"ID3test-audio",
                headers={"Content-Type": "audio/mpeg"},
            ),
        }
    )

    monkeypatch.setattr("anki_vocab_automation.tts_generator.requests.Session", lambda: session)

    generator = TTSGenerator(
        service="openai_compat",
        base_url=base_url,
        model_name=CUSTOM_VOICE_MODEL,
        openai_compat_voice="Ryan",
        openai_compat_instructions="This should be omitted",
        response_format="mp3",
        temp_dir=str(tmp_path),
    )

    audio_path = generator.generate_audio_reference("agentic", language="en-US")

    assert Path(audio_path).exists()
    assert Path(audio_path).suffix == ".mp3"
    assert session.post_calls[0]["json"]["voice"] == "Ryan"
    assert "instructions" not in session.post_calls[0]["json"]


def test_build_tts_service_priority_prefers_openai_compat_and_keeps_legacy_optional() -> None:
    assert build_tts_service_priority("", "http://127.0.0.1:8000") == ["openai_compat"]
    assert build_tts_service_priority("google", "http://127.0.0.1:8000") == ["openai_compat", "google"]
    assert build_tts_service_priority("google", "") == ["google"]
    assert build_tts_service_priority("", "") == []
