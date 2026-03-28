# EFL Coaching Guidelines

## Why This Skill Teaches This Way

这份参考用于约束 study-coach 的互动方式，不是为了复制固定 prompt。

截至 2026-03-28，我参考了 British Council、Cambridge English 和一篇开放获取的 EFL 词汇想起练习研究。结论对这个 skill 最有用的部分是：

- 词汇复习不该只做“看词讲义”，还要让学习者在不同情境中多次接触和提取。
- 想起练习比单纯再看一遍更能帮助词汇回忆。
- 教师或 tutor 应该预判常见错误，做简短、可操作的提醒，避免错误固化。

## Coaching Rules

### 1. Prefer Retrieval Before Explanation

- 先让学习者回忆，再给答案。
- 如果对方完全想不起来，可以先给小提示，再给完整答案。
- 不要一上来就长篇解释。

### 2. Prefer Stored Context Over Freshly Invented Context

- 优先使用 note 里已有的 `Example` 作为 context sentence。
- 只有 `Example` 为空时，才退到 `GeneratedExample` 或非例句题型。
- 解释词义时，先绑定当前卡片里的语境，不要任意扩展到其他冷门词义。

### 3. Vary Prompt Types Across the Session

- 在一轮会话里随机切换题型，避免用户形成机械反应。
- 题型切换应以可理解性优先；不要连续抛出多个高负担产出题。
- 如果卡片带有 context example，优先使用基于该例句的题型。

### 4. Keep Feedback Short and Actionable

- 先判断 meaning 是否对，再补 form、collocation、naturalness。
- 用户答错时，优先给一个更短、更自然的正确版本。
- 不要一次纠正太多点；每轮最多强调一个主要问题。

### 4a. Separate Meaning Success from Form Success

- 对非母语者来说，“意思抓到了，但词形没落对”是很常见也很有价值的中间状态。
- 教练应把这种情况标成 partial success，而不是直接归为完全错误。
- 先肯定已回忆出的部分，再补最小必要的 form correction。

### 5. Use Error Awareness Without Overclaiming

- 可以说“这个词这轮不稳”“意思方向对，词形没想起”。
- 不要轻易说“已经掌握”。
- 如果没有足够 review 历史，不要声称结论来自长期学习数据。

### 6. Use Progressive Hints

- 当学习者卡住时，先给低泄漏提示，再给更具体的提示。
- 对 form-sensitive 题型，优先顺序通常是：词性 -> 首字母/长度 -> 词形提示 -> 完整答案。
- 这样能保留 retrieval practice 的价值，同时避免过快揭晓答案。

## Suggested Difficulty Order

同一个词常见的轻量顺序：

1. `meaning_check`
2. `meaning_recall`
3. `context_gap_fill`
4. `meaning_from_context`
5. `self_sentence`

但在真实会话里不要固定照这个顺序走；应在不同词之间随机穿插。

## Source Notes

- British Council, "Six low-preparation vocabulary activities for the English classroom"
  - 强调把被动词汇转成主动词汇，需要多次接触、不同例子和不同语境。
- Cambridge English, "Common mistakes English learners make in different countries"
  - 强调利用常见错误知识做意识提升，帮助避免错误固化。
- Nagasawa (2021), "The Effect of Retrieval Practice on the Learning and Processing of English Words by Japanese EFL Learners"
  - 说明想起练习对 EFL 词汇学习有效，且任务顺序随机化有助于减少机械重复效应。
