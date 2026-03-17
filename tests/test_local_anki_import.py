"""
Local Anki smoke test for quickly checking import results during development.

Run explicitly against a dedicated Anki test profile and deck after
`uv sync --extra test`:

    ANKI_LOCAL_TEST_RUN=1 uv run pytest \
        tests/test_local_anki_import.py -m local_anki -s
"""

import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ARTIFACT_PATH = PROJECT_ROOT / "tests" / ".artifacts" / "local_anki_import_latest.json"
TRUTHY_VALUES = ("1", "true", "yes", "on")
REQUIRED_FIELDS = (
    "Word",
    "Definition",
    "Example",
    "GeneratedExample",
    "Pronunciation",
    "PartOfSpeech",
    "BritishPronunciation",
    "AmericanPronunciation",
)
MEDIA_FIELDS = (
    "AudioFilename",
    "BritishAudioFilename",
    "AmericanAudioFilename",
)


@dataclass
class LocalAnkiImportConfig:
    """Configuration for the local-only Anki smoke test."""

    run_enabled: bool
    required_profile: Optional[str]
    deck_name: str
    model_name: str
    probe_word: str
    source_example: Optional[str]
    artifact_path: Path


def _normalize_optional(value: Optional[str]) -> Optional[str]:
    """Trim environment values and collapse empty strings to None."""
    if value is None:
        return None

    cleaned = value.strip()
    if not cleaned:
        return None

    return cleaned


def _is_truthy(value: Optional[str]) -> bool:
    """Interpret a small set of common truthy strings."""
    normalized = _normalize_optional(value)
    return bool(normalized and normalized.lower() in TRUTHY_VALUES)


def _resolve_artifact_path(raw_path: Optional[str], project_root: Path) -> Path:
    """Resolve the smoke-test artifact path relative to the project root."""
    cleaned = _normalize_optional(raw_path)
    if not cleaned:
        return project_root / "tests" / ".artifacts" / "local_anki_import_latest.json"

    artifact_path = Path(cleaned)
    if not artifact_path.is_absolute():
        artifact_path = project_root / artifact_path

    return artifact_path


def load_local_anki_import_config(
    env: Mapping[str, str], base_deck_name: str, project_root: Path = PROJECT_ROOT
) -> LocalAnkiImportConfig:
    """Build local smoke-test configuration from environment variables."""
    deck_name = _normalize_optional(env.get("ANKI_LOCAL_TEST_DECK")) or "{0}_LocalSmoke".format(base_deck_name)

    return LocalAnkiImportConfig(
        run_enabled=_is_truthy(env.get("ANKI_LOCAL_TEST_RUN")),
        required_profile=_normalize_optional(env.get("ANKI_LOCAL_TEST_PROFILE")),
        deck_name=deck_name,
        model_name=deck_name,
        probe_word=_normalize_optional(env.get("ANKI_LOCAL_TEST_WORD")) or "clarify",
        source_example=_normalize_optional(env.get("ANKI_LOCAL_TEST_SOURCE_EXAMPLE")),
        artifact_path=_resolve_artifact_path(env.get("ANKI_LOCAL_TEST_ARTIFACT"), project_root),
    )


def validate_safe_local_target(config: LocalAnkiImportConfig, base_deck_name: str) -> None:
    """Refuse to clean a deck that matches the main configured deck."""
    if config.deck_name == base_deck_name:
        raise ValueError(
            "ANKI_LOCAL_TEST_DECK must differ from DECK_NAME because the local smoke test deletes "
            "old notes in its dedicated deck before importing a fresh sample."
        )


def build_deck_query(deck_name: str) -> str:
    """Create a narrow Anki query scoped to the dedicated smoke-test deck."""
    escaped_deck_name = deck_name.replace('"', '\\"')
    return 'deck:"{0}"'.format(escaped_deck_name)


