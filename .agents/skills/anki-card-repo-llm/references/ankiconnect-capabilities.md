# AnkiConnect Capabilities

## Canonical Source

截至 2026-03-28，AnkiConnect 的权威文档源应视为 sourcehut 上的 README，而不是 GitHub 镜像。

- Canonical source: `https://git.sr.ht/~foosoft/anki-connect/tree/master/item/README.md`
- GitHub mirror: `https://github.com/FooSoft/anki-connect`
- GitHub 仓库页面显示其已在 2025-11-04 归档。

当前 README 列出 8 类、116 个 action。

## API Basics

- 默认 HTTP 地址：`http://127.0.0.1:8765`
- 推荐请求体结构：

```json
{
  "action": "version",
  "version": 6,
  "params": {}
}
```

- 如果配置了 API key，则在顶层额外传 `key`。
- 如果省略 `version`，AnkiConnect 会回退到版本 4 兼容行为。
- 对 version 4 及以下客户端，响应格式与 version 6 不同，因此新脚本或新流程统一使用 version 6。

## High-Value Actions by Job

### Discover and Connectivity

- `requestPermission`
- `version`
- `apiReflect`
- `getProfiles`
- `getActiveProfile`
- `loadProfile`

常用命令：

```bash
python3 .agents/skills/anki-card-repo-llm/scripts/ankiconnect_request.py --action version --pretty
python3 .agents/skills/anki-card-repo-llm/scripts/ankiconnect_request.py --action apiReflect --params-json '{"scopes":["actions"],"actions":null}' --pretty
```

### Deck and Model Prep

- `deckNames`
- `deckNamesAndIds`
- `createDeck`
- `modelNames`
- `modelNamesAndIds`
- `modelFieldNames`
- `createModel`
- `modelFieldAdd`
- `updateModelTemplates`
- `updateModelStyling`

适用场景：

- 确认 deck 是否已存在
- 确认当前 note type 的字段集合
- 为现有模型增量补字段
- 更新模板 HTML/CSS

### Note CRUD and Validation

- `canAddNotes`
- `canAddNotesWithErrorDetail`
- `addNote`
- `addNotes`
- `findNotes`
- `notesInfo`
- `updateNoteFields`
- `updateNote`
- `updateNoteModel`
- `updateNoteTags`
- `deleteNotes`
- `removeEmptyNotes`

实务建议：

- 批量导入前优先用 `canAddNotesWithErrorDetail` 看失败原因。
- 先 `findNotes` 再 `notesInfo`，避免盲改。
- `updateNoteFields` 时不要让目标 note 正被 Anki Browser 打开。

### Media

- `storeMediaFile`
- `retrieveMediaFile`
- `getMediaFilesNames`
- `getMediaDirPath`
- `deleteMediaFile`

关键点：

- `storeMediaFile` 支持 `data`、`path`、`url` 三种输入。
- 如果同时给多个来源，优先级是 `data` > `path` > `url`。
- 默认会覆盖同名文件；如需避免覆盖，设置 `deleteExisting=false`。
- 用 `_` 开头的文件名可以避免被 Anki 当作未使用媒体清理。

### Query, Review, and Stats

- `findCards`
- `cardsInfo`
- `cardsToNotes`
- `getNumCardsReviewedToday`
- `getNumCardsReviewedByDay`
- `cardReviews`
- `getReviewsOfCards`

### GUI Automation

- `guiBrowse`
- `guiSelectCard`
- `guiSelectedNotes`
- `guiAddCards`
- `guiEditNote`
- `guiAddNoteSetData`
- `guiCurrentCard`
- `guiDeckOverview`
- `guiDeckBrowser`
- `guiDeckReview`
- `guiImportFile`
- `guiExitAnki`
- `guiCheckDatabase`
- `guiPlayAudio`

只有在用户明确想驱动 Anki GUI 时才优先使用这组动作。

## Query Patterns

AnkiConnect 的搜索参数遵循 Anki 搜索语法。官方手册：

- `https://docs.ankiweb.net/searching.html`

常用模式：

