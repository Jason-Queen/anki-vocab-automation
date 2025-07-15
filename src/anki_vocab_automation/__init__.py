"""
Anki Vocabulary Automation Package
自动化将单词列表转换为 Anki 卡牌的工具包
"""

from .main import VocabularyAutomation
from .collins_api import CollinsAPI
from .html_parser import HTMLParser
from .anki_connect import AnkiConnect
from .openai_compatible_client import OpenAICompatibleClient
from .models import VocabularyCard

__version__ = "2.0.0"
__author__ = "Anki Vocabulary Automation Team"

__all__ = [
    "VocabularyAutomation",
    "CollinsAPI", 
    "HTMLParser",
    "AnkiConnect",
    "OpenAICompatibleClient",
    "VocabularyCard",
] 