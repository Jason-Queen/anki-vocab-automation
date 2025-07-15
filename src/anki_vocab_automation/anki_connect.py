"""
Anki Connect客户端
Anki Connect API client for interacting with Anki
"""

import requests
import logging
import base64
from pathlib import Path
from typing import Dict, Optional

from .models import VocabularyCard
from .config import (
    ANKI_CONNECT_HOST,
    ANKI_CONNECT_PORT,
    DECK_NAME,
    MODEL_NAME,
    REQUEST_TIMEOUT
)

logger = logging.getLogger(__name__)

class AnkiConnect:
    """Anki Connect API 客户端"""
    
    def __init__(self, host: str = ANKI_CONNECT_HOST, port: int = ANKI_CONNECT_PORT):
        """
        初始化Anki Connect客户端
        
        Args:
            host: Anki Connect服务器地址
            port: Anki Connect服务器端口
        """
        self.url = f"http://{host}:{port}"
        self.deck_name = DECK_NAME
        self.model_name = self.deck_name  # 始终与牌组名一致
        self.session = requests.Session()
    
    def _request(self, action: str, params: dict = None) -> dict:
        """
        发送请求到Anki Connect
        
        Args:
            action: API动作名称
            params: 参数字典
            
        Returns:
            API响应字典
        """
        payload = {
            "action": action,
            "version": 6,
            "params": params or {}
        }
        
        try:
            response = self.session.post(
                self.url, 
                json=payload, 
                timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Anki Connect请求失败: {str(e)}")
            return {"error": str(e)}
    
    def check_connection(self) -> bool:
        """
        检查Anki Connect连接
        
        Returns:
            True如果连接成功，False否则
        """
        result = self._request("version")
        if result.get("error"):
            logger.error("无法连接到Anki Connect，请确保Anki正在运行且已安装AnkiConnect插件")
            return False
        
        logger.info(f"成功连接到Anki Connect，版本: {result.get('result', 'Unknown')}")
        return True
    
    def ensure_deck_exists(self) -> bool:
        """
        确保目标卡牌组存在
        
        Returns:
            True如果卡牌组存在或创建成功，False否则
        """
        # 获取所有卡牌组
        result = self._request("deckNames")
        if result.get("error"):
            logger.error(f"获取卡牌组列表失败: {result['error']}")
            return False
        
        deck_names = result.get("result", [])
        if self.deck_name not in deck_names:
            # 创建新的卡牌组
            result = self._request("createDeck", {"deck": self.deck_name})
            if result.get("error"):
                logger.error(f"创建卡牌组失败: {result['error']}")
                return False
            logger.info(f"成功创建卡牌组: {self.deck_name}")
        
        return True
    
    def ensure_model_exists(self) -> bool:
        """
        确保词汇模板存在
        
        Returns:
            True如果模板存在或创建成功，False否则
        """
        # 获取所有模板名称
        result = self._request("modelNames")
        if result.get("error"):
            logger.error(f"获取模板列表失败: {result['error']}")
            return False
        
        model_names = result.get("result", [])
        template_name = self.model_name
        
        # 检查是否存在同名模板且字段完整
        if template_name in model_names:
            if self._check_model_fields_for_model(template_name):
                logger.info(f"使用模板: {template_name}")
                return True
            else:
                logger.error(f"模板 '{template_name}' 已存在但字段不完整。请在Anki中手动删除该模板后重试。");
                return False
        # 不存在则创建
        logger.info(f"创建新模板: {template_name}")
        return self._create_vocabulary_model()
        
        # 旧的逻辑保留作为备用
        if self.model_name not in model_names:
            # 创建新的模板
            logger.info(f"模板 '{self.model_name}' 不存在，正在创建...")
            return self._create_vocabulary_model()
        else:
            # 检查现有模板是否包含双重发音字段
            if self._check_model_fields():
                logger.info(f"模板 '{self.model_name}' 已存在且包含双重发音字段")
                return True
            else:
                logger.warning(f"模板 '{self.model_name}' 已存在但不包含双重发音字段")
                # 尝试使用更新的模板名称
                updated_model_name = f"{self.model_name}_v2"
                if updated_model_name in model_names:
                    if self._check_model_fields_for_model(updated_model_name):
                        logger.info(f"使用更新的模板: {updated_model_name}")
                        self.model_name = updated_model_name
                        return True
                
                # 创建新的v2模板
                logger.info(f"创建新的双重发音模板: {updated_model_name}")
                original_name = self.model_name
                self.model_name = updated_model_name
                return self._create_vocabulary_model()
    
    def _check_model_fields_for_model(self, model_name: str) -> bool:
        """
        检查指定模板是否包含双重发音字段
        
        Args:
            model_name: 模板名称
            
        Returns:
            True如果包含双重发音字段，False否则
        """
        # 获取模板字段信息
        result = self._request("modelFieldNames", {"modelName": model_name})
        if result.get("error"):
            logger.error(f"获取模板字段失败: {result['error']}")
            return False
        
        field_names = result.get("result", [])
        
        # 检查是否包含双重发音字段
        dual_pronunciation_fields = ["BritishPronunciation", "AmericanPronunciation", "BritishAudioFilename", "AmericanAudioFilename"]
        for field in dual_pronunciation_fields:
            if field not in field_names:
                return False
        
        return True
    
    def _check_model_fields(self) -> bool:
        """
        检查模板是否包含双重发音字段
        
        Returns:
            True如果包含双重发音字段，False否则
        """
        # 获取模板字段信息
        result = self._request("modelFieldNames", {"modelName": self.model_name})
        if result.get("error"):
            logger.error(f"获取模板字段失败: {result['error']}")
            return False
        
        field_names = result.get("result", [])
        
        # 检查是否包含双重发音字段
        dual_pronunciation_fields = ["BritishPronunciation", "AmericanPronunciation", "BritishAudioFilename", "AmericanAudioFilename"]
        for field in dual_pronunciation_fields:
            if field not in field_names:
                logger.info(f"模板缺少字段: {field}")
                return False
        
        return True
 
    
    def _create_vocabulary_model(self) -> bool:
        """
        创建词汇学习模板（支持双重发音）
        
        Returns:
            True如果创建成功，False否则
        """
        # 定义模板的前端HTML
        front_template = """<div class="card">
    <div class="word">{{Word}}</div>
    <div class="example">
      <span class="label label-example">Example:</span><br>
      {{Example}}
    </div>
  </div>"""
        
        # 定义模板的后端HTML（支持双重发音）
        back_template = """<div class="card">
    {{FrontSide}}
    <hr class="divider">
    <div class="part-of-speech-back">
      <span class="pos-tag">{{PartOfSpeech}}</span>
    </div>
    <div class="definition">
      <span class="label label-definition">Definition:</span><br>
      {{Definition}}
    </div>
    
    <!-- 双重发音部分 -->
    <div class="pronunciation-section">
      <span class="label label-pronunciation">Pronunciation:</span><br>
      
      <!-- 英式发音 -->
      <div class="pronunciation-item">
        <div class="pronunciation-header">
          <span class="flag-icon">🇬🇧</span>
          <span class="pronunciation-label">British:</span>
          <span class="pronunciation-text">{{BritishPronunciation}}</span>
        </div>
        {{#BritishAudioFilename}}
        <audio controls class="pronunciation-audio">
          <source src="{{BritishAudioFilename}}" type="audio/mpeg">
          Your browser does not support the audio element.
        </audio>
        {{/BritishAudioFilename}}
      </div>
      
      <!-- 美式发音（只在有美式发音时显示） -->
      {{#AmericanPronunciation}}
      <div class="pronunciation-item">
        <div class="pronunciation-header">
          <span class="flag-icon">🇺🇸</span>
          <span class="pronunciation-label">American:</span>
          <span class="pronunciation-text">{{AmericanPronunciation}}</span>
        </div>
        {{#AmericanAudioFilename}}
        <audio controls class="pronunciation-audio">
          <source src="{{AmericanAudioFilename}}" type="audio/mpeg">
          Your browser does not support the audio element.
        </audio>
        {{/AmericanAudioFilename}}
      </div>
      {{/AmericanPronunciation}}
    </div>
  </div>"""
        
        # 定义CSS样式（支持双重发音）
        css_style = """/* Color variables */
    :root {
      --color-word: #2b6cb0;
      --color-example: #805ad5;
      --color-definition: #38a169;
      --color-pronunciation: #dd6b20;
      --color-pos: #d53f8c;
      --divider-color: #a0aec0;
      --background-light: #f7fafc;
      --background-dark: #2d3748;
    }
    @media (prefers-color-scheme: dark) {
      :root {
        --color-word: #63b3ed;
        --color-example: #9f7aea;
        --color-definition: #48bb78;
        --color-pronunciation: #f6ad55;
        --color-pos: #ed64a6;
        --divider-color: #718096;
        --background-light: #4a5568;
        --background-dark: #1a202c;
      }
    }
    
    .card {
      font-family: Arial, sans-serif;
      line-height: 1.6;
    }
    .card > * {
      margin: 0.5em 0;
    }
    .word {
      font-size: 1.5em;
      font-weight: bold;
      color: var(--color-word);
    }
    .label {
      font-weight: 600;
    }
    .label-example { color: var(--color-example); }
    .label-definition { color: var(--color-definition); }
    .label-pronunciation { color: var(--color-pronunciation); }
    .label-pos { color: var(--color-pos); }
    .pos-value { 
      color: var(--color-pos); 
      font-weight: 500; 
      margin-left: 0.5em;
    }
    .part-of-speech {
      margin: 0.5em 0;
      padding: 0.3em 0;
    }
    .part-of-speech-back {
      margin: 0.5em 0;
      text-align: left;
    }
    .pos-tag {
      display: inline-block;
      background-color: var(--color-pos);
      color: white;
      padding: 0.2em 0.5em;
      border-radius: 12px;
      font-size: 0.8em;
      font-weight: 500;
      margin: 0;
      vertical-align: top;
    }
    .divider {
      border: 0;
      height: 1px;
      background-color: var(--divider-color);
      margin: 0.75em 0;
    }
    
    /* 双重发音样式 */
    .pronunciation-section {
      background-color: var(--background-light);
      padding: 1em;
      border-radius: 8px;
      margin: 1em 0;
    }
    
    .pronunciation-item {
      margin: 0.5em 0;
      padding: 0.5em;
      border-left: 3px solid var(--color-pronunciation);
      background-color: rgba(255, 255, 255, 0.5);
      border-radius: 4px;
    }
    
    @media (prefers-color-scheme: dark) {
      .pronunciation-item {
        background-color: rgba(255, 255, 255, 0.1);
      }
    }
    
    .pronunciation-header {
      display: flex;
      align-items: center;
      gap: 0.5em;
      margin-bottom: 0.5em;
    }
    
    .flag-icon {
      font-size: 1.2em;
    }
    
    .pronunciation-label {
      font-weight: 600;
      color: var(--color-pronunciation);
      min-width: 80px;
    }
    
    .pronunciation-text {
      font-family: 'Courier New', monospace;
      font-size: 1.1em;
      color: var(--color-pronunciation);
      font-weight: 500;
    }
    
    .pronunciation-audio {
      width: 100%;
      max-width: 300px;
      height: 32px;
      margin-top: 0.25em;
    }
    
    /* 移动设备优化 */
    @media (max-width: 480px) {
      .pronunciation-header {
        flex-direction: column;
        align-items: flex-start;
        gap: 0.25em;
      }
      
      .pronunciation-text {
        font-size: 1em;
      }
      
      .pronunciation-audio {
        width: 100%;
        max-width: none;
      }
    }"""
        
        # 创建模板参数（包含双重发音字段）
        model_params = {
            "modelName": self.model_name,
            "inOrderFields": [
                "Word",
                "PartOfSpeech",
                "Example",
                "Definition", 
                "Pronunciation",
                "AudioFilename",
                # 双重发音字段
                "BritishPronunciation",
                "AmericanPronunciation",
                "BritishAudioFilename",
                "AmericanAudioFilename"
            ],
            "css": css_style,
            "isCloze": False,
            "cardTemplates": [
                {
                    "Name": "Card 1",
                    "Front": front_template,
                    "Back": back_template
                }
            ]
        }
        
        result = self._request("createModel", model_params)
        if result.get("error"):
            logger.error(f"创建词汇模板失败: {result['error']}")
            return False
        
        logger.info(f"成功创建词汇模板: {self.model_name}")
        return True
    
    def setup_environment(self) -> bool:
        """
        设置Anki环境，包括检查连接、创建卡牌组和模板
        
        Returns:
            True如果环境设置成功，False否则
        """
        print("🔍 正在检查Anki环境...")
        
        # 1. 检查AnkiConnect连接
        if not self.check_connection():
            print("❌ 无法连接到Anki")
            print("请确保:")
            print("  1. Anki正在运行")
            print("  2. 已安装AnkiConnect插件")
            print("  3. AnkiConnect插件已启用")
            return False
        
        print("✅ AnkiConnect连接正常")
        
        # 2. 检查并创建卡牌组
        if not self.ensure_deck_exists():
            print(f"❌ 无法创建卡牌组 '{self.deck_name}'")
            return False
        
        print(f"✅ 卡牌组 '{self.deck_name}' 已就绪")
        
        # 3. 检查并创建模板
        if not self.ensure_model_exists():
            print(f"❌ 无法创建词汇模板 '{self.model_name}'")
            return False
        
        print(f"✅ 词汇模板 '{self.model_name}' 已就绪")
        
        print("🎉 Anki环境设置完成！")
        return True
    
    def add_note(self, card: VocabularyCard) -> bool:
        """
        添加单词卡片到Anki
        
        Args:
            card: 词汇卡片实例
            
        Returns:
            True如果添加成功，False否则
        """
        note_data = {
            "deckName": self.deck_name,
            "modelName": self.model_name,
            "fields": card.to_dict(),
            "tags": []
        }
        
        result = self._request("addNote", {"note": note_data})
        if result.get("error"):
            logger.error(f"添加卡片失败 - {card.word}: {result['error']}")
            return False
        
        logger.info(f"成功添加卡片: {card.original_word} → {card.word}")
        return True
    
    def find_duplicate(self, word: str) -> bool:
        """
        检查是否已存在相同的单词
        
        Args:
            word: 要检查的单词
            
        Returns:
            True如果存在重复，False否则
        """
        query = f"deck:\"{self.deck_name}\" Word:{word}"
        result = self._request("findNotes", {"query": query})
        
        if result.get("error"):
            logger.warning(f"检查重复时出错: {result['error']}")
            return False
        
        notes = result.get("result", [])
        return len(notes) > 0
    
    def get_model_field_names(self) -> Optional[list]:
        """
        获取模型字段名称
        
        Returns:
            字段名称列表，如果失败则返回None
        """
        result = self._request("modelFieldNames", {"modelName": self.model_name})
        if result.get("error"):
            logger.error(f"获取模型字段失败: {result['error']}")
            return None
        
        return result.get("result", [])
    
    def get_deck_stats(self) -> Optional[dict]:
        """
        获取卡牌组统计信息
        
        Returns:
            统计信息字典，如果失败则返回None
        """
        result = self._request("getNumCardsReviewedToday")
        if result.get("error"):
            logger.error(f"获取统计信息失败: {result['error']}")
            return None
        
        return result.get("result", {})
    
    def store_media_file(self, file_path: str, filename: str) -> bool:
        """
        将音频文件存储到Anki媒体文件夹
        
        Args:
            file_path: 本地文件路径
            filename: 在Anki中的文件名
            
        Returns:
            True如果存储成功，False否则
        """
        try:
            path = Path(file_path)
            if not path.exists():
                logger.error(f"文件不存在: {file_path}")
                return False
            
            # 读取文件并编码为base64
            with open(path, 'rb') as f:
                file_data = f.read()
            
            base64_data = base64.b64encode(file_data).decode('utf-8')
            
            # 调用Anki Connect API存储媒体文件
            result = self._request("storeMediaFile", {
                "filename": filename,
                "data": base64_data
            })
            
            if result.get("error"):
                logger.error(f"存储媒体文件失败: {result['error']}")
                return False
            
            logger.info(f"成功存储媒体文件: {filename}")
            return True
            
        except Exception as e:
            logger.error(f"存储媒体文件时发生异常: {str(e)}")
            return False
    
    def retrieve_media_file(self, filename: str) -> Optional[bytes]:
        """
        从Anki媒体文件夹检索文件
        
        Args:
            filename: 文件名
            
        Returns:
            文件内容的字节数据，如果失败则返回None
        """
        try:
            result = self._request("retrieveMediaFile", {"filename": filename})
            
            if result.get("error"):
                logger.error(f"检索媒体文件失败: {result['error']}")
                return None
            
            # 解码base64数据
            base64_data = result.get("result")
            if not base64_data:
                return None
            
            return base64.b64decode(base64_data)
            
        except Exception as e:
            logger.error(f"检索媒体文件时发生异常: {str(e)}")
            return None
    
    def delete_media_file(self, filename: str) -> bool:
        """
        从Anki媒体文件夹删除文件
        
        Args:
            filename: 文件名
            
        Returns:
            True如果删除成功，False否则
        """
        try:
            result = self._request("deleteMediaFile", {"filename": filename})
            
            if result.get("error"):
                logger.error(f"删除媒体文件失败: {result['error']}")
                return False
            
            logger.info(f"成功删除媒体文件: {filename}")
            return True
            
        except Exception as e:
            logger.error(f"删除媒体文件时发生异常: {str(e)}")
            return False
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出，关闭会话"""
        self.session.close() 