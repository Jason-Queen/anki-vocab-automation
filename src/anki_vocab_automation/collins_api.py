"""
Collins Dictionary API 客户端
Collins Dictionary API client for fetching word data
"""

import requests
import json
import logging
from typing import Optional, Dict, Any, List, Tuple
from urllib.parse import quote

from .config import (
    COLLINS_API_KEY,
    COLLINS_API_BASE_URL,
    DICTIONARIES,
    PRONUNCIATION_SOURCES,
    REQUEST_TIMEOUT,
    MAX_RETRIES,
    USER_AGENT
)
from .input_validator import validate_word_input, sanitize_word_input

logger = logging.getLogger(__name__)

class CollinsAPI:
    """Collins Dictionary API 客户端"""
    
    def __init__(self, api_key: str = COLLINS_API_KEY):
        """
        初始化Collins API客户端
        
        Args:
            api_key: Collins API密钥
        """
        self.api_key = api_key
        self.base_url = COLLINS_API_BASE_URL
        
        # 只有当API密钥存在时才设置headers
        if api_key:
            self.headers = {
                'accessKey': api_key,
                'User-Agent': USER_AGENT
            }
        else:
            self.headers = {
                'User-Agent': USER_AGENT
            }
            
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def search_word(self, word: str) -> Optional[Dict[str, Any]]:
        """
        搜索单词，返回解析后的词汇数据
        
        Args:
            word: 要搜索的单词
            
        Returns:
            包含词汇数据的字典，如果失败则返回None
        """
        # 输入验证
        is_valid, error_msg = validate_word_input(word)
        if not is_valid:
            logger.warning(f"无效的单词输入: {error_msg} - {word}")
            return None
        
        # 清理输入
        word = sanitize_word_input(word)
        
        if not word.strip():
            logger.warning("搜索词为空")
            return None
        
        if not self.api_key:
            logger.warning("Collins API密钥未配置，无法查询")
            return None
            
        logger.info(f"正在查询单词: {word}")
        
        # 按优先级尝试不同词典
        for dictionary in DICTIONARIES:
            logger.debug(f"尝试词典: {dictionary}")
            result = self._search_in_dictionary(word, dictionary)
            if result:
                logger.info(f"成功获取单词数据: {word} (词典: {dictionary})")
                return result
        
        logger.warning(f"所有词典都未找到单词: {word}")
        return None
    
    def search_word_with_dual_pronunciation(self, word: str) -> Optional[Dict[str, Any]]:
        """
        搜索单词，支持双重发音
        
        Args:
            word: 要搜索的单词
            
        Returns:
            包含完整词汇数据的字典，包括双重发音信息
        """
        # 输入验证
        is_valid, error_msg = validate_word_input(word)
        if not is_valid:
            logger.warning(f"无效的单词输入: {error_msg} - {word}")
            return None
        
        # 清理输入
        word = sanitize_word_input(word)
        
        if not word.strip():
            logger.warning("搜索词为空")
            return None
        
        if not self.api_key:
            logger.warning("Collins API密钥未配置，无法查询")
            return None
            
        logger.info(f"正在查询单词（双重发音）: {word}")
        
        # 第1步：从主词典获取最优单词数据
        main_data = self._get_primary_word_data(word)
        if not main_data:
            logger.warning(f"无法从主词典获取单词数据: {word}")
            return None
        
        # 第2步：专门查询双重发音数据
        dual_pronunciation_data = self._get_dual_pronunciation_data(word)
        
        # 第3步：合并数据
        result = main_data.copy()
        result.update(dual_pronunciation_data)
        
        logger.info(f"成功获取双重发音数据: {word}")
        return result
    

    
    def _get_primary_word_data(self, word: str) -> Optional[Dict[str, Any]]:
        """
        从主词典获取最优单词数据
        
        Args:
            word: 要搜索的单词
            
        Returns:
            主词典数据，如果失败则返回None
        """
        # 优先从english词典获取主要数据（有重音符号的音标）
        main_data = self._search_in_dictionary(word, "english")
        if main_data:
            logger.debug(f"从english词典获取主要数据: {word}")
            return main_data
        
        # 如果english词典没有，按优先级尝试其他词典
        for dictionary in DICTIONARIES:
            if dictionary == "english":  # 已经尝试过了
                continue
            main_data = self._search_in_dictionary(word, dictionary)
            if main_data:
                logger.debug(f"从{dictionary}词典获取主要数据: {word}")
                return main_data
        
        return None
    
    def _get_dual_pronunciation_data(self, word: str) -> Dict[str, Any]:
        """
        专门查询双重发音数据
        
        Args:
            word: 要查询的单词
            
        Returns:
            包含双重发音信息的字典
        """
        result = {
            "british_data": None,
            "american_data": None,
            "pronunciations": []
        }
        
        # 获取英式发音数据
        logger.debug(f"查询英式发音: {word}")
        for dict_name in PRONUNCIATION_SOURCES["british"]:
            data = self._search_in_dictionary(word, dict_name)
            if data:
                result["british_data"] = data
                logger.debug(f"从{dict_name}词典获取英式发音: {word}")
                break
        
        # 获取美式发音数据
        logger.debug(f"查询美式发音: {word}")
        for dict_name in PRONUNCIATION_SOURCES["american"]:
            data = self._search_in_dictionary(word, dict_name)
            if data:
                result["american_data"] = data
                logger.debug(f"从{dict_name}词典获取美式发音: {word}")
                break
        
        # 获取pronunciations API数据
        pronunciations = self._get_pronunciations_from_api(word)
        if pronunciations:
            result["pronunciations"] = pronunciations
            logger.debug(f"从pronunciations API获取{len(pronunciations)}个发音文件: {word}")
        
        return result
    
    def _get_pronunciations_from_api(self, word: str) -> List[Dict[str, Any]]:
        """
        从pronunciations API获取发音信息
        
        Args:
            word: 要查询的单词
            
        Returns:
            发音信息列表
        """
        pronunciations = []
        
        # 首先需要获取entry ID
        entry_id = self._get_entry_id(word)
        if not entry_id:
            return pronunciations
        
        # 构建pronunciations API URL
        url = f"{self.base_url}/dictionaries/english/entries/{entry_id}/pronunciations"
        
        try:
            response = self.session.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            
            if response.status_code == 200:
                data = response.json()
                if 'pronunciations' in data:
                    pronunciations = data['pronunciations']
                    logger.debug(f"获取到 {len(pronunciations)} 个发音文件: {word}")
                    
        except requests.exceptions.ConnectionError as e:
            logger.debug(f"获取pronunciations API连接失败: {word} - {str(e)}")
        except requests.exceptions.Timeout as e:
            logger.debug(f"获取pronunciations API超时: {word} - {str(e)}")
        except requests.exceptions.RequestException as e:
            logger.debug(f"获取pronunciations API请求异常: {word} - {str(e)}")
        except json.JSONDecodeError as e:
            logger.debug(f"获取pronunciations API响应JSON解析失败: {word} - {str(e)}")
        except KeyError as e:
            logger.debug(f"获取pronunciations API响应缺少字段: {word} - {str(e)}")
        
        return pronunciations
    
    def _get_entry_id(self, word: str) -> Optional[str]:
        """
        获取单词的entry ID
        
        Args:
            word: 要查询的单词
            
        Returns:
            entry ID或None
        """
        url = f"{self.base_url}/dictionaries/english/search/first/"
        params = {"q": word, "format": "json"}
        
        try:
            response = self.session.get(url, params=params, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            
            if response.status_code == 200:
                data = response.json()
                if 'entryId' in data:
                    return data['entryId']
                    
        except requests.exceptions.ConnectionError as e:
            logger.debug(f"获取entry ID连接失败: {word} - {str(e)}")
        except requests.exceptions.Timeout as e:
            logger.debug(f"获取entry ID超时: {word} - {str(e)}")
        except requests.exceptions.RequestException as e:
            logger.debug(f"获取entry ID请求异常: {word} - {str(e)}")
        except json.JSONDecodeError as e:
            logger.debug(f"获取entry ID响应JSON解析失败: {word} - {str(e)}")
        except KeyError as e:
            logger.debug(f"获取entry ID响应缺少字段: {word} - {str(e)}")
        
        return None
    
    def _search_in_dictionary(self, word: str, dictionary: str) -> Optional[Dict[str, Any]]:
        """
        在指定词典中搜索单词
        
        Args:
            word: 要搜索的单词
            dictionary: 词典名称
            
        Returns:
            包含词汇数据的字典，如果失败则返回None
        """
        url = f"{self.base_url}/dictionaries/{dictionary}/search/first/"
        params = {"q": word, "format": "html"}
        
        for attempt in range(MAX_RETRIES):
            try:
                response = self.session.get(url, params=params, timeout=REQUEST_TIMEOUT)
                response.raise_for_status()
                
                if response.status_code == 200 and response.text:
                    # 解析JSON响应
                    try:
                        data = response.json()
                        if 'entryContent' in data:
                            # 添加词典信息到响应中
                            data['dictionary'] = dictionary
                            return data
                        else:
                            logger.debug(f"响应中没有找到entryContent字段: {word} (词典: {dictionary})")
                            return None
                    except json.JSONDecodeError:
                        # 如果不是JSON格式，尝试作为HTML处理（向后兼容）
                        logger.debug(f"响应不是JSON格式，尝试作为HTML处理: {word} (词典: {dictionary})")
                        return {'entryContent': response.text, 'dictionary': dictionary}
                else:
                    logger.debug(f"未找到单词: {word} (词典: {dictionary})")
                    return None
                    
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 404:
                    logger.debug(f"词典 {dictionary} 中未找到单词: {word}")
                    return None
                else:
                    logger.warning(f"API请求失败 - {word} (词典: {dictionary}, 尝试 {attempt + 1}/{MAX_RETRIES}): {str(e)}")
                    
            except requests.exceptions.RequestException as e:
                logger.warning(f"API请求失败 - {word} (词典: {dictionary}, 尝试 {attempt + 1}/{MAX_RETRIES}): {str(e)}")
                    
            except (ValueError, TypeError, AttributeError) as e:
                logger.error(f"查询单词时发生数据处理异常 - {word} (词典: {dictionary}): {str(e)}")
                return None
        
        logger.debug(f"所有重试都失败 - {word} (词典: {dictionary})")
        return None
    
    def check_api_key(self) -> bool:
        """
        检查API密钥是否有效
        
        Returns:
            True如果密钥有效，False否则
        """
        if not self.api_key:
            logger.error("API密钥为空")
            return False
            
        # 测试查询一个简单的单词
        result = self.search_word("test")
        return result is not None
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出，关闭会话"""
        self.session.close() 