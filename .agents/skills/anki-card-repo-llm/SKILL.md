---
name: anki-card-repo-llm
description: "Use when Codex should create or validate Anki cards through the anki-card repository's direct CLI and local-LLM workflow, including `uv run anki-vocab --entry` or `--stdin`, local model connectivity checks, post-import back-language localization, and the repository's local Anki smoke test. Do not use when Codex should directly author the card content instead of calling the repository's LLM path."
---

# Anki Card Repo LLM

在 `anki-card` 仓库里需要复现项目当前的 direct CLI / 本地 LLM 工作流时，使用这个 skill。

## Confirm Scope

- 先确认当前 cwd 是仓库根目录，并且 `uv`、`src/anki_vocab_automation/main.py`、`.codex-work/progress.md` 存在。
- 如果用户要的是“由 agent 自己直接写卡，再导入 Anki”，不要继续本 skill，改用 `anki-card-agent-authored`。

## Workflow

1. 先读 `references/project-agent-workflow.md`。
2. 做 preflight：
   - `python3 .agents/skills/anki-card-repo-llm/scripts/ankiconnect_request.py --action version --pretty`
   - 如果用户在排查模型链路，再检查本地 provider/LM Studio 是否可达
3. 单条导入优先：
   - `uv run anki-vocab --entry 'word｜sentence'`
4. 批量导入优先：
   - `uv run anki-vocab --stdin --concurrent`
5. 记住 direct mode 会强制走 `llm_only`，不要把 Collins 行为当成默认路径。
6. 如果用户要求背面解释语言，先建标准卡，再读 `references/localized-back-language.md` 做后处理。
7. 导入后用 `findNotes`、`notesInfo`、`retrieveMediaFile` 回查；如果要看更底层的原生能力，再读 `references/ankiconnect-capabilities.md`。

## Default Rules

- 只要用户明确要求“用项目当前 LLM / LM Studio / 本地模型 / direct CLI”，就优先本 skill。
- 输入优先用 `word<TAB>sentence`、`word｜sentence`、`word|sentence`。
- 需要精确复现仓库 prompt、模板字段映射、音频后备链路时，不要改成 agent-authored。

## Safety

- 本地 smoke test 只在 dedicated profile 和 dedicated deck 上运行。
- 不要把测试 deck 指到主用 `Vocabulary`。
- 记住当前运行时把 `model name` 绑定到 `deck name`。
- 不要通过删除重建模型来“修”字段或模板问题。

## Resources

- `references/project-agent-workflow.md`: direct CLI、输入格式、smoke test、常见排障。
- `references/localized-back-language.md`: 标准卡导入后的解释语言本地化流程。
- `references/project-anki-model.md`: 字段顺序、模板更新和重复检测约束。
- `references/ankiconnect-capabilities.md`: 原生 AnkiConnect 查询与动作。
- `.agents/skills/anki-card-repo-llm/scripts/ankiconnect_request.py`: 通用 AnkiConnect 请求脚本。
- `.agents/skills/anki-card-repo-llm/scripts/localize_back_template.py`: 模型级背面标签本地化脚本。
