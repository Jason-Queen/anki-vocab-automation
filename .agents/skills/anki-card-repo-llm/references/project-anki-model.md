# anki-card Anki Model and Wrapped API Surface

## Runtime Model Contract

这个仓库的 `AnkiConnect` 客户端在运行时把 `model_name` 直接设成 `deck_name`。

这意味着：

- 虽然配置和文档里仍可能出现 `MODEL_NAME`，
- 但当前运行行为实际上要求“目标模型名 == 目标牌组名”。

在没有明确迁移任务时，不要改变这条约束。

## Required Field Order

当前词汇模型要求这些字段，且顺序固定：

1. `Word`
2. `PartOfSpeech`
3. `Example`
4. `GeneratedExample`
5. `Definition`
6. `Pronunciation`
7. `AudioFilename`
8. `AudioSource`
9. `BritishPronunciation`
10. `AmericanPronunciation`
11. `BritishAudioFilename`
12. `AmericanAudioFilename`
13. `BritishAudioSource`
14. `AmericanAudioSource`

对 agent 的含义：

- 不要私自改字段名。
- 不要用不兼容的 note type 直接写入这些字段。
- 如果要检查模型兼容性，先看 `modelFieldNames` 的返回值。

## Template Update Strategy

仓库使用 packaged templates 作为 canonical model assets，并在运行时：

- 检查目标 model 是否存在；
- 缺字段时用 `modelFieldAdd` 增量补齐；
- 再用 `updateModelTemplates` 和 `updateModelStyling` 更新 HTML/CSS；
- 如果 model 不存在，再用 `createModel` 创建。

不要用“删掉重建 note type”的方式替代这套策略，除非用户明确要求迁移。

## Wrapped AnkiConnect Actions

仓库本身直接封装或依赖了这些原生动作：

- `version`
- `deckNames`
- `createDeck`
- `modelNames`
- `modelFieldNames`
- `createModel`
- `modelFieldAdd`
- `updateModelTemplates`
- `updateModelStyling`
- `addNote`
- `findNotes`
- `getNumCardsReviewedToday`
- `storeMediaFile`
- `retrieveMediaFile`
- `deleteMediaFile`

如果用户要做的事情已经落在这组动作里，优先复用仓库逻辑，而不是重新手拼一套平行流程。

## Duplicate Behavior

仓库当前用 `findNotes` 做重复检测，查询模式是：

```text
deck:"<deck_name>" Word:<word>
```

注意：

- 这是基于目标牌组和 `Word` 字段的项目级重复策略。
- 它不是 AnkiConnect `addNote` 的 `allowDuplicate` / `duplicateScope` 那套通用机制。
- 如果你直接调用原生 `addNote` 批量建卡，要自己决定是否先跑 `canAddNotesWithErrorDetail`。

## Audio and Media Expectations

项目约束比“能插入一个文件”更严格：

- 损坏音频比缺失音频更糟。
- 只有真实下载或真实生成成功的音频，才能写进字段。
- 导入后可以再用 `retrieveMediaFile` 反查媒体是否存在。

## Smoke-Test Safety Boundary

本仓库的本地验收测试带有明确保护边界：

- 默认必须手动开启 `ANKI_LOCAL_TEST_RUN=1` 才会运行。
- 必须指定 dedicated profile。
- dedicated deck 不能等于主运行 deck。
- 测试会先清空 dedicated deck，再导入一个样例。

只有在这个安全边界里，删除 notes 才是默认允许的。

## When to Prefer Raw AnkiConnect

这些情况更适合直接打原生 API：

- 只想查询 profile、deck、note、media 现状。
- 需要 `notesInfo` / `cardsInfo` / `apiReflect` 之类仓库未包裹的能力。
- 想验证模型字段是否真的落到 Anki 里。
- 想看 media 文件是否真的存在于 Anki media 目录。

这些情况仍优先走仓库 CLI：

- 从词和原句生成 learner-friendly 卡片。
- 想复用当前 LLM prompt、音频策略、模板字段映射。
- 想确保导入行为和项目默认路径保持一致。
