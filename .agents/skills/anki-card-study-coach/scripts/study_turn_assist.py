#!/usr/bin/env python3
"""Assist one study turn with form checks and progressive hints."""

import argparse
import json
import re
from typing import Dict, List, Optional, Sequence

FORM_SENSITIVE_QUESTION_TYPES = {"context_gap_fill"}
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "can",
    "due",
    "for",
    "from",
    "had",
    "has",
    "have",
    "in",
    "is",
    "it",
    "its",
    "need",
    "needs",
    "next",
    "of",
    "on",
    "or",
    "that",
    "the",
    "their",
    "this",
    "to",
    "was",
    "we",
    "will",
    "with",
    "without",
}


def _normalize_word(value: str) -> str:
    return re.sub(r"[^a-z]", "", value.lower())


def _extract_answer_tokens(answer: str) -> List[str]:
    return [_normalize_word(token) for token in re.findall(r"[A-Za-z']+", answer) if _normalize_word(token)]


def _plural_form(word: str) -> str:
    if re.search(r"[^aeiou]y$", word):
        return word[:-1] + "ies"
    if re.search(r"(s|x|z|ch|sh|o)$", word):
        return word + "es"
    return word + "s"


def _third_person_form(word: str) -> str:
    if re.search(r"[^aeiou]y$", word):
        return word[:-1] + "ies"
    if re.search(r"(s|x|z|ch|sh|o)$", word):
        return word + "es"
    return word + "s"


def _past_form(word: str) -> str:
    if word.endswith("e"):
        return word + "d"
    if re.search(r"[^aeiou]y$", word):
        return word[:-1] + "ied"
    return word + "ed"


def _ing_form(word: str) -> str:
    if word.endswith("ie"):
        return word[:-2] + "ying"
    if word.endswith("e") and not word.endswith("ee"):
        return word[:-1] + "ing"
    return word + "ing"


def _possible_surface_forms(word: str, part_of_speech: str) -> List[str]:
    lemma = _normalize_word(word)
    pos = part_of_speech.lower().strip()
    forms = [lemma]

    if pos == "noun":
        forms.append(_plural_form(lemma))
    elif pos == "verb":
        forms.extend([
            _third_person_form(lemma),
            _past_form(lemma),
            _ing_form(lemma),
        ])

    deduped = []
    seen = set()
    for form in forms:
        if form and form not in seen:
            seen.add(form)
            deduped.append(form)
    return deduped


def _find_expected_surface_form(word: str, part_of_speech: str, context_example: str) -> str:
    lemma = _normalize_word(word)
    if not context_example:
        return lemma

    normalized_context = context_example.lower()
    candidates = sorted(_possible_surface_forms(word, part_of_speech), key=len, reverse=True)
    for form in candidates:
        if re.search(r"(?<![A-Za-z]){0}(?![A-Za-z])".format(re.escape(form)), normalized_context):
            return form
    return lemma


def _levenshtein_distance(left: str, right: str) -> int:
    if left == right:
        return 0
    if not left:
        return len(right)
    if not right:
        return len(left)

    previous = list(range(len(right) + 1))
    for i, left_char in enumerate(left, start=1):
        current = [i]
        for j, right_char in enumerate(right, start=1):
            cost = 0 if left_char == right_char else 1
            current.append(
                min(
                    previous[j] + 1,
                    current[j - 1] + 1,
                    previous[j - 1] + cost,
                )
            )
        previous = current
    return previous[-1]


def _is_near_spelling_match(answer_tokens: Sequence[str], expected_forms: Sequence[str]) -> bool:
    for token in answer_tokens:
        for expected in expected_forms:
            max_distance = 1 if max(len(token), len(expected)) <= 6 else 2
            if _levenshtein_distance(token, expected) <= max_distance:
                return True
    return False