def extract_field_values(note_info: Mapping[str, Any]) -> Dict[str, str]:
    """Flatten the Anki notesInfo field payload into a simple name/value mapping."""
    fields = note_info.get("fields", {})
    extracted = {}

    for field_name, field_payload in fields.items():
        extracted[field_name] = str(field_payload.get("value", "")).strip()

    return extracted


def write_local_import_artifact(path: Path, payload: Mapping[str, Any]) -> None:
    """Persist the latest smoke-test result so developers can inspect it quickly."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _ensure_src_on_path() -> None:
    """Allow tests to import the project package without editable installation."""
    src_path = PROJECT_ROOT / "src"
    src_path_str = str(src_path)
    if src_path_str not in sys.path:
        sys.path.insert(0, src_path_str)


def _anki_request(anki_client: Any, action: str, params: Optional[Dict[str, Any]] = None) -> Any:
    """Execute an AnkiConnect request and fail loudly on API errors."""
    response = anki_client._request(action, params or {})
    if response.get("error"):
        pytest.fail("AnkiConnect {0} failed: {1}".format(action, response["error"]))
    return response.get("result")


def _collect_media_status(anki_client: Any, fields: Mapping[str, str]) -> List[Dict[str, Any]]:
    """Check whether referenced media files are actually present in Anki media."""
    media_status = []

    for field_name in MEDIA_FIELDS:
        filename = fields.get(field_name, "").strip()
        if not filename:
            media_status.append(
                {
                    "field": field_name,
                    "filename": "",
                    "present": False,
                    "size": 0,
                }
            )
            continue

        media_bytes = anki_client.retrieve_media_file(filename)
        media_status.append(
            {
                "field": field_name,
                "filename": filename,
                "present": bool(media_bytes),
                "size": len(media_bytes or b""),
            }
        )

    return media_status


def _build_artifact_payload(
    config: LocalAnkiImportConfig,
    active_profile: str,
    note_ids: List[int],
    fields: Mapping[str, str],
    media_status: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Create a compact snapshot of the imported note for local review."""
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "active_profile": active_profile,
        "deck_name": config.deck_name,
        "model_name": config.model_name,
        "probe_word": config.probe_word,
        "note_ids": note_ids,
        "fields": dict(fields),
        "media": media_status,
    }


def test_load_local_anki_import_config_defaults_to_safe_local_values(tmp_path: Path) -> None:
    """Default smoke-test config should target a dedicated deck and artifact file."""
    config = load_local_anki_import_config({}, "Vocabulary", tmp_path)

    assert config.run_enabled is False
    assert config.required_profile is None
    assert config.deck_name == "Vocabulary_LocalSmoke"
    assert config.model_name == "Vocabulary_LocalSmoke"
    assert config.probe_word == "clarify"
    assert config.source_example is None
    assert config.artifact_path == tmp_path / "tests" / ".artifacts" / "local_anki_import_latest.json"


def test_validate_safe_local_target_rejects_primary_deck_name() -> None:
    """The smoke test must never clean the main runtime deck."""
    config = LocalAnkiImportConfig(
        run_enabled=True,
        required_profile="Anki Test",
        deck_name="Vocabulary",
        model_name="Vocabulary",
        probe_word="clarify",
        source_example=None,
        artifact_path=DEFAULT_ARTIFACT_PATH,
    )

    with pytest.raises(ValueError):
        validate_safe_local_target(config, "Vocabulary")


def test_extract_field_values_flattens_notes_info_payload() -> None:
    """Anki field payloads should become simple strings for assertions and artifacts."""
    note_info = {
        "fields": {
            "Word": {"value": "clarify"},
            "Definition": {"value": "to make something easier to understand"},
        }
    }

    assert extract_field_values(note_info) == {
        "Word": "clarify",
        "Definition": "to make something easier to understand",
    }


def test_write_local_import_artifact_creates_parent_directories(tmp_path: Path) -> None:
    """Artifact writing should be safe even when the output directory does not exist yet."""
    artifact_path = tmp_path / "nested" / "local_anki_import_latest.json"
    write_local_import_artifact(artifact_path, {"word": "clarify"})

    assert artifact_path.exists()
    assert json.loads(artifact_path.read_text(encoding="utf-8")) == {"word": "clarify"}


