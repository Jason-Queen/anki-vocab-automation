"""
主程序
Main automation workflow for Anki Vocabulary Automation
"""

import time
import logging
from typing import List
from pathlib import Path

from .collins_api import CollinsAPI
from .html_parser import HTMLParser
from .anki_connect import AnkiConnect
from .openai_compatible_client import OpenAICompatibleClient
from .audio_manager import AudioManager
from .concurrent_processor import (
    ConcurrentProcessor, 
    ProcessingResult, 
    ProcessingStats,
    create_progress_callback,
    process_words_concurrently
)
from .config import (
    COLLINS_API_KEY,
    WORD_LIST_FILE,
    REQUEST_DELAY,
    LOG_FILE,
    LOG_FORMAT,
    LOG_LEVEL,
    LLM_BASE_URL,
    LLM_API_KEY,
    LLM_MODEL_NAME,
    LLM_TIMEOUT,
    LLM_AUTO_DETECT_CAPABILITIES,
    LLM_FORCE_THINKING_MODE,
    LLM_CUSTOM_TEMPERATURE,
    LLM_CUSTOM_MAX_TOKENS,
    ENABLE_LLM_FALLBACK,
    DATA_SOURCE_STRATEGY,
    ENABLE_TTS_FALLBACK,
    TTS_SERVICE,
    TTS_VOICE
)

