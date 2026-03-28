# Agent-Authored Vocabulary Cards

## Purpose

这个流程用于让 Codex 自己完成词卡内容生成，而不是把内容生成阶段交给仓库里的本地 LLM。

目标：

- 直接生成 learner-friendly 卡片内容
- 仍然复用本仓库的 Anki 模型字段契约
- 仍然通过 AnkiConnect 写入 Anki
- 可选接入本地 TTS；默认在没有本地 TTS 时回落到 Google TTS

## When to Prefer This Path

优先使用 `agent-authored` 的场景：

- 用户只想“做一张卡”，没有要求必须走本地 LLM
- 用户希望 agent 自己决定释义、例句和背面语言
- 用户需要比仓库默认 prompt 更强的中文/日文/法文等背面控制
- 用户当前本地 LLM 环境不稳定，或不想依赖它

优先使用 `repo-llm` 的场景：

- 用户明确要求复现仓库当前本地 LLM 行为
- 用户想验证 prompt、provider、模型配置
- 用户要测试仓库本身的生成链路

## Required Output Contract

Agent 至少需要产出这些字段：

- `word`
- `original_word`
- `part_of_speech`
- `definition`
- `example`
- `generated_example`
- `pronunciation`

建议同时给出：

- `british_pronunciation`
- `american_pronunciation`

如果音频尚未准备好，也不要手写这些文件名；应由导入脚本根据真实音频或 Google TTS 自动填充：

- `audio_filename`
- `british_audio_filename`
- `american_audio_filename`
- 对应的 `*_audio_source`

## Quality Bar

### Lexical correctness

- 以用户原句决定词义和词性。
- 有歧义时先核验，不要硬写。
- 如果你不确定 IPA，宁可留空或显式说明不确定，不要编造。

### Learner usability

- 释义面向初学者。
- 不循环定义。
- 新例句必须自然、简短、并真正帮助理解该词。

### Reproducibility

- 尽量把最终 payload 写成清晰 JSON，再调用导入脚本。
- 需要时把核验来源写进工作说明，而不是塞进 note 字段。

## Back Language Rule

如果用户指定背面解释语言：

- `PartOfSpeech`
- `Definition`
- `GeneratedExample`

直接用目标语种生成。

通常保留原样的部分：

- `Word`
- 正面 `Example`
- IPA 音标
- 音频文件和播放

## TTS Policy

### If local TTS is available

- 生成真实本地音频文件。
- 在 payload 中附带本地路径和来源标记。
- 导入时由脚本上传到 Anki media，并自动填写文件名字段。

### If local TTS is unavailable and the user has no special request

- 默认回落到 Google TTS。
- 导入脚本会为 `main`、`british`、`american` 三个槽位生成真实媒体文件。
- 对应来源字段会写成 `Google TTS`。

### If the user explicitly wants no audio

- 可以保留空音频字段。
- 但这是显式例外，不应作为默认行为。

## Suggested Workflow

1. 先做 preflight：
   - `version`
   - `deckNames`
   - 必要时 `modelFieldNames`
2. 起草卡片内容。
3. 如果用户要求指定背面语言，直接用该语种起草解释性字段。
4. 组装成 JSON payload。
5. 用 `scripts/create_agent_vocab_note.py` 导入。
6. 最后用 `findNotes`、`notesInfo`、`retrieveMediaFile` 回查。

## Example Minimal Payload

```json
{
  "word": "resilient",
  "original_word": "resilient",
  "part_of_speech": "形容词",
  "definition": "能迅速恢复的；适应力强的。",
  "example": "Children are often more resilient than adults expect.",
  "generated_example": "孩子通常比大人想象中更有韧性。",
  "pronunciation": "/rɪˈzɪl.jənt/",
  "british_pronunciation": "/rɪˈzɪl.jənt/",
  "american_pronunciation": "/rɪˈzɪl.jənt/"
}
```

## Example With Local Audio

```json
{
  "word": "resilient",
  "original_word": "resilient",
  "part_of_speech": "adjective",
  "definition": "Able to recover quickly after difficulty.",
  "example": "Children are often more resilient than adults expect.",
  "generated_example": "Resilient students keep trying after mistakes.",
  "pronunciation": "/rɪˈzɪl.jənt/",
  "british_pronunciation": "/rɪˈzɪl.jənt/",
  "american_pronunciation": "/rɪˈzɪl.jənt/",
  "main_audio_path": "/absolute/path/resilient-main.mp3",
  "main_audio_source": "Local TTS",
  "british_audio_path": "/absolute/path/resilient-gb.mp3",
  "british_audio_source": "Local TTS",
  "american_audio_path": "/absolute/path/resilient-us.mp3",
  "american_audio_source": "Local TTS"
}
```

## Example Without Local TTS

即使 payload 不带任何音频路径，默认导入脚本也会尝试 Google TTS：

```json
{
  "word": "resilient",
  "original_word": "resilient",
  "part_of_speech": "adjective",
  "definition": "Able to recover quickly after difficulty.",
  "example": "Children are often more resilient than adults expect.",
  "generated_example": "Resilient students keep trying after mistakes.",
  "pronunciation": "/rɪˈzɪl.jənt/",
  "british_pronunciation": "/rɪˈzɪl.jənt/",
  "american_pronunciation": "/rɪˈzɪl.jənt/"
}
```

默认结果：

- `main` -> Google TTS
- `british` -> Google TTS (`en-GB`)
- `american` -> Google TTS (`en-US`)

## Validation Checklist

- `Word` 正确
- `Example` 与用户原句一致或按用户要求保留
- `Definition` 不循环
- `GeneratedExample` 自然
- `PartOfSpeech` 与原句一致
- 音标可信
- 默认应有 3 个真实媒体文件，除非用户明确接受无音频

## Failure Policy

如果高置信内容无法生成：

- 不要硬写低质量卡片
- 可以先回到“核验后再导入”
- 或询问用户是否接受临时无音频 / 无美式发音 / 无翻译版背面