def _form_difference_hint(lemma: str, expected_surface_form: str, part_of_speech: str) -> str:
    if expected_surface_form == lemma:
        return "Use the exact word form shown on the card."

    if part_of_speech.lower().strip() == "noun" and expected_surface_form == _plural_form(lemma):
        return "This sentence needs the plural form."

    if part_of_speech.lower().strip() == "verb":
        if expected_surface_form == _third_person_form(lemma):
            return "This sentence needs the -s verb form."
        if expected_surface_form == _past_form(lemma):
            return "This sentence needs the past form."
        if expected_surface_form == _ing_form(lemma):
            return "This sentence needs the -ing form."

    return "This sentence needs the exact form used in the card's example."


def _context_keywords(context_example: str, expected_surface_form: str) -> List[str]:
    tokens = []
    for token in re.findall(r"[A-Za-z]+", context_example.lower()):
        normalized = _normalize_word(token)
        if not normalized or normalized == expected_surface_form:
            continue
        if normalized in STOPWORDS or len(normalized) <= 3:
            continue
        if normalized not in tokens:
            tokens.append(normalized)
    return tokens[:3]


def build_hint_ladder(
    word: str,
    part_of_speech: str,
    context_example: str,
    question_type: str,
    definition: str = "",
) -> Dict[str, object]:
    lemma = _normalize_word(word)
    expected_surface_form = _find_expected_surface_form(word, part_of_speech, context_example)
    hints: List[str] = []
    pos_text = part_of_speech.strip().lower() or "word"

    if question_type in FORM_SENSITIVE_QUESTION_TYPES:
        hints.append("Part of speech: {0}.".format(pos_text))
        hints.append('It starts with "{0}" and has {1} letters.'.format(expected_surface_form[:1], len(expected_surface_form)))
        hints.append(_form_difference_hint(lemma, expected_surface_form, part_of_speech))
    elif question_type in {"meaning_recall", "meaning_from_context", "meaning_check"}:
        hints.append("Part of speech: {0}.".format(pos_text))
        keywords = _context_keywords(context_example, expected_surface_form)
        if keywords:
            hints.append("Context clue: {0}.".format(", ".join(keywords)))
        elif context_example:
            hints.append("Use the stored example sentence as your context clue.")
        if definition:
            hints.append("Short meaning clue: {0}.".format(definition))
        else:
            hints.append("Think about the core meaning used in the card's example.")
    else:
        hints.append("Part of speech: {0}.".format(pos_text))
        if context_example:
            hints.append("Reuse the pattern from this example: {0}".format(context_example))
        if definition:
            hints.append("Try a short sentence that matches this meaning: {0}.".format(definition))

    return {
        "expected_surface_form": expected_surface_form,
        "hint_ladder": hints,
    }


