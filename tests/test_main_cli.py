import io
import builtins

import anki_vocab_automation.main as main_module


def test_main_processes_inline_entry_without_file(monkeypatch) -> None:
    captured = {}

    class FakeAutomation:
        def __init__(self, collins_api_key, data_source_strategy=None):
            captured["collins_api_key"] = collins_api_key
            captured["data_source_strategy"] = data_source_strategy

        def process_word_list(self, word_list):
            captured["mode"] = "single"
            captured["word_list"] = word_list
            return True

    monkeypatch.setattr(main_module, "VocabularyAutomation", FakeAutomation)
    monkeypatch.setattr(main_module, "DATA_SOURCE_STRATEGY", "collins_first")
    monkeypatch.setattr(main_module, "COLLINS_API_KEY", "")

    result = main_module.main(["--entry", "clarify｜I asked the teacher to clarify the lesson."])

    assert result == 0
    assert captured["mode"] == "single"
    assert captured["data_source_strategy"] == "llm_only"
    assert captured["collins_api_key"] == ""
    assert len(captured["word_list"]) == 1
    assert captured["word_list"][0].word == "clarify"
    assert captured["word_list"][0].source_example == "I asked the teacher to clarify the lesson."


def test_main_processes_stdin_entries_concurrently(monkeypatch) -> None:
    captured = {}

    class FakeAutomation:
        def __init__(self, collins_api_key, data_source_strategy=None):
            captured["collins_api_key"] = collins_api_key
            captured["data_source_strategy"] = data_source_strategy

        def process_word_list_concurrent(self, word_list, max_workers, rate_limit):
            captured["mode"] = "concurrent"
            captured["word_list"] = word_list
            captured["max_workers"] = max_workers
            captured["rate_limit"] = rate_limit
            return True

    monkeypatch.setattr(main_module, "VocabularyAutomation", FakeAutomation)
    monkeypatch.setattr(main_module, "DATA_SOURCE_STRATEGY", "collins_only")
    monkeypatch.setattr(main_module, "COLLINS_API_KEY", "")
    monkeypatch.setattr(
        main_module.sys,
        "stdin",
        io.StringIO(
            "clarify｜I asked the teacher to clarify the lesson.\n"
            "schedule|We need to change the meeting schedule again.\n"
        ),
    )

    result = main_module.main(["--stdin", "--concurrent", "--max-workers", "12", "--rate-limit", "20"])

    assert result == 0
    assert captured["mode"] == "concurrent"
    assert captured["data_source_strategy"] == "llm_only"
    assert captured["collins_api_key"] == ""
    assert len(captured["word_list"]) == 2
    assert captured["max_workers"] == 8
    assert captured["rate_limit"] == 10.0


def test_main_file_mode_still_rejects_collins_strategy_without_key(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "DATA_SOURCE_STRATEGY", "collins_first")
    monkeypatch.setattr(main_module, "COLLINS_API_KEY", "")
    monkeypatch.setattr(builtins, "input", lambda prompt="": "")

    result = main_module.main([])

    assert result == 1


def test_main_returns_non_zero_when_single_run_aborts(monkeypatch) -> None:
    class FakeAutomation:
        def __init__(self, collins_api_key, data_source_strategy=None):
            del collins_api_key, data_source_strategy

        def process_word_list(self, word_list):
            del word_list
            return False

    monkeypatch.setattr(main_module, "VocabularyAutomation", FakeAutomation)

    result = main_module.main(["--entry", "clarify｜I asked the teacher to clarify the lesson."])

    assert result == 1


def test_main_returns_non_zero_when_concurrent_run_aborts(monkeypatch) -> None:
    class FakeAutomation:
        def __init__(self, collins_api_key, data_source_strategy=None):
            del collins_api_key, data_source_strategy

        def process_word_list_concurrent(self, word_list, max_workers, rate_limit):
            del word_list, max_workers, rate_limit
            return False

    monkeypatch.setattr(main_module, "VocabularyAutomation", FakeAutomation)
    monkeypatch.setattr(
        main_module.sys,
        "stdin",
        io.StringIO("clarify｜I asked the teacher to clarify the lesson.\n"),
    )

    result = main_module.main(["--stdin", "--concurrent"])

    assert result == 1
