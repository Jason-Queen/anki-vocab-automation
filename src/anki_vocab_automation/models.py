"""
数据模型定义
Data models for Anki Vocabulary Automation
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class VocabularyInput:
    """Structured user input for a vocabulary lookup."""

    word: str
    source_example: str = ""
    original_line: str = ""


@dataclass
class VocabularyCard:
    """词汇卡片数据类"""

    word: str
    definition: str
    example: str  # 正面展示的例句（优先使用用户提供的原句）
    generated_example: str  # 背面额外展示的新例句
    pronunciation: str  # 主要音标（英式，有重音符号）
    audio_filename: str  # 主要音频文件名
    part_of_speech: str
    original_word: str  # 原始输入的单词

    # 双重发音支持
    british_pronunciation: Optional[str] = None  # 英式音标
    american_pronunciation: Optional[str] = None  # 美式音标
    british_audio_filename: Optional[str] = None  # 英式音频文件名
    american_audio_filename: Optional[str] = None  # 美式音频文件名
    audio_source: Optional[str] = None  # 主要音频来源标记
    british_audio_source: Optional[str] = None  # 英式音频来源标记
    american_audio_source: Optional[str] = None  # 美式音频来源标记
    source: Optional[str] = None  # 词卡数据来源（内部使用）

    def __post_init__(self):
        """数据验证和默认值设置"""
        if not self.word:
            raise ValueError("Word cannot be empty")
        if not self.original_word:
            raise ValueError("Original word cannot be empty")

        if not self.generated_example and self.example:
            self.generated_example = self.example
        if not self.example and self.generated_example:
            self.example = self.generated_example

        # 如果没有设置双重发音，则用主要发音填充
        if not self.british_pronunciation and self.pronunciation:
            self.british_pronunciation = self.pronunciation
        if not self.british_audio_filename and self.audio_filename:
            self.british_audio_filename = self.audio_filename
        if not self.british_audio_source and self.audio_source:
            self.british_audio_source = self.audio_source

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "Word": self.word,
            "Definition": self.definition,
            "Example": self.example,
            "GeneratedExample": self.generated_example,
            "Pronunciation": self.pronunciation,
            "AudioFilename": self.audio_filename,
            "PartOfSpeech": self.part_of_speech,
            # 双重发音字段
            "BritishPronunciation": self.british_pronunciation or self.pronunciation,
            "AmericanPronunciation": self.american_pronunciation or self.pronunciation,
            "BritishAudioFilename": self.british_audio_filename or self.audio_filename,
            "AmericanAudioFilename": self.american_audio_filename or self.audio_filename,
            "AudioSource": self.audio_source or "",
            "BritishAudioSource": self.british_audio_source or self.audio_source or "",
            "AmericanAudioSource": self.american_audio_source or self.audio_source or "",
        }

    def __str__(self) -> str:
        return f"VocabularyCard(word='{self.word}', original='{self.original_word}')"