def assess_answer(
    word: str,
    part_of_speech: str,
    context_example: str,
    question_type: str,
    user_answer: str,
) -> Dict[str, object]:
    lemma = _normalize_word(word)
    expected_surface_form = _find_expected_surface_form(word, part_of_speech, context_example)
    expected_forms = _possible_surface_forms(word, part_of_speech)
    answer_tokens = _extract_answer_tokens(user_answer)

    if question_type not in FORM_SENSITIVE_QUESTION_TYPES:
        return {
            "mode": "manual_semantic_review",
            "status": "semantic_judgment_required",
            "semantic_judgment_required": True,
            "observed_tokens": answer_tokens,
            "expected_surface_form": expected_surface_form,
            "coach_signal": "judge_meaning_manually",
            "feedback": "Use the hint ladder or your own judgment; this question type is not auto-graded for meaning.",
            "recommended_next_step": "manual_review_or_offer_hint",
        }

    if not answer_tokens:
        return {
            "mode": "form_sensitive",
            "status": "no_attempt",
            "semantic_judgment_required": False,
            "observed_tokens": answer_tokens,
            "expected_surface_form": expected_surface_form,
            "coach_signal": "offer_hint",
            "feedback": "No usable word form was detected in the answer.",
            "recommended_next_step": "offer_next_hint",
        }

    if expected_surface_form in answer_tokens:
        return {
            "mode": "form_sensitive",
            "status": "exact_surface_match",
            "semantic_judgment_required": False,
            "observed_tokens": answer_tokens,
            "expected_surface_form": expected_surface_form,
            "coach_signal": "praise_and_continue",
            "feedback": "The expected surface form was recalled correctly.",
            "recommended_next_step": "praise_and_continue",
        }

    if lemma in answer_tokens:
        return {
            "mode": "form_sensitive",
            "status": "lemma_match_form_mismatch",
            "semantic_judgment_required": False,
            "observed_tokens": answer_tokens,
            "expected_surface_form": expected_surface_form,
            "coach_signal": "praise_partial_then_prompt_form",
            "feedback": "The learner recalled the base word, but the sentence needs a different surface form.",
            "recommended_next_step": "acknowledge_partial_then_give_form_hint",
            "form_hint": _form_difference_hint(lemma, expected_surface_form, part_of_speech),
        }

    if _is_near_spelling_match(answer_tokens, [expected_surface_form] + expected_forms):
        return {
            "mode": "form_sensitive",
            "status": "near_spelling_match",
            "semantic_judgment_required": False,
            "observed_tokens": answer_tokens,
            "expected_surface_form": expected_surface_form,
            "coach_signal": "acknowledge_near_miss_then_hint",
            "feedback": "The answer looks close in spelling, but it does not match the expected form yet.",
            "recommended_next_step": "offer_spelling_or_form_hint",
        }

    return {
        "mode": "form_sensitive",
        "status": "not_form_match",
        "semantic_judgment_required": False,
        "observed_tokens": answer_tokens,
        "expected_surface_form": expected_surface_form,
        "coach_signal": "offer_hint",
        "feedback": "The answer does not match the expected word form.",
        "recommended_next_step": "offer_next_hint",
    }


def build_turn_assist_payload(
    word: str,
    part_of_speech: str,
    context_example: str,
    question_type: str,
    definition: str = "",
    user_answer: str = "",
    hint_level: int = 0,
) -> Dict[str, object]:
    hint_payload = build_hint_ladder(word, part_of_speech, context_example, question_type, definition)
    hint_ladder = hint_payload["hint_ladder"]
    selected_hint: Optional[str] = None
    if hint_level > 0 and hint_ladder:
        selected_hint = hint_ladder[min(hint_level, len(hint_ladder)) - 1]

    return {
        "word": _normalize_word(word),
        "part_of_speech": part_of_speech.strip().lower(),
        "question_type": question_type,
        "context_example": context_example,
        "expected_surface_form": hint_payload["expected_surface_form"],
        "hint_ladder": hint_ladder,
        "requested_hint_level": hint_level,
        "hint": selected_hint,
        "answer_check": assess_answer(word, part_of_speech, context_example, question_type, user_answer),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Assess one study answer for form-sensitive prompts and generate progressive hints.",
    )
    parser.add_argument("--word", required=True, help="Target lemma from the card.")
    parser.add_argument("--part-of-speech", default="", help="Part of speech from the card.")
    parser.add_argument("--context-example", default="", help="Stored example sentence from the card.")
    parser.add_argument("--question-type", required=True, help="Current study question type.")
    parser.add_argument("--definition", default="", help="Short card definition for meaning hints.")
    parser.add_argument("--user-answer", default="", help="Learner answer to assess.")
    parser.add_argument("--hint-level", type=int, default=0, help="1-based hint level to reveal.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print the JSON payload.")
    args = parser.parse_args()

    payload = build_turn_assist_payload(
        word=args.word,
        part_of_speech=args.part_of_speech,
        context_example=args.context_example,
        question_type=args.question_type,
        definition=args.definition,
        user_answer=args.user_answer,
        hint_level=max(args.hint_level, 0),
    )

    if args.pretty:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
