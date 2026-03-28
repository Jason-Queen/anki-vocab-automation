#!/usr/bin/env python3
"""Create an Anki vocabulary note from agent-authored content using stdlib only."""

import argparse
import base64
import hashlib
import json
import sys
from urllib.parse import quote
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List


REQUIRED_MODEL_FIELDS: List[str] = [
    "Word",
    "PartOfSpeech",
    "Example",
    "GeneratedExample",
    "Definition",
    "Pronunciation",
    "AudioFilename",
    "AudioSource",
    "BritishPronunciation",
    "AmericanPronunciation",
    "BritishAudioFilename",
    "AmericanAudioFilename",
    "BritishAudioSource",
    "AmericanAudioSource",
]


def _load_payload(args: argparse.Namespace) -> Dict[str, Any]:
    sources = [bool(args.note_json), bool(args.note_file), bool(args.note_stdin)]
    if sum(sources) != 1:
        raise ValueError("Provide exactly one of --note-json, --note-file, or --note-stdin.")

    if args.note_json:
        payload = json.loads(args.note_json)
    elif args.note_file:
        payload = json.loads(Path(args.note_file).read_text(encoding="utf-8"))
    else:
        payload = json.loads(sys.stdin.read())

    if not isinstance(payload, dict):
        raise ValueError("Note payload must decode to a JSON object.")
    return payload


