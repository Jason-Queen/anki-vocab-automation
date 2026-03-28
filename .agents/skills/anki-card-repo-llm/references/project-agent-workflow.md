# anki-card Agent Workflow

## Repo Contract

这个仓库最近增加了适合 agent 直接调用的入口，目标是“不要新建 server，不要新建 daemon，不要另起一条 agent-only pipeline”，而是复用现有 `VocabularyAutomation` 和 `VocabularyInput`。

要点：

- 直接入口接受内联或 stdin 输入。
- 输入推荐格式是 `word<TAB>sentence`、`word｜sentence`、`word|sentence`。
- 只要使用 `--entry` 或 `--stdin`，本次运行就会强制走 `llm_only`。
- 公开网页词典核验不在仓库运行时内部做，而是留给 agent 外层流程。

仓库内优先读取这些文件：

- `.codex-work/progress.md`
- `src/anki_vocab_automation/main.py`
- `src/anki_vocab_automation/anki_connect.py`
- `README_CN.md`
- `tests/test_local_anki_import.py`

## Preferred Create Commands

单条：

```bash
uv run anki-vocab --entry 'clarify｜I asked the teacher to clarify the lesson.'
```

多条：

```bash
printf 'clarify｜I asked the teacher to clarify the lesson.\nschedule｜We need to change the meeting schedule again.\n' | \
  uv run anki-vocab --stdin --concurrent
```

仍兼容旧文件流，但对 agent 来说通常不是首选：

```bash
echo -e "sophisticated\nimplementation\noptimization" > data/New_Words.txt
uv run python app.py
```

## Input Rules

支持的直接输入分隔符：

- `TAB`
- `｜`
- `|`

示例：

```text
clarify	I asked the teacher to clarify the lesson.
fundamental	The report explains the fundamental problem in the design.
schedule | We need to change the meeting schedule again.
implementation
```

行为解释：

- 提供原句时，LLM 更容易选对词义和词性。
- 只写单词仍然可用，但结果通常不如带原句稳定。
- 多行输入会先统一解析，再由仓库已有流程处理。

## Direct Mode Behavior

当使用 `--entry` 或 `--stdin` 时：

- `active_data_source_strategy` 被强制设为 `llm_only`。
- 不再要求 `COLLINS_API_KEY`。
- 并发参数会被限制在安全范围内：
  - `--max-workers` 最多 8
  - `--rate-limit` 最多 10.0

对 agent 的含义：

- 想快速制卡时，直接 CLI 是默认路径。
- 想做公开词典核验时，先由 agent 在外层核验，再调用 CLI。
- 不要把 Collins 相关行为误认为 direct mode 会自动启用。
- 如果用户要求“背面解释性语言”不是英语，先建标准卡，再做本地化后处理。

## Preflight Checklist

先确认：

1. 当前 cwd 是仓库根目录。
2. `uv` 可用。
3. Anki 已启动。
4. AnkiConnect 插件已启用。
5. `ANKI_CONNECT_HOST` / `ANKI_CONNECT_PORT` 与当前环境一致。

可选快速检查：

```bash
python3 scripts/ankiconnect_request.py --action version --pretty
```

## Local Smoke Test

这是本仓库推荐的第一手手工验收路径。

准备：

1. 保持 `ANKI_LOCAL_TEST_RUN=false` 作为默认值。
2. 把 `ANKI_LOCAL_TEST_PROFILE` 设成专用测试账户。
3. 把 `ANKI_LOCAL_TEST_DECK` 设成可清空的专用牌组，比如 `Vocabulary_LocalSmoke`。
4. 可选：设置 `ANKI_LOCAL_TEST_SOURCE_EXAMPLE`。
5. 用专用测试账户启动 Anki，并确认 AnkiConnect 已启用。

执行：

```bash
ANKI_LOCAL_TEST_RUN=1 uv run pytest tests/test_local_anki_import.py -m local_anki -s
```

产物：

- 最新导入快照会写到 `tests/.artifacts/local_anki_import_latest.json`。
- 测试会检查字段是否为空、原句是否落到 `Example`、引用媒体是否真实存在。

## Troubleshooting

AnkiConnect 不通时：

- 确认 Anki 正在运行。
- 确认插件已安装并启用。
- 确认 host/port 没配错。
- 在 macOS 上考虑 App Nap。

导入结果不对时：

- 优先检查输入原句是否足够明确。
- 检查 `LLM_PROMPT_VERSION`。
- 对照 smoke-test artifact 看字段和媒体是否都落对了。

如果只是想知道“仓库实际封装了哪些 AnkiConnect 能力”，读 `project-anki-model.md`。

## Back Language Localization Workflow

当用户要求“背面除了音标和发音，其余都用某语种”时，推荐流程是：

1. 用仓库 CLI 正常建卡。
2. 用 `findNotes` / `notesInfo` 取回新 note。
3. 把 `PartOfSpeech`、`Definition`、`GeneratedExample` 翻译成目标语种。
4. 用 `updateNoteFields` 更新这三个字段。
5. 如果还要把背面标签也变成目标语种，再更新该隔离模型的背面模板。
6. 用 `notesInfo`、`modelTemplates`、`retrieveMediaFile` 回查。

保留英文或原文的部分通常是：

- `Word`
- `Example`
- IPA 音标
- 音频文件与播放

原因：

- 这几项承担“词形识别”和“发音训练”作用，通常不应随解释语言变化。
