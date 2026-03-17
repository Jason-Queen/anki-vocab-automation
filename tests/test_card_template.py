from pathlib import Path

from anki_vocab_automation.anki_connect import (
    AnkiConnect,
    MODEL_TEMPLATE_ASSET_PATHS,
    load_vocabulary_model_assets,
)
from anki_vocab_automation.input_validator import parse_vocabulary_input
from anki_vocab_automation.models import VocabularyCard

REPOSITORY_TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "templates"


def test_parse_vocabulary_input_supports_word_and_example() -> None:
    entry, error = parse_vocabulary_input("clarify\tI asked the teacher to clarify the lesson.")

    assert error is None
    assert entry is not None
    assert entry.word == "clarify"
    assert entry.source_example == "I asked the teacher to clarify the lesson."


def test_vocabulary_card_to_dict_exposes_generated_example() -> None:
    card = VocabularyCard(
        word="clarify",
        definition="to make something easier to understand",
        example="I asked the teacher to clarify the lesson.",
        generated_example="Please clarify the final step for me.",
        pronunciation="/ˈklær.ɪ.faɪ/",
        audio_filename="",
        part_of_speech="verb",
        original_word="clarify",
        audio_source="mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-bf16",
    )

    payload = card.to_dict()

    assert payload["Example"] == "I asked the teacher to clarify the lesson."
    assert payload["GeneratedExample"] == "Please clarify the final step for me."
    assert payload["AudioSource"] == "mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-bf16"


def test_packaged_template_assets_match_repository_templates() -> None:
    packaged_assets = load_vocabulary_model_assets()

    assert MODEL_TEMPLATE_ASSET_PATHS["front"].is_file()
    assert MODEL_TEMPLATE_ASSET_PATHS["back"].is_file()
    assert MODEL_TEMPLATE_ASSET_PATHS["css"].is_file()
    assert packaged_assets["front"] == (REPOSITORY_TEMPLATE_DIR / "vocabulary_front.html").read_text(
        encoding="utf-8"
    ).strip()
    assert packaged_assets["back"] == (REPOSITORY_TEMPLATE_DIR / "vocabulary_back.html").read_text(
        encoding="utf-8"
    ).strip()
    assert packaged_assets["css"] == (REPOSITORY_TEMPLATE_DIR / "vocabulary.css").read_text(encoding="utf-8").strip()


def test_anki_template_uses_example_on_front_and_generated_example_on_back() -> None:
    anki = AnkiConnect()

    fields = anki._get_required_model_fields()
    templates = anki._build_model_templates()
    expected_front = (REPOSITORY_TEMPLATE_DIR / "vocabulary_front.html").read_text(encoding="utf-8").strip()
    expected_back = (REPOSITORY_TEMPLATE_DIR / "vocabulary_back.html").read_text(encoding="utf-8").strip()

    assert "GeneratedExample" in fields
    assert "BritishAudioSource" in fields
    assert "AmericanAudioSource" in fields
    assert templates["Card 1"]["Front"] == expected_front
    assert templates["Card 1"]["Back"] == expected_back
    assert "{{Example}}" in templates["Card 1"]["Front"]
    assert "{{GeneratedExample}}" in templates["Card 1"]["Back"]
    assert "{{BritishAudioSource}}" in templates["Card 1"]["Back"]
    assert "{{AmericanAudioSource}}" in templates["Card 1"]["Back"]
    assert '<div class="vocab-card">' in templates["Card 1"]["Front"]
    assert '<div class="card">' not in templates["Card 1"]["Front"]
    assert '<div class="vocab-card">' in templates["Card 1"]["Back"]


def test_anki_template_css_supports_anki_night_mode() -> None:
    anki = AnkiConnect()

    css = anki._build_model_css()
    expected_css = (REPOSITORY_TEMPLATE_DIR / "vocabulary.css").read_text(encoding="utf-8").strip()

    assert css == expected_css
    assert ".card.nightMode" in css
    assert "--surface-muted: #2d3748;" in css
    assert ".vocab-card {" in css
    assert "color: inherit;" in css
    assert ".vocab-card > * {" in css
    assert "margin: 0.5em 0;" in css
    assert ".generated-example {" in css
    assert "background-color: var(--surface-muted);" in css
    assert ".pronunciation-section {" in css
    assert "prefers-color-scheme: dark" not in css
