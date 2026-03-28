import importlib.util
from pathlib import Path


def _load_selection_module():
    script_path = (
        Path(__file__).resolve().parents[1]
        / ".agents"
        / "skills"
        / "anki-card-study-coach"
        / "scripts"
        / "select_study_cards.py"
    )
    spec = importlib.util.spec_from_file_location("study_skill_select", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _card(card_id, note_id, word, definition, example, **overrides):
    payload = {
        "cardId": card_id,
        "note": note_id,
        "deckName": "Vocabulary",
        "fields": {
            "Word": {"value": word, "order": 0},
            "Definition": {"value": definition, "order": 1},
            "Example": {"value": example, "order": 2},
            "PartOfSpeech": {"value": "verb", "order": 3},
        },
        "factor": 2500,
        "interval": 4,
        "queue": 2,
        "due": 10,
        "reps": 4,
        "lapses": 0,
        "mod": 1700000000,
    }
    payload.update(overrides)
    return payload


def test_select_study_cards_prioritizes_recent_low_ease_lapses():
    module = _load_selection_module()
    now_ms = 1_750_000_000_000
    session_seed = 20260328

    cards_info = [
        _card(
            1001,
            2001,
            "clarify",
            "to make something easier to understand",
            "The teacher clarified the question.",
            factor=2050,
            reps=6,
            lapses=2,
        ),
        _card(
            1002,
            2002,
            "schedule",
            "a plan of activities or events",
            "We changed the study schedule again.",
            factor=2300,
            reps=5,
            lapses=1,
        ),
        _card(
            1003,
            2003,
            "implement",
            "to put a plan into action",
            "They implemented the new rule quickly.",
            factor=2550,
            reps=8,
            lapses=0,
        ),
    ]
    reviews = {
        "1001": [{"id": now_ms - (2 * module.MS_PER_DAY), "ease": 2}],
        "1002": [{"id": now_ms - (5 * module.MS_PER_DAY), "ease": 1}],
        "1003": [{"id": now_ms - (20 * module.MS_PER_DAY), "ease": 3}],
    }

    payload = module.select_study_cards(
        cards_info=cards_info,
        reviews_by_card=reviews,
        limit=2,
        now_ms=now_ms,
        session_seed=session_seed,
        deck_name="Vocabulary",
        query='deck:"Vocabulary"',
    )

    assert payload["selection_mode"] == "review_history"
    assert payload["session_seed"] == session_seed
    assert payload["selected_count"] == 2
    assert [card["word"] for card in payload["cards"]] == ["clarify", "schedule"]
    assert payload["cards"][0]["context_example"] == "The teacher clarified the question."
    assert payload["cards"][0]["context_source"] == "existing_example"
    assert "multiple lapses" in payload["cards"][0]["why_selected"]
    assert "has lapsed before" in payload["cards"][1]["why_selected"]
    assert payload["cards"][0]["question_type"] != "self_sentence"
    assert payload["cards"][1]["question_type"] != payload["cards"][0]["question_type"]

    repeated_payload = module.select_study_cards(
        cards_info=cards_info,
        reviews_by_card=reviews,
        limit=2,
        now_ms=now_ms,
        session_seed=session_seed,
        deck_name="Vocabulary",
        query='deck:"Vocabulary"',
    )
    assert [card["question_type"] for card in payload["cards"]] == [
        card["question_type"] for card in repeated_payload["cards"]
    ]


def test_select_study_cards_falls_back_without_reviews_and_skips_suspended_duplicates():
    module = _load_selection_module()
    now_ms = 1_750_000_000_000
    session_seed = 7

    cards_info = [
        _card(
            1101,
            2101,
            "implementation",
            "the act of putting a plan into action",
            "Implementation takes time.",
            reps=0,
            lapses=0,
            queue=0,
        ),
        _card(
            1102,
            2102,
            "implementation",
            "the act of putting a plan into action",
            "Good implementation matters.",
            reps=3,
            lapses=1,
            queue=2,
        ),
        _card(
            1103,
            2103,
            "review",
            "to study something again",
            "I need to review these words tonight.",
            reps=2,
            lapses=1,
            queue=-1,
        ),
    ]

    payload = module.select_study_cards(
        cards_info=cards_info,
        reviews_by_card={},
        limit=3,
        now_ms=now_ms,
        session_seed=session_seed,
        deck_name="Vocabulary",
        query='deck:"Vocabulary"',
    )

    assert payload["selection_mode"] == "deck_fallback"
    assert payload["selected_count"] == 1
    assert [card["word"] for card in payload["cards"]] == ["implementation"]
    assert payload["cards"][0]["note_id"] == 2102
    assert payload["cards"][0]["queue"] != -1
    assert payload["cards"][0]["context_example"] == "Good implementation matters."
    assert payload["cards"][0]["context_source"] == "existing_example"
    assert payload["cards"][0]["question_type"] in {
        "meaning_recall",
        "meaning_check",
        "meaning_from_context",
        "context_gap_fill",
        "self_sentence",
    }
