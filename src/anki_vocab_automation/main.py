"""
主程序
Main automation workflow for Anki Vocabulary Automation
"""

import argparse
import time
import logging
import sys
from pathlib import Path
from typing import List, Optional, Sequence

from .collins_api import CollinsAPI
from .html_parser import HTMLParser
from .anki_connect import AnkiConnect
from .llm_client import LLMClient
from .input_validator import parse_vocabulary_lines
from .models import VocabularyInput
from .audio_manager import AudioManager
from .concurrent_processor import (
    ConcurrentProcessor,
    ProcessingResult,
)
from .config import (
    COLLINS_API_KEY,
    WORD_LIST_FILE,
    REQUEST_DELAY,
    LOG_FILE,
    LOG_FORMAT,
    LOG_LEVEL,
    LLM_PROVIDER,
    LLM_API_MODE,
    LLM_BASE_URL,
    LLM_API_KEY,
    LLM_MODEL_NAME,
    LLM_TIMEOUT,
    LLM_CUSTOM_TEMPERATURE,
    LLM_CUSTOM_MAX_TOKENS,
    LLM_GPT_OSS_REASONING_EFFORT,
    LLM_PROMPT_VERSION,
    ENABLE_LLM_FALLBACK,
    DATA_SOURCE_STRATEGY,
    ENABLE_TTS_FALLBACK,
    TTS_SERVICE,
    TTS_SERVICE_PRIORITY,
    TTS_VOICE,
    TTS_OPENAI_COMPAT_BASE_URL,
    TTS_OPENAI_COMPAT_API_KEY,
    TTS_OPENAI_COMPAT_MODEL,
    TTS_OPENAI_COMPAT_VOICE,
    TTS_OPENAI_COMPAT_INSTRUCTIONS,
    TTS_OPENAI_COMPAT_RESPONSE_FORMAT,
    TTS_OPENAI_COMPAT_TIMEOUT,
)

