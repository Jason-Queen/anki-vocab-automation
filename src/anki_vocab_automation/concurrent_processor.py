"""
并发处理模块
Concurrent processing module for improved batch word processing performance
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional, Callable, Tuple, Union
from dataclasses import dataclass
from threading import Lock
import threading

from .models import VocabularyCard, VocabularyInput
from .input_validator import sanitize_word_input, validate_word_input

logger = logging.getLogger(__name__)


@dataclass
class ProcessingResult:
    """处理结果数据类"""

    word: str
    success: bool
    result: Optional[VocabularyCard] = None
    error: Optional[str] = None
    processing_time: float = 0.0


@dataclass
class ProcessingStats:
    """处理统计信息数据类"""

    total_words: int = 0
    successful: int = 0
    failed: int = 0
    skipped: int = 0
    total_time: float = 0.0
    average_time_per_word: float = 0.0


class ConcurrentProcessor:
    """
    并发处理器
    Concurrent processor for batch word processing with rate limiting and error handling
    """

    def __init__(
        self,
        max_workers: int = 4,
        rate_limit_per_second: Optional[float] = None,
        timeout_per_word: float = 60.0,
        retry_attempts: int = 2,
        retry_delay: float = 1.0,
    ):
        """
        初始化并发处理器

        Args:
            max_workers: 最大并发工作线程数
            rate_limit_per_second: 每秒请求限制（None表示无限制）
            timeout_per_word: 每个单词的超时时间（秒）
            retry_attempts: 重试次数
            retry_delay: 重试延迟（秒）
        """
        self.max_workers = max_workers
        self.rate_limit_per_second = rate_limit_per_second
        self.timeout_per_word = timeout_per_word
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay

        # 速率限制相关
        self.last_request_time = 0.0
        self.rate_limit_lock = Lock()

        # 统计信息
        self.stats = ProcessingStats()
        self.stats_lock = Lock()

        logger.info(
            f"并发处理器初始化: max_workers={max_workers}, "
            f"rate_limit={rate_limit_per_second}/s, timeout={timeout_per_word}s"
        )

    def _wait_for_rate_limit(self):
        """等待速率限制"""
        if self.rate_limit_per_second is None:
            return

        with self.rate_limit_lock:
            current_time = time.time()
            min_interval = 1.0 / self.rate_limit_per_second
            time_since_last = current_time - self.last_request_time

            if time_since_last < min_interval:
                sleep_time = min_interval - time_since_last
                logger.debug(f"速率限制: 等待 {sleep_time:.2f}s")
                time.sleep(sleep_time)

            self.last_request_time = time.time()

    def _update_stats(self, result: ProcessingResult):
        """更新统计信息"""
        with self.stats_lock:
            if result.success:
                self.stats.successful += 1
            else:
                self.stats.failed += 1

            self.stats.total_time += result.processing_time

    def _process_single_word(
        self,
        word_input: Union[str, VocabularyInput],
        processor_func: Callable[[VocabularyInput], Optional[VocabularyCard]],
        word_index: int,
        total_words: int,
    ) -> ProcessingResult:
        """
        处理单个单词（带重试和错误处理）

        Args:
            word_input: 要处理的输入
            processor_func: 处理函数
            word_index: 单词索引（用于日志）
            total_words: 总单词数

        Returns:
            ProcessingResult对象
        """
        thread_id = threading.get_ident()
        start_time = time.time()
        entry = self._normalize_input(word_input)

        # 输入验证
        is_valid, error_msg = validate_word_input(entry.word)
        if not is_valid:
            logger.warning(f"[线程{thread_id}] 单词 '{entry.word}' 验证失败: {error_msg}")
            return ProcessingResult(
                word=entry.word,
                success=False,
                error=f"输入验证失败: {error_msg}",
                processing_time=time.time() - start_time,
            )

        # 清理输入
        clean_word = sanitize_word_input(entry.word)
        clean_entry = VocabularyInput(
            word=clean_word,
            source_example=entry.source_example,
            original_line=entry.original_line or clean_word,
        )

        # 重试逻辑
        last_error = None
        for attempt in range(self.retry_attempts + 1):
            try:
                # 等待速率限制
                self._wait_for_rate_limit()

                logger.info(
                    f"[线程{thread_id}] 处理单词 '{clean_word}' "
                    f"({word_index + 1}/{total_words}) - 尝试 {attempt + 1}"
                )

                # 调用处理函数
                result = processor_func(clean_entry)

                processing_time = time.time() - start_time

                if result is not None:
                    logger.info(f"[线程{thread_id}] 成功处理 '{clean_word}' " f"(耗时: {processing_time:.2f}s)")
                    return ProcessingResult(
                        word=entry.word, success=True, result=result, processing_time=processing_time
                    )
                else:
                    last_error = "处理函数返回None"

            except Exception as e:
                last_error = str(e)
                logger.warning(f"[线程{thread_id}] 处理 '{clean_word}' 失败 " f"(尝试 {attempt + 1}): {last_error}")

                # 如果不是最后一次尝试，等待后重试
                if attempt < self.retry_attempts:
                    time.sleep(self.retry_delay * (attempt + 1))  # 指数退避

        # 所有重试都失败了
        processing_time = time.time() - start_time
        logger.error(f"[线程{thread_id}] 单词 '{clean_word}' 处理失败，已用尽所有重试")

        return ProcessingResult(word=entry.word, success=False, error=last_error, processing_time=processing_time)

    def process_words_batch(
        self,
        words: List[Union[str, VocabularyInput]],
        processor_func: Callable[[VocabularyInput], Optional[VocabularyCard]],
        progress_callback: Optional[Callable[[int, int, ProcessingResult], None]] = None,
    ) -> Tuple[List[ProcessingResult], ProcessingStats]:
        """
        批量处理单词列表

        Args:
            words: 要处理的单词列表
            processor_func: 处理函数
            progress_callback: 进度回调函数 (current, total, result)

        Returns:
            (结果列表, 统计信息)
        """
        if not words:
            logger.warning("单词列表为空")
            return [], ProcessingStats()

        # 重置统计信息
        self.stats = ProcessingStats(total_words=len(words))
        start_time = time.time()

        logger.info(f"开始批量处理 {len(words)} 个单词 (并发度: {self.max_workers})")

        results = []
        completed_count = 0

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_word = {}
            for i, word in enumerate(words):
                future = executor.submit(self._process_single_word, word, processor_func, i, len(words))
                future_to_word[future] = (word, i)

            # 收集结果
            for future in as_completed(future_to_word, timeout=self.timeout_per_word * len(words)):
                try:
                    result = future.result()
                    results.append(result)
                    completed_count += 1

                    # 更新统计信息
                    self._update_stats(result)

                    # 调用进度回调
                    if progress_callback:
                        try:
                            progress_callback(completed_count, len(words), result)
                        except Exception as e:
                            logger.warning(f"进度回调出错: {e}")

                    # 记录进度
                    if completed_count % 5 == 0 or completed_count == len(words):
                        logger.info(
                            f"进度: {completed_count}/{len(words)} "
                            f"(成功: {self.stats.successful}, "
                            f"失败: {self.stats.failed})"
                        )

                except Exception as e:
                    word, index = future_to_word[future]
                    entry = self._normalize_input(word)
                    error_result = ProcessingResult(word=entry.word, success=False, error=f"任务执行异常: {str(e)}")
                    results.append(error_result)
                    completed_count += 1

                    self._update_stats(error_result)
                    logger.error(f"任务执行异常 - 单词 '{word}': {e}")

        # 完善统计信息
        total_time = time.time() - start_time
        self.stats.total_time = total_time
        self.stats.average_time_per_word = total_time / len(words) if words else 0

        logger.info(
            f"批量处理完成: 总耗时 {total_time:.2f}s, "
            f"平均 {self.stats.average_time_per_word:.2f}s/词, "
            f"成功 {self.stats.successful}/{len(words)}"
        )

        return results, self.stats

    def process_words_with_fallback(
        self,
        words: List[Union[str, VocabularyInput]],
        primary_processor: Callable[[VocabularyInput], Optional[VocabularyCard]],
        fallback_processor: Optional[Callable[[VocabularyInput], Optional[VocabularyCard]]] = None,
        progress_callback: Optional[Callable[[int, int, ProcessingResult], None]] = None,
    ) -> Tuple[List[ProcessingResult], ProcessingStats]:
        """
        使用主处理器和备用处理器进行批量处理

        Args:
            words: 要处理的单词列表
            primary_processor: 主处理器
            fallback_processor: 备用处理器（可选）
            progress_callback: 进度回调函数

        Returns:
            (结果列表, 统计信息)
        """

        def combined_processor(entry: VocabularyInput) -> Optional[VocabularyCard]:
            """组合处理器"""
            # 首先尝试主处理器
            try:
                result = primary_processor(entry)
                if result is not None:
                    return result
            except Exception as e:
                logger.debug(f"主处理器失败: {e}")

            # 如果主处理器失败且有备用处理器，尝试备用处理器
            if fallback_processor is not None:
                try:
                    logger.info(f"使用备用处理器处理 '{entry.word}'")
                    return fallback_processor(entry)
                except Exception as e:
                    logger.debug(f"备用处理器也失败: {e}")

            return None

        return self.process_words_batch(words, combined_processor, progress_callback)

    def _normalize_input(self, word_input: Union[str, VocabularyInput]) -> VocabularyInput:
        """Normalize raw strings and structured inputs into a VocabularyInput."""
        if isinstance(word_input, VocabularyInput):
            return word_input

        return VocabularyInput(word=str(word_input), original_line=str(word_input))


def create_progress_callback(show_details: bool = True) -> Callable[[int, int, ProcessingResult], None]:
    """
    创建进度回调函数

    Args:
        show_details: 是否显示详细信息

    Returns:
        进度回调函数
    """

    def progress_callback(current: int, total: int, result: ProcessingResult):
        if show_details:
            status = "✅" if result.success else "❌"
            time_info = f"({result.processing_time:.1f}s)" if result.processing_time > 0 else ""

            if result.success:
                logger.info(f"{status} [{current}/{total}] {result.word} {time_info}")
            else:
                logger.warning(f"{status} [{current}/{total}] {result.word} - {result.error} {time_info}")
        else:
            # 每10个显示一次进度
            if current % 10 == 0 or current == total:
                success_rate = (current - result.processing_time) / current if current > 0 else 0
                logger.info(f"进度: {current}/{total} (成功率: {success_rate:.1%})")

    return progress_callback


# 便利函数
def process_words_concurrently(
    words: List[str],
    processor_func: Callable[[str], Optional[VocabularyCard]],
    max_workers: int = 4,
    rate_limit: Optional[float] = None,
    show_progress: bool = True,
) -> Tuple[List[ProcessingResult], ProcessingStats]:
    """
    并发处理单词的便利函数

    Args:
        words: 单词列表
        processor_func: 处理函数
        max_workers: 最大工作线程数
        rate_limit: 速率限制（每秒请求数）
        show_progress: 是否显示进度

    Returns:
        (结果列表, 统计信息)
    """
    processor = ConcurrentProcessor(max_workers=max_workers, rate_limit_per_second=rate_limit)

    progress_callback = create_progress_callback() if show_progress else None

    return processor.process_words_batch(words, processor_func, progress_callback)