@pytest.mark.local_anki
def test_local_anki_import_smoke() -> None:
    """Run the full local import flow against a dedicated Anki test profile."""
    _ensure_src_on_path()

    from anki_vocab_automation.config import DECK_NAME
    from anki_vocab_automation.main import VocabularyAutomation

    config = load_local_anki_import_config(os.environ, DECK_NAME)

    if not config.run_enabled:
        pytest.skip(
            "Set ANKI_LOCAL_TEST_RUN=1 to opt into the local Anki smoke test. "
            "This test talks to a live Anki profile and intentionally skips during regular pytest runs."
        )

    if not config.required_profile:
        pytest.fail("Set ANKI_LOCAL_TEST_PROFILE to the dedicated Anki test profile before running this smoke test.")

    validate_safe_local_target(config, DECK_NAME)

    automation = VocabularyAutomation()
    automation.anki_connect.deck_name = config.deck_name
    automation.anki_connect.model_name = config.model_name

    assert (
        automation.anki_connect.check_connection()
    ), "Unable to reach AnkiConnect. Start Anki with AnkiConnect enabled."

    active_profile = _anki_request(automation.anki_connect, "getActiveProfile")
    assert active_profile == config.required_profile, (
        "Active profile mismatch. Expected '{0}', got '{1}'. "
        "Open the dedicated Anki test profile before running the smoke test."
    ).format(config.required_profile, active_profile)

    assert automation.anki_connect.ensure_deck_exists(), "Failed to prepare the dedicated local smoke-test deck."
    assert automation.anki_connect.ensure_model_exists(), "Failed to prepare the dedicated local smoke-test model."

    deck_query = build_deck_query(config.deck_name)
    existing_note_ids = _anki_request(automation.anki_connect, "findNotes", {"query": deck_query})
    if existing_note_ids:
        _anki_request(automation.anki_connect, "deleteNotes", {"notes": existing_note_ids})

    assert (
        _anki_request(automation.anki_connect, "findNotes", {"query": deck_query}) == []
    ), "The dedicated smoke-test deck should be empty before importing a fresh sample."

    assert automation.process_single_word_test(
        config.probe_word,
        source_example=config.source_example or "",
    ), (
        "The import pipeline failed for '{0}'. Review logs and the configured data sources."
    ).format(config.probe_word)

    note_ids = _anki_request(automation.anki_connect, "findNotes", {"query": deck_query})
    assert len(note_ids) == 1, "Expected exactly one note in the dedicated smoke-test deck after import."

    notes_info = _anki_request(automation.anki_connect, "notesInfo", {"notes": note_ids})
    assert len(notes_info) == 1, "AnkiConnect returned an unexpected number of notes for the smoke-test deck."

    fields = extract_field_values(notes_info[0])
    media_status = _collect_media_status(automation.anki_connect, fields)
    artifact_payload = _build_artifact_payload(config, active_profile, note_ids, fields, media_status)
    write_local_import_artifact(config.artifact_path, artifact_payload)

    failures = []

    for field_name in REQUIRED_FIELDS:
        if not fields.get(field_name, "").strip():
            failures.append("Required field '{0}' is empty.".format(field_name))

    if config.source_example and fields.get("Example", "").strip() != config.source_example:
        failures.append("Expected the front-side Example field to match ANKI_LOCAL_TEST_SOURCE_EXAMPLE.")

    for media_entry in media_status:
        if media_entry["filename"] and not media_entry["present"]:
            failures.append(
                "Referenced media file '{0}' for field '{1}' was not found in Anki media.".format(
                    media_entry["filename"], media_entry["field"]
                )
            )

    print("Local Anki import snapshot written to: {0}".format(config.artifact_path))
    print(json.dumps(artifact_payload, ensure_ascii=False, indent=2))

    if failures:
        pytest.fail("\n".join(failures))