# 配置日志
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=LOG_FORMAT,
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class VocabularyAutomation:
    """主要的自动化流程类"""

    def __init__(
        self,
        collins_api_key: str = COLLINS_API_KEY,
        data_source_strategy: Optional[str] = None,
    ):
        """
        初始化自动化流程

        Args:
            collins_api_key: Collins API密钥
            data_source_strategy: 可选的运行时数据源策略覆盖
        """
        self.collins_api = CollinsAPI(collins_api_key)
        self.html_parser = HTMLParser()
        self.anki_connect = AnkiConnect()
        self.data_source_strategy = (data_source_strategy or DATA_SOURCE_STRATEGY).strip().lower()

        # 初始化OpenAI兼容客户端
        self.llm_client = self._initialize_llm_client()

        # 初始化音频管理器
        self.audio_manager = AudioManager()

        self.stats = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "duplicates": 0,
            "not_found": 0,
            "collins_used": 0,
            "llm_used": 0,
            "audio_downloaded": 0,
            "audio_failed": 0,
        }

    def _initialize_llm_client(self) -> LLMClient:
        """
        初始化LLM客户端，支持高级配置

        Returns:
            配置好的LLMClient实例
        """
        client = LLMClient(
            provider=LLM_PROVIDER,
            api_mode=LLM_API_MODE,
            base_url=LLM_BASE_URL,
            api_key=LLM_API_KEY,
            model_name=LLM_MODEL_NAME,
            timeout=LLM_TIMEOUT,
            enable_tts=ENABLE_TTS_FALLBACK,
            tts_service=TTS_SERVICE,
            tts_service_order=list(TTS_SERVICE_PRIORITY),
            tts_voice=TTS_VOICE,
            tts_base_url=TTS_OPENAI_COMPAT_BASE_URL,
            tts_api_key=TTS_OPENAI_COMPAT_API_KEY,
            tts_model_name=TTS_OPENAI_COMPAT_MODEL,
            tts_openai_compat_voice=TTS_OPENAI_COMPAT_VOICE,
            tts_openai_compat_instructions=TTS_OPENAI_COMPAT_INSTRUCTIONS,
            tts_response_format=TTS_OPENAI_COMPAT_RESPONSE_FORMAT,
            tts_timeout=TTS_OPENAI_COMPAT_TIMEOUT,
            temperature=LLM_CUSTOM_TEMPERATURE,
            max_output_tokens=LLM_CUSTOM_MAX_TOKENS,
            gpt_oss_reasoning_effort=LLM_GPT_OSS_REASONING_EFFORT,
            prompt_version=LLM_PROMPT_VERSION,
        )

        logger.info(
            "LLM客户端初始化完成 - provider: %s, mode: %s, model: %s, base_url: %s",
            client.resolved_provider,
            client.resolved_api_mode,
            LLM_MODEL_NAME,
            client.base_url,
        )
        return client

    def process_word_list(self, word_list: List[VocabularyInput]) -> bool:
        """
        处理单词列表

        Args:
            word_list: 单词列表
        """
        if not self.anki_connect.check_connection():
            logger.error("无法连接到Anki Connect")
            return False

        if not self.anki_connect.ensure_deck_exists():
            logger.error("无法创建或访问卡牌组")
            return False

        # 确保支持双重发音的模板存在
        if not self.anki_connect.ensure_model_exists():
            logger.error("无法创建或访问词汇模板")
            return False

        self.stats["total"] = len(word_list)
        logger.info(f"开始处理 {len(word_list)} 个单词")

        for i, word in enumerate(word_list, 1):
            logger.info(f"处理进度: {i}/{len(word_list)} - {word.word}")

            if not self._process_single_word(word):
                continue

            # 添加延迟避免API限制
            if i < len(word_list):  # 最后一个单词不需要延迟
                time.sleep(REQUEST_DELAY)

        self._print_stats()
        return True

    def process_word_list_concurrent(
        self, word_list: List[VocabularyInput], max_workers: int = 4, rate_limit: float = 2.0
    ) -> bool:
        """
        并发处理单词列表（实时添加到Anki版本）

        Args:
            word_list: 单词列表
            max_workers: 最大并发工作线程数
            rate_limit: 速率限制（每秒请求数）
        """
        if not self.anki_connect.check_connection():
            logger.error("无法连接到Anki Connect")
            return False

        if not self.anki_connect.ensure_deck_exists():
            logger.error("无法创建或访问卡牌组")
            return False

        # 确保支持双重发音的模板存在
        if not self.anki_connect.ensure_model_exists():
            logger.error("无法创建或访问词汇模板")
            return False

        self.stats["total"] = len(word_list)
        logger.info(f"开始并发处理 {len(word_list)} 个单词 (并发度: {max_workers}, 速率: {rate_limit}/s)")
        logger.info("💡 改进: 每个单词处理完成后立即添加到Anki，无需等待所有单词完成")

        # 创建并发处理器
        processor = ConcurrentProcessor(
            max_workers=max_workers,
            rate_limit_per_second=rate_limit,
            timeout_per_word=120.0,  # 每个单词2分钟超时
            retry_attempts=2,
        )

        # 创建实时进度回调 - 边处理边添加到Anki
        def progress_callback(current: int, total: int, result: ProcessingResult):
            if result.success and result.result:
                try:
                    # 检查重复
                    if self.anki_connect.find_duplicate(result.result.word):
                        logger.info(f"⚠️  [{current}/{total}] {result.word} - 跳过重复单词")
                        self.stats["duplicates"] += 1
                        return

                    # 处理音频
                    logger.debug(f"处理音频: {result.result.word}")
                    if not self._process_card_audio(result.result):
                        logger.warning(f"音频处理失败，但仍继续添加卡片: {result.result.word}")

                    # 立即添加到Anki
                    if self.anki_connect.add_note(result.result):
                        self.stats["success"] += 1
                        logger.info(
                            f"🎉 [{current}/{total}] {result.word} - 成功添加到Anki! ({result.processing_time:.1f}s)"
                        )
                        # 确定数据源
                        if hasattr(result.result, "source"):
                            if result.result.source == "collins":
                                self.stats["collins_used"] += 1
                            elif result.result.source == "llm":
                                self.stats["llm_used"] += 1
                    else:
                        self.stats["failed"] += 1
                        logger.error(f"❌ [{current}/{total}] {result.word} - 添加到Anki失败")

                except Exception as e:
                    logger.error(f"添加卡片到Anki失败 - {result.result.word}: {e}")
                    self.stats["failed"] += 1
                    import traceback

                    logger.error(f"异常详情: {traceback.format_exc()}")
            else:
                self.stats["not_found"] += 1
                if result.success:
                    logger.warning(f"⚠️  [{current}/{total}] {result.word} - 处理成功但无结果")
                else:
                    logger.error(f"❌ [{current}/{total}] {result.word} - 处理失败: {result.error}")

        # 定义单词处理函数
        def process_word_func(entry: VocabularyInput):
            return self._get_vocabulary_card(entry)

        try:
            logger.info("🚀 开始实时并发处理...")

            # 执行并发处理（现在会实时添加到Anki）
            results, stats = processor.process_words_batch(word_list, process_word_func, progress_callback)

            logger.info("✅ 并发处理全部完成!")
            logger.info(
                f"📊 最终统计: 处理={len(results)}, 成功={self.stats['success']}, "
                f"失败={self.stats['failed']}, 重复={self.stats['duplicates']}"
            )
            logger.info(f"⏱️  总耗时: {stats.total_time:.2f}s, 平均: {stats.average_time_per_word:.2f}s/词")

        except Exception as e:
            logger.error(f"并发处理过程中发生异常: {e}")
            import traceback

            logger.error(f"异常详情: {traceback.format_exc()}")
            return False

        logger.info("开始打印最终统计信息...")
        self._print_stats()
        return True

    def _process_single_word(self, entry: VocabularyInput) -> bool:
        """
        处理单个单词

        Args:
            word: 单词

        Returns:
            True如果处理成功，False否则
        """
        try:
            # 检查是否已存在
            if self.anki_connect.find_duplicate(entry.word):
                logger.info(f"跳过重复单词: {entry.word}")
                self.stats["duplicates"] += 1
                return False

            # 根据策略获取词汇卡片
            card = self._get_vocabulary_card(entry)
            if not card:
                self.stats["not_found"] += 1
                return False

            # 再次检查是否已存在（使用标准词汇形式）
            if card.word != entry.word and self.anki_connect.find_duplicate(card.word):
                logger.info(f"跳过重复单词: {entry.word} → {card.word}")
                self.stats["duplicates"] += 1
                return False

            # 处理音频：下载并存储到Anki
            if not self._process_card_audio(card):
                logger.warning(f"音频处理失败，但仍继续添加卡片: {entry.word}")

            # 添加到Anki
            if self.anki_connect.add_note(card):
                self.stats["success"] += 1
                return True
            else:
                self.stats["failed"] += 1
                return False

        except Exception as e:
            logger.error(f"处理单词时发生异常 - {entry.word}: {str(e)}")
            self.stats["failed"] += 1
            return False

    def _get_vocabulary_card(self, entry: VocabularyInput):
        """
        根据配置的策略获取词汇卡片

        Args:
            entry: 结构化输入

        Returns:
            VocabularyCard对象或None
        """
        card = None

        if self.data_source_strategy == "collins_only":
            card = self._get_card_from_collins(entry)
        elif self.data_source_strategy == "llm_only":
            card = self._get_card_from_llm(entry)
        elif self.data_source_strategy == "collins_first":
            # 优先使用Collins API
            card = self._get_card_from_collins(entry)
            if not card and ENABLE_LLM_FALLBACK:
                logger.info(f"Collins API失败或无密钥，尝试使用LLM: {entry.word}")
                card = self._get_card_from_llm(entry)
        elif self.data_source_strategy == "llm_first":
            # 优先使用LLM
            card = self._get_card_from_llm(entry)
            if not card:
                logger.info(f"LLM失败，尝试使用Collins API: {entry.word}")
                card = self._get_card_from_collins(entry)
        else:
            logger.error(f"未知的数据源策略: {self.data_source_strategy}")
            return None

        if card:
            self._prepare_card_audio_metadata(card)

        return card

    def _get_card_from_collins(self, entry: VocabularyInput):
        """
        从Collins API获取词汇卡片（支持双重发音）

        Args:
            entry: 结构化输入

        Returns:
            VocabularyCard对象或None
        """
        try:
            # 使用新的双重发音API
            response_data = self.collins_api.search_word_with_dual_pronunciation(entry.word)
            if not response_data:
                return None

            card = self.html_parser.parse_collins_response_with_dual_pronunciation(response_data, entry.word)
            if card:
                if entry.source_example:
                    card.generated_example = card.example
                    card.example = entry.source_example
                self.stats["collins_used"] += 1
                logger.debug(f"成功使用Collins API获取（双重发音）: {entry.word}")
            return card
        except Exception as e:
            logger.error(f"Collins API查询失败 - {entry.word}: {str(e)}")
            return None

    def _get_card_from_llm(self, entry: VocabularyInput):
        """
        从LLM获取词汇卡片

        Args:
            entry: 结构化输入

        Returns:
            VocabularyCard对象或None
        """
        try:
            card = self.llm_client.generate_vocabulary_card(
                entry.word,
                source_example=entry.source_example,
            )
            if card:
                self.stats["llm_used"] += 1
                logger.debug(f"成功使用LLM获取: {entry.word}")
            return card
        except Exception as e:
            logger.error(f"LLM查询失败 - {entry.word}: {str(e)}")
            return None

    def _prepare_card_audio_metadata(self, card) -> None:
        """Apply audio provenance labels and fill missing audio via TTS fallback."""
        self._mark_existing_audio_sources(card)

        if self.llm_client:
            self.llm_client.populate_missing_audio(card)

        self._mark_existing_audio_sources(card)

    def _mark_existing_audio_sources(self, card) -> None:
        """Label audio fields that already came from the dictionary path."""
        if getattr(card, "source", "") != "collins":
            return

        if card.audio_filename and not getattr(card, "audio_source", ""):
            card.audio_source = "Dictionary"

        if getattr(card, "british_audio_filename", "") and not getattr(card, "british_audio_source", ""):
            card.british_audio_source = "Dictionary"

        if getattr(card, "american_audio_filename", "") and not getattr(card, "american_audio_source", ""):
            card.american_audio_source = "Dictionary"

    def _process_card_audio(self, card) -> bool:
        """
        处理卡片音频：下载音频文件并存储到Anki（支持双重发音）

        Args:
            card: 词汇卡片对象

        Returns:
            True如果处理成功，False否则
        """
        success = True

        # 处理主要音频文件
        if card.audio_filename:
            main_success = self._process_single_audio_file(card, card.audio_filename, "main")
            if main_success:
                logger.debug(f"主要音频处理成功: {card.word}")
            else:
                success = False

        # 处理英式音频文件
        if hasattr(card, "british_audio_filename") and card.british_audio_filename:
            if card.british_audio_filename != card.audio_filename:  # 避免重复处理
                british_success = self._process_single_audio_file(card, card.british_audio_filename, "british")
                if british_success:
                    logger.debug(f"英式音频处理成功: {card.word}")
                else:
                    success = False

        # 处理美式音频文件
        if hasattr(card, "american_audio_filename") and card.american_audio_filename:
            if card.american_audio_filename not in [card.audio_filename, card.british_audio_filename]:  # 避免重复处理
                american_success = self._process_single_audio_file(card, card.american_audio_filename, "american")
                if american_success:
                    logger.debug(f"美式音频处理成功: {card.word}")
                else:
                    success = False

        return success

    def _process_single_audio_file(self, card, audio_url: str, audio_type: str = "main") -> bool:
        """
        处理单个音频文件

        Args:
            card: 词汇卡片对象
            audio_url: 音频URL或文件名
            audio_type: 音频类型 ('main', 'british', 'american')

        Returns:
            True如果处理成功，False否则
        """
        # 如果没有音频文件名，说明不需要处理音频
        if not audio_url:
            logger.debug(f"无音频文件: {card.word} ({audio_type})")
            return True

        # 如果音频文件名看起来像URL，需要下载
        if audio_url.startswith(("http://", "https://")):
            try:
                # 下载音频文件
                local_file_path = self.audio_manager.download_audio(audio_url, card.word)
                if not local_file_path:
                    logger.error(f"下载音频失败: {card.word} ({audio_type})")
                    self._clear_audio_filename(card, audio_type)
                    self.stats["audio_failed"] += 1
                    return False
                return self._store_audio_file(card, local_file_path, audio_url, audio_type)

            except Exception as e:
                logger.error(f"处理音频文件时发生异常 - {card.word} ({audio_type}): {str(e)}")
                self._clear_audio_filename(card, audio_type)
                self.stats["audio_failed"] += 1
                return False

        local_path = Path(audio_url)
        if local_path.exists() and local_path.is_file():
            return self._store_audio_file(card, str(local_path), str(local_path), audio_type)

        # 如果音频文件名不是URL，认为是已经处理过的文件名
        logger.debug(f"使用现有音频文件: {card.word} ({audio_type}) -> {audio_url}")
        return True

    def _store_audio_file(self, card, local_file_path: str, source_identifier: str, audio_type: str) -> bool:
        """将已存在的本地音频文件存入Anki媒体目录。"""
        from pathlib import Path
        import hashlib

        local_path = Path(local_file_path)
        if not local_path.exists() or not local_path.is_file():
            logger.error(f"待存储的本地音频文件不存在: {local_file_path}")
            self._clear_audio_filename(card, audio_type)
            self.stats["audio_failed"] += 1
            return False

        source_hash = hashlib.md5(source_identifier.encode()).hexdigest()[:8]
        safe_word = "".join(c for c in card.word if c.isalnum() or c in "._-")[:20]
        if not safe_word:
            safe_word = "audio"
        extension = local_path.suffix or ".mp3"
        anki_filename = f"vocab_{safe_word}_{audio_type}_{source_hash}{extension}"

        if self.anki_connect.store_media_file(str(local_path), anki_filename):
            self._set_audio_filename(card, audio_type, anki_filename)
            self.stats["audio_downloaded"] += 1
            logger.info(f"成功存储音频文件: {card.word} ({audio_type}) -> {anki_filename}")
            return True

        logger.error(f"存储音频文件失败: {card.word} ({audio_type})")
        self._clear_audio_filename(card, audio_type)
        self.stats["audio_failed"] += 1
        return False

    def _set_audio_filename(self, card, audio_type: str, filename: str):
        """设置音频文件名"""
        if audio_type == "main":
            card.audio_filename = filename
        elif audio_type == "british":
            card.british_audio_filename = filename
        elif audio_type == "american":
            card.american_audio_filename = filename

    def _clear_audio_filename(self, card, audio_type: str):
        """清空音频文件名"""
        if audio_type == "main":
            card.audio_filename = ""
            card.audio_source = ""
        elif audio_type == "british":
            card.british_audio_filename = ""
            card.british_audio_source = ""
        elif audio_type == "american":
            card.american_audio_filename = ""
            card.american_audio_source = ""

    def _print_stats(self) -> None:
        """打印统计信息"""
        logger.info("=" * 50)
        logger.info("处理完成统计:")
        logger.info(f"总数: {self.stats['total']}")
        logger.info(f"成功: {self.stats['success']}")
        logger.info(f"失败: {self.stats['failed']}")
        logger.info(f"重复: {self.stats['duplicates']}")
        logger.info(f"未找到: {self.stats['not_found']}")
        logger.info("数据源使用统计:")
        logger.info(f"Collins API: {self.stats['collins_used']}")
        logger.info(f"LLM生成: {self.stats['llm_used']}")
        logger.info("音频处理统计:")
        logger.info(f"音频下载成功: {self.stats['audio_downloaded']}")
        logger.info(f"音频下载失败: {self.stats['audio_failed']}")
        logger.info("=" * 50)

    def process_single_word_test(self, word: str, source_example: str = "") -> bool:
        """
        测试处理单个单词（用于调试）

        Args:
            word: 单词
            source_example: 可选的用户原句

        Returns:
            True如果处理成功，False否则
        """
        logger.info(f"测试处理单词: {word}")

        if not self.anki_connect.check_connection():
            return False

        if not self.anki_connect.ensure_deck_exists():
            return False

        # 确保支持双重发音的模板存在
        if not self.anki_connect.ensure_model_exists():
            return False

        return self._process_single_word(
            VocabularyInput(
                word=word,
                source_example=source_example,
                original_line=word,
            )
        )


