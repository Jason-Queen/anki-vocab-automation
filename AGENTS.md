# AGENTS.md

## Mission
Maintain and evolve this repository into a reliable tool that creates beginner-friendly English vocabulary cards for Anki.

Optimize for:
1. lexical correctness,
2. learner usability,
3. reproducibility,
4. maintainability,
5. safe integration with external services.

Favor boring, trustworthy behavior over flashy AI behavior.

## Primary audience
- **End users:** English learners using Anki, especially beginners and lower-intermediate learners.
- **Maintainers:** humans using Codex to read, change, test, and ship the codebase.

Treat learner harm as a real bug. Examples:
- wrong sense selection,
- circular or misleading definitions,
- broken or fake audio,
- duplicate note creation,
- destructive Anki model changes,
- setup flows that are too fragile for ordinary users.

## Operating mode for Codex
- **Plan first** for multi-file work, architecture changes, external-API work, schema changes, or user-facing behavior changes.
- **Research first** when touching unstable integrations such as model names, provider capabilities, AnkiConnect behavior, Collins API behavior, TTS endpoints, or packaging/tooling.
- **Read the minimum necessary files first.** Prefer tight file selection over broad repo scans.
- **Make the smallest safe diff** that solves the task.
- **Preserve working paths** unless the task explicitly requests a migration or deprecation.
- **When behavior/config/schema/templates appear in multiple places, confirm the active runtime path first.** Prefer the smallest change that matches the current working path unless the task explicitly asks for consolidation or refactoring.
- **Run a review pass after implementation** with these lenses: learner correctness, schema compatibility, security/privacy, docs drift, test coverage.
- **Capture repeated lessons.** If the same avoidable mistake happens twice, update this file or a nearby doc.

## Execution discipline
- Work in **phases**, not endless accumulation. Each phase should have:
  - one main theme,
  - explicit non-goals,
  - a clear verification step.
- When a phase goal has been reached and verified, **stop adding behavior**. Summarize the phase, verify the touched paths, and only then start the next phase.
- Split plans into small units where each unit has:
  - one observable outcome,
  - one primary layer of code,
  - one main verification step.
- Prefer `one behavior change + one verification step + docs update if needed` over mixed broad changes.
- If the worktree becomes broad, **group by purpose before continuing**. Typical groups in this repo are:
  - runtime/integration path,
  - UI/template rendering,
  - benchmark/tests,
  - config/docs,
  - mechanical cleanup.
- Do not keep stacking new features onto a wide, unreviewed diff unless the task explicitly values speed over isolation.

## Safety / non-negotiables
- Do not `commit`, `push`, `merge`, create tags, or open PRs unless the task explicitly asks for it.
- Do not edit `config.env`, `.env*`, API keys, tokens, or auth-related flows unless the task explicitly requires it.
- Do not edit CI workflows, release/deployment config, billing-related settings, or infrastructure config unless the task explicitly requires it.
- Do not delete tests, weaken assertions, or bypass failing checks just to make the task look complete.
- Do not add new runtime or dev dependencies unless they are necessary for the task. Explain the reason and prefer existing tooling when practical.
- Avoid unrelated opportunistic changes outside the requested scope.

## Strategic direction (preferred, not assumed current state)
These are preferred directions for future iterations. Do not pretend they already exist.

- Move from script-heavy behavior toward a **schema-first core** with explicit data models, provenance, and confidence.
- Keep a **beginner-first mode** as the default user experience.
- Prefer **dictionary facts first, LLM rewriting second**.
- Replace brittle provider-specific logic with **adapters and capability-based behavior**.
- Move from live/manual-only testing toward **deterministic fixture-based unit and integration tests**.
- Preserve both **local/offline-friendly usage** and optional cloud integrations.
- Modernize Python/tooling only in **intentional, separately documented migrations**.

## Repository map (current)
### Top level
- `app.py` — interactive launcher and config wizard; currently a main user entrypoint.
- `config.env.example` — canonical configuration template.
- `requirements.txt` — legacy compatibility snapshot; the active install path is the `uv` workflow from `pyproject.toml` and `uv.lock`.
- `pyproject.toml` — packaging metadata, optional dev/test deps, formatter/linter/type-check/test config.
- `uv.lock` — committed dependency lockfile for reproducible `uv sync`.
- `.github/workflows/ci.yml` — CI currently runs `flake8`, `pytest`, `safety`, and `bandit`.
- `README.md` / `README_CN.md` — user-facing documentation.
- `setup.py` — legacy compatibility shim that points users to the `uv` workflow.
- `scripts/setup.py` — legacy compatibility shim that points users to the `uv` workflow.

