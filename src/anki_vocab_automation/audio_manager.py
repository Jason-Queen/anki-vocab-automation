"""
音频管理器
Audio manager for downloading and managing audio files for Anki vocabulary cards
"""

import os
import logging
import requests
import hashlib
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlparse
import tempfile
import time

logger = logging.getLogger(__name__)

class AudioManager:
    """音频文件管理器"""
    
    def __init__(self, temp_dir: Optional[str] = None):
        """
        初始化音频管理器
        
        Args:
            temp_dir: 临时目录路径，如果为None则使用系统临时目录
        """
        self.temp_dir = Path(temp_dir) if temp_dir else Path(tempfile.gettempdir()) / "anki_audio"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Anki-Vocabulary-Automation/2.0 (Audio Download)'
        })
        
    def download_audio(self, url: str, word: str, timeout: int = 30) -> Optional[str]:
        """
        下载音频文件
        
        Args:
            url: 音频URL
            word: 单词（用于生成文件名）
            timeout: 下载超时时间
            
        Returns:
            下载的文件路径，如果失败则返回None
        """
        if not url or not url.strip():
            logger.warning(f"空的音频URL: {word}")
            return None
            
        try:
            # 清理可能的URL前缀问题
            url = self._clean_url(url)
            
            # 生成文件名
            filename = self._generate_filename(word, url)
            file_path = self.temp_dir / filename
            
            # 如果文件已存在，直接返回
            if file_path.exists():
                logger.debug(f"音频文件已存在: {filename}")
                return str(file_path)
            
            # 下载文件
            logger.info(f"开始下载音频: {word} -> {url}")
            response = self.session.get(url, timeout=timeout, stream=True)
            response.raise_for_status()
            
            # 验证Content-Type
            content_type = response.headers.get('Content-Type', '')
            if not self._is_valid_audio_content_type(content_type):
                logger.warning(f"可疑的音频Content-Type: {content_type} for {word}")
            
            # 写入文件
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            # 验证文件大小
            file_size = file_path.stat().st_size
            if file_size == 0:
                logger.error(f"下载的音频文件为空: {word}")
                file_path.unlink()
                return None
            elif file_size < 100:  # 小于100字节可能是错误页面
                logger.warning(f"音频文件过小({file_size}字节): {word}")
            
            logger.info(f"成功下载音频: {word} -> {filename} ({file_size}字节)")
            return str(file_path)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"下载音频失败 - {word}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"下载音频时发生异常 - {word}: {str(e)}")
            return None
    
    def _clean_url(self, url: str) -> str:
        """
        清理URL，修复常见问题
        
        Args:
            url: 原始URL
            
        Returns:
            清理后的URL
        """
        # 移除可能的前缀符号
        url = url.strip()
        if url.startswith('@'):
            url = url[1:]
        
        # 修复HTML编码的&符号
        url = url.replace('&amp;', '&')
        
        # 确保是有效的URL
        if not url.startswith(('http://', 'https://')):
            logger.warning(f"无效的URL格式: {url}")
            return url
        
        return url
    
    def _generate_filename(self, word: str, url: str) -> str:
        """
        生成音频文件名
        
        Args:
            word: 单词
            url: 音频URL
            
        Returns:
            文件名
        """
        # 使用单词和URL哈希生成唯一文件名
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        safe_word = "".join(c for c in word if c.isalnum() or c in "._-")[:20]
        
        # 尝试从URL获取文件扩展名
        parsed_url = urlparse(url)
        path = parsed_url.path
        if path and '.' in path:
            ext = path.split('.')[-1].lower()
            if ext in ['mp3', 'wav', 'ogg', 'm4a', 'aac']:
                return f"{safe_word}_{url_hash}.{ext}"
        
        # 默认使用mp3扩展名
        return f"{safe_word}_{url_hash}.mp3"
    
    def _is_valid_audio_content_type(self, content_type: str) -> bool:
        """
        检查Content-Type是否是有效的音频类型
        
        Args:
            content_type: HTTP Content-Type头
            
        Returns:
            True如果是有效的音频类型
        """
        if not content_type:
            return True  # 允许空Content-Type
        
        audio_types = [
            'audio/',
            'application/octet-stream',  # 通用二进制类型
            'binary/octet-stream'
        ]
        
        return any(content_type.startswith(t) for t in audio_types)
    
    def cleanup_temp_files(self, max_age_hours: int = 24):
        """
        清理临时文件
        
        Args:
            max_age_hours: 文件最大保存时间（小时）
        """
        try:
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            
            for file_path in self.temp_dir.glob("*"):
                if file_path.is_file():
                    file_age = current_time - file_path.stat().st_mtime
                    if file_age > max_age_seconds:
                        file_path.unlink()
                        logger.debug(f"删除过期临时文件: {file_path.name}")
        except Exception as e:
            logger.warning(f"清理临时文件失败: {str(e)}")
    
    def get_audio_info(self, file_path: str) -> Optional[dict]:
        """
        获取音频文件信息
        
        Args:
            file_path: 音频文件路径
            
        Returns:
            音频信息字典，如果失败则返回None
        """
        try:
            path = Path(file_path)
            if not path.exists():
                return None
            
            stat = path.stat()
            return {
                'filename': path.name,
                'size': stat.st_size,
                'modified': stat.st_mtime,
                'exists': True
            }
        except Exception as e:
            logger.warning(f"获取音频信息失败 - {file_path}: {str(e)}")
            return None
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.session.close() 