```text
deck:"Vocabulary_LocalSmoke"
deck:"Vocabulary_LocalSmoke" Word:clarify
nid:1234567890
tag:none
note:"Basic"
```

关键提醒：

- 字段搜索默认偏向精确匹配。
- 带空格的 deck 名、field 名、note type 名应使用引号。
- 复杂查询先在只读动作里验证，再拿去做删除或更新。

## Important Gotchas

- `requestPermission` 是跨 origin 场景下的首个探测入口。
- `multi` 会按顺序返回每个子 action 的响应，适合批量只读查询。
- `guiAddNoteSetData` 需要 Add Note 对话框已经打开。
- `updateNoteFields` 在目标 note 正被 browser 打开时可能看起来没更新。
- macOS 下如果 Anki 切后台后断联，考虑 App Nap。

## Full Action Catalog

### Card Actions (17)

- `getEaseFactors`
- `setEaseFactors`
- `setSpecificValueOfCard`
- `suspend`
- `unsuspend`
- `suspended`
- `areSuspended`
- `areDue`
- `getIntervals`
- `findCards`
- `cardsToNotes`
- `cardsModTime`
- `cardsInfo`
- `forgetCards`
- `relearnCards`
- `answerCards`
- `setDueDate`

### Deck Actions (12)

- `deckNames`
- `deckNamesAndIds`
- `getDecks`
- `createDeck`
- `changeDeck`
- `deleteDecks`
- `getDeckConfig`
- `saveDeckConfig`
- `setDeckConfigId`
- `cloneDeckConfigId`
- `removeDeckConfigId`
- `getDeckStats`

### Graphical Actions (19)

- `guiBrowse`
- `guiSelectCard`
- `guiSelectedNotes`
- `guiAddCards`
- `guiEditNote`
- `guiAddNoteSetData`
- `guiCurrentCard`
- `guiStartCardTimer`
- `guiShowQuestion`
- `guiShowAnswer`
- `guiAnswerCard`
- `guiUndo`
- `guiDeckOverview`
- `guiDeckBrowser`
- `guiDeckReview`
- `guiImportFile`
- `guiExitAnki`
- `guiCheckDatabase`
- `guiPlayAudio`

### Media Actions (5)

- `storeMediaFile`
- `retrieveMediaFile`
- `getMediaFilesNames`
- `getMediaDirPath`
- `deleteMediaFile`

### Miscellaneous Actions (11)

- `requestPermission`
- `version`
- `apiReflect`
- `sync`
- `getProfiles`
- `getActiveProfile`
- `loadProfile`
- `multi`
- `exportPackage`
- `importPackage`
- `reloadCollection`

### Model Actions (25)

- `modelNames`
- `modelNamesAndIds`
- `findModelsById`
- `findModelsByName`
- `modelFieldNames`
- `modelFieldDescriptions`
- `modelFieldFonts`
- `modelFieldsOnTemplates`
- `createModel`
- `modelTemplates`
- `modelStyling`
- `updateModelTemplates`
- `updateModelStyling`
- `findAndReplaceInModels`
- `modelTemplateRename`
- `modelTemplateReposition`
- `modelTemplateAdd`
- `modelTemplateRemove`
- `modelFieldRename`
- `modelFieldReposition`
- `modelFieldAdd`
- `modelFieldRemove`
- `modelFieldSetFont`
- `modelFieldSetFontSize`
- `modelFieldSetDescription`

### Note Actions (20)

- `addNote`
- `addNotes`
- `canAddNotes`
- `canAddNotesWithErrorDetail`
- `updateNoteFields`
- `updateNote`
- `updateNoteModel`
- `updateNoteTags`
- `getNoteTags`
- `addTags`
- `removeTags`
- `getTags`
- `clearUnusedTags`
- `replaceTags`
- `replaceTagsInAllNotes`
- `findNotes`
- `notesInfo`
- `notesModTime`
- `deleteNotes`
- `removeEmptyNotes`

### Statistic Actions (7)

- `getNumCardsReviewedToday`
- `getNumCardsReviewedByDay`
- `getCollectionStatsHTML`
- `cardReviews`
- `getReviewsOfCards`
- `getLatestReviewID`
- `insertReviews`