### Source package
- `src/anki_vocab_automation/config.py` — env loading, defaults, config validation.
- `src/anki_vocab_automation/models.py` — core data class `VocabularyCard`.
- `src/anki_vocab_automation/collins_api.py` — Collins integration.
- `src/anki_vocab_automation/html_parser.py` — parsing fallback logic.
- `src/anki_vocab_automation/openai_compatible_client.py` — LLM integration and prompt logic.
- `src/anki_vocab_automation/tts_generator.py` — TTS URL generation; treat as legacy design.
- `src/anki_vocab_automation/audio_manager.py` — audio download/cache/temp-file handling.
- `src/anki_vocab_automation/anki_connect.py` — note model, deck, and AnkiConnect integration.
- `src/anki_vocab_automation/concurrent_processor.py` — thread-based batch processing.
- `src/anki_vocab_automation/input_validator.py` — input/file validation boundary.
- `src/anki_vocab_automation/secure_logger.py` — logging safety/sanitization.
- `src/anki_vocab_automation/main.py` — package entrypoint.

### Other directories
- `tests/test_automation.py` — mostly manual/integration-oriented; not enough as a regression suite by itself.
- `examples/` — demos and sample word lists.
- `docs/API Developer Documentation 0.4.pdf` — upstream reference asset.
- `templates/` — authoritative runtime Anki template assets loaded by `anki_connect.py`.
- `data/` — word lists and local input files.

## Product rules
### Lexical correctness
- Dictionary/provider data is the primary source of truth for:
  - headword / lemma,
  - part of speech,
  - IPA / pronunciation strings,
  - authoritative audio,
  - dictionary sense boundaries.
- LLMs may rewrite, simplify, summarize, or fill gaps, but they are **not** the primary source of lexical truth.
- Prefer **one correct, high-confidence sense** over several weak or merged senses.
- If confidence is low, **mark or skip** rather than fabricate.

### Learner-facing content
- No circular definitions.
- Beginner mode should prefer:
  - short definitions,
  - common vocabulary,
  - simple syntax,
  - short example sentences,
  - minimal idiom density,
  - one clear use at a time.
- A fancy example sentence that introduces more confusion than the target word is a bad example sentence.
- Do not silently switch from beginner-friendly output to dictionary-like dense output without an explicit product decision.

### Audio
- Broken audio is worse than missing audio metadata.
- Never claim an audio file exists unless it was actually downloaded or generated.
- Prefer authoritative dictionary audio first.
- TTS is fallback behavior, not the gold standard.

### Anki compatibility
- Duplicate note creation is a high-severity regression.
- Destructive note-model changes are high-severity regressions.
- Backward compatibility for field names and existing note structure matters.

## Change guardrails
### Entry points and UX
- Keep `app.py`, package entrypoints, and docs aligned.
- Do not add a third or fourth “main way” to run the app unless the task explicitly asks for it and docs are updated.
- Many prompts/config messages are currently Chinese-first or bilingual. Preserve that intent when editing user-facing text.
- If you change setup flow, configuration keys, default providers, or required services, update all relevant user docs in the same task:
  - `README.md`
  - `README_CN.md`
  - `config.env.example`

### Python and tooling
- Current runtime compatibility is `>=3.9`. Do not introduce 3.10+ only syntax or stdlib APIs unless the task explicitly includes a version bump plus CI/docs updates.
- For new code, prefer typed models and explicit validation over loose dict passing.
- Keep files focused. Prefer smaller modules with clear ownership over giant multi-purpose files.
- Avoid mixing broad refactors with feature work unless doing so is necessary and clearly explained.
- Do not modernize packaging/tooling opportunistically in unrelated tasks.

### Structure and abstraction heuristics
- Choose a file by **responsibility**, not by who happens to call it today.
  - config/defaults/validation belong in `config.py`,
  - external service behavior belongs in the relevant client/adapter module,
  - data shape and schema mapping belong in `models.py` or nearby validation code,
  - rendering belongs in template assets or the integration layer that owns them,
  - orchestration belongs in entrypoints such as `app.py` or `main.py`.
- Prefer adding code near the current owner module rather than creating a new file/folder too early.
- **Keep it simple** when:
  - the logic has one caller,
  - the requirements are still changing,
  - the abstraction name is unclear,
  - the extra layer would only add indirection without removing complexity.
- **Abstract** when:
  - the same logic or rule appears around three times,
  - multiple places must share one invariant,
  - the same class of bug keeps appearing in parallel paths,
  - a concept can be named clearly and defended in one sentence.
- Prefer a little duplication over premature abstraction when behavior is still unstable.
- If an abstraction needs a long explanation before it feels justified, it is probably too early.

