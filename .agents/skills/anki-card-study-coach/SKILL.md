---
name: anki-card-study-coach
description: "Use when Codex should inspect existing Anki vocabulary cards and review history in this anki-card workspace, choose the highest-priority words to practice, and run a short read-only interactive study session. Do not use when the task is to create new cards or reproduce the repository CLI workflow."
---

# Anki Card Study Coach

在 `anki-card` 仓库里需要由 Codex 利用 AnkiConnect 读取用户已经存在的卡片和复习记录，挑选最值得练的词，并进行短时互动学习时，使用这个 skill。

## Confirm Scope

- 先确认当前工作区是 `anki-card` 仓库，并且存在 `.agents/skills/anki-card-study-coach/`、`src/anki_vocab_automation/anki_connect.py`、`tests/`。
- 如果用户明确要求“创建新卡”“复现仓库 CLI / 本地 LLM 工作流”，不要继续本 skill，改用 `anki-card-agent-authored` 或 `anki-card-repo-llm`。

## Workflow

1. 先做轻量 preflight：
   - `python3 .agents/skills/anki-card-study-coach/scripts/ankiconnect_request.py --action version --pretty`
   - 必要时再看 `getActiveProfile`、`deckNames`
2. 如果要确认原生 action、查询写法或 context 例句来源，读 `references/ankiconnect-study-queries.md`。
3. 如果要确认互动引导方式，读 `references/efl-coaching-guidelines.md`。
4. 用 `python3 .agents/skills/anki-card-study-coach/scripts/select_study_cards.py --deck <deck> --limit <n> --seed <seed> --pretty` 生成候选练习词和本轮题型计划。
   - 没有指定 `--seed` 时，脚本会自动生成一个 session seed，并在输出里回显。
5. 如果筛选结果需要排查，再用 `findCards`、`cardsInfo`、`getReviewsOfCards` 做只读核对。
6. 进行 5 到 10 题的小型互动练习。优先一次只练一个词，跟随脚本规划的随机题型，但保持 beginner-friendly。
7. 如果用户答不上来、明显接近、或者是 gap-fill 这类词形敏感题，运行：
   - `python3 .agents/skills/anki-card-study-coach/scripts/study_turn_assist.py --word <word> --part-of-speech <pos> --context-example '<example>' --question-type <type> --definition '<definition>' --user-answer '<answer>' --hint-level <n> --pretty`
8. 结束后输出简短总结：今天练了哪些词、哪些词不稳、下次建议练什么。

## Default Rules

- 默认只读。不要自动调用 `guiAnswerCard`、`updateNoteFields`、`deleteNotes` 或其他写操作。
- 默认优先使用最近有复习记录、`lapses` 较多、`factor` 较低的词。
- 默认优先使用 note 里已有的 `Example` 作为 `context_example`。只有它为空时，才退到 `GeneratedExample` 或非 context 题型。
- 默认在一轮会话里随机切换题型，但要避免连续多个高负担产出题。
- 默认把“词义方向对，但词形不对”视为部分正确，而不是直接判全错。
- 默认提示模式是一层一层给：先词性，再首字母/长度或 context clue，再必要的词形提示，最后才公布答案。
- 如果读不到 review 历史，要明确说明已经降级为 deck 内普通练习，不要假装有个性化能力。
- 优先短定义、单一词义、短例句、简单反馈，保持 beginner-friendly。
- 不要根据少量日志夸大“掌握程度”；最多说“最近不稳定”“近期较熟”“缺少足够记录”。

## Safety

- 把 `Vocabulary` 和主用 profile 视为受保护目标。
- 没有用户明确确认前，不要驱动 Anki GUI 提交评分。
- 没有用户明确确认前，不要修改 note、tag、model、deck、media。
- 没必要时不要扫描用户所有牌组；优先只看用户指定 deck，或者当前配置的默认 deck。

## Resources

- `references/study-session-rules.md`: 学习会话节奏、题型和反馈边界。
- `references/efl-coaching-guidelines.md`: 研究导向的 EFL 引导原则和反馈策略。
- `references/ankiconnect-study-queries.md`: 只读查询动作、示例命令、降级规则。
- `.agents/skills/anki-card-study-coach/scripts/ankiconnect_request.py`: 通用 AnkiConnect 请求脚本。
- `.agents/skills/anki-card-study-coach/scripts/select_study_cards.py`: 从现有 deck 和复习日志中筛选优先练习词。
- `.agents/skills/anki-card-study-coach/scripts/study_turn_assist.py`: 检查词形近似、生成逐级提示，帮助判断“部分正确”。
