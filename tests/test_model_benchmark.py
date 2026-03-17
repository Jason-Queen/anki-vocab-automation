from pathlib import Path

from anki_vocab_automation.model_benchmark import (
    BenchmarkCase,
    evaluate_benchmark_case,
    load_benchmark_cases,
    normalize_prompt_versions,
    run_lmstudio_benchmark,
)
from anki_vocab_automation.models import VocabularyCard


def test_load_benchmark_cases_reads_fixture() -> None:
    fixture_path = Path(__file__).resolve().parent / "fixtures" / "lmstudio_llm_benchmark_cases.json"

    cases = load_benchmark_cases(fixture_path)

    assert len(cases) == 10
    assert cases[0].case_id == "clarify_verb"
    assert cases[-1].case_id == "working_adjective"


def test_normalize_prompt_versions_defaults_to_baseline_and_revised() -> None:
    assert normalize_prompt_versions(None) == ["baseline", "revised"]
    assert normalize_prompt_versions(["revised", "baseline", "revised", "unknown"]) == ["revised", "baseline"]


def test_evaluate_benchmark_case_marks_good_output_as_pass() -> None:
    case = BenchmarkCase(
        case_id="clarify_verb",
        word="clarify",
        source_example="Please clarify the final step for me.",
        expected_lemmas=["clarify"],
        expected_parts_of_speech=["verb"],
        sense_keywords=["clear", "understand", "explain"],
        sense_min_hits=1,
        forbidden_keywords=[],
    )
    card = VocabularyCard(
        word="clarify",
        definition="To make something clear and easier to understand.",
        example=case.source_example,
        generated_example="The teacher asked him to clarify his answer in class.",
        pronunciation="/ˈklær.ɪ.faɪ/",
        audio_filename="",
        part_of_speech="verb",
        original_word="clarify",
        british_pronunciation="/ˈklær.ɪ.faɪ/",
        american_pronunciation="/ˈklær.ə.faɪ/",
    )

    evaluation = evaluate_benchmark_case(case, card)

    assert evaluation.passed is True
    assert evaluation.checks["lemma_correct"] is True
    assert evaluation.checks["part_of_speech_correct"] is True
    assert evaluation.checks["sense_correct"] is True
    assert evaluation.checks["example_mentions_target"] is True


def test_evaluate_benchmark_case_flags_wrong_lemma_and_copied_example() -> None:
    case = BenchmarkCase(
        case_id="defining_adjective",
        word="defining",
        source_example="Code execution is the defining capability that makes agentic engineering possible.",
        expected_lemmas=["defining"],
        expected_parts_of_speech=["adjective"],
        sense_keywords=["most important", "essential", "feature", "nature"],
        sense_min_hits=2,
        forbidden_keywords=["state the meaning"],
    )
    card = VocabularyCard(
        word="define",
        definition="To state the exact meaning of a word.",
        example=case.source_example,
        generated_example=case.source_example,
        pronunciation="/dɪˈfaɪn/",
        audio_filename="",
        part_of_speech="verb",
        original_word="defining",
        british_pronunciation="/dɪˈfaɪn/",
        american_pronunciation="/dɪˈfaɪn/",
    )

    evaluation = evaluate_benchmark_case(case, card)

    assert evaluation.passed is False
    assert evaluation.checks["lemma_correct"] is False
    assert evaluation.checks["part_of_speech_correct"] is False
    assert evaluation.checks["sense_correct"] is False
    assert evaluation.checks["example_distinct_from_source"] is False
    assert "lemma mismatch" in evaluation.issues


def test_evaluate_benchmark_case_accepts_calibrated_defining_wording() -> None:
    case = BenchmarkCase(
        case_id="defining_adjective",
        word="defining",
        source_example="Code execution is the defining capability that makes agentic engineering possible.",
        expected_lemmas=["defining"],
        expected_parts_of_speech=["adjective"],
        sense_keywords=["essential", "feature", "nature", "factor"],
        sense_min_hits=2,
        forbidden_keywords=["state the meaning", "meaning of a word"],
    )
    card = VocabularyCard(
        word="defining",
        definition="essential in determining the nature of something",
        example=case.source_example,
        generated_example="Trust is the defining factor in any successful partnership.",
        pronunciation="/dɪˈfaɪ.nɪŋ/",
        audio_filename="",
        part_of_speech="adjective",
        original_word="defining",
        british_pronunciation="/dɪˈfaɪ.nɪŋ/",
        american_pronunciation="/dɪˈfaɪ.nɪŋ/",
    )

    evaluation = evaluate_benchmark_case(case, card)

    assert evaluation.passed is True
    assert evaluation.matched_sense_keywords == ["essential", "factor", "nature"]


