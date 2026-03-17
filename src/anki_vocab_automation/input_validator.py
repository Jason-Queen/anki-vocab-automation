"""
输入验证模块
Input validation module for security and data integrity
"""

import re
import logging
from typing import Optional

from .models import VocabularyInput

logger = logging.getLogger(__name__)


class InputValidator:
    """输入验证器类"""

    # 允许的单词字符模式 - 包含字母、空格、连字符、撇号、句点
    WORD_PATTERN = re.compile(r"^[a-zA-Z\s\-\'\.\u00C0-\u017F]+$")

    # 最大单词长度
    MAX_WORD_LENGTH = 100

    # 最大例句长度
    MAX_EXAMPLE_LENGTH = 500

    # 最小单词长度
    MIN_WORD_LENGTH = 1

    # 危险字符模式
    DANGEROUS_PATTERNS = [
        r"<script",  # 脚本标签
        r"javascript:",  # JavaScript URL
        r"data:",  # Data URL
        r"vbscript:",  # VBScript URL
        r"onload=",  # 事件处理器
        r"onerror=",  # 事件处理器
        r"eval\(",  # eval函数
        r"exec\(",  # exec函数
        r"system\(",  # system调用
        re.escape("<?php"),  # PHP标签
        re.escape("<%"),  # ASP标签
        r"\.\./",  # 路径遍历
        r"\.\.\\",  # 路径遍历（Windows）
        r"/etc/",  # 系统路径
        r"\\system32",  # Windows系统路径
    ]

    @classmethod
    def validate_word(cls, word: str) -> tuple[bool, Optional[str]]:
        """
        验证单词输入的安全性和有效性

        Args:
            word: 要验证的单词

        Returns:
            (是否有效, 错误信息) - 如果有效返回(True, None)，否则返回(False, 错误信息)
        """
        if not word:
            return False, "单词不能为空"

        if not isinstance(word, str):
            return False, "单词必须是字符串类型"

        # 清理并检查基本格式
        word = word.strip()
        if not word:
            return False, "单词不能只包含空白字符"

        # 长度检查
        if len(word) > cls.MAX_WORD_LENGTH:
            return False, f"单词长度不能超过{cls.MAX_WORD_LENGTH}个字符"

        if len(word) < cls.MIN_WORD_LENGTH:
            return False, f"单词长度不能少于{cls.MIN_WORD_LENGTH}个字符"

        # 字符模式检查
        if not cls.WORD_PATTERN.match(word):
            return False, "单词包含无效字符，只允许字母、空格、连字符、撇号和句点"

        # 危险模式检查
        word_lower = word.lower()
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, word_lower, re.IGNORECASE):
                logger.warning(f"检测到危险模式 '{pattern}' 在输入中: {word}")
                return False, "单词包含不安全的字符或模式"

        # 检查是否只包含数字（通常不是有效单词）
        if word.replace(" ", "").replace("-", "").replace(".", "").isdigit():
            return False, "单词不能只包含数字"

        # 检查重复字符（可能的攻击尝试）
        if cls._has_excessive_repetition(word):
            return False, "单词包含过多重复字符"

        return True, None

    @classmethod
    def _has_excessive_repetition(cls, text: str, max_repeat: int = 10) -> bool:
        """
        检查是否有过多的重复字符

        Args:
            text: 要检查的文本
            max_repeat: 允许的最大连续重复次数

        Returns:
            如果有过多重复返回True
        """
        if len(text) < max_repeat:
            return False

        for i in range(len(text) - max_repeat + 1):
            char = text[i]
            count = 1
            for j in range(i + 1, len(text)):
                if text[j] == char:
                    count += 1
                    if count >= max_repeat:
                        return True
                else:
                    break
        return False

    @classmethod
    def sanitize_word(cls, word: str) -> str:
        """
        清理单词输入，移除潜在危险字符

        Args:
            word: 原始单词

        Returns:
            清理后的单词
        """
        if not word or not isinstance(word, str):
            return ""

        # 基本清理
        word = word.strip()

        # 移除控制字符
        word = "".join(char for char in word if ord(char) >= 32 or char in "\t\n\r")

        # 限制长度
        word = word[: cls.MAX_WORD_LENGTH]

        # 移除多余空格
        word = re.sub(r"\s+", " ", word)

        return word

    @classmethod
    def sanitize_example(cls, example: str) -> str:
        """清理用户提供的例句。"""
        if not example or not isinstance(example, str):
            return ""

        cleaned = example.strip()
        cleaned = "".join(char for char in cleaned if ord(char) >= 32 or char in "\t\n\r")
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned[: cls.MAX_EXAMPLE_LENGTH].strip()

    @classmethod
    def validate_file_path(cls, file_path: str) -> tuple[bool, Optional[str]]:
        """
        验证文件路径的安全性

        Args:
            file_path: 要验证的文件路径

        Returns:
            (是否有效, 错误信息)
        """
        if not file_path or not isinstance(file_path, str):
            return False, "文件路径不能为空"

        # 检查路径遍历攻击
        dangerous_path_patterns = [
            "..",  # 目录遍历
            "/etc/",  # 系统目录
            "/root/",  # 根目录
            "/home/",  # 用户目录（如果不在允许范围内）
            "\\system32",  # Windows系统目录
            "\\windows",  # Windows目录
        ]

        file_path_lower = file_path.lower()
        for pattern in dangerous_path_patterns:
            if pattern in file_path_lower:
                return False, f"文件路径包含危险模式: {pattern}"

        # 检查绝对路径（根据需要调整策略）
        if file_path.startswith("/") or (len(file_path) > 1 and file_path[1] == ":"):
            return False, "不允许使用绝对路径"

        return True, None

    @classmethod
    def sanitize_filename(cls, filename: str) -> str:
        """
        清理文件名，确保安全

        Args:
            filename: 原始文件名

        Returns:
            清理后的安全文件名
        """
        if not filename or not isinstance(filename, str):
            return "unknown"

        # 移除路径分隔符和其他危险字符
        unsafe_chars = r'[<>:"/\\|?*\x00-\x1f]'
        filename = re.sub(unsafe_chars, "_", filename)

        # 移除点开头（隐藏文件）
        filename = filename.lstrip(".")

        # 限制长度
        if len(filename) > 100:
            name_part, ext_part = filename.rsplit(".", 1) if "." in filename else (filename, "")
            filename = name_part[:95] + ("." + ext_part if ext_part else "")

        # 确保不为空
        if not filename:
            filename = "sanitized_file"

        return filename


# 便利函数
def validate_word_input(word: str) -> tuple[bool, Optional[str]]:
    """验证单词输入的便利函数"""
    return InputValidator.validate_word(word)


def sanitize_word_input(word: str) -> str:
    """清理单词输入的便利函数"""
    return InputValidator.sanitize_word(word)


def sanitize_example_input(example: str) -> str:
    """清理例句输入的便利函数"""
    return InputValidator.sanitize_example(example)


def parse_vocabulary_input(line: str) -> tuple[Optional[VocabularyInput], Optional[str]]:
    """Parse one input line into a structured vocabulary request."""
    if not line or not isinstance(line, str):
        return None, "输入为空"

    raw_line = line.strip()
    if not raw_line:
        return None, "输入为空"

    if "\t" in raw_line:
        word_part, example_part = raw_line.split("\t", 1)
    elif " | " in raw_line:
        word_part, example_part = raw_line.split(" | ", 1)
    else:
        word_part, example_part = raw_line, ""

    word = sanitize_word_input(word_part)
    is_valid, error = validate_word_input(word)
    if not is_valid:
        return None, error

    return (
        VocabularyInput(
            word=word,
            source_example=sanitize_example_input(example_part),
            original_line=raw_line,
        ),
        None,
    )
