# LLM Benchmark Phase Summary (2026-03-17)

This note records the current phase conclusion for the local-model generation path.
It is a maintainer-facing design note, not a promise that the system is finished.

## Scope

This phase covered four connected tasks:

1. Fix the local-model transport path so models can reliably return structured cards.
2. Separate `gpt-oss` handling from other local models.
3. Build a benchmark that can compare prompt variants on the same model set.
4. Use that benchmark to identify which local models are currently reliable enough for English-learning use.

## What Was Stabilized

The following runtime behavior is now considered the current intended path:

- `gpt-oss` models use the Responses API.
- Other LM Studio and compatible local models use Chat Completions + JSON Schema.
- Reasoning/thinking content is filtered out during response extraction and is not treated as final output.
- `gpt-oss` reasoning effort is configurable with `LLM_GPT_OSS_REASONING_EFFORT`, default `medium`.
- Benchmark runs are sequential, model-by-model, with explicit load and readiness waits.
- Benchmark artifacts now record both prompt versions and their comparison deltas.

These changes were made because the older single-path approach mixed reasoning content with final content and understated several models that could in fact produce valid structured cards.

## Benchmark Setup

Date of latest full run: 2026-03-17  
Environment: local LM Studio on the maintainer machine  
Artifact files:

- [latest JSON](../tests/.artifacts/model_benchmarks/lmstudio_model_benchmark_latest.json)
- [latest Markdown](../tests/.artifacts/model_benchmarks/lmstudio_model_benchmark_latest.md)

Current benchmark shape:

- 8 models
- 10 cases
- 2 prompt rounds: `baseline` and `revised`

The current case set intentionally mixes ordinary words and harder ambiguity cases:

- basic cases: `clarify`, `instruction`, `actually`
- ambiguity and lemma cases: `running` as verb, `present`, `conduct`
- harder sense-stability cases: `defining`, `agentic`, `running` as adjective, `working`

## Aggregate Result

Across all 8 models:

- `baseline` total pass rate: `77.5%`
- `revised` total pass rate: `83.75%`

So the revised prompt is better overall, but not universally better for every model family.

## Model-Level Conclusion

### Top tier in this run

- `openai/gpt-oss-120b`
  - `baseline`: `100%`
  - `revised`: `100%`
  - Most stable model in the current benchmark.

- `qwen3.5-122b-a10b`
  - `baseline`: `90%`
  - `revised`: `100%`
  - Strongest non-`gpt-oss` model in this run, but slower than smaller models.

- `openai/gpt-oss-20b`
  - `baseline`: `70%`
  - `revised`: `100%`
  - Biggest prompt gain in this run. Very strong quality/resource tradeoff.

### Strong practical options

- `qwen/qwen3.5-35b-a3b`
  - `baseline`: `70%`
  - `revised`: `90%`
  - Fast and stable in the corrected `chat + json_schema` path.

- `nvidia/nemotron-3-super`
  - `baseline`: `90%`
  - `revised`: `90%`
  - Good quality, but load time is much worse than the better-balanced alternatives.

### Weaker or less stable options

- `unsloth/qwen3.5-27b`
  - `baseline`: `90%`
  - `revised`: `80%`
  - Still usable, but the revised prompt regressed one verb case.

- `zai-org/glm-4.7-flash`
  - `baseline`: `50%`
  - `revised`: `70%`
  - Better with the revised prompt, but structure-following is still shaky.
  - During the full run it repeatedly returned content that failed JSON extraction and needed retries.

- `nvidia/nemotron-3-nano`
  - `baseline`: `60%`
  - `revised`: `40%`
  - Too weak for this task in its current role.

## What The Benchmark Says About Prompting

The revised prompt helps mainly when the task is:

- distinguishing adjective vs verb uses of the same surface form,
- preserving the learner-sentence part of speech,
- avoiding unnecessary lemmatization.

The clearest success was `running_adjective`:

- baseline failures across models: `5`
- revised failures across models: `1`

This suggests the explicit guardrails around adjective preservation are working.

The revised prompt also clearly helped:

- `present_adjective`
  - failures dropped from `6` to `4`
- `instruction_noun`
  - failures dropped from `1` to `0`

But the revised prompt did not solve every difficult case:

- `running_verb`
  - failures stayed at `4` in both rounds

That means the current revised wording is better at "do not wrongly keep the surface form" than it is at "reliably recover the correct verb sense and lemma for all model families."

## Hard Cases That Still Matter

### `present_adjective`

This is still one of the hardest cases.
Many models drift toward other senses such as "gift" or "introduce/present".

### `running_verb`

This remains hard even after the prompt rewrite.
The problem is not only lemma recovery (`running -> run`).
Models also fail by:

- choosing the wrong sense,
- keeping the wrong example semantics,
- or producing an example that does not cleanly stay on the running/jogging sense.

### `defining_adjective`

This is no longer the catastrophic failure it was earlier in the project.
The routing fix plus calibrated scoring made it a meaningful sense-selection test instead of a broken-pipeline artifact.
However, a few weaker models still drift on the sense wording.

## Current Practical Recommendation

If the goal is to choose a local model path today, the current recommendation is:

### Quality-first

- `openai/gpt-oss-120b`
- `qwen3.5-122b-a10b`

### Best balance of quality and cost

- `openai/gpt-oss-20b`
- `qwen/qwen3.5-35b-a3b`

### Not recommended as default

- `nvidia/nemotron-3-nano`
- `zai-org/glm-4.7-flash`

## What Is Still Not Solved

These results do not mean the LLM path is now a source of lexical truth.

The project should still treat dictionary/provider data as primary for:

- lemma,
- part of speech,
- IPA,
- authoritative sense boundaries.

The current benchmark only says which local models are less risky for pedagogical generation in the current pipeline.
It does not prove that any model should replace dictionary truth.

Open work that still makes sense after this phase:

1. Choose prompt defaults by model family instead of one prompt for everyone.
2. Strengthen the `running_verb` case or add sub-cases to separate lemma failure from sense failure.
3. Keep pushing dictionary-first truth and use LLM mainly for rewriting and learner-friendly examples.
4. Add a small maintained "golden set" of especially risky words for fast smoke checks before larger reruns.

## Phase Decision

As of 2026-03-17, the repository should treat this phase as complete:

- runtime transport split is corrected,
- benchmark structure is usable,
- prompt A/B comparison is in place,
- and there is enough evidence to make model-family recommendations.

The next phase should not reopen the transport work unless a real provider regression is found.
The more valuable next step is to refine model-family defaults and keep lexical truth separate from LLM rewriting.
