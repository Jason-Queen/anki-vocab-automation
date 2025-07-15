"""
TTS音频生成器
Text-to-Speech audio URL generator for vocabulary cards
"""

import logging
import urllib.parse
from typing import Optional
from urllib.parse import quote

logger = logging.getLogger(__name__)

class TTSGenerator:
    """TTS音频生成器"""
    
    def __init__(self, service: str = "google", voice: str = "en-US"):
        """
        初始化TTS生成器
        
        Args:
            service: TTS服务提供商 ("google", "microsoft", "responsivevoice")
            voice: 语音类型
        """
        self.service = service.lower()
        self.voice = voice
        
    def generate_audio_url(self, word: str, pronunciation: str = "", language: str = "en-US") -> str:
        """
        生成单词的音频URL
        
        Args:
            word: 单词
            pronunciation: 发音（可选，用于某些服务）
            language: 语言代码 (en-US, en-GB等)
            
        Returns:
            音频URL字符串，如果失败则返回空字符串
        """
        if not word.strip():
            return ""
            
        try:
            if self.service == "google":
                return self._generate_google_tts_url(word, language)
            elif self.service == "microsoft":
                return self._generate_microsoft_tts_url(word, language)
            elif self.service == "responsivevoice":
                return self._generate_responsivevoice_url(word, language)
            else:
                logger.warning(f"不支持的TTS服务: {self.service}")
                return ""
                
        except Exception as e:
            logger.error(f"生成TTS URL失败 - {word}: {str(e)}")
            return ""
    
    def _generate_google_tts_url(self, word: str, language: str = "en-US") -> str:
        """
        生成Google TTS URL
        
        Args:
            word: 单词
            language: 语言代码
            
        Returns:
            Google TTS URL
        """
        # 将language转换为Google TTS支持的格式
        if language == "en-GB":
            tl = "en-gb"
        elif language == "en-US":
            tl = "en-us"
        else:
            tl = "en"
        
        # Google Translate TTS API
        encoded_word = quote(word)
        url = f"https://translate.google.com/translate_tts?ie=UTF-8&tl={tl}&client=tw-ob&q={encoded_word}"
        logger.debug(f"生成Google TTS URL: {word} ({language}) -> {url}")
        return url
    
    def _generate_microsoft_tts_url(self, word: str, language: str = "en-US") -> str:
        """
        生成Microsoft TTS URL
        
        Args:
            word: 单词
            language: 语言代码
            
        Returns:
            Microsoft TTS URL
        """
        # 选择合适的语音
        if language == "en-GB":
            voice = "en-GB-LibbyNeural"
        elif language == "en-US":
            voice = "en-US-JennyNeural"
        else:
            voice = self.voice
        
        # Microsoft Edge TTS (需要特定的API调用)
        encoded_word = quote(word)
        url = f"https://speech.platform.bing.com/synthesize?text={encoded_word}&voice={voice}&format=audio-16khz-32kbitrate-mono-mp3"
        logger.debug(f"生成Microsoft TTS URL: {word} ({language}) -> {url}")
        return url
    
    def _generate_responsivevoice_url(self, word: str, language: str = "en-US") -> str:
        """
        生成ResponsiveVoice TTS URL
        
        Args:
            word: 单词
            language: 语言代码
            
        Returns:
            ResponsiveVoice TTS URL
        """
        # 选择合适的语音
        if language == "en-GB":
            voice = "UK English Female"
        elif language == "en-US":
            voice = "US English Female"
        else:
            voice = "US English Female"
        
        # ResponsiveVoice API
        encoded_word = quote(word)
        encoded_voice = quote(voice)
        url = f"https://responsivevoice.org/responsivevoice/getvoice.php?t={encoded_word}&tl={language}&sv={encoded_voice}&pitch=0.5&rate=0.5&vol=1"
        logger.debug(f"生成ResponsiveVoice TTS URL: {word} ({language}) -> {url}")
        return url
    
    def is_available(self) -> bool:
        """
        检查TTS服务是否可用
        
        Returns:
            True如果服务可用，False否则
        """
        # 这里可以添加实际的服务可用性检查
        return True
    
    @staticmethod
    def get_available_services() -> list:
        """
        获取可用的TTS服务列表
        
        Returns:
            服务名称列表
        """
        return ["google", "microsoft", "responsivevoice"] 