### Test philosophy
- Default tests should be deterministic and offline.
- Any test requiring live Collins access, running Anki, public TTS, network access, or real API keys must be treated as integration/manual unless the task explicitly sets up a safe test harness.
- For Anki-facing work, use the dedicated local smoke test as the first manual verification step: `ANKI_LOCAL_TEST_RUN=1 uv run pytest tests/test_local_anki_import.py -m local_anki -s`. It must run only against the dedicated Anki test profile named by `ANKI_LOCAL_TEST_PROFILE`, and only against the disposable deck named by `ANKI_LOCAL_TEST_DECK`.
- Do not mistake `tests/test_automation.py` for sufficient regression coverage.
- For non-trivial changes, add assertion-based tests.
- When touching parsers, prompts, schema mapping, or duplicate logic, add at least one regression example.

### External services
- Do not hardcode secrets, tokens, or personal credentials.
- Do not assume model marketing names stay valid forever.
- Prefer config, capability detection, or adapter layers over scattered hardcoded provider branches.
- Before changing provider-specific behavior, verify current upstream behavior from official docs or clearly identified upstream references.
- Keep cloud services optional unless project scope explicitly changes.

## Current run and verification commands
Use the smallest relevant set first, then the broader set.

### Bootstrap
Current documented path:
```bash
uv sync
```

Maintainer / test environment:
```bash
uv sync --extra dev --extra test
```

### Run
```bash
uv run python app.py
```

Direct automation entrypoint (bypasses the interactive launcher and processes the current word list immediately):
```bash
uv run anki-vocab
```

Manual helper / live integration style check:
```bash
uv run python tests/test_automation.py
```

Recommended first-check for Anki import behavior during development:
```bash
ANKI_LOCAL_TEST_RUN=1 uv run pytest tests/test_local_anki_import.py -m local_anki -s
```

### Local quality checks
```bash
uv run pytest tests/ -v --cov=src/anki_vocab_automation --cov-report=xml
uv run flake8 src/
```

Optional when installed/configured:
```bash
uv run black .
uv run isort .
uv run mypy src
```

### Security checks
Use transient `uv` tool environments for these commands. Current upstream `safety`
and `bandit` releases require newer Python versions than the project's `>=3.9`
runtime floor, so they are not part of the default synced extras. Keep
`safety check` here for now: upstream `safety scan` prompts for interactive
login when no Safety account/API key is configured, which breaks unattended CI.

```bash
uv run --with safety safety check --json > safety-report.json
uv run --with bandit bandit -r src/ -f json -o bandit-report.json
```

If a command cannot run because the environment is missing Anki, keys, network, or optional tooling, state that clearly instead of pretending verification happened.

## Domain-specific implementation rules
### Dictionary and parser layer
- Prefer documented API/JSON responses over HTML scraping whenever possible.
- Treat `html_parser.py` as fallback behavior, not the preferred data path.
- When changing parsing selectors or heuristics, preserve before/after samples in tests or fixtures.
- Preserve British/American pronunciation distinctions and source attribution.
- Do not silently merge ambiguous senses.

### LLM layer
- Separate **lexical truth** from **pedagogical rewriting**.
- Use structured outputs or explicit schema validation when provider support makes that practical.
- Avoid making hardcoded model name tables the only source of behavior.
- Any prompt change that affects learner-facing text should ship with representative examples in tests or docs.
- Do not make the LLM path mandatory for basic usage unless the project scope explicitly changes.
- Keep local-model flows possible.

### TTS and audio layer
- Treat the current `tts_generator.py` URL-template approach as legacy.
- Do not deepen coupling to brittle public URL shapes unless there is a strong reason and the behavior has been re-verified.
- Prefer authoritative dictionary audio first.
- If TTS fallback is used, keep provider / voice / language explicit when practical.
- Verify audio by real file outcomes: existence, nonzero size, sane content type or file size.
- Be conservative with concurrent TTS/network changes; throughput gains are meaningless if downloads become flaky.

### Anki integration layer
- Current card fields come from `VocabularyCard.to_dict()` and include:
  - `Word`
  - `Definition`
  - `Example`
  - `Pronunciation`
  - `AudioFilename`
  - `PartOfSpeech`
  - `BritishPronunciation`
  - `AmericanPronunciation`
  - `BritishAudioFilename`
  - `AmericanAudioFilename`
- Do not rename or remove existing fields lightly.
- If schema changes are necessary, provide migration notes and compatibility handling.
- Prefer additive changes over destructive note-model recreation.
- Existing code currently ties the model name to the deck name in `AnkiConnect`. If you change that behavior, update docs, config assumptions, and migration guidance together.
- Preserve or improve duplicate detection.

