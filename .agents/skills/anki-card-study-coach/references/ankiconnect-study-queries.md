# AnkiConnect Study Queries

## Preferred Read-Only Actions

这个 skill 的首选动作是：

- `version`
- `getActiveProfile`
- `deckNames`
- `findCards`
- `cardsInfo`
- `getReviewsOfCards`
- `getNumCardsReviewedToday`
- `getNumCardsReviewedByDay`

第一版默认不要用：

- `guiAnswerCard`
- `answerCards`
- `updateNoteFields`
- `deleteNotes`
- `insertReviews`

## Preferred Flow

1. `version`
2. `getActiveProfile`
3. `findCards` with `deck:"<deck>"`
4. `cardsInfo`
5. `getReviewsOfCards`
6. `.agents/skills/anki-card-study-coach/scripts/select_study_cards.py`

在 study-coach 里，`Example` 字段应视为当前卡片的首选 context sentence。

- 首选：`Example`
- 回退：`GeneratedExample`
- 如果两者都没有，再使用非 context 题型

## Example Commands

检查连接：

```bash
python3 .agents/skills/anki-card-study-coach/scripts/ankiconnect_request.py --action version --pretty
```

查看当前 profile：

```bash
python3 .agents/skills/anki-card-study-coach/scripts/ankiconnect_request.py --action getActiveProfile --pretty
```

查询牌组里的卡片：

```bash
python3 .agents/skills/anki-card-study-coach/scripts/ankiconnect_request.py \
  --action findCards \
  --params-json '{"query":"deck:\"Vocabulary\""}' \
  --pretty
```

直接筛出优先练习词：

```bash
python3 .agents/skills/anki-card-study-coach/scripts/select_study_cards.py --deck "Vocabulary" --limit 8 --seed 20260328 --pretty
```

## Degraded Mode

如果 `getReviewsOfCards` 返回空结果或不可用：

- 允许降级到 deck fallback。
- 可以参考 `reps`、`lapses`、`queue`、定义和例句做基础练习。
- 必须明确告诉用户：这次不是完整的 review-aware 个性化筛选。
