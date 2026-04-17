---
name: anki-card-agent-authored
description: "Use when Codex should directly author beginner-friendly English vocabulary card content for the anki-card repository and write it into Anki via AnkiConnect, optionally localize the back-side explanatory language, inspect the imported note or media, and fall back to Google TTS when no local TTS is available. Do not use when the goal is to reproduce the repository's local-LLM CLI behavior."
---

# Anki Card Agent-Authored

在 `anki-card` 仓库里需要由 Codex 自己完成词义判断、释义、例句和背面解释语言控制时，使用这个 skill。

## Confirm Scope

- 先确认当前工作区是 `anki-card` 仓库，并且存在 `src/anki_vocab_automation/main.py`、`src/anki_vocab_automation/anki_connect.py`、`src/anki_vocab_automation/templates/`。
- 如果用户明确要求“复现仓库现在的本地 LLM / LM Studio / CLI 行为”，不要继续本 skill，改用 `anki-card-repo-llm`。

## Workflow

1. 先做轻量 preflight：
   - `python3 .agents/skills/anki-card-agent-authored/scripts/ankiconnect_request.py --action version --pretty`
   - 必要时再看 `deckNames`、`modelFieldNames`、`getActiveProfile`
2. 如果需要字段约束、模板或重复检测规则，读 `references/project-anki-model.md`。
3. 在真正起草卡片前，读 `references/agent-authored-cards.md`。
4. 直接生成 learner-friendly payload，至少包含：
   - `word`
   - `original_word`
   - `part_of_speech`
   - `definition`
   - `example`
   - `generated_example`
   - `pronunciation`
5. 用 `python3 .agents/skills/anki-card-agent-authored/scripts/create_agent_vocab_note.py --repo-root <repo-root> --deck-name <deck> --note-json '<json>' --pretty` 导入。
6. 如果用户要求背面解释语言，读 `references/localized-back-language.md`：
   - 单卡语言切换：更新 note 字段
   - 模型级标签切换：再用 `python3 .agents/skills/anki-card-agent-authored/scripts/localize_back_template.py ...`
7. 最后用 `findNotes`、`notesInfo`、`retrieveMediaFile` 回查结果。

## Default Rules

- 默认由 Codex 直接写卡，不调用仓库 LLM。
- 默认保留 `Word`、`Example`、IPA 和音频训练部分；只本地化解释性字段。
- 默认音频策略是：优先本地真实音频；如果没有本地 TTS 且用户无特殊要求，就回落到 Google TTS；只有用户明确接受无音频时才留空。
- 有明显词义、词性或 IPA 歧义时，先核验，再导入；不要装作确定。

## Safety

- 把 `Vocabulary` 和主用 profile 视为受保护目标。
- 新流程、模板标签本地化、批量验证，优先限制在 dedicated smoke deck/model。
- 不要破坏现有字段名，也不要删除再重建 note type。
- 背面模板是模型级设置；没有用户明确确认前，不要改主模型。

## Resources

- `references/agent-authored-cards.md`: 直接写卡时的字段契约、质量标准、TTS 策略。
- `references/localized-back-language.md`: 背面解释语言切换流程和标签映射。
- `references/project-anki-model.md`: 模型字段、模板和重复检测约束。
- `references/ankiconnect-capabilities.md`: 原生 AnkiConnect action 和查询例子。
- `.agents/skills/anki-card-agent-authored/scripts/ankiconnect_request.py`: 通用 AnkiConnect 请求脚本。
- `.agents/skills/anki-card-agent-authored/scripts/create_agent_vocab_note.py`: 导入 agent 已经写好的 note payload。
- `.agents/skills/anki-card-agent-authored/scripts/localize_back_template.py`: 更新模型背面标签。
