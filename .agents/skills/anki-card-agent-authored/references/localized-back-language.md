# Localized Back Language

## Purpose

这个流程用于让卡片“背面解释性内容”使用用户指定语种，同时保留：

- 单词本体
- 正面原句
- IPA 音标
- 英式/美式发音音频

这是 skill 的可选能力，不改变仓库默认的英文 learner card 生成路径。

## What Counts as Explanatory Language

通常会本地化这些部分：

- `PartOfSpeech`
- `Definition`
- `GeneratedExample`
- 背面模板标签文字

通常不会本地化这些部分：

- `Word`
- `Example`
- `Pronunciation`
- `BritishPronunciation`
- `AmericanPronunciation`
- `AudioFilename`
- `BritishAudioFilename`
- `AmericanAudioFilename`
- 对应的音频来源字段

## Recommended Decision Rule

### If the user wants only one card localized

- 只更新 note 字段。
- 不改模型模板。

### If the user wants all future cards in a test model to show that language

- 更新 note 字段。
- 再更新该模型的背面模板标签。

### If the user wants the main production deck changed

- 先明确提醒这会影响同模型下的所有卡。
- 没有明确确认前，不要改主模型。

## Workflow

1. 先用 `uv run anki-vocab --entry` 或 `--stdin` 正常建卡。
2. 用 `findNotes` 找到新 note。
3. 用 `notesInfo` 取回字段，确认单词、原句、音标、音频都已经落地。
4. 把 `PartOfSpeech`、`Definition`、`GeneratedExample` 翻译成目标语种。
5. 用 `updateNoteFields` 写回翻译后的字段。
6. 如果要把背面标签也改掉：
   - 先用 `modelTemplates` 读取当前模板；
   - 再用 `scripts/localize_back_template.py` 按标签映射更新该模型的 `Card 1` 背面模板；
   - 或用 `updateModelTemplates` 手动更新。
7. 最后验证：
   - `notesInfo`
   - `modelTemplates`
   - `retrieveMediaFile`

## Template Label Mapping

标准英文背面标签通常是：

- `Definition:`
- `New Example:`
- `Pronunciation:`
- `British:`
- `American:`
- `Source:`

简体中文示例：

```json
{
  "Definition:": "中文释义：",
  "New Example:": "中文例句：",
  "Pronunciation:": "音标与发音：",
  "British:": "英式：",
  "American:": "美式：",
  "Source:": "来源："
}
```

日语示例：

```json
{
  "Definition:": "意味：",
  "New Example:": "例文：",
  "Pronunciation:": "発音と音声：",
  "British:": "イギリス英語：",
  "American:": "アメリカ英語：",
  "Source:": "音源："
}
```

法语示例：

```json
{
  "Definition:": "Définition :",
  "New Example:": "Nouvel exemple :",
  "Pronunciation:": "Prononciation et audio :",
  "British:": "Britannique :",
  "American:": "Américain :",
  "Source:": "Source :"
}
```

## Example Request Shapes

这些用户请求都应该触发本流程：

- “生成一张新卡，但背面解释部分用简体中文。”
- “Make the back side explanatory text Japanese, but keep IPA and audio.”
- “Create a French-learning version of this card, with French definitions on the back.”

## Validation Checklist

确认这些条件成立：

- `Word` 未被翻译。
- `Example` 仍是原始学习句。
- `Definition` / `GeneratedExample` / `PartOfSpeech` 已切到目标语种。
- `BritishPronunciation` / `AmericanPronunciation` 仍是 IPA。
- 3 个音频文件都能通过 `retrieveMediaFile` 读到。
- 如果更新了模板，`modelTemplates` 中的背面标签也已经是目标语种。

## Script Usage

先准备一个标签映射 JSON 文件，例如 `labels-zh-cn.json`。

然后执行：

```bash
python3 scripts/localize_back_template.py \
  --model-name Vocabulary_LocalSmoke_ChineseBack \
  --label-file labels-zh-cn.json \
  --pretty
```

这个脚本只改指定模型的背面模板，不会翻译 note 字段内容；字段翻译仍应通过 `updateNoteFields` 完成。
