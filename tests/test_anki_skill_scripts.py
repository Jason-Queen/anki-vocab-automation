import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = REPO_ROOT / ".agents" / "skills"
REPO_BACKED_ANKI_SKILLS = (
    "anki-card-agent-authored",
    "anki-card-repo-llm",
    "anki-card-study-coach",
)


def _load_script_module(skill_name: str, script_name: str):
    script_path = SKILLS_ROOT / skill_name / "scripts" / script_name
    spec = importlib.util.spec_from_file_location(
        "{0}_{1}".format(skill_name.replace("-", "_"), script_name.replace(".py", "")),
        script_path,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class _FakeHeaders(dict):
    def get_content_type(self) -> str:
        return self.get("Content-Type", "").split(";", 1)[0]


class _FakeResponse:
    def __init__(self, data: bytes, content_type: str):
        self._data = data
        self.headers = _FakeHeaders({"Content-Type": content_type})

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return self._data


def _zh_labels():
    return {
        "Definition:": "中文释义：",
        "New Example:": "中文例句：",
        "Pronunciation:": "音标与发音：",
        "British:": "英式：",
        "American:": "美式：",
        "Source:": "来源：",
    }


def _ja_labels():
    return {
        "Definition:": "意味：",
        "New Example:": "例文：",
        "Pronunciation:": "発音と音声：",
        "British:": "イギリス英語：",
        "American:": "アメリカ英語：",
        "Source:": "音源：",
    }


def test_create_agent_vocab_note_rejects_text_like_local_audio(tmp_path, monkeypatch):
    module = _load_script_module("anki-card-agent-authored", "create_agent_vocab_note.py")
    bad_audio = tmp_path / "broken.mp3"
    bad_audio.write_text("<html>rate limited</html>", encoding="utf-8")

    invoke_calls = []

    def _fake_invoke(*args, **kwargs):
        invoke_calls.append((args, kwargs))
        return {"result": None}

    monkeypatch.setattr(module, "_invoke", _fake_invoke)

    with pytest.raises(ValueError, match="looked like text/html/json"):
        module._store_local_audio(
            "http://127.0.0.1:8765",
            "governance",
            {"main_audio_path": str(bad_audio)},
            "main",
        )

    assert invoke_calls == []


def test_create_agent_vocab_note_accepts_valid_local_audio_signature(tmp_path, monkeypatch):
    module = _load_script_module("anki-card-agent-authored", "create_agent_vocab_note.py")
    good_audio = tmp_path / "valid.mp3"
    good_audio.write_bytes(b"ID3" + (b"\x00" * 32))

    invoke_calls = []

    def _fake_invoke(url, action, params):
        invoke_calls.append((url, action, params))
        return {"result": None}

    monkeypatch.setattr(module, "_invoke", _fake_invoke)

    payload = {"main_audio_path": str(good_audio)}
    filename = module._store_local_audio("http://127.0.0.1:8765", "governance", payload, "main")

    assert filename.endswith(".mp3")
    assert payload["main_audio_source"] == "Local Audio"
    assert [call[1] for call in invoke_calls] == ["storeMediaFile"]


def test_create_agent_vocab_note_rejects_google_tts_html_payload(monkeypatch):
    module = _load_script_module("anki-card-agent-authored", "create_agent_vocab_note.py")

    def _fake_urlopen(request, timeout=30):
        return _FakeResponse(b"<html>Too Many Requests</html>", "text/html; charset=utf-8")

    invoke_calls = []

    def _fake_invoke(*args, **kwargs):
        invoke_calls.append((args, kwargs))
        return {"result": None}

    monkeypatch.setattr(module.urllib.request, "urlopen", _fake_urlopen)
    monkeypatch.setattr(module, "_invoke", _fake_invoke)

    with pytest.raises(ValueError, match="non-audio content-type"):
        module._store_google_tts_audio(
            "http://127.0.0.1:8765",
            "governance",
            {},
            "main",
            "en-GB",
        )

    assert invoke_calls == []


def test_create_agent_vocab_note_accepts_google_tts_with_audio_signature(monkeypatch):
    module = _load_script_module("anki-card-agent-authored", "create_agent_vocab_note.py")

    def _fake_urlopen(request, timeout=30):
        return _FakeResponse(b"ID3" + (b"\x00" * 24), "application/octet-stream")

    invoke_calls = []

    def _fake_invoke(url, action, params):
        invoke_calls.append((url, action, params))
        return {"result": None}

    monkeypatch.setattr(module.urllib.request, "urlopen", _fake_urlopen)
    monkeypatch.setattr(module, "_invoke", _fake_invoke)

    payload = {}
    filename = module._store_google_tts_audio(
        "http://127.0.0.1:8765",
        "governance",
        payload,
        "main",
        "en-GB",
    )

    assert filename.endswith(".mp3")
    assert payload["main_audio_source"] == "Google TTS"
    assert [call[1] for call in invoke_calls] == ["storeMediaFile"]


@pytest.mark.parametrize(
    "skill_name",
    ("anki-card-agent-authored", "anki-card-repo-llm"),
)
def test_localize_back_template_rebuilds_from_canonical_template(monkeypatch, skill_name):
    module = _load_script_module(skill_name, "localize_back_template.py")
    chinese_back, _ = module._localize_canonical_back_template(_zh_labels())

    update_calls = []

    def _fake_invoke(url, action, params):
        if action == "modelTemplates":
            return {
                "result": {
                    "Card 1": {
                        "Front": "<front-template>",
                        "Back": chinese_back,
                    }
                }
            }
        if action == "updateModelTemplates":
            update_calls.append(params)
            return {"result": True}
        raise AssertionError("Unexpected action: {0}".format(action))

    monkeypatch.setattr(module, "_invoke", _fake_invoke)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "localize_back_template.py",
            "--model-name",
            "Vocabulary",
            "--label-json",
            json.dumps(_ja_labels(), ensure_ascii=False),
        ],
    )

    assert module.main() == 0

    updated_template = update_calls[0]["model"]["templates"]["Card 1"]
    assert updated_template["Front"] == "<front-template>"
    assert "意味：" in updated_template["Back"]
    assert "発音と音声：" in updated_template["Back"]
    assert "中文释义：" not in updated_template["Back"]