def test_evaluate_benchmark_case_does_not_treat_agentic_as_forbidden_agent() -> None:
    case = BenchmarkCase(
        case_id="agentic_adjective",
        word="agentic",
        source_example="Code execution is the defining capability that makes agentic engineering possible.",
        expected_lemmas=["agentic"],
        expected_parts_of_speech=["adjective"],
        sense_keywords=["independent", "independently", "autonomous"],
        sense_min_hits=1,
        forbidden_keywords=["agent", "chemical agent"],
    )
    card = VocabularyCard(
        word="agentic",
        definition="Having the ability to act independently and make decisions.",
        example=case.source_example,
        generated_example="The new software shows agentic behavior by solving problems alone.",
        pronunciation="/əˈdʒen.tɪk/",
        audio_filename="",
        part_of_speech="adjective",
        original_word="agentic",
        british_pronunciation="/əˈdʒen.tɪk/",
        american_pronunciation="/əˈdʒen.tɪk/",
    )

    evaluation = evaluate_benchmark_case(case, card)

    assert evaluation.checks["sense_correct"] is True
    assert "forbidden sense keywords: agent" not in evaluation.issues


def test_run_lmstudio_benchmark_returns_dual_prompt_rounds(monkeypatch) -> None:
    case = BenchmarkCase(
        case_id="defining_adjective",
        word="defining",
        source_example="Code execution is the defining capability that makes agentic engineering possible.",
        expected_lemmas=["defining"],
        expected_parts_of_speech=["adjective"],
        sense_keywords=["essential", "feature", "nature", "factor"],
        sense_min_hits=2,
        forbidden_keywords=["state the meaning"],
    )

    def make_card(word: str, part_of_speech: str, definition: str, example: str) -> VocabularyCard:
        return VocabularyCard(
            word=word,
            definition=definition,
            example=case.source_example,
            generated_example=example,
            pronunciation="/dɪˈfaɪ.nɪŋ/",
            audio_filename="",
            part_of_speech=part_of_speech,
            original_word="defining",
            british_pronunciation="/dɪˈfaɪ.nɪŋ/",
            american_pronunciation="/dɪˈfaɪ.nɪŋ/",
        )

    class FakeLLMClient:
        def __init__(self, prompt_version="baseline", **kwargs):
            del kwargs
            self.prompt_version = prompt_version

        def generate_vocabulary_card(self, word, source_example=""):
            del word, source_example
            if self.prompt_version == "baseline":
                return make_card(
                    "define",
                    "verb",
                    "to state the exact meaning of a word",
                    "Please define the technical term before the meeting.",
                )
            return make_card(
                "defining",
                "adjective",
                "essential feature that shows the nature of something",
                "Trust is the defining factor in any successful partnership.",
            )

    monkeypatch.setattr(
        "anki_vocab_automation.model_benchmark.get_installed_lmstudio_models",
        lambda base_url: ["openai/gpt-oss-20b"],
    )
    monkeypatch.setattr("anki_vocab_automation.model_benchmark.unload_all_lmstudio_models", lambda: None)
    monkeypatch.setattr(
        "anki_vocab_automation.model_benchmark.load_lmstudio_model",
        lambda model_key: (True, 1.0, ""),
    )
    monkeypatch.setattr(
        "anki_vocab_automation.model_benchmark.wait_for_lmstudio_model_ready",
        lambda model_key, base_url, timeout_seconds: (True, 0.5, 1, ""),
    )
    monkeypatch.setattr("anki_vocab_automation.model_benchmark.LLMClient", FakeLLMClient)

    result_payload = run_lmstudio_benchmark(
        models=["openai/gpt-oss-20b"],
        cases=[case],
        prompt_versions=["baseline", "revised"],
        ready_timeout_seconds=1,
    )

    assert result_payload["prompt_versions"] == ["baseline", "revised"]
    assert len(result_payload["models"]) == 1
    model_entry = result_payload["models"][0]
    assert [item["prompt_version"] for item in model_entry["prompt_runs"]] == ["baseline", "revised"]
    assert model_entry["prompt_runs"][0]["summary"]["pass_rate"] == 0.0
    assert model_entry["prompt_runs"][1]["summary"]["pass_rate"] == 100.0
    assert model_entry["comparison"]["improved_cases"] == ["defining_adjective"]
    assert model_entry["comparison"]["pass_rate_delta"] == 100.0
    assert result_payload["ranking"][0]["revised_pass_rate"] == 100.0
    assert "### Prompt: baseline" in result_payload["markdown_report"]
    assert "### Prompt: revised" in result_payload["markdown_report"]
