#!/usr/bin/env python3
"""Select high-priority study cards from existing Anki data."""

import argparse
import html
import json
import random
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

MS_PER_DAY = 24 * 60 * 60 * 1000
DEFAULT_LIMIT = 8
DEFAULT_TIMEOUT = 30.0
DEFAULT_EASE_BASELINE = 2500
SUSPENDED_QUEUE = -1
QUESTION_HINTS = {
    "meaning_recall": "Show the word and ask for a brief meaning first.",
    "context_gap_fill": "Use the stored context example with the target word blanked out.",
    "meaning_from_context": "Show the stored context example and ask what the word means in that sentence.",
    "self_sentence": "Ask the learner to produce one short original sentence with the word.",
    "meaning_check": "Offer a simple recognition check before moving back to recall.",
}


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _clean_text(value: Any) -> str:
    if not value:
        return ""
    text = html.unescape(str(value))
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _field_value(card_info: Dict[str, Any], field_name: str) -> str:
    fields = card_info.get("fields") or {}
    field_payload = fields.get(field_name) or {}
    return _clean_text(field_payload.get("value", ""))


def _context_example(card_info: Dict[str, Any]) -> Dict[str, str]:
    example = _field_value(card_info, "Example")
    if example:
        return {"context_example": example, "context_source": "existing_example"}

    generated_example = _field_value(card_info, "GeneratedExample")
    if generated_example:
        return {"context_example": generated_example, "context_source": "generated_example"}

    return {"context_example": "", "context_source": "none"}


