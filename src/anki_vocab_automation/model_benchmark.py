"""
Local LM Studio benchmark helpers for vocabulary-card generation models.
"""

import json
import re
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Dict, List, Optional, Tuple

import requests
from openai import OpenAI

from .input_validator import sanitize_word_input
from .llm_client import DEFAULT_PROMPT_VERSION, LLMClient, SUPPORTED_PROMPT_VERSIONS, is_gpt_oss_model
from .models import VocabularyCard

DEFAULT_LMSTUDIO_BASE_URL = "http://localhost:1234"
DEFAULT_BENCHMARK_PROMPT_VERSIONS = ("baseline", "revised")
DEFAULT_MODELS = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "nvidia/nemotron-3-nano",
    "zai-org/glm-4.7-flash",
    "qwen/qwen3.5-35b-a3b",
    "qwen3.5-122b-a10b",
    "unsloth/qwen3.5-27b",
    "nvidia/nemotron-3-super",
]


@dataclass
class BenchmarkCase:
    case_id: str
    word: str
    source_example: str
    expected_lemmas: List[str]
    expected_parts_of_speech: List[str]
    sense_keywords: List[str]
    sense_min_hits: int = 1
    forbidden_keywords: List[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class CaseEvaluation:
    passed: bool
    score: int
    checks: Dict[str, bool]
    issues: List[str]
    matched_sense_keywords: List[str]


@dataclass
class CaseResult:
    case_id: str
    word: str
    attempts: int
    latency_seconds: float
    evaluation: CaseEvaluation
    card: Optional[Dict[str, str]]
    error: str = ""


@dataclass
class PromptRunResult:
    prompt_version: str
    case_results: List[CaseResult]

    def summary(self) -> Dict[str, object]:
        return summarize_case_results(self.case_results)


@dataclass
class ModelRunResult:
    model: str
    status: str
    load_seconds: float
    ready_seconds: float
    ready_attempts: int
    ready_error: str
    prompt_runs: List[PromptRunResult]

    def get_prompt_run(self, prompt_version: str) -> Optional[PromptRunResult]:
        for prompt_run in self.prompt_runs:
            if prompt_run.prompt_version == prompt_version:
                return prompt_run
        return None


def load_benchmark_cases(cases_path: Path) -> List[BenchmarkCase]:
    payload = json.loads(cases_path.read_text(encoding="utf-8"))
    return [BenchmarkCase(**item) for item in payload]


def normalize_prompt_versions(prompt_versions: Optional[List[str]]) -> List[str]:
    normalized_versions = []
    for version in prompt_versions or list(DEFAULT_BENCHMARK_PROMPT_VERSIONS):
        normalized = (version or "").strip().lower()
        if normalized in SUPPORTED_PROMPT_VERSIONS and normalized not in normalized_versions:
            normalized_versions.append(normalized)

    if not normalized_versions:
        return [DEFAULT_PROMPT_VERSION]

    return normalized_versions


def summarize_case_results(case_results: List[CaseResult]) -> Dict[str, object]:
    completed_cases = [case for case in case_results if case.card]
    passed_cases = [case for case in completed_cases if case.evaluation.passed]
    scores = [case.evaluation.score for case in completed_cases]
    latencies = [case.latency_seconds for case in case_results if case.latency_seconds > 0]

    aggregate_checks = {}
    for case in completed_cases:
        for check_name, passed in case.evaluation.checks.items():
            aggregate_checks.setdefault(check_name, []).append(1 if passed else 0)

    return {
        "cases_total": len(case_results),
        "cases_completed": len(completed_cases),
        "cases_passed": len(passed_cases),
        "pass_rate": round((len(passed_cases) / len(case_results)) * 100, 2) if case_results else 0.0,
        "average_score": round(mean(scores), 2) if scores else 0.0,
        "average_latency_seconds": round(mean(latencies), 2) if latencies else 0.0,
        "check_pass_rates": {
            check_name: round((sum(values) / len(values)) * 100, 2)
            for check_name, values in aggregate_checks.items()
        },
    }


def collect_issue_counts(case_results: List[CaseResult]) -> Dict[str, int]:
    issue_counts: Dict[str, int] = {}
    for case_result in case_results:
        for issue in case_result.evaluation.issues:
            issue_counts[issue] = issue_counts.get(issue, 0) + 1
    return dict(sorted(issue_counts.items()))


def compare_prompt_runs(prompt_runs: List[PromptRunResult]) -> Dict[str, object]:
    prompt_run_map = {prompt_run.prompt_version: prompt_run for prompt_run in prompt_runs}
    baseline_run = prompt_run_map.get("baseline")
    revised_run = prompt_run_map.get("revised")

    if baseline_run is None or revised_run is None:
        return {}

    baseline_summary = baseline_run.summary()
    revised_summary = revised_run.summary()
    baseline_cases = {case_result.case_id: case_result for case_result in baseline_run.case_results}
    revised_cases = {case_result.case_id: case_result for case_result in revised_run.case_results}

    improved_cases = []
    regressed_cases = []
    score_improved_cases = []
    score_regressed_cases = []

    for case_id in sorted(set(baseline_cases) | set(revised_cases)):
        baseline_case = baseline_cases.get(case_id)
        revised_case = revised_cases.get(case_id)
        if baseline_case is None or revised_case is None:
            continue

        if not baseline_case.evaluation.passed and revised_case.evaluation.passed:
            improved_cases.append(case_id)
        if baseline_case.evaluation.passed and not revised_case.evaluation.passed:
            regressed_cases.append(case_id)
        if revised_case.evaluation.score > baseline_case.evaluation.score:
            score_improved_cases.append(case_id)
        if revised_case.evaluation.score < baseline_case.evaluation.score:
            score_regressed_cases.append(case_id)

    baseline_issue_counts = collect_issue_counts(baseline_run.case_results)
    revised_issue_counts = collect_issue_counts(revised_run.case_results)
    issue_delta = {}
    for issue in sorted(set(baseline_issue_counts) | set(revised_issue_counts)):
        delta = revised_issue_counts.get(issue, 0) - baseline_issue_counts.get(issue, 0)
        if delta:
            issue_delta[issue] = delta

    return {
        "baseline_prompt_version": baseline_run.prompt_version,
        "revised_prompt_version": revised_run.prompt_version,
        "baseline_pass_rate": baseline_summary["pass_rate"],
        "revised_pass_rate": revised_summary["pass_rate"],
        "pass_rate_delta": round(revised_summary["pass_rate"] - baseline_summary["pass_rate"], 2),
        "baseline_average_score": baseline_summary["average_score"],
        "revised_average_score": revised_summary["average_score"],
        "average_score_delta": round(revised_summary["average_score"] - baseline_summary["average_score"], 2),
        "improved_cases": improved_cases,
        "regressed_cases": regressed_cases,
        "score_improved_cases": score_improved_cases,
        "score_regressed_cases": score_regressed_cases,
        "issue_counts": {
            baseline_run.prompt_version: baseline_issue_counts,
            revised_run.prompt_version: revised_issue_counts,
        },
        "issue_delta": issue_delta,
    }


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def normalize_token(value: str) -> str:
    return sanitize_word_input((value or "").strip().lower())


def normalize_pos(value: str) -> str:
    normalized = normalize_text(value)
    aliases = {
        "adj": "adjective",
        "adv": "adverb",
        "n": "noun",
        "v": "verb",
    }
    return aliases.get(normalized, normalized)


def contains_candidate(sentence: str, candidate_words: List[str]) -> bool:
    for candidate in candidate_words:
        normalized = normalize_token(candidate)
        if not normalized:
            continue
        pattern = r"(?<![A-Za-z]){0}(?![A-Za-z])".format(re.escape(normalized))
        if re.search(pattern, sentence, re.IGNORECASE):
            return True
    return False


def contains_bounded_phrase(text: str, phrase: str) -> bool:
    """Match phrases on token boundaries to avoid false hits inside larger words."""
    normalized_text = normalize_text(text)
    normalized_phrase = normalize_text(phrase)
    if not normalized_text or not normalized_phrase:
        return False

    pattern = r"(?<![A-Za-z]){0}(?![A-Za-z])".format(re.escape(normalized_phrase))
    return re.search(pattern, normalized_text, re.IGNORECASE) is not None


def evaluate_benchmark_case(case: BenchmarkCase, card: VocabularyCard) -> CaseEvaluation:
    issues = []

    normalized_definition = normalize_text(card.definition)
    normalized_example = normalize_text(card.generated_example)
    normalized_source_example = normalize_text(case.source_example)
    normalized_headword = normalize_token(card.word)
    expected_lemmas = [normalize_token(item) for item in case.expected_lemmas]
    expected_pos = [normalize_pos(item) for item in case.expected_parts_of_speech]

    sense_text = "{0} {1}".format(card.definition or "", card.generated_example or "").lower()
    matched_sense_keywords = sorted(
        {keyword for keyword in case.sense_keywords if contains_bounded_phrase(sense_text, keyword)}
    )
    forbidden_hits = sorted(
        {keyword for keyword in case.forbidden_keywords if contains_bounded_phrase(sense_text, keyword)}
    )

    candidate_words = [case.word] + case.expected_lemmas + [card.word]
    definition_avoids_target = not contains_candidate(normalized_definition, candidate_words)
    example_mentions_target = contains_candidate(normalized_example, candidate_words)
    example_distinct = bool(normalized_example) and normalized_example != normalized_source_example

    checks = {
        "lemma_correct": normalized_headword in expected_lemmas,
        "part_of_speech_correct": normalize_pos(card.part_of_speech) in expected_pos,
        "sense_correct": len(matched_sense_keywords) >= case.sense_min_hits and not forbidden_hits,
        "definition_avoids_target": definition_avoids_target,
        "definition_length_ok": 1 <= len((card.definition or "").split()) <= 18,
        "example_mentions_target": example_mentions_target,
        "example_distinct_from_source": example_distinct,
        "example_length_ok": 6 <= len((card.generated_example or "").split()) <= 22,
        "british_pronunciation_present": bool((card.british_pronunciation or "").strip()),
        "american_pronunciation_present": bool((card.american_pronunciation or "").strip()),
    }

    if not checks["lemma_correct"]:
        issues.append("lemma mismatch")
    if not checks["part_of_speech_correct"]:
        issues.append("part-of-speech mismatch")
    if not checks["sense_correct"]:
        issues.append("sense mismatch")
    if forbidden_hits:
        issues.append("forbidden sense keywords: {0}".format(", ".join(forbidden_hits)))
    if not checks["definition_avoids_target"]:
        issues.append("definition repeats target word")
    if not checks["example_mentions_target"]:
        issues.append("generated example does not mention target or lemma")
    if not checks["example_distinct_from_source"]:
        issues.append("generated example copies the source sentence")
    if not checks["british_pronunciation_present"] or not checks["american_pronunciation_present"]:
        issues.append("missing pronunciation fields")

    score_weights = {
        "lemma_correct": 20,
        "part_of_speech_correct": 15,
        "sense_correct": 25,
        "definition_avoids_target": 10,
        "definition_length_ok": 5,
        "example_mentions_target": 10,
        "example_distinct_from_source": 5,
        "example_length_ok": 5,
        "british_pronunciation_present": 3,
        "american_pronunciation_present": 2,
    }
    score = sum(weight for check_name, weight in score_weights.items() if checks[check_name])

    passed = all(
        checks[name]
        for name in (
            "lemma_correct",
            "part_of_speech_correct",
            "sense_correct",
            "definition_avoids_target",
            "example_mentions_target",
            "example_distinct_from_source",
            "british_pronunciation_present",
            "american_pronunciation_present",
        )
    )

    return CaseEvaluation(
        passed=passed,
        score=score,
        checks=checks,
        issues=issues,
        matched_sense_keywords=matched_sense_keywords,
    )


def get_installed_lmstudio_models(base_url: str = DEFAULT_LMSTUDIO_BASE_URL) -> List[str]:
    response = requests.get("{0}/api/v0/models".format(base_url.rstrip("/")), timeout=30)
    response.raise_for_status()
    payload = response.json()
    return [item.get("id", "").strip() for item in payload.get("data", []) if item.get("id", "").strip()]


def get_lmstudio_model_state(model_key: str, base_url: str = DEFAULT_LMSTUDIO_BASE_URL) -> str:
    response = requests.get("{0}/api/v0/models/{1}".format(base_url.rstrip("/"), model_key), timeout=30)
    response.raise_for_status()
    payload = response.json()
    return str(payload.get("state", "")).strip()


def unload_all_lmstudio_models() -> None:
    if shutil.which("lms") is None:
        raise RuntimeError("找不到 lms CLI，请确认 LM Studio 已安装并可在 PATH 中使用。")
    subprocess.run(["lms", "unload", "--all"], check=False, capture_output=True, text=True)


def load_lmstudio_model(model_key: str) -> Tuple[bool, float, str]:
    if shutil.which("lms") is None:
        raise RuntimeError("找不到 lms CLI，请确认 LM Studio 已安装并可在 PATH 中使用。")

    start = time.monotonic()
    process = subprocess.run(
        ["lms", "load", model_key, "-y"],
        check=False,
        capture_output=True,
        text=True,
    )
    load_seconds = time.monotonic() - start
    output = "{0}\n{1}".format(process.stdout or "", process.stderr or "").strip()
    return process.returncode == 0, load_seconds, output


def wait_for_lmstudio_model_ready(
    model_key: str,
    base_url: str = DEFAULT_LMSTUDIO_BASE_URL,
    timeout_seconds: int = 900,
    poll_interval_seconds: int = 5,
) -> Tuple[bool, float, int, str]:
    openai_client = OpenAI(
        base_url="{0}/v1".format(base_url.rstrip("/")),
        api_key="not-needed",
        timeout=60,
    )
    start = time.monotonic()
    attempts = 0
    last_error = ""

    while time.monotonic() - start < timeout_seconds:
        attempts += 1
        try:
            state = get_lmstudio_model_state(model_key, base_url)
            if state != "loaded":
                time.sleep(poll_interval_seconds)
                continue

            if is_gpt_oss_model(model_key):
                openai_client.responses.create(
                    model=model_key,
                    instructions="Reply with READY only.",
                    input="READY",
                    temperature=0,
                    max_output_tokens=16,
                    reasoning={"effort": "low"},
                )
            else:
                openai_client.chat.completions.create(
                    model=model_key,
                    messages=[
                        {"role": "system", "content": "Reply with READY only."},
                        {"role": "user", "content": "READY"},
                    ],
                    temperature=0,
                    response_format={
                        "type": "json_schema",
                        "json_schema": {
                            "name": "readiness_probe",
                            "strict": True,
                            "schema": {
                                "type": "object",
                                "properties": {"status": {"type": "string"}},
                                "required": ["status"],
                                "additionalProperties": False,
                            },
                        },
                    },
                    max_tokens=32,
                )
            return True, time.monotonic() - start, attempts, ""
        except Exception as exc:  # pragma: no cover - integration exercised by script
            last_error = str(exc)
            time.sleep(poll_interval_seconds)

    return False, time.monotonic() - start, attempts, last_error


def run_single_case(
    client: LLMClient,
    case: BenchmarkCase,
    max_attempts: int = 2,
) -> CaseResult:
    last_error = ""

    for attempt in range(1, max_attempts + 1):
        started_at = time.monotonic()
        try:
            card = client.generate_vocabulary_card(case.word, source_example=case.source_example)
            latency_seconds = time.monotonic() - started_at
            if not card:
                last_error = "LLMClient returned no card"
                continue

            evaluation = evaluate_benchmark_case(case, card)
            return CaseResult(
                case_id=case.case_id,
                word=case.word,
                attempts=attempt,
                latency_seconds=round(latency_seconds, 2),
                evaluation=evaluation,
                card=card.to_dict(),
            )
        except Exception as exc:  # pragma: no cover - integration exercised by script
            last_error = str(exc)

    return CaseResult(
        case_id=case.case_id,
        word=case.word,
        attempts=max_attempts,
        latency_seconds=0.0,
        evaluation=CaseEvaluation(
            passed=False,
            score=0,
            checks={},
            issues=["generation failed"],
            matched_sense_keywords=[],
        ),
        card=None,
        error=last_error,
    )


def build_markdown_report(
    run_started_at: str,
    cases: List[BenchmarkCase],
    model_results: List[ModelRunResult],
) -> str:
    lines = [
        "# LM Studio Vocabulary Benchmark",
        "",
        "Generated at: {0}".format(run_started_at),
        "",
        "## Cases",
        "",
        "| Case | Word | Expected Lemma | Expected POS | Source Example |",
        "| --- | --- | --- | --- | --- |",
    ]

    for case in cases:
        lines.append(
            "| {0} | {1} | {2} | {3} | {4} |".format(
                case.case_id,
                case.word,
                ", ".join(case.expected_lemmas),
                ", ".join(case.expected_parts_of_speech),
                case.source_example.replace("|", "\\|"),
            )
        )

    lines.extend(
        [
            "",
            "## Model Summary",
            "",
            "| Model | Status | Baseline Pass | Revised Pass | Delta | "
            "Baseline Avg | Revised Avg | Delta | Load s | Ready s |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )

    for model_result in model_results:
        baseline_run = model_result.get_prompt_run("baseline")
        revised_run = model_result.get_prompt_run("revised")
        baseline_summary = baseline_run.summary() if baseline_run else {}
        revised_summary = revised_run.summary() if revised_run else {}
        comparison = compare_prompt_runs(model_result.prompt_runs)
        lines.append(
            "| {0} | {1} | {2}% | {3}% | {4} | {5} | {6} | {7} | {8} | {9} |".format(
                model_result.model,
                model_result.status,
                baseline_summary.get("pass_rate", "n/a"),
                revised_summary.get("pass_rate", "n/a"),
                comparison.get("pass_rate_delta", "n/a"),
                baseline_summary.get("average_score", "n/a"),
                revised_summary.get("average_score", "n/a"),
                comparison.get("average_score_delta", "n/a"),
                round(model_result.load_seconds, 2),
                round(model_result.ready_seconds, 2),
            )
        )

    for model_result in model_results:
        lines.extend(["", "## {0}".format(model_result.model), ""])
        if model_result.status != "completed":
            lines.append(
                "Status: `{0}`. Ready error: `{1}`".format(model_result.status, model_result.ready_error or "n/a")
            )
            continue

        comparison = compare_prompt_runs(model_result.prompt_runs)
        if comparison:
            lines.extend(
                [
                    "Prompt comparison:",
                    "- Baseline pass rate: {0}%".format(comparison["baseline_pass_rate"]),
                    "- Revised pass rate: {0}%".format(comparison["revised_pass_rate"]),
                    "- Pass-rate delta: {0}".format(comparison["pass_rate_delta"]),
                    "- Average-score delta: {0}".format(comparison["average_score_delta"]),
                    "- Improved cases: {0}".format(", ".join(comparison["improved_cases"]) or "none"),
                    "- Regressed cases: {0}".format(", ".join(comparison["regressed_cases"]) or "none"),
                    "- Score-improved cases: {0}".format(", ".join(comparison["score_improved_cases"]) or "none"),
                    "- Score-regressed cases: {0}".format(", ".join(comparison["score_regressed_cases"]) or "none"),
                    "- Issue delta: {0}".format(
                        ", ".join(
                            "{0}: {1:+d}".format(issue, delta)
                            for issue, delta in comparison["issue_delta"].items()
                        )
                        or "none"
                    ),
                ]
            )

        for prompt_run in model_result.prompt_runs:
            summary = prompt_run.summary()
            lines.extend(
                [
                    "",
                    "### Prompt: {0}".format(prompt_run.prompt_version),
                    "",
                    "Pass rate: {0}% | Average score: {1} | Average latency: {2}s".format(
                        summary["pass_rate"],
                        summary["average_score"],
                        summary["average_latency_seconds"],
                    ),
                    "",
                    "| Case | Score | Passed | Attempts | Latency s | Issues |",
                    "| --- | --- | --- | --- | --- | --- |",
                ]
            )
            for case_result in prompt_run.case_results:
                issues = ", ".join(case_result.evaluation.issues) if case_result.evaluation.issues else "OK"
                lines.append(
                    "| {0} | {1} | {2} | {3} | {4} | {5} |".format(
                        case_result.case_id,
                        case_result.evaluation.score,
                        "yes" if case_result.evaluation.passed else "no",
                        case_result.attempts,
                        case_result.latency_seconds,
                        issues.replace("|", "\\|"),
                    )
                )

    return "\n".join(lines) + "\n"


def run_lmstudio_benchmark(
    models: List[str],
    cases: List[BenchmarkCase],
    base_url: str = DEFAULT_LMSTUDIO_BASE_URL,
    load_timeout_seconds: int = 900,
    ready_timeout_seconds: int = 300,
    case_attempts: int = 2,
    prompt_versions: Optional[List[str]] = None,
) -> Dict[str, object]:
    run_started_at = datetime.now(timezone.utc).isoformat()
    selected_prompt_versions = normalize_prompt_versions(prompt_versions)
    installed_models = set(get_installed_lmstudio_models(base_url))
    model_results = []

    for model_key in models:
        if model_key not in installed_models:
            model_results.append(
                ModelRunResult(
                    model=model_key,
                    status="not_installed",
                    load_seconds=0.0,
                    ready_seconds=0.0,
                    ready_attempts=0,
                    ready_error="model not found in LM Studio",
                    prompt_runs=[],
                )
            )
            continue

        unload_all_lmstudio_models()
        loaded, load_seconds, load_output = load_lmstudio_model(model_key)
        if not loaded:
            model_results.append(
                ModelRunResult(
                    model=model_key,
                    status="load_failed",
                    load_seconds=load_seconds,
                    ready_seconds=0.0,
                    ready_attempts=0,
                    ready_error=load_output,
                    prompt_runs=[],
                )
            )
            continue

        ready, ready_seconds, ready_attempts, ready_error = wait_for_lmstudio_model_ready(
            model_key,
            base_url=base_url,
            timeout_seconds=ready_timeout_seconds,
        )
        if not ready:
            model_results.append(
                ModelRunResult(
                    model=model_key,
                    status="ready_timeout",
                    load_seconds=load_seconds,
                    ready_seconds=ready_seconds,
                    ready_attempts=ready_attempts,
                    ready_error=ready_error,
                    prompt_runs=[],
                )
            )
            continue

        prompt_runs = []
        for prompt_version in selected_prompt_versions:
            client = LLMClient(
                provider="lmstudio",
                api_mode="auto",
                base_url=base_url,
                api_key="not-needed",
                model_name=model_key,
                timeout=120,
                enable_tts=False,
                temperature=0.0,
                max_output_tokens=0,
                prompt_version=prompt_version,
            )
            case_results = [run_single_case(client, case, max_attempts=case_attempts) for case in cases]
            prompt_runs.append(
                PromptRunResult(
                    prompt_version=prompt_version,
                    case_results=case_results,
                )
            )

        model_results.append(
            ModelRunResult(
                model=model_key,
                status="completed",
                load_seconds=load_seconds,
                ready_seconds=ready_seconds,
                ready_attempts=ready_attempts,
                ready_error="",
                prompt_runs=prompt_runs,
            )
        )

    ranking = []
    for model_result in model_results:
        baseline_run = model_result.get_prompt_run("baseline")
        revised_run = model_result.get_prompt_run("revised")
        baseline_summary = baseline_run.summary() if baseline_run else {}
        revised_summary = revised_run.summary() if revised_run else {}
        comparison = compare_prompt_runs(model_result.prompt_runs)
        ranking.append(
            {
                "model": model_result.model,
                "status": model_result.status,
                "baseline_pass_rate": baseline_summary.get("pass_rate", 0.0),
                "revised_pass_rate": revised_summary.get("pass_rate", 0.0),
                "pass_rate_delta": comparison.get("pass_rate_delta", 0.0),
                "baseline_average_score": baseline_summary.get("average_score", 0.0),
                "revised_average_score": revised_summary.get("average_score", 0.0),
                "average_score_delta": comparison.get("average_score_delta", 0.0),
            }
        )

    ranking.sort(
        key=lambda item: (
            item["status"] == "completed",
            item["revised_pass_rate"],
            item["pass_rate_delta"],
            item["revised_average_score"],
        ),
        reverse=True,
    )

    result_payload = {
        "generated_at": run_started_at,
        "base_url": base_url,
        "prompt_versions": selected_prompt_versions,
        "models": [
            {
                "model": model_result.model,
                "status": model_result.status,
                "load_seconds": round(model_result.load_seconds, 2),
                "ready_seconds": round(model_result.ready_seconds, 2),
                "ready_attempts": model_result.ready_attempts,
                "ready_error": model_result.ready_error,
                "prompt_runs": [
                    {
                        "prompt_version": prompt_run.prompt_version,
                        "summary": prompt_run.summary(),
                        "case_results": [
                            {
                                "case_id": case_result.case_id,
                                "word": case_result.word,
                                "attempts": case_result.attempts,
                                "latency_seconds": case_result.latency_seconds,
                                "evaluation": asdict(case_result.evaluation),
                                "card": case_result.card,
                                "error": case_result.error,
                            }
                            for case_result in prompt_run.case_results
                        ],
                    }
                    for prompt_run in model_result.prompt_runs
                ],
                "comparison": compare_prompt_runs(model_result.prompt_runs),
            }
            for model_result in model_results
        ],
        "ranking": ranking,
        "cases": [asdict(case) for case in cases],
    }
    result_payload["markdown_report"] = build_markdown_report(run_started_at, cases, model_results)
    return result_payload