### Concurrency and retry logic
- Throughput is not the main metric.
- A fast pipeline that creates bad cards, misses audio, or produces inconsistent results is a failure.
- Keep concurrency, retry counts, rate limits, and timeouts configurable.
- Prefer idempotent operations and clear partial-failure reporting.
- When adding caching, make cache keys sensitive to provider and source differences.

### Security and privacy
- Treat all file input, network input, and API responses as untrusted.
- Preserve or strengthen the validation boundary in `input_validator.py`.
- Preserve or strengthen log sanitization in `secure_logger.py`.
- Avoid logging raw secrets, bearer tokens, or full provider payloads unless they are sanitized.
- Avoid writing files outside intended directories (repo data dirs, temp dirs, explicit export dirs).
- If adding telemetry or remote features, they must be opt-in and documented.

## Documentation and knowledge capture
- Update docs whenever you change:
  - setup steps,
  - configuration keys,
  - provider support,
  - default behavior,
  - user-visible fields,
  - output format,
  - required runtime assumptions.
- Prefer adding design notes under `docs/` over creating new top-level markdown files.
- Keep this file practical. If repo guidance grows too large, add nested `AGENTS.md` files near the relevant code rather than turning this file into a dump.
- If a workflow becomes repetitive and stable, consider extracting it into a reusable repo skill or dedicated maintenance doc instead of bloating prompts.

## Repository TODO
- Align documented config with actual runtime behavior:
  - remove placeholder defaults that cause immediate failures (for example invalid default local model names),
  - make documented concurrency/runtime knobs actually configurable or remove them from docs/config examples,
  - keep `README.md`, `README_CN.md`, and `config.env.example` in sync with live behavior.
- Strengthen lexical correctness guardrails on the LLM path:
  - add checks for lemma/sense/part-of-speech mismatches when context indicates a different form,
  - add regression tests for inflected forms and ambiguous context sentences.
- Expand deterministic regression coverage for learner-facing behavior:
  - parser fallbacks,
  - prompt/output validation,
  - audio provenance labels,
  - template rendering assumptions that affect readability in Anki.
- Reduce maintenance drift from legacy compatibility shims:
  - keep `openai_compatible_client.py`, `setup.py`, and other compatibility entrypoints minimal,
  - document clearly which paths are primary and which are retained only for backward compatibility.

## Large-change playbook
Use this sequence for architectural or long-running tasks:
1. Write a short plan with scope, risks, assumptions, and rollback strategy.
2. Add or improve tests around current behavior before major refactoring.
3. Make one migration at a time. Examples:
   - Python/tooling upgrade
   - LLM adapter redesign
   - audio pipeline redesign
   - Anki schema/export changes
   - CLI/UI rewrite
4. Keep old and new paths side-by-side briefly when compatibility matters.
5. Remove old behavior only after verification and doc updates are complete.
6. End the phase with a short written conclusion before starting another major theme.

## Things to avoid
- Incidental full rewrites.
- Silent breaking changes to env vars, field names, deck/model naming, or file layout.
- Shipping code that depends on live APIs without deterministic test coverage for the touched logic.
- Adding always-on heavyweight infrastructure when a focused adapter or local script solves the problem.
- Checking in generated audio/media, secrets, or machine-local state.
- Claiming verification happened when it did not.

## Definition of done
A task is done only when:
- the code change is minimal, readable, and appropriate for the touched area,
- relevant checks/tests were run, or the reason they could not run is stated clearly,
- docs/config/examples were updated if behavior changed,
- security/privacy impact was considered,
- before pushing packaging-related changes or a release, `uv build` does not emit known setuptools/`pyproject.toml` metadata deprecation warnings (for example license/classifier warnings), or that follow-up is made explicit if it is truly out of scope,
- learner-facing changes include at least one before/after example in task notes or PR text,
- known follow-ups are explicit rather than hidden.

## Preferred commit and PR style
- Use conventional commits where practical:
  - `feat:`
  - `fix:`
  - `refactor:`
  - `docs:`
  - `test:`
  - `chore:`
  - `perf:`
  - `ci:`
- Separate behavioral changes from mass formatting or unrelated cleanup when practical.
- Prefer logically cohesive commits over arbitrary line-count targets.
- A `200-300` line commit is a good heuristic, not a law. A larger single-purpose commit is better than a smaller mixed-purpose commit.
- If current work spans several themes, split commits by theme before adding more code.
- A good PR/task summary includes:
  - what changed,
  - why,
  - how it was verified,
  - migration notes,
  - known risks or follow-ups.