def build_cli_parser() -> argparse.ArgumentParser:
    """Build the command-line parser for non-interactive and legacy file-driven runs."""
    parser = argparse.ArgumentParser(
        description="Create Anki vocabulary cards from a file, inline entries, or stdin.",
    )
    parser.add_argument(
        "-e",
        "--entry",
        action="append",
        default=[],
        help="Inline entry such as 'clarify｜I asked the teacher to clarify the lesson.'. Can be repeated.",
    )
    parser.add_argument(
        "--stdin",
        action="store_true",
        help=(
            "Read entries from standard input, one per line. "
            "Supports word<TAB>sentence, word｜sentence, and word|sentence."
        ),
    )
    parser.add_argument(
        "--concurrent",
        action="store_true",
        help="Use concurrent processing for the supplied entries.",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=4,
        help="Maximum worker threads when --concurrent is enabled (default: 4).",
    )
    parser.add_argument(
        "--rate-limit",
        type=float,
        default=2.0,
        help="Per-second rate limit when --concurrent is enabled (default: 2.0).",
    )
    return parser


def _log_invalid_input_lines(errors: Sequence[str]) -> None:
    for error in errors:
        logger.warning("跳过无效输入行: %s", error)
    if errors:
        logger.warning("共有 %s 条输入被跳过", len(errors))


