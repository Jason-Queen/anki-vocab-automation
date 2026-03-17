from types import SimpleNamespace

from anki_vocab_automation.main import VocabularyAutomation
from anki_vocab_automation.models import VocabularyCard


def test_process_single_audio_file_accepts_local_generated_audio(tmp_path) -> None:
    local_audio = tmp_path / "agentic.wav"
    local_audio.write_bytes(b"RIFFtest-audio")

    stored = {}

    def store_media_file(source_path: str, target_name: str) -> bool:
        stored["source_path"] = source_path
        stored["target_name"] = target_name
        return True

    automation = VocabularyAutomation.__new__(VocabularyAutomation)
    automation.anki_connect = SimpleNamespace(store_media_file=store_media_file)
    automation.stats = {
        "audio_downloaded": 0,
        "audio_failed": 0,
    }

    card = VocabularyCard(
        word="agentic",
        definition="showing initiative and independent action",
        example="Agentic engineers use tools with clear goals.",
        generated_example="Agentic engineers use tools with clear goals.",
        pronunciation="/eɪˈdʒentɪk/",
        audio_filename="",
        part_of_speech="adjective",
        original_word="agentic",
        british_audio_filename=str(local_audio),
        american_audio_filename="",
    )

    result = VocabularyAutomation._process_single_audio_file(
        automation,
        card,
        str(local_audio),
        "british",
    )

    assert result is True
    assert stored["source_path"] == str(local_audio)
    assert stored["target_name"].startswith("vocab_agentic_british_")
    assert stored["target_name"].endswith(".wav")
    assert card.british_audio_filename == stored["target_name"]
    assert automation.stats["audio_downloaded"] == 1
    assert automation.stats["audio_failed"] == 0


def test_prepare_card_audio_metadata_keeps_dictionary_labels_and_fills_missing_audio() -> None:
    def populate_missing_audio(card):
        card.american_audio_filename = "https://tts.example/clarify-us.mp3"
        card.american_audio_source = "mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-bf16"
        return card

    automation = VocabularyAutomation.__new__(VocabularyAutomation)
    automation.llm_client = SimpleNamespace(populate_missing_audio=populate_missing_audio)

    card = VocabularyCard(
        word="clarify",
        definition="to make something easier to understand",
        example="Please clarify the final step for me.",
        generated_example="Please clarify the final step for me.",
        pronunciation="/ˈklær.ɪ.faɪ/",
        audio_filename="https://dictionary.example/clarify-uk.mp3",
        part_of_speech="verb",
        original_word="clarify",
        british_audio_filename="https://dictionary.example/clarify-uk.mp3",
        source="collins",
    )

    VocabularyAutomation._prepare_card_audio_metadata(automation, card)

    assert card.audio_source == "Dictionary"
    assert card.british_audio_source == "Dictionary"
    assert card.american_audio_filename == "https://tts.example/clarify-us.mp3"
    assert card.american_audio_source == "mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-bf16"
