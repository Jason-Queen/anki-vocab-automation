"""
HTML解析器
HTML parser for extracting vocabulary data from Collins Dictionary responses
"""

import re
import json
import logging
from typing import Optional, Dict, Any
from bs4 import BeautifulSoup

from .models import VocabularyCard
from .config import (
    HEADWORD_SELECTORS,
    DEFINITION_SELECTORS,
    EXAMPLE_SELECTORS,
    PRONUNCIATION_SELECTORS,
    PART_OF_SPEECH_SELECTORS
)

logger = logging.getLogger(__name__)

class HTMLParser:
    """HTML解析器，从Collins API响应中提取词汇信息"""
    
    def __init__(self):
        """初始化解析器"""
        self.soup = None
        self.data = None
    
    def parse_collins_response_with_dual_pronunciation(self, response_data: Dict[str, Any], original_word: str) -> Optional[VocabularyCard]:
        """
        解析Collins API返回的响应数据，支持双重发音
        
        Args:
            response_data: API响应数据字典，包含主要数据和双重发音数据
            original_word: 原始输入的单词
            
        Returns:
            VocabularyCard实例，如果解析失败则返回None
        """
        try:
            self.data = response_data
            
            # 提取主要HTML内容
            html_content = response_data.get('entryContent', '')
            if not html_content:
                logger.warning(f"未找到HTML内容: {original_word}")
                return None
            
            # 反转义HTML内容
            html_content = self._unescape_html(html_content)
            
            # 解析主要HTML
            self.soup = BeautifulSoup(html_content, 'html.parser')
            
            # 提取标准词汇形式
            word = self._extract_headword()
            if not word:
                logger.warning(f"未找到标准词汇形式: {original_word}")
                return None
            
            # 提取基本字段
            definition = self._extract_definition()
            example = self._extract_example()
            part_of_speech = self._extract_part_of_speech()
            
            # 提取主要发音（英式，有重音符号）
            main_pronunciation = self._extract_pronunciation()
            main_audio_url = self._extract_audio_url()
            
            # 提取双重发音信息
            dual_pronunciation_data = self._extract_dual_pronunciation_data(response_data)
            
            card = VocabularyCard(
                word=word,
                definition=definition,
                example=example,
                pronunciation=main_pronunciation,
                audio_filename=main_audio_url,
                part_of_speech=part_of_speech,
                original_word=original_word,
                # 双重发音数据
                british_pronunciation=dual_pronunciation_data.get('british_pronunciation', main_pronunciation),
                american_pronunciation=dual_pronunciation_data.get('american_pronunciation', ''),
                british_audio_filename=dual_pronunciation_data.get('british_audio_url', main_audio_url),
                american_audio_filename=dual_pronunciation_data.get('american_audio_url', '')
            )
            
            logger.info(f"成功解析词汇（双重发音）: {original_word} → {word}")
            return card
            
        except Exception as e:
            logger.error(f"解析响应时发生异常 - {original_word}: {str(e)}")
            return None
    
    def _extract_dual_pronunciation_data(self, response_data: Dict[str, Any]) -> Dict[str, str]:
        """
        提取双重发音数据
        
        Args:
            response_data: 包含双重发音信息的响应数据
            
        Returns:
            包含双重发音信息的字典
        """
        result = {
            'british_pronunciation': '',
            'american_pronunciation': '',
            'british_audio_url': '',
            'american_audio_url': ''
        }
        
        # 处理英式发音数据
        british_data = response_data.get('british_data')
        if british_data:
            brit_pronunciation, brit_audio = self._extract_pronunciation_from_data(british_data)
            if brit_pronunciation:
                result['british_pronunciation'] = brit_pronunciation
                logger.debug(f"提取英式发音: {brit_pronunciation}")
            if brit_audio:
                result['british_audio_url'] = brit_audio
                logger.debug(f"提取英式音频: {brit_audio}")
        
        # 处理美式发音数据
        american_data = response_data.get('american_data')
        if american_data:
            amer_pronunciation, amer_audio = self._extract_pronunciation_from_data(american_data)
            if amer_pronunciation:
                result['american_pronunciation'] = amer_pronunciation
                logger.debug(f"提取美式发音: {amer_pronunciation}")
            if amer_audio:
                result['american_audio_url'] = amer_audio
                logger.debug(f"提取美式音频: {amer_audio}")
        
        # 处理pronunciations API数据
        pronunciations = response_data.get('pronunciations', [])
        if pronunciations:
            brit_audios, amer_audios = self._extract_audio_from_pronunciations(pronunciations)
            
            # 只在没有从词典数据中获取到音频时才使用API音频
            if brit_audios and not result['british_audio_url']:
                result['british_audio_url'] = brit_audios[0]
                logger.debug(f"从API获取英式音频: {brit_audios[0]}")
            
            if amer_audios and not result['american_audio_url']:
                result['american_audio_url'] = amer_audios[0]
                logger.debug(f"从API获取美式音频: {amer_audios[0]}")
        
        # 确保字段不为空时才返回值，空字符串保持为空
        final_result = {}
        for key, value in result.items():
            if value and value.strip():
                final_result[key] = value
            else:
                final_result[key] = ''
        
        return final_result
    
    def _extract_pronunciation_from_data(self, data: Dict[str, Any]) -> tuple[str, str]:
        """
        从词典数据中提取发音信息
        
        Args:
            data: 词典数据
            
        Returns:
            (发音, 音频URL) 元组
        """
        pronunciation = ""
        audio_url = ""
        
        if not data or 'entryContent' not in data:
            return pronunciation, audio_url
        
        try:
            # 解析HTML内容
            html_content = self._unescape_html(data['entryContent'])
            temp_soup = BeautifulSoup(html_content, 'html.parser')
            
            # 提取发音
            selectors = ['.pron', 'span.pron', '.pronunciation', '.ipa', '.phonetic']
            for selector in selectors:
                element = temp_soup.select_one(selector)
                if element:
                    elem_copy = BeautifulSoup(str(element), 'html.parser')
                    
                    # 移除音频相关标签
                    for audio in elem_copy.find_all('audio'):
                        audio.decompose()
                    for a_tag in elem_copy.find_all('a'):
                        a_tag.decompose()
                    for img in elem_copy.find_all('img'):
                        img.decompose()
                    
                    pron = elem_copy.get_text().strip()
                    if pron:
                        pronunciation = self._clean_pronunciation(pron)
                        break
            
            # 提取音频URL
            audio_tags = temp_soup.find_all('audio')
            for audio in audio_tags:
                source = audio.find('source')
                if source and source.get('src'):
                    src = source.get('src')
                    if src.startswith('//'):
                        src = 'https:' + src
                    elif src.startswith('/'):
                        src = 'https://api.collinsdictionary.com' + src
                    audio_url = src
                    break
            
            # 如果没有找到audio标签，尝试查找链接
            if not audio_url:
                audio_links = temp_soup.find_all('a', href=re.compile(r'\.mp3|\.wav|\.ogg'))
                if audio_links:
                    href = audio_links[0].get('href')
                    if href.startswith('//'):
                        href = 'https:' + href
                    elif href.startswith('/'):
                        href = 'https://api.collinsdictionary.com' + href
                    audio_url = href
                    
        except Exception as e:
            logger.debug(f"从数据提取发音失败: {str(e)}")
        
        return pronunciation, audio_url
    
    def _extract_audio_from_pronunciations(self, pronunciations: list) -> tuple[list, list]:
        """
        从pronunciations API数据中提取音频URL
        
        Args:
            pronunciations: pronunciations API返回的数据
            
        Returns:
            (英式音频列表, 美式音频列表) 元组
        """
        british_audios = []
        american_audios = []
        
        for pron in pronunciations:
            if not isinstance(pron, dict):
                continue
                
            lang = pron.get('lang', '').lower()
            audio_url = pron.get('audioUrl', '')
            
            if not audio_url:
                continue
                
            # 确保URL是完整的
            if audio_url.startswith('//'):
                audio_url = 'https:' + audio_url
            elif audio_url.startswith('/'):
                audio_url = 'https://api.collinsdictionary.com' + audio_url
            
            # 根据语言分类
            if lang == 'uk' or 'uk' in lang:
                british_audios.append(audio_url)
            elif lang == 'us' or 'us' in lang:
                american_audios.append(audio_url)
        
        return british_audios, american_audios

    def parse_collins_response(self, response_data: Dict[str, Any], original_word: str) -> Optional[VocabularyCard]:
        """
        解析Collins API返回的响应数据
        
        Args:
            response_data: API响应数据字典
            original_word: 原始输入的单词
            
        Returns:
            VocabularyCard实例，如果解析失败则返回None
        """
        try:
            self.data = response_data
            
            # 提取HTML内容
            html_content = response_data.get('entryContent', '')
            if not html_content:
                logger.warning(f"未找到HTML内容: {original_word}")
                return None
            
            # 反转义HTML内容
            html_content = self._unescape_html(html_content)
            
            # 解析HTML
            self.soup = BeautifulSoup(html_content, 'html.parser')
            
            # 提取标准词汇形式
            word = self._extract_headword()
            if not word:
                logger.warning(f"未找到标准词汇形式: {original_word}")
                return None
            
            # 提取各个字段
            definition = self._extract_definition()
            example = self._extract_example()
            pronunciation = self._extract_pronunciation()
            audio_url = self._extract_audio_url()
            part_of_speech = self._extract_part_of_speech()
            
            card = VocabularyCard(
                word=word,
                definition=definition,
                example=example,
                pronunciation=pronunciation,
                audio_filename=audio_url,  # 暂时存储URL，稍后会被下载转换为文件名
                part_of_speech=part_of_speech,
                original_word=original_word
            )
            
            logger.info(f"成功解析词汇: {original_word} → {word}")
            return card
            
        except Exception as e:
            logger.error(f"解析响应时发生异常 - {original_word}: {str(e)}")
            return None
    
    def _unescape_html(self, html_content: str) -> str:
        """
        反转义HTML内容
        
        Args:
            html_content: 转义的HTML内容
            
        Returns:
            反转义后的HTML内容
        """
        # 替换常见的转义字符
        html_content = html_content.replace('\\/', '/')
        html_content = html_content.replace('\\n', '\n')
        html_content = html_content.replace('\\t', '\t')
        html_content = html_content.replace('\\r', '\r')
        html_content = html_content.replace('\\"', '"')
        html_content = html_content.replace("\\'", "'")
        
        return html_content
    
    def _extract_headword(self) -> str:
        """提取标准词汇形式"""
        # 首先尝试从JSON数据中获取
        if self.data and 'entryLabel' in self.data:
            label = self.data['entryLabel']
            if label:
                return label
        
        # 使用配置文件中的选择器
        selectors = ['h1.hwd', 'h1', '.headword', '.hw', 'span.headword', '.entry-title']
        
        for selector in selectors:
            element = self.soup.select_one(selector)
            if element:
                headword = element.get_text().strip()
                if headword:
                    return headword
        
        # 如果都没找到，尝试从title标签提取
        title = self.soup.find('title')
        if title:
            title_text = title.get_text()
            # 提取标题中的单词部分
            match = re.search(r'^([a-zA-Z-]+)', title_text)
            if match:
                return match.group(1)
        
        return ""
    
    def _extract_definition(self) -> str:
        """提取定义"""
        # 使用更具体的选择器
        selectors = [
            '.def',
            '.definition',
            '.sense .def',
            'div.sense .def',
            '.collins-definition',
            '.meaning'
        ]
        
        for selector in selectors:
            elements = self.soup.select(selector)
            if elements:
                # 获取第一个定义并清理格式
                definition = elements[0].get_text().strip()
                if definition:
                    return self._clean_text(definition)
        
        return "Definition not found"
    
    def _extract_example(self) -> str:
        """提取例句"""
        # 首先从主数据中尝试提取例句
        example = self._extract_example_from_soup(self.soup)
        if example and example != "Example not found":
            return example
        
        # 如果主数据没有例句，尝试从其他数据源中查找
        if self.data:
            # 尝试从英式发音数据中查找
            british_data = self.data.get('british_data')
            if british_data:
                example = self._extract_example_from_data(british_data)
                if example and example != "Example not found":
                    return example
            
            # 尝试从美式发音数据中查找
            american_data = self.data.get('american_data')
            if american_data:
                example = self._extract_example_from_data(american_data)
                if example and example != "Example not found":
                    return example
        
        return "Example not found"
    
    def _extract_example_from_soup(self, soup: BeautifulSoup) -> str:
        """从BeautifulSoup对象中提取例句"""
        # 优先选择完整例句的选择器
        high_priority_selectors = [
            '.example',
            '.collins-example',
            '.usage-example',
            '.exemplification',
            '.sense .example',
            '.def .example'
        ]
        
        # 次优选择器（可能包含引用或例句）
        medium_priority_selectors = [
            '.cit',
            '.citation',
            '.quotation',
            '.sense .cit',
            '.illus',
            '.sample'
        ]
        
        # 最后选择器（可能包含用法示例）
        low_priority_selectors = [
            '.quote',
            '.cit .quote',
            'span.quote',
            '.sense .quote',
            '.def .quote',
            '.phrase .quote',
            '.phrase .example'
        ]
        
        # 按优先级尝试选择器
        for selector_group in [high_priority_selectors, medium_priority_selectors, low_priority_selectors]:
            for selector in selector_group:
                elements = soup.select(selector)
                if elements:
                    for element in elements:
                        example = self._extract_and_evaluate_example(element)
                        if example:
                            return example
        
        # 如果没有找到，尝试查找包含引号的文本
        quoted_texts = soup.find_all(string=lambda text: text and '→' in text)
        for text in quoted_texts:
            example = self._extract_and_evaluate_example_text(text)
            if example:
                return example
        
        return "Example not found"
    
    def _extract_and_evaluate_example(self, element) -> str:
        """提取并评估例句质量"""
        text = element.get_text().strip()
        return self._extract_and_evaluate_example_text(text)
    
    def _extract_and_evaluate_example_text(self, text: str) -> str:
        """提取并评估例句文本质量"""
        if not text:
            return ""
        
        # 清理文本
        text = self._clean_text(text)
        
        # 过滤掉明显的用法示例
        if self._is_usage_example(text):
            return ""
        
        # 评估例句质量
        if self._is_good_example(text):
            return text
        
        return ""
    
    def _is_usage_example(self, text: str) -> bool:
        """判断是否是用法示例而不是完整例句"""
        # 过滤以⇒开头的用法示例
        if text.startswith('⇒') or text.startswith('→'):
            return True
        
        # 过滤太短的文本
        if len(text) < 8:  # 从10降低到8
            return True
        
        # 过滤只有短语的内容
        if not any(marker in text for marker in ['.', '!', '?', ';', ',']):
            # 如果没有标点符号，检查是否只是短语
            word_count = len(text.split())
            if word_count < 3:  # 少于3个词的可能是短语
                return True
            
            # 对于技术术语，如果包含专业词汇，即使没有标点符号也可能有用
            tech_indicators = ['computer', 'computing', 'technology', 'technical', 'system', 'data', 'digital', 'software', 'hardware', 'network', 'printer', 'printing']
            text_lower = text.lower()
            has_tech_term = any(tech in text_lower for tech in tech_indicators)
            
            if has_tech_term and word_count >= 3:
                return False  # 不过滤技术术语相关的短语
        
        # 过滤常见的用法模式，但对技术术语放宽
        usage_patterns = [
            r'^a \w+ \w+$',  # 例如：a prestige car
            r'^an \w+ \w+$',  # 例如：an elaborate plan
            r'^the \w+ \w+$',  # 例如：the main consequence
            r'^it\'s \w+ \w+$',  # 例如：it's of no consequence
            r'^\w+ly \w+$',  # 副词形式
        ]
        
        import re
        for pattern in usage_patterns:
            if re.match(pattern, text, re.IGNORECASE):
                # 对于技术术语，即使匹配了简单模式，也可能是有用的
                tech_indicators = ['computer', 'computing', 'technology', 'technical', 'system', 'data', 'digital', 'software', 'hardware', 'network', 'printer', 'printing']
                text_lower = text.lower()
                has_tech_term = any(tech in text_lower for tech in tech_indicators)
                
                if not has_tech_term:
                    return True
        
        return False
    
    def _is_good_example(self, text: str) -> bool:
        """判断是否是好的例句"""
        # 长度检查 - 稍微降低最小长度要求
        if len(text) < 12:  # 从15降低到12
            return False
        
        # 检查是否包含句子结构
        word_count = len(text.split())
        if word_count < 3:  # 至少3个词
            return False
        
        # 检查是否包含动词（简单启发式）
        verb_indicators = ['is', 'are', 'was', 'were', 'has', 'have', 'had', 'will', 'would', 'can', 'could', 'do', 'does', 'did', 'be', 'been', 'being']
        text_lower = text.lower()
        has_verb = any(verb in text_lower.split() for verb in verb_indicators)
        
        # 检查是否包含动词的ing/ed形式
        words = text.split()
        has_verb_form = any(word.endswith('ing') or word.endswith('ed') for word in words)
        
        # 检查是否包含动词的第三人称单数形式
        has_third_person = any(word.endswith('s') and len(word) > 2 for word in words)
        
        # 如果包含动词指示器或动词形式，且有适当的长度，认为是好例句
        if (has_verb or has_verb_form) and word_count >= 3:  # 从4降低到3
            return True
        
        # 检查是否包含完整的句子结构（有主语和谓语）
        pronouns = ['i', 'you', 'he', 'she', 'it', 'we', 'they', 'this', 'that', 'these', 'those']
        has_subject = any(pronoun in text_lower.split() for pronoun in pronouns)
        
        if has_subject and (has_verb or has_verb_form):
            return True
        
        # 检查是否是有用的短句（包含形容词和名词的组合）
        if word_count >= 3 and word_count <= 8:  # 放宽到8个词
            articles = ['a', 'an', 'the']
            has_article = any(article in text_lower.split() for article in articles)
            
            # 对于技术术语，降低长度要求
            if has_article and len(text) >= 15:  # 从20降低到15
                return True
        
        # 如果文本较长且包含标点符号，可能是好例句
        if len(text) > 20 and any(punct in text for punct in ['.', '!', '?', ';']):  # 从25降低到20
            return True
        
        # 检查是否包含常见的句子连接词
        connectives = ['and', 'but', 'or', 'because', 'since', 'although', 'however', 'therefore', 'moreover', 'furthermore']
        has_connective = any(conn in text_lower.split() for conn in connectives)
        
        if has_connective and word_count >= 4:  # 从5降低到4
            return True
        
        # 对于技术术语，如果包含特定的技术词汇，也允许通过
        tech_indicators = ['computer', 'computing', 'technology', 'technical', 'system', 'data', 'digital', 'software', 'hardware', 'network']
        has_tech_term = any(tech in text_lower for tech in tech_indicators)
        
        if has_tech_term and word_count >= 3 and len(text) >= 15:
            return True
        
        return False
    
    def _extract_example_from_data(self, data: Dict[str, Any]) -> str:
        """从词典数据中提取例句"""
        if not data or 'entryContent' not in data:
            return "Example not found"
        
        try:
            # 解析HTML内容
            html_content = self._unescape_html(data['entryContent'])
            temp_soup = BeautifulSoup(html_content, 'html.parser')
            
            return self._extract_example_from_soup(temp_soup)
            
        except Exception as e:
            logger.debug(f"从数据中提取例句时出错: {str(e)}")
            return "Example not found"
    
    def _extract_pronunciation(self) -> str:
        """提取发音"""
        # 使用更具体的选择器
        selectors = [
            '.pron',
            'span.pron',
            '.pronunciation',
            '.ipa',
            '.phonetic'
        ]
        
        for selector in selectors:
            element = self.soup.select_one(selector)
            if element:
                # 创建元素副本并移除音频相关标签
                elem_copy = BeautifulSoup(str(element), 'html.parser')
                
                # 移除音频元素
                for audio in elem_copy.find_all('audio'):
                    audio.decompose()
                
                # 移除播放按钮链接
                for a_tag in elem_copy.find_all('a'):
                    a_tag.decompose()
                
                # 移除图片元素
                for img in elem_copy.find_all('img'):
                    img.decompose()
                
                pronunciation = elem_copy.get_text().strip()
                if pronunciation:
                    # 清理发音符号，保留重要格式
                    pronunciation = self._clean_pronunciation(pronunciation)
                    return pronunciation
        
        return "Pronunciation not found"
    
    def _clean_pronunciation(self, pronunciation: str) -> str:
        """
        清理音标格式，保持标准IPA格式
        
        Args:
            pronunciation: 原始音标文本
            
        Returns:
            清理后的标准IPA音标
        """
        # 移除多余的空格和换行
        pronunciation = re.sub(r'\s+', ' ', pronunciation).strip()
        
        # 移除非音标字符但保留IPA符号和斜杠
        # 允许的字符：字母、IPA符号、斜杠、空格、重音符号等
        pronunciation = re.sub(r'[^\w\s/ˈˌæɑɒɔɪʊʌɛɜɝəɞɘɵɐɯɨʉɥɪeɛoʔθðʃʒŋtʃdʒjwrhʰʱ̃ː̩̯̍̆̈̂̌̄̀́̋̏̌̑̒̓̔̕̚ʷʲʳⁿᵗˢᵖ]', '', pronunciation)
        
        # 如果没有斜杠包围，添加标准IPA格式
        if pronunciation and not (pronunciation.startswith('/') and pronunciation.endswith('/')):
            # 移除首尾可能的残余斜杠或空格
            pronunciation = pronunciation.strip('/ ')
            # 添加标准IPA格式斜杠
            pronunciation = f"/{pronunciation}/"
        
        # 确保斜杠内没有多余空格
        if pronunciation.startswith('/') and pronunciation.endswith('/'):
            inner_part = pronunciation[1:-1].strip()
            pronunciation = f"/{inner_part}/"
        
        return pronunciation
    
    def _extract_audio_url(self) -> str:
        """提取音频URL"""
        # 查找音频标签
        audio_tags = self.soup.find_all('audio')
        for audio in audio_tags:
            source = audio.find('source')
            if source and source.get('src'):
                src = source.get('src')
                # 确保URL是完整的
                if src.startswith('//'):
                    src = 'https:' + src
                elif src.startswith('/'):
                    src = 'https://api.collinsdictionary.com' + src
                return src
        
        # 查找音频链接
        audio_links = self.soup.find_all('a', href=re.compile(r'\.mp3|\.wav|\.ogg'))
        if audio_links:
            href = audio_links[0].get('href')
            if href.startswith('//'):
                href = 'https:' + href
            elif href.startswith('/'):
                href = 'https://api.collinsdictionary.com' + href
            return href
        
        return ""
    
    def _extract_part_of_speech(self) -> str:
        """提取词性"""
        # 使用更具体的选择器
        selectors = [
            '.pos',
            'span.pos',
            '.part-of-speech',
            '.grammar',
            '.wordtype'
        ]
        
        for selector in selectors:
            element = self.soup.select_one(selector)
            if element:
                pos = element.get_text().strip()
                if pos:
                    return pos
        
        return "Unknown"
    
    def _clean_text(self, text: str) -> str:
        """
        清理文本，移除多余的空白字符和标记
        
        Args:
            text: 原始文本
            
        Returns:
            清理后的文本
        """
        if not text:
            return ""
        
        # 移除多余的空白字符
        text = re.sub(r'\s+', ' ', text).strip()
        
        # 移除例句标记
        example_markers = [
            '■ EG: ',
            'EG: ',
            'Example: ',
            'EXAMPLE: ',
            'e.g. ',
            'E.g. ',
            'E.G. ',
            '► ',
            '▶ ',
            '• ',
            '→ ',
            '⇒ '
        ]
        
        for marker in example_markers:
            if text.startswith(marker):
                text = text[len(marker):].strip()
                break
        
        # 移除开头的省略号
        if text.startswith('...'):
            text = text[3:].strip()
        
        # 移除结尾的省略号（如果不是句子结尾）
        if text.endswith('...') and not text.endswith('....'):
            text = text[:-3].strip()
        
        # 确保句子以大写字母开头（如果是字母）
        if text and text[0].islower():
            text = text[0].upper() + text[1:]
        
        return text 