def _invoke(url: str, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
    payload = json.dumps({"action": action, "version": 6, "params": params}).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        parsed = json.loads(response.read().decode("utf-8"))
    if parsed.get("error") is not None:
        raise RuntimeError("{0} failed: {1}".format(action, parsed["error"]))
    return parsed


def _load_template_assets(repo_root: Path) -> Dict[str, str]:
    base = repo_root / "src" / "anki_vocab_automation" / "templates"
    paths = {
        "front": base / "vocabulary_front.html",
        "back": base / "vocabulary_back.html",
        "css": base / "vocabulary.css",
    }
    assets: Dict[str, str] = {}
    for key, path in paths.items():
        if not path.exists():
            raise ValueError("Missing template asset: {0}".format(path))
        assets[key] = path.read_text(encoding="utf-8").strip()
    return assets


def _ensure_deck(url: str, deck_name: str) -> None:
    decks = _invoke(url, "deckNames", {})["result"]
    if deck_name not in decks:
        _invoke(url, "createDeck", {"deck": deck_name})


def _ensure_model(url: str, model_name: str, assets: Dict[str, str]) -> None:
    model_names = _invoke(url, "modelNames", {})["result"]
    if model_name not in model_names:
        _invoke(
            url,
            "createModel",
            {
                "modelName": model_name,
                "inOrderFields": REQUIRED_MODEL_FIELDS,
                "css": assets["css"],
                "isCloze": False,
                "cardTemplates": [
                    {
                        "Name": "Card 1",
                        "Front": assets["front"],
                        "Back": assets["back"],
                    }
                ],
            },
        )
        return

    field_names = _invoke(url, "modelFieldNames", {"modelName": model_name})["result"]
    for index, field_name in enumerate(REQUIRED_MODEL_FIELDS):
        if field_name not in field_names:
            _invoke(url, "modelFieldAdd", {"modelName": model_name, "fieldName": field_name, "index": index})

    _invoke(
        url,
        "updateModelTemplates",
        {"model": {"name": model_name, "templates": {"Card 1": {"Front": assets["front"], "Back": assets["back"]}}}},
    )
    _invoke(url, "updateModelStyling", {"model": {"name": model_name, "css": assets["css"]}})


def _find_duplicate(url: str, deck_name: str, word: str) -> bool:
    query = 'deck:"{0}" Word:{1}'.format(deck_name, word)
    notes = _invoke(url, "findNotes", {"query": query})["result"]
    return bool(notes)


def _store_local_audio(url: str, word: str, payload: Dict[str, Any], slot: str) -> str:
    path_key = "{0}_audio_path".format(slot)
    source_key = "{0}_audio_source".format(slot)
    local_path = str(payload.get(path_key, "")).strip()
    if not local_path:
        payload[source_key] = str(payload.get(source_key, "")).strip()
        return ""

    file_path = Path(local_path)
    if not file_path.exists() or not file_path.is_file():
        raise ValueError("Audio file not found for {0}: {1}".format(slot, local_path))

    source_hash = hashlib.md5(local_path.encode("utf-8")).hexdigest()[:8]
    safe_word = "".join(char for char in word if char.isalnum() or char in "._-")[:20] or "audio"
    extension = file_path.suffix or ".mp3"
    filename = "vocab_{0}_{1}_{2}{3}".format(safe_word, slot, source_hash, extension)
    encoded = base64.b64encode(file_path.read_bytes()).decode("utf-8")
    _invoke(url, "storeMediaFile", {"filename": filename, "data": encoded})
    payload[source_key] = str(payload.get(source_key, "")).strip() or "Local Audio"
    return filename


def _google_tts_url(word: str, language: str) -> str:
    if language == "en-GB":
        tl = "en-gb"
    elif language == "en-US":
        tl = "en-us"
    else:
        tl = "en"
    return "https://translate.google.com/translate_tts?ie=UTF-8&tl={0}&client=tw-ob&q={1}".format(
        tl,
        quote(word),
    )


def _download_bytes(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Anki-Vocabulary-Automation/2.0 (Agent Authored Audio)"},
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        data = response.read()
    if not data:
        raise RuntimeError("Downloaded audio was empty: {0}".format(url))
    return data


def _store_google_tts_audio(url: str, word: str, payload: Dict[str, Any], slot: str, language: str) -> str:
    source_key = "{0}_audio_source".format(slot)
    audio_url = _google_tts_url(word, language)
    source_hash = hashlib.md5(audio_url.encode("utf-8")).hexdigest()[:8]
    safe_word = "".join(char for char in word if char.isalnum() or char in "._-")[:20] or "audio"
    filename = "vocab_{0}_{1}_{2}.mp3".format(safe_word, slot, source_hash)
    encoded = base64.b64encode(_download_bytes(audio_url)).decode("utf-8")
    _invoke(url, "storeMediaFile", {"filename": filename, "data": encoded})
    payload[source_key] = "Google TTS"
    return filename


def _build_fields(payload: Dict[str, Any]) -> Dict[str, str]:
    word = str(payload.get("word", "")).strip()
    pronunciation = str(payload.get("pronunciation", "")).strip()
    main_audio = str(payload.get("main_audio_filename", "")).strip()
    main_audio_source = str(payload.get("main_audio_source", "")).strip()

    british_pronunciation = str(payload.get("british_pronunciation", "")).strip() or pronunciation
    american_pronunciation = str(payload.get("american_pronunciation", "")).strip() or pronunciation
    british_audio = str(payload.get("british_audio_filename", "")).strip() or main_audio
    american_audio = str(payload.get("american_audio_filename", "")).strip() or main_audio
    british_source = str(payload.get("british_audio_source", "")).strip() or main_audio_source
    american_source = str(payload.get("american_audio_source", "")).strip() or main_audio_source

    generated_example = str(payload.get("generated_example", "")).strip()
    example = str(payload.get("example", "")).strip()
    if not generated_example:
        generated_example = example

    return {
        "Word": word,
        "PartOfSpeech": str(payload.get("part_of_speech", "")).strip(),
        "Example": example,
        "GeneratedExample": generated_example,
        "Definition": str(payload.get("definition", "")).strip(),
        "Pronunciation": pronunciation,
        "AudioFilename": main_audio,
        "AudioSource": main_audio_source,
        "BritishPronunciation": british_pronunciation,
        "AmericanPronunciation": american_pronunciation,
        "BritishAudioFilename": british_audio,
        "AmericanAudioFilename": american_audio,
        "BritishAudioSource": british_source,
        "AmericanAudioSource": american_source,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Write an agent-authored vocabulary card into Anki using the repo model contract.",
    )
    parser.add_argument("--repo-root", default=".", help="anki-card repository root (default: current directory).")
    parser.add_argument("--host", default="127.0.0.1", help="AnkiConnect host (default: 127.0.0.1).")
    parser.add_argument("--port", type=int, default=8765, help="AnkiConnect port (default: 8765).")
    parser.add_argument("--deck-name", default="", help="Override deck/model name for this note.")
    parser.add_argument("--allow-duplicate", action="store_true", help="Allow duplicates in the target deck.")
    parser.add_argument(
        "--audio-policy",
        choices=("google", "none"),
        default="google",
        help="Fallback audio policy when local audio paths are absent (default: google).",
    )
    parser.add_argument("--note-json", default="", help="Inline JSON payload for the note.")
    parser.add_argument("--note-file", default="", help="Path to a JSON file containing the note payload.")
    parser.add_argument("--note-stdin", action="store_true", help="Read the note payload JSON object from stdin.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print the import result.")
    args = parser.parse_args()

    try:
        repo_root = Path(args.repo_root).resolve()
        payload = _load_payload(args)
        word = str(payload.get("word", "")).strip()
        if not word:
            raise ValueError("Payload must include a non-empty 'word'.")

        deck_name = (args.deck_name or str(payload.get("deck_name", "")).strip() or "Vocabulary").strip()
        url = "http://{0}:{1}".format(args.host, args.port)
        assets = _load_template_assets(repo_root)

        _invoke(url, "version", {})
        _ensure_deck(url, deck_name)
        _ensure_model(url, deck_name, assets)

        if not args.allow_duplicate and _find_duplicate(url, deck_name, word):
            output = {"ok": False, "duplicate": True, "word": word, "deckName": deck_name}
            print(json.dumps(output, ensure_ascii=False, indent=2 if args.pretty else None))
            return 2

        payload["main_audio_filename"] = _store_local_audio(url, word, payload, "main")
        payload["british_audio_filename"] = _store_local_audio(url, word, payload, "british")
        payload["american_audio_filename"] = _store_local_audio(url, word, payload, "american")

        if args.audio_policy == "google":
            if not payload["main_audio_filename"]:
                payload["main_audio_filename"] = _store_google_tts_audio(url, word, payload, "main", "en-GB")
            if not payload["british_audio_filename"]:
                payload["british_audio_filename"] = _store_google_tts_audio(url, word, payload, "british", "en-GB")
            if not payload["american_audio_filename"]:
                payload["american_audio_filename"] = _store_google_tts_audio(url, word, payload, "american", "en-US")

        fields = _build_fields(payload)
        note = {"deckName": deck_name, "modelName": deck_name, "fields": fields, "tags": []}
        note_id = _invoke(url, "addNote", {"note": note})["result"]

        result = {
            "ok": True,
            "noteId": note_id,
            "word": word,
            "deckName": deck_name,
            "modelName": deck_name,
            "audio": {
                "main": payload.get("main_audio_filename", ""),
                "british": payload.get("british_audio_filename", ""),
                "american": payload.get("american_audio_filename", ""),
            },
        }
        print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
        return 0
    except Exception as exc:
        print("Failed to create agent-authored note: {0}".format(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
