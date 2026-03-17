from types import SimpleNamespace

from anki_vocab_automation.llm_client import LLMClient

INVALID_INSTRUCTION_RESPONSE = """
{
  "word": "instruction",
  "definition": "a direction or order to do something",
  "generated_example": "The teacher gave the students a step-by-step guide for the experiment.",
  "pronunciation": "/ɪnˈstrʌkʃən/",
  "british_pronunciation": "/ɪnˈstrʌkʃən/",
  "american_pronunciation": "/ɪnˈstrʌkʃən/",
  "audio_url": "",
  "british_audio_url": "",
  "american_audio_url": "",
  "part_of_speech": "noun"
}
""".strip()


VALID_INSTRUCTION_RESPONSE = """
{
  "word": "instruction",
  "definition": "a direction or order to do something",
  "generated_example": "The manual gives clear instruction for each repair step.",
  "pronunciation": "/ɪnˈstrʌkʃən/",
  "british_pronunciation": "/ɪnˈstrʌkʃən/",
  "american_pronunciation": "/ɪnˈstrʌkʃən/",
  "audio_url": "",
  "british_audio_url": "",
  "american_audio_url": "",
  "part_of_speech": "noun"
}
""".strip()


def test_llm_client_retries_when_generated_example_omits_target_word(monkeypatch) -> None:
    requests = []
    responses = [INVALID_INSTRUCTION_RESPONSE, VALID_INSTRUCTION_RESPONSE]

    def fake_get(*args, **kwargs):
        raise AssertionError("explicit local model should not probe provider-native loaded-model endpoints")

    class FakeOpenAI:
        def __init__(self, **kwargs):
            self.responses = SimpleNamespace(create=self._create_response)
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=lambda **kwargs: None))
            self.models = SimpleNamespace(list=lambda: [SimpleNamespace(id="openai/gpt-oss-20b")])

        def _create_response(self, **kwargs):
            requests.append(kwargs)
            return SimpleNamespace(output_text=responses.pop(0))

    monkeypatch.setattr("anki_vocab_automation.llm_client.requests.get", fake_get)
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
        "instruction",
        source_example="So I say run the test and then I say use red-green TDD and give it its instruction.",
    )

    assert card is not None
    assert card.example == "So I say run the test and then I say use red-green TDD and give it its instruction."
    assert card.generated_example == "The manual gives clear instruction for each repair step."
    assert len(requests) == 2
    assert 'MUST contain the exact target word "instruction"' in requests[1]["input"]


def test_llm_client_rejects_generated_example_without_target_word(monkeypatch) -> None:
    def fake_get(*args, **kwargs):
        raise AssertionError("explicit local model should not probe provider-native loaded-model endpoints")

    class FakeOpenAI:
        def __init__(self, **kwargs):
            self.responses = SimpleNamespace(
                create=lambda **kwargs: SimpleNamespace(output_text=INVALID_INSTRUCTION_RESPONSE)
            )
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=lambda **kwargs: None))
            self.models = SimpleNamespace(list=lambda: [SimpleNamespace(id="openai/gpt-oss-20b")])

    monkeypatch.setattr("anki_vocab_automation.llm_client.requests.get", fake_get)
    monkeypatch.setattr("anki_vocab_automation.llm_client.OpenAI", FakeOpenAI)

    client = LLMClient(
        provider="lmstudio",
        api_mode="responses",
        base_url="http://localhost:1234",
        api_key="not-needed",
        model_name="openai/gpt-oss-20b",
        enable_tts=False,
    )

    card = client.generate_vocabulary_card("instruction")

    assert card is None
