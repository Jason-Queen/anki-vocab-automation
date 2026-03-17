#!/usr/bin/env python3
"""
Run a sequential LM Studio benchmark for vocabulary-card generation models.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from anki_vocab_automation.model_benchmark import (  # noqa: E402
    DEFAULT_BENCHMARK_PROMPT_VERSIONS,
    DEFAULT_LMSTUDIO_BASE_URL,
    DEFAULT_MODELS,
    load_benchmark_cases,
    run_lmstudio_benchmark,
)

DEFAULT_CASES_PATH = PROJECT_ROOT / "tests" / "fixtures" / "lmstudio_llm_benchmark_cases.json"
DEFAULT_ARTIFACT_DIR = PROJECT_ROOT / "tests" / ".artifacts" / "model_benchmarks"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark multiple LM Studio models one at a time.")
    parser.add_argument("--base-url", default=DEFAULT_LMSTUDIO_BASE_URL, help="LM Studio base URL")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES_PATH, help="JSON file containing benchmark cases")
    parser.add_argument(
        "--artifact-dir",
        type=Path,
        default=DEFAULT_ARTIFACT_DIR,
        help="Directory to write JSON/Markdown benchmark artifacts",
    )
    parser.add_argument(
        "--load-timeout-seconds",
        type=int,
        default=900,
        help="Maximum seconds to wait for a model to finish loading",
    )
    parser.add_argument(
        "--ready-timeout-seconds",
        type=int,
        default=300,
        help="Maximum seconds to wait for a loaded model to answer a warm-up request",
    )
    parser.add_argument(
        "--case-attempts",
        type=int,
        default=2,
        help="How many times to retry a case when generation returns no card",
    )
    parser.add_argument(
        "--models",
        nargs="*",
        default=DEFAULT_MODELS,
        help="Model keys to benchmark. Defaults to the current curated model list.",
    )
    parser.add_argument(
        "--prompt-versions",
        nargs="*",
        default=list(DEFAULT_BENCHMARK_PROMPT_VERSIONS),
        help="Prompt variants to run for each model. Defaults to baseline and revised.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cases = load_benchmark_cases(args.cases)

    print("LM Studio benchmark starting")
    print("Base URL:", args.base_url)
    print("Cases:", args.cases)
    print("Models:", ", ".join(args.models))
    print("Prompt versions:", ", ".join(args.prompt_versions))
    print("Case count:", len(cases))
    print()

    args.artifact_dir.mkdir(parents=True, exist_ok=True)

    result_payload = run_lmstudio_benchmark(
        models=args.models,
        cases=cases,
        base_url=args.base_url,
        load_timeout_seconds=args.load_timeout_seconds,
        ready_timeout_seconds=args.ready_timeout_seconds,
        case_attempts=args.case_attempts,
        prompt_versions=args.prompt_versions,
    )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = args.artifact_dir / "lmstudio_model_benchmark_{0}.json".format(timestamp)
    md_path = args.artifact_dir / "lmstudio_model_benchmark_{0}.md".format(timestamp)
    latest_json_path = args.artifact_dir / "lmstudio_model_benchmark_latest.json"
    latest_md_path = args.artifact_dir / "lmstudio_model_benchmark_latest.md"

    json_path.write_text(json.dumps(result_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(result_payload["markdown_report"], encoding="utf-8")
    latest_json_path.write_text(json.dumps(result_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    latest_md_path.write_text(result_payload["markdown_report"], encoding="utf-8")

    print("JSON report:", json_path)
    print("Markdown report:", md_path)
    print()
    print("Ranking:")
    for item in result_payload["ranking"]:
        print(
            "  - {0}: status={1}, baseline_pass_rate={2}%, revised_pass_rate={3}%, delta={4}, revised_avg_score={5}".format(
                item["model"],
                item["status"],
                item["baseline_pass_rate"],
                item["revised_pass_rate"],
                item["pass_rate_delta"],
                item["revised_average_score"],
            )
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
