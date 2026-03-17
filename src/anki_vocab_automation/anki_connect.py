"""
Anki Connect客户端
Anki Connect API client for interacting with Anki
"""

import requests
import logging
import base64
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Dict, Optional

from .models import VocabularyCard
from .config import ANKI_CONNECT_HOST, ANKI_CONNECT_PORT, DECK_NAME, REQUEST_TIMEOUT

logger = logging.getLogger(__name__)

MODEL_TEMPLATE_ASSET_FILENAMES = {
    "front": "vocabulary_front.html",
    "back": "vocabulary_back.html",
    "css": "vocabulary.css",
}
MODEL_TEMPLATE_ASSET_PATHS = {
    asset_name: resources.files("anki_vocab_automation").joinpath("templates", asset_filename)
    for asset_name, asset_filename in MODEL_TEMPLATE_ASSET_FILENAMES.items()
}


@lru_cache(maxsize=1)
def load_vocabulary_model_assets() -> Dict[str, str]:
    """Load the canonical vocabulary model assets from packaged resources."""
    assets = {}

    for asset_name, asset_path in MODEL_TEMPLATE_ASSET_PATHS.items():
        if not asset_path.is_file():
            raise FileNotFoundError("缺少模板资源文件: {0}".format(asset_path))
        assets[asset_name] = asset_path.read_text(encoding="utf-8").strip()

    return assets


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

    def _get_required_model_fields(self) -> list:
        """Return the canonical field order for the vocabulary model."""
        return [
            "Word",
            "PartOfSpeech",
            "Example",
            "GeneratedExample",
            "Definition",
            "Pronunciation",
            "AudioFilename",
            "AudioSource",
            "BritishPronunciation",
            "AmericanPronunciation",
            "BritishAudioFilename",
            "AmericanAudioFilename",
            "BritishAudioSource",
            "AmericanAudioSource",
        ]

    def _build_model_templates(self) -> Dict[str, Dict[str, str]]:
        """Build the current front/back templates."""
        assets = load_vocabulary_model_assets()
        return {"Card 1": {"Front": assets["front"], "Back": assets["back"]}}

    def _build_model_css(self) -> str:
        """Build CSS for the current vocabulary model."""
        return load_vocabulary_model_assets()["css"]

    def _request(self, action: str, params: dict = None) -> dict:
        """
        发送请求到Anki Connect

        Args:
            action: API动作名称
            params: 参数字典

        Returns:
            API响应字典
        """
        payload = {"action": action, "version": 6, "params": params or {}}

        try:
            response = self.session.post(self.url, json=payload, timeout=REQUEST_TIMEOUT)
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

        try:
            if template_name in model_names:
                if not self._ensure_model_fields(template_name):
                    logger.error(f"模板 '{template_name}' 字段更新失败")
                    return False
                if not self._update_vocabulary_model(template_name):
                    logger.error(f"模板 '{template_name}' 模板更新失败")
                    return False
                logger.info(f"使用并更新模板: {template_name}")
                return True

            logger.info(f"创建新模板: {template_name}")
            return self._create_vocabulary_model()
        except (OSError, ValueError) as exc:
            logger.error("加载词汇模板资源失败: %s", exc)
            return False

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

        for field in self._get_required_model_fields():
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

        for field in self._get_required_model_fields():
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
        model_params = {
            "modelName": self.model_name,
            "inOrderFields": self._get_required_model_fields(),
            "css": self._build_model_css(),
            "isCloze": False,
            "cardTemplates": [
                {
                    "Name": "Card 1",
                    "Front": self._build_model_templates()["Card 1"]["Front"],
                    "Back": self._build_model_templates()["Card 1"]["Back"],
                }
            ],
        }

        result = self._request("createModel", model_params)
        if result.get("error"):
            logger.error(f"创建词汇模板失败: {result['error']}")
            return False

        logger.info(f"成功创建词汇模板: {self.model_name}")
        return True

    def _ensure_model_fields(self, model_name: str) -> bool:
        """Add any missing fields to an existing model without recreating it."""
        for index, field_name in enumerate(self._get_required_model_fields()):
            result = self._request(
                "modelFieldAdd",
                {"modelName": model_name, "fieldName": field_name, "index": index},
            )
            if result.get("error"):
                logger.error(f"补充模板字段失败 - {model_name}.{field_name}: {result['error']}")
                return False
        return True

    def _update_vocabulary_model(self, model_name: str) -> bool:
        """Update templates and CSS for an existing model."""
        template_result = self._request(
            "updateModelTemplates",
            {
                "model": {
                    "name": model_name,
                    "templates": self._build_model_templates(),
                }
            },
        )
        if template_result.get("error"):
            logger.error(f"更新模板HTML失败: {template_result['error']}")
            return False

        styling_result = self._request(
            "updateModelStyling",
            {
                "model": {
                    "name": model_name,
                    "css": self._build_model_css(),
                }
            },
        )
        if styling_result.get("error"):
            logger.error(f"更新模板CSS失败: {styling_result['error']}")
            return False

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
        note_data = {"deckName": self.deck_name, "modelName": self.model_name, "fields": card.to_dict(), "tags": []}

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
        query = f'deck:"{self.deck_name}" Word:{word}'
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
            with open(path, "rb") as f:
                file_data = f.read()

            base64_data = base64.b64encode(file_data).decode("utf-8")

            # 调用Anki Connect API存储媒体文件
            result = self._request("storeMediaFile", {"filename": filename, "data": base64_data})

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
