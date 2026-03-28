from anki_vocab_automation.input_validator import parse_vocabulary_input


def test_parse_vocabulary_input_accepts_full_width_separator() -> None:
    entry, error = parse_vocabulary_input("clarify｜I asked the teacher to clarify the lesson.")

    assert error is None
    assert entry is not None
    assert entry.word == "clarify"
    assert entry.source_example == "I asked the teacher to clarify the lesson."


def test_parse_vocabulary_input_accepts_plain_pipe_without_spaces() -> None:
    entry, error = parse_vocabulary_input("schedule|We need to change the meeting schedule again.")

    assert error is None
    assert entry is not None
    assert entry.word == "schedule"
    assert entry.source_example == "We need to change the meeting schedule again."