# 配置日志
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=LOG_FORMAT,
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class VocabularyAutomation:
    """主要的自动化流程类"""
    
    def __init__(self, collins_api_key: str = COLLINS_API_KEY):
        """
        初始化自动化流程
        
        Args:
            collins_api_key: Collins API密钥
        """
        self.collins_api = CollinsAPI(collins_api_key)
        self.html_parser = HTMLParser()
        self.anki_connect = AnkiConnect()
        
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
            "audio_failed": 0
        }
    
    def _initialize_llm_client(self) -> OpenAICompatibleClient:
        """
        初始化LLM客户端，支持高级配置
        
        Returns:
            配置好的OpenAICompatibleClient实例
        """
        # 创建基本客户端
        client = OpenAICompatibleClient(
            base_url=LLM_BASE_URL,
            api_key=LLM_API_KEY,
            model_name=LLM_MODEL_NAME,
            timeout=LLM_TIMEOUT,
            enable_tts=ENABLE_TTS_FALLBACK,
            tts_service=TTS_SERVICE
        )
        
        # 应用高级配置
        if not LLM_AUTO_DETECT_CAPABILITIES:
            # 禁用自动检测，使用默认配置
            from .openai_compatible_client import ModelCapabilities
            client.model_capabilities = ModelCapabilities()
        
        if LLM_FORCE_THINKING_MODE is not None:
            # 强制设置thinking模式
            client.model_capabilities.supports_thinking = LLM_FORCE_THINKING_MODE
            logger.info(f"强制设置thinking模式: {LLM_FORCE_THINKING_MODE}")
        
        if LLM_CUSTOM_TEMPERATURE is not None:
            # 自定义温度
            client.model_capabilities.temperature = LLM_CUSTOM_TEMPERATURE
            logger.info(f"自定义温度: {LLM_CUSTOM_TEMPERATURE}")
        
        if LLM_CUSTOM_MAX_TOKENS is not None:
            # 自定义最大token数
            client.model_capabilities.max_tokens = LLM_CUSTOM_MAX_TOKENS
            logger.info(f"自定义最大token数: {LLM_CUSTOM_MAX_TOKENS}")
        
        logger.info(f"LLM客户端初始化完成 - 模型: {LLM_MODEL_NAME}, 支持thinking: {client.model_capabilities.supports_thinking}")
        return client
    
    def process_word_list(self, word_list: List[str]) -> None:
        """
        处理单词列表
        
        Args:
            word_list: 单词列表
        """
        if not self.anki_connect.check_connection():
            logger.error("无法连接到Anki Connect")
            return
        
        if not self.anki_connect.ensure_deck_exists():
            logger.error("无法创建或访问卡牌组")
            return
        
        # 确保支持双重发音的模板存在
        if not self.anki_connect.ensure_model_exists():
            logger.error("无法创建或访问词汇模板")
            return
        
        self.stats["total"] = len(word_list)
        logger.info(f"开始处理 {len(word_list)} 个单词")
        
        for i, word in enumerate(word_list, 1):
            word = word.strip()
            if not word:
                continue
            
            logger.info(f"处理进度: {i}/{len(word_list)} - {word}")
            
            if not self._process_single_word(word):
                continue
            
            # 添加延迟避免API限制
            if i < len(word_list):  # 最后一个单词不需要延迟
                time.sleep(REQUEST_DELAY)
        
        self._print_stats()
    
    def process_word_list_concurrent(self, 
                                   word_list: List[str], 
                                   max_workers: int = 4,
                                   rate_limit: float = 2.0) -> None:
        """
        并发处理单词列表（实时添加到Anki版本）
        
        Args:
            word_list: 单词列表
            max_workers: 最大并发工作线程数
            rate_limit: 速率限制（每秒请求数）
        """
        if not self.anki_connect.check_connection():
            logger.error("无法连接到Anki Connect")
            return
        
        if not self.anki_connect.ensure_deck_exists():
            logger.error("无法创建或访问卡牌组")
            return
        
        # 确保支持双重发音的模板存在
        if not self.anki_connect.ensure_model_exists():
            logger.error("无法创建或访问词汇模板")
            return
        
        self.stats["total"] = len(word_list)
        logger.info(f"开始并发处理 {len(word_list)} 个单词 (并发度: {max_workers}, 速率: {rate_limit}/s)")
        logger.info("💡 改进: 每个单词处理完成后立即添加到Anki，无需等待所有单词完成")
        
        # 创建并发处理器
        processor = ConcurrentProcessor(
            max_workers=max_workers,
            rate_limit_per_second=rate_limit,
            timeout_per_word=120.0,  # 每个单词2分钟超时
            retry_attempts=2
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
                        logger.info(f"🎉 [{current}/{total}] {result.word} - 成功添加到Anki! ({result.processing_time:.1f}s)")
                        # 确定数据源
                        if hasattr(result.result, 'source'):
                            if result.result.source == 'collins':
                                self.stats["collins_used"] += 1
                            elif result.result.source == 'llm':
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
        def process_word_func(word: str):
            return self._get_vocabulary_card(word)
        
        try:
            logger.info("🚀 开始实时并发处理...")
            
            # 执行并发处理（现在会实时添加到Anki）
            results, stats = processor.process_words_batch(
                word_list, 
                process_word_func, 
                progress_callback
            )
            
            logger.info(f"✅ 并发处理全部完成!")
            logger.info(f"📊 最终统计: 处理={len(results)}, 成功={self.stats['success']}, 失败={self.stats['failed']}, 重复={self.stats['duplicates']}")
            logger.info(f"⏱️  总耗时: {stats.total_time:.2f}s, 平均: {stats.average_time_per_word:.2f}s/词")
            
        except Exception as e:
            logger.error(f"并发处理过程中发生异常: {e}")
            import traceback
            logger.error(f"异常详情: {traceback.format_exc()}")
        
        logger.info("开始打印最终统计信息...")
        self._print_stats()
    
    def _process_single_word(self, word: str) -> bool:
        """
        处理单个单词
        
        Args:
            word: 单词
            
        Returns:
            True如果处理成功，False否则
        """
        try:
            # 检查是否已存在
            if self.anki_connect.find_duplicate(word):
                logger.info(f"跳过重复单词: {word}")
                self.stats["duplicates"] += 1
                return False
            
            # 根据策略获取词汇卡片
            card = self._get_vocabulary_card(word)
            if not card:
                self.stats["not_found"] += 1
                return False
            
            # 再次检查是否已存在（使用标准词汇形式）
            if card.word != word and self.anki_connect.find_duplicate(card.word):
                logger.info(f"跳过重复单词: {word} → {card.word}")
                self.stats["duplicates"] += 1
                return False
            
            # 处理音频：下载并存储到Anki
            if not self._process_card_audio(card):
                logger.warning(f"音频处理失败，但仍继续添加卡片: {word}")
            
            # 添加到Anki
            if self.anki_connect.add_note(card):
                self.stats["success"] += 1
                return True
            else:
                self.stats["failed"] += 1
                return False
                
        except Exception as e:
            logger.error(f"处理单词时发生异常 - {word}: {str(e)}")
            self.stats["failed"] += 1
            return False
    
    def _get_vocabulary_card(self, word: str):
        """
        根据配置的策略获取词汇卡片
        
        Args:
            word: 单词
            
        Returns:
            VocabularyCard对象或None
        """
        if DATA_SOURCE_STRATEGY == "collins_only":
            return self._get_card_from_collins(word)
        elif DATA_SOURCE_STRATEGY == "llm_only":
            return self._get_card_from_llm(word)
        elif DATA_SOURCE_STRATEGY == "collins_first":
            # 优先使用Collins API
            card = self._get_card_from_collins(word)
            if card:
                return card
            # Collins失败，尝试LLM
            if ENABLE_LLM_FALLBACK:
                logger.info(f"Collins API失败或无密钥，尝试使用LLM: {word}")
                return self._get_card_from_llm(word)
            return None
        elif DATA_SOURCE_STRATEGY == "llm_first":
            # 优先使用LLM
            card = self._get_card_from_llm(word)
            if card:
                return card
            # LLM失败，尝试Collins API
            logger.info(f"LLM失败，尝试使用Collins API: {word}")
            return self._get_card_from_collins(word)
        else:
            logger.error(f"未知的数据源策略: {DATA_SOURCE_STRATEGY}")
            return None
    
    def _get_card_from_collins(self, word: str):
        """
        从Collins API获取词汇卡片（支持双重发音）
        
        Args:
            word: 单词
            
        Returns:
            VocabularyCard对象或None
        """
        try:
            # 使用新的双重发音API
            response_data = self.collins_api.search_word_with_dual_pronunciation(word)
            if not response_data:
                return None
            
            card = self.html_parser.parse_collins_response_with_dual_pronunciation(response_data, word)
            if card:
                self.stats["collins_used"] += 1
                logger.debug(f"成功使用Collins API获取（双重发音）: {word}")
            return card
        except Exception as e:
            logger.error(f"Collins API查询失败 - {word}: {str(e)}")
            return None
    
    def _get_card_from_llm(self, word: str):
        """
        从LLM获取词汇卡片
        
        Args:
            word: 单词
            
        Returns:
            VocabularyCard对象或None
        """
        try:
            card = self.llm_client.generate_vocabulary_card(word)
            if card:
                self.stats["llm_used"] += 1
                logger.debug(f"成功使用LLM获取: {word}")
            return card
        except Exception as e:
            logger.error(f"LLM查询失败 - {word}: {str(e)}")
            return None
    
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
            main_success = self._process_single_audio_file(card, card.audio_filename, 'main')
            if main_success:
                logger.debug(f"主要音频处理成功: {card.word}")
            else:
                success = False
        
        # 处理英式音频文件
        if hasattr(card, 'british_audio_filename') and card.british_audio_filename:
            if card.british_audio_filename != card.audio_filename:  # 避免重复处理
                british_success = self._process_single_audio_file(card, card.british_audio_filename, 'british')
                if british_success:
                    logger.debug(f"英式音频处理成功: {card.word}")
                else:
                    success = False
        
        # 处理美式音频文件
        if hasattr(card, 'american_audio_filename') and card.american_audio_filename:
            if card.american_audio_filename not in [card.audio_filename, card.british_audio_filename]:  # 避免重复处理
                american_success = self._process_single_audio_file(card, card.american_audio_filename, 'american')
                if american_success:
                    logger.debug(f"美式音频处理成功: {card.word}")
                else:
                    success = False
        
        return success
    
    def _process_single_audio_file(self, card, audio_url: str, audio_type: str = 'main') -> bool:
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
        if audio_url.startswith(('http://', 'https://')):
            try:
                # 下载音频文件
                local_file_path = self.audio_manager.download_audio(audio_url, card.word)
                if not local_file_path:
                    logger.error(f"下载音频失败: {card.word} ({audio_type})")
                    self._clear_audio_filename(card, audio_type)
                    self.stats["audio_failed"] += 1
                    return False
                
                # 生成Anki中的文件名
                from pathlib import Path
                import hashlib
                
                # 使用单词、URL和类型生成唯一文件名
                url_hash = hashlib.md5(audio_url.encode()).hexdigest()[:8]
                safe_word = "".join(c for c in card.word if c.isalnum() or c in "._-")[:20]
                
                # 从本地文件获取扩展名
                local_path = Path(local_file_path)
                extension = local_path.suffix
                anki_filename = f"vocab_{safe_word}_{audio_type}_{url_hash}{extension}"
                
                # 存储到Anki媒体文件夹
                if self.anki_connect.store_media_file(local_file_path, anki_filename):
                    self._set_audio_filename(card, audio_type, anki_filename)
                    self.stats["audio_downloaded"] += 1
                    logger.info(f"成功存储音频文件: {card.word} ({audio_type}) -> {anki_filename}")
                    return True
                else:
                    logger.error(f"存储音频文件失败: {card.word} ({audio_type})")
                    self._clear_audio_filename(card, audio_type)
                    self.stats["audio_failed"] += 1
                    return False
                    
            except Exception as e:
                logger.error(f"处理音频文件时发生异常 - {card.word} ({audio_type}): {str(e)}")
                self._clear_audio_filename(card, audio_type)
                self.stats["audio_failed"] += 1
                return False
        
        # 如果音频文件名不是URL，认为是已经处理过的文件名
        logger.debug(f"使用现有音频文件: {card.word} ({audio_type}) -> {audio_url}")
        return True
    
    def _set_audio_filename(self, card, audio_type: str, filename: str):
        """设置音频文件名"""
        if audio_type == 'main':
            card.audio_filename = filename
        elif audio_type == 'british':
            card.british_audio_filename = filename
        elif audio_type == 'american':
            card.american_audio_filename = filename
    
    def _clear_audio_filename(self, card, audio_type: str):
        """清空音频文件名"""
        if audio_type == 'main':
            card.audio_filename = ""
        elif audio_type == 'british':
            card.british_audio_filename = ""
        elif audio_type == 'american':
            card.american_audio_filename = ""
    
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
    
    def process_single_word_test(self, word: str) -> bool:
        """
        测试处理单个单词（用于调试）
        
        Args:
            word: 单词
            
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
        
        return self._process_single_word(word)

def read_word_list(file_path: Path = WORD_LIST_FILE) -> List[str]:
    """
    读取单词列表文件
    
    Args:
        file_path: 文件路径
        
    Returns:
        单词列表
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            words = [line.strip() for line in f if line.strip()]
        logger.info(f"成功读取 {len(words)} 个单词")
        return words
    except FileNotFoundError:
        logger.error(f"文件未找到: {file_path}")
        return []
    except Exception as e:
        logger.error(f"读取文件时发生错误: {str(e)}")
        return []

def main():
    """主函数"""
    logger.info("启动Anki词汇自动化程序")
    logger.info(f"数据源策略: {DATA_SOURCE_STRATEGY}")
    
    # 根据数据源策略配置Collins API密钥
    collins_api_key = COLLINS_API_KEY
    if DATA_SOURCE_STRATEGY in ["collins_only", "collins_first"]:
        if not collins_api_key:
            collins_api_key = input("请输入Collins API密钥: ").strip()
            if not collins_api_key:
                logger.error("API密钥不能为空")
                return 1
    else:
        # 对于llm_only和llm_first策略，Collins API密钥是可选的
        logger.info("当前策略不需要Collins API密钥")
    
    # 读取单词列表
    word_list = read_word_list()
    if not word_list:
        logger.error("无法读取单词列表或列表为空")
        return 1
    
    # 创建自动化实例
    automation = VocabularyAutomation(collins_api_key)
    
    # 处理单词列表
    automation.process_word_list(word_list)
    
    logger.info("程序执行完成")
    return 0

if __name__ == "__main__":
    exit(main()) 