def _fetch_ankiconnect(
    action: str,
    params: Optional[Dict[str, Any]] = None,
    host: str = "127.0.0.1",
    port: int = 8765,
    version: int = 6,
    key: str = "",
    timeout: float = DEFAULT_TIMEOUT,
) -> Any:
    payload = {"action": action, "version": version, "params": params or {}}
    if key:
        payload["key"] = key

    request = urllib.request.Request(
        "http://{0}:{1}".format(host, port),
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError("AnkiConnect HTTP error {0}: {1}".format(exc.code, error_body))
    except urllib.error.URLError as exc:
        raise RuntimeError("AnkiConnect connection failed: {0}".format(exc.reason))

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("AnkiConnect returned invalid JSON: {0}".format(exc))

    if parsed.get("error") is not None:
        raise RuntimeError("AnkiConnect {0} failed: {1}".format(action, parsed["error"]))

    return parsed.get("result")


def _load_fixture(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _iter_reviews(raw_reviews: Any, card_id: int) -> List[Dict[str, Any]]:
    if isinstance(raw_reviews, dict):
        return list(raw_reviews.get(str(card_id), raw_reviews.get(card_id, [])) or [])
    return []


def _reason(condition: bool, reasons: List[str], text: str) -> None:
    if condition and text not in reasons:
        reasons.append(text)


def _score_card(card_info: Dict[str, Any], reviews: List[Dict[str, Any]], now_ms: int) -> Dict[str, Any]:
    card_id = _as_int(card_info.get("cardId"))
    note_id = _as_int(card_info.get("note"))
    word = _field_value(card_info, "Word")
    definition = _field_value(card_info, "Definition")
    example = _field_value(card_info, "Example")
    part_of_speech = _field_value(card_info, "PartOfSpeech")
    context_info = _context_example(card_info)
    lapses = _as_int(card_info.get("lapses"))
    reps = _as_int(card_info.get("reps"))
    factor = _as_int(card_info.get("factor"))
    interval = _as_int(card_info.get("interval"))
    queue = _as_int(card_info.get("queue"))
    due = _as_int(card_info.get("due"))
    mod = _as_int(card_info.get("mod"))
    review_count = len(reviews)
    last_review_at = None

    if reviews:
        last_review_at = max(_as_int(review.get("id")) for review in reviews)

    reasons: List[str] = []
    score = 0.0

    if last_review_at is not None:
        age_ms = max(0, now_ms - last_review_at)
        if age_ms <= 3 * MS_PER_DAY:
            score += 3.0
            reasons.append("reviewed in last 3 days")
        elif age_ms <= 7 * MS_PER_DAY:
            score += 2.0
            reasons.append("recently reviewed")
        elif age_ms <= 14 * MS_PER_DAY:
            score += 1.0
            reasons.append("reviewed in last 14 days")

    if lapses >= 2:
        score += min(float(lapses) * 2.5, 8.0)
        reasons.append("multiple lapses")
    elif lapses == 1:
        score += 2.0
        reasons.append("has lapsed before")

    if factor > 0 and factor < DEFAULT_EASE_BASELINE:
        score += min((DEFAULT_EASE_BASELINE - factor) / 200.0, 4.0)
        _reason(factor < 2200, reasons, "low ease")

    if queue in (1, 3):
        score += 1.5
        reasons.append("still in learning")

    if 0 < reps <= 3:
        score += 1.0
        reasons.append("still early in repetition")

    if review_count == 0:
        if reps == 0:
            score += 0.25
            reasons.append("new or unseen card")
        else:
            score += 0.5
            reasons.append("review history unavailable")

    return {
        "card_id": card_id,
        "note_id": note_id,
        "deck_name": _clean_text(card_info.get("deckName", "")),
        "word": word,
        "part_of_speech": part_of_speech,
        "definition": definition,
        "example": example,
        "context_example": context_info["context_example"],
        "context_source": context_info["context_source"],
        "reps": reps,
        "lapses": lapses,
        "factor": factor,
        "interval": interval,
        "queue": queue,
        "due": due,
        "mod": mod,
        "review_count": review_count,
        "last_review_at": last_review_at,
        "priority_score": round(score, 2),
        "why_selected": reasons[:3],
    }


def _question_pool(candidate: Dict[str, Any]) -> List[str]:
    if candidate.get("context_example"):
        return [
            "context_gap_fill",
            "meaning_from_context",
            "meaning_recall",
            "meaning_recall",
            "self_sentence",
        ]

    return [
        "meaning_recall",
        "meaning_check",
        "meaning_recall",
        "self_sentence",
    ]


def _is_high_load_question(question_type: str) -> bool:
    return question_type == "self_sentence"


def _assign_question_plan(cards: List[Dict[str, Any]], session_seed: int) -> List[Dict[str, Any]]:
    rng = random.Random(session_seed)
    planned_cards: List[Dict[str, Any]] = []
    previous_type = ""

    for index, candidate in enumerate(cards):
        pool = _question_pool(candidate)
        rng.shuffle(pool)
        available = [question_type for question_type in pool if question_type != previous_type] or pool
        if index == 0 or float(candidate.get("priority_score", 0.0)) >= 8.0:
            lower_load = [question_type for question_type in available if not _is_high_load_question(question_type)]
            if lower_load:
                available = lower_load
        elif previous_type and _is_high_load_question(previous_type):
            lower_load = [question_type for question_type in available if not _is_high_load_question(question_type)]
            if lower_load:
                available = lower_load
        question_type = available[0]

        planned_candidate = dict(candidate)
        planned_candidate["question_type"] = question_type
        planned_candidate["question_prompt_hint"] = QUESTION_HINTS[question_type]
        planned_cards.append(planned_candidate)
        previous_type = question_type

    return planned_cards


def _dedupe_candidates(candidates: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    selected: List[Dict[str, Any]] = []
    seen_note_ids = set()
    seen_words = set()

    for candidate in candidates:
        note_id = candidate.get("note_id")
        word_key = candidate.get("word", "").strip().lower()

        if note_id and note_id in seen_note_ids:
            continue
        if word_key and word_key in seen_words:
            continue

        if note_id:
            seen_note_ids.add(note_id)
        if word_key:
            seen_words.add(word_key)
        selected.append(candidate)

    return selected


def select_study_cards(
    cards_info: List[Dict[str, Any]],
    reviews_by_card: Dict[str, Any],
    limit: int = DEFAULT_LIMIT,
    now_ms: Optional[int] = None,
    session_seed: Optional[int] = None,
    deck_name: str = "",
    query: str = "",
) -> Dict[str, Any]:
    if now_ms is None:
        now_ms = int(time.time() * 1000)
    if session_seed is None:
        session_seed = int(time.time())

    scored_candidates: List[Dict[str, Any]] = []
    reviewed_candidates: List[Dict[str, Any]] = []
    fallback_candidates: List[Dict[str, Any]] = []

    for card_info in cards_info:
        if not isinstance(card_info, dict):
            continue

        if _as_int(card_info.get("queue")) == SUSPENDED_QUEUE:
            continue

        word = _field_value(card_info, "Word")
        if not word:
            continue

        reviews = _iter_reviews(reviews_by_card, _as_int(card_info.get("cardId")))
        candidate = _score_card(card_info, reviews, now_ms)
        scored_candidates.append(candidate)

        if candidate["review_count"] > 0:
            reviewed_candidates.append(candidate)
        else:
            fallback_candidates.append(candidate)

    def sort_key(candidate: Dict[str, Any]) -> Any:
        return (
            -float(candidate["priority_score"]),
            -_as_int(candidate.get("last_review_at")),
            -_as_int(candidate.get("lapses")),
            candidate.get("word", "").lower(),
        )

    reviewed_candidates.sort(key=sort_key)
    fallback_candidates.sort(key=sort_key)
    scored_candidates.sort(key=sort_key)

    chosen = _dedupe_candidates(reviewed_candidates)
    selection_mode = "review_history"

    if len(chosen) < limit:
        chosen = _dedupe_candidates(chosen + fallback_candidates)
        if reviewed_candidates:
            selection_mode = "mixed"
        else:
            selection_mode = "deck_fallback"

    chosen = _assign_question_plan(chosen[:limit], session_seed)

    return {
        "deck": deck_name,
        "query": query,
        "session_seed": session_seed,
        "selected_count": len(chosen),
        "candidate_count": len(scored_candidates),
        "selection_mode": selection_mode,
        "cards_with_reviews": len(reviewed_candidates),
        "cards_without_reviews": len(fallback_candidates),
        "cards": chosen,
    }


def _load_live_cards(args: argparse.Namespace) -> Dict[str, Any]:
    query = args.query or 'deck:"{0}"'.format(args.deck)
    card_ids = _fetch_ankiconnect(
        "findCards",
        {"query": query},
        host=args.host,
        port=args.port,
        version=args.version,
        key=args.key,
        timeout=args.timeout,
    )
    cards_info = _fetch_ankiconnect(
        "cardsInfo",
        {"cards": card_ids},
        host=args.host,
        port=args.port,
        version=args.version,
        key=args.key,
        timeout=args.timeout,
    )
    reviews = _fetch_ankiconnect(
        "getReviewsOfCards",
        {"cards": card_ids},
        host=args.host,
        port=args.port,
        version=args.version,
        key=args.key,
        timeout=args.timeout,
    )
    return {
        "deck": args.deck,
        "query": query,
        "cards_info": cards_info,
        "reviews_by_card": reviews,
    }


def _load_data(args: argparse.Namespace) -> Dict[str, Any]:
    if args.cards_info_file or args.reviews_file:
        if not args.cards_info_file or not args.reviews_file:
            raise ValueError("Provide both --cards-info-file and --reviews-file when using fixture mode.")
        return {
            "deck": args.deck,
            "query": args.query,
            "cards_info": _load_fixture(args.cards_info_file),
            "reviews_by_card": _load_fixture(args.reviews_file),
        }

    if not args.deck and not args.query:
        raise ValueError("Provide --deck or --query for live AnkiConnect mode.")
    return _load_live_cards(args)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Select the highest-priority study cards from existing Anki notes and review history.",
    )
    parser.add_argument("--deck", default="", help="Deck name to inspect.")
    parser.add_argument("--query", default="", help="Optional Anki search query. Defaults to deck:\"<deck>\".")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help="Maximum number of cards to return.")
    parser.add_argument("--host", default="127.0.0.1", help="AnkiConnect host (default: 127.0.0.1).")
    parser.add_argument("--port", type=int, default=8765, help="AnkiConnect port (default: 8765).")
    parser.add_argument("--version", type=int, default=6, help="AnkiConnect API version (default: 6).")
    parser.add_argument("--key", default="", help="Optional AnkiConnect API key.")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, help="HTTP timeout in seconds.")
    parser.add_argument("--cards-info-file", default="", help="Fixture JSON file for cardsInfo output.")
    parser.add_argument("--reviews-file", default="", help="Fixture JSON file for getReviewsOfCards output.")
    parser.add_argument(
        "--now-ms",
        type=int,
        default=0,
        help="Override current time in epoch milliseconds for deterministic testing.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=0,
        help="Optional session seed for reproducible randomized question types.",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print the JSON payload.")
    args = parser.parse_args()

    if args.limit <= 0:
        print("Limit must be positive.", file=sys.stderr)
        return 1

    try:
        raw_data = _load_data(args)
        payload = select_study_cards(
            cards_info=list(raw_data.get("cards_info") or []),
            reviews_by_card=dict(raw_data.get("reviews_by_card") or {}),
            limit=args.limit,
            now_ms=args.now_ms or None,
            session_seed=args.seed or None,
            deck_name=raw_data.get("deck", "") or args.deck,
            query=raw_data.get("query", "") or args.query,
        )
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print("Failed to select study cards: {0}".format(exc), file=sys.stderr)
        return 1

    if args.pretty:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