def parse_inline_entries(entry_values: Sequence[str], stdin_text: str = "") -> List[VocabularyInput]:
    """Parse inline arguments and piped input into vocabulary requests."""
    raw_lines: List[str] = []

    for entry_value in entry_values:
        raw_lines.extend(entry_value.splitlines())

    if stdin_text:
        raw_lines.extend(stdin_text.splitlines())

    entries, errors = parse_vocabulary_lines(raw_lines)
    _log_invalid_input_lines(errors)
    logger.info("成功读取 %s 条直接输入", len(entries))
    return entries


def read_word_list(file_path: Path = WORD_LIST_FILE) -> List[VocabularyInput]:
    """
    读取单词列表文件

    Args:
        file_path: 文件路径

    Returns:
        单词列表
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            entries, errors = parse_vocabulary_lines(f)
        logger.info(f"成功读取 {len(entries)} 条输入")
        _log_invalid_input_lines(errors)
        return entries
    except FileNotFoundError:
        logger.error(f"文件未找到: {file_path}")
        return []
    except Exception as e:
        logger.error(f"读取文件时发生错误: {str(e)}")
        return []


def _resolve_collins_api_key(active_data_source_strategy: str, allow_interactive_prompt: bool) -> Optional[str]:
    """Resolve the Collins API key for the current run mode."""
    collins_api_key = COLLINS_API_KEY

    if active_data_source_strategy in ["collins_only", "collins_first"]:
        if collins_api_key:
            return collins_api_key

        if allow_interactive_prompt:
            collins_api_key = input("请输入Collins API密钥: ").strip()
            if collins_api_key:
                return collins_api_key
            raise ValueError("API密钥不能为空")

        raise ValueError("当前数据源策略需要 COLLINS_API_KEY；非交互模式不会提示输入。")

    logger.info("当前策略不需要Collins API密钥")
    return collins_api_key


def _collect_requested_entries(args: argparse.Namespace) -> List[VocabularyInput]:
    """Collect inline or piped inputs for agent-friendly direct runs."""
    stdin_text = ""
    if args.stdin:
        stdin_text = sys.stdin.read()

    if not args.entry and not stdin_text:
        return []

    return parse_inline_entries(args.entry, stdin_text=stdin_text)


def main(argv: Optional[Sequence[str]] = None):
    """主函数"""
    parser = build_cli_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    direct_entries = _collect_requested_entries(args)
    is_direct_mode = bool(args.entry or args.stdin)
    active_data_source_strategy = "llm_only" if is_direct_mode else DATA_SOURCE_STRATEGY

    logger.info("启动Anki词汇自动化程序")
    logger.info("数据源策略: %s", active_data_source_strategy)
    logger.info("LLM Prompt版本: %s", LLM_PROMPT_VERSION)

    try:
        collins_api_key = _resolve_collins_api_key(
            active_data_source_strategy=active_data_source_strategy,
            allow_interactive_prompt=not is_direct_mode,
        )
    except ValueError as exc:
        logger.error(str(exc))
        return 1

    # 读取单词列表
    word_list = direct_entries if is_direct_mode else read_word_list()
    if not word_list:
        if is_direct_mode:
            logger.error("没有可处理的直接输入，请传入 --entry 或通过 --stdin 提供内容")
        else:
            logger.error("无法读取单词列表或列表为空")
        return 1

    # 创建自动化实例
    automation = VocabularyAutomation(
        collins_api_key,
        data_source_strategy=active_data_source_strategy,
    )

    # 处理单词列表
    if args.concurrent:
        max_workers = max(1, min(args.max_workers, 8))
        rate_limit = max(0.1, min(args.rate_limit, 10.0))
        processing_succeeded = automation.process_word_list_concurrent(
            word_list,
            max_workers=max_workers,
            rate_limit=rate_limit,
        )
    else:
        processing_succeeded = automation.process_word_list(word_list)

    if not processing_succeeded:
        logger.error("程序未能完成导入流程")
        return 1

    logger.info("程序执行完成")
    return 0


if __name__ == "__main__":
    exit(main())