@pytest.mark.parametrize(
    "skill_name",
    ("anki-card-agent-authored", "anki-card-repo-llm"),
)
def test_localize_back_template_rejects_unknown_mapping_keys(skill_name):
    module = _load_script_module(skill_name, "localize_back_template.py")

    with pytest.raises(ValueError, match="not found in canonical back template"):
        module._localize_canonical_back_template({"MissingLabel:": "Should fail"})


def test_anki_skill_docs_do_not_reference_root_level_scripts():
    banned_snippets = (
        "python3 scripts/",
        "`scripts/ankiconnect_request.py`",
        "`scripts/create_agent_vocab_note.py`",
        "`scripts/localize_back_template.py`",
        "`scripts/select_study_cards.py`",
        "`scripts/study_turn_assist.py`",
    )

    for skill_name in REPO_BACKED_ANKI_SKILLS:
        for path in (SKILLS_ROOT / skill_name).rglob("*"):
            if not path.is_file():
                continue
            if path.suffix not in {".md", ".py", ".yaml"}:
                continue
            text = path.read_text(encoding="utf-8")
            for snippet in banned_snippets:
                assert snippet not in text, "{0} still contains {1!r}".format(path, snippet)


@pytest.mark.parametrize("skill_name", REPO_BACKED_ANKI_SKILLS)
def test_ankiconnect_request_help_uses_repo_relative_paths(skill_name):
    script_path = SKILLS_ROOT / skill_name / "scripts" / "ankiconnect_request.py"
    result = subprocess.run(
        [sys.executable, str(script_path), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert ".agents/skills/{0}/scripts/ankiconnect_request.py".format(skill_name) in result.stdout
