import importlib.util
from pathlib import Path


def _load_turn_assist_module():
    script_path = (
        Path(__file__).resolve().parents[1]
        / ".agents"
        / "skills"
        / "anki-card-study-coach"
        / "scripts"
        / "study_turn_assist.py"
    )
    spec = importlib.util.spec_from_file_location("study_turn_assist", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_gap_fill_detects_lemma_match_but_surface_form_mismatch():
    module = _load_turn_assist_module()

    payload = module.build_turn_assist_payload(
        word="circumstance",
        part_of_speech="noun",
        context_example="We had to cancel the trip due to unforeseen circumstances.",
        question_type="context_gap_fill",
        definition="a condition or fact affecting a situation",
        user_answer="circumstance",
        hint_level=3,
    )

    assert payload["expected_surface_form"] == "circumstances"
    assert payload["answer_check"]["status"] == "lemma_match_form_mismatch"
    assert payload["answer_check"]["coach_signal"] == "praise_partial_then_prompt_form"
    assert payload["answer_check"]["form_hint"] == "This sentence needs the plural form."
    assert payload["hint"] == "This sentence needs the plural form."


def test_gap_fill_hint_ladder_uses_pos_then_first_letter_then_form_hint():
    module = _load_turn_assist_module()

    payload = module.build_turn_assist_payload(
        word="circumstance",
        part_of_speech="noun",
        context_example="We had to cancel the trip due to unforeseen circumstances.",
        question_type="context_gap_fill",
        definition="a condition or fact affecting a situation",
        user_answer="",
        hint_level=2,
    )

    assert payload["hint_ladder"][0] == "Part of speech: noun."
    assert payload["hint_ladder"][1] == 'It starts with "c" and has 13 letters.'
    assert payload["hint_ladder"][2] == "This sentence needs the plural form."
    assert payload["answer_check"]["status"] == "no_attempt"
    assert payload["hint"] == 'It starts with "c" and has 13 letters.'


def test_meaning_questions_require_manual_semantic_review_but_offer_context_hints():
    module = _load_turn_assist_module()

    payload = module.build_turn_assist_payload(
        word="implement",
        part_of_speech="verb",
        context_example="The company will implement a new safety policy next month.",
        question_type="meaning_from_context",
        definition="to put a plan, decision, or policy into effect",
        user_answer="实施",
        hint_level=2,
    )

    assert payload["answer_check"]["status"] == "semantic_judgment_required"
    assert payload["answer_check"]["semantic_judgment_required"] is True
    assert payload["hint_ladder"][0] == "Part of speech: verb."
    assert payload["hint_ladder"][1] == "Context clue: company, safety, policy."
    assert payload["hint"] == "Context clue: company, safety, policy."
