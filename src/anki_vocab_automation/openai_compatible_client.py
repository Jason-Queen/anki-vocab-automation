"""
OpenAI API 兼容客户端
OpenAI-compatible API client for vocabulary generation using various LLM services
"""

import requests
import json
import logging
import re
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from .models import VocabularyCard
from .tts_generator import TTSGenerator

logger = logging.getLogger(__name__)

@dataclass
class ModelCapabilities:
    """模型能力配置"""
    supports_thinking: bool = False      # 是否支持<think>标签
    supports_system_prompt: bool = True  # 是否支持系统提示词
    max_tokens: int = 4000               # 最大token数
    temperature: float = 0.3             # 默认温度
    requires_json_format: bool = False   # 是否需要JSON格式指示

# 预定义的模型配置
MODEL_CONFIGS = {
    # OpenAI models
    "gpt-4o": ModelCapabilities(supports_thinking=False, max_tokens=4000, temperature=0.3),
    "gpt-4o-mini": ModelCapabilities(supports_thinking=False, max_tokens=4000, temperature=0.3),
    "gpt-4-turbo": ModelCapabilities(supports_thinking=False, max_tokens=4000, temperature=0.3),
    "gpt-3.5-turbo": ModelCapabilities(supports_thinking=False, max_tokens=4000, temperature=0.3),
    
    # Anthropic models (Claude)
    "claude-3-5-sonnet": ModelCapabilities(supports_thinking=True, max_tokens=4000, temperature=0.3),
    "claude-3-opus": ModelCapabilities(supports_thinking=True, max_tokens=4000, temperature=0.3),
    "claude-3-haiku": ModelCapabilities(supports_thinking=True, max_tokens=4000, temperature=0.3),
    
    # OpenAI o1 series
    "o1-preview": ModelCapabilities(supports_thinking=True, max_tokens=4000, temperature=0.3),
    "o1-mini": ModelCapabilities(supports_thinking=True, max_tokens=4000, temperature=0.3),
    
    # Local models (common names)
    "qwen": ModelCapabilities(supports_thinking=True, max_tokens=4000, temperature=0.3),
    "llama": ModelCapabilities(supports_thinking=False, max_tokens=4000, temperature=0.3),
    "gemma": ModelCapabilities(supports_thinking=False, max_tokens=4000, temperature=0.3),
    "mistral": ModelCapabilities(supports_thinking=False, max_tokens=4000, temperature=0.3),
    
    # Generic fallback
    "local-model": ModelCapabilities(supports_thinking=True, max_tokens=4000, temperature=0.3),
    "default": ModelCapabilities(supports_thinking=False, max_tokens=4000, temperature=0.3),
}

class OpenAICompatibleClient:
    """OpenAI API兼容客户端 - 支持所有兼容OpenAI API格式的LLM服务"""
    
    def __init__(self, 
                 base_url: str = "http://localhost:1234", 
                 api_key: str = "not-needed",
                 model_name: str = "local-model",
                 timeout: int = 60,
                 enable_tts: bool = True,
                 tts_service: str = "google"):
        """
        初始化OpenAI兼容客户端
        
        Args:
            base_url: API服务器地址（如https://api.openai.com, http://localhost:1234等）
            api_key: API密钥（本地服务可设置为"not-needed"）
            model_name: 模型名称
            timeout: 请求超时时间
            enable_tts: 是否启用TTS音频生成
            tts_service: TTS服务提供商
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.model_name = model_name
        self.timeout = timeout
        self.enable_tts = enable_tts
        
        # 初始化TTS生成器
        if enable_tts:
            self.tts_generator = TTSGenerator(service=tts_service)
        else:
            self.tts_generator = None
        
        # 确定模型能力
        self.model_capabilities = self._detect_model_capabilities(model_name)
        
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'Anki-Vocabulary-Automation/2.0'
        })
        
        # 设置认证头
        if api_key and api_key != "not-needed":
            self.session.headers.update({
                'Authorization': f'Bearer {api_key}'
            })
    
    def _detect_model_capabilities(self, model_name: str) -> ModelCapabilities:
        """
        检测模型能力
        
        Args:
            model_name: 模型名称
            
        Returns:
            ModelCapabilities对象
        """
        model_name_lower = model_name.lower()
        
        # 精确匹配
        if model_name in MODEL_CONFIGS:
            return MODEL_CONFIGS[model_name]
        
        # 模糊匹配
        for key, config in MODEL_CONFIGS.items():
            if key in model_name_lower:
                logger.info(f"模型 {model_name} 匹配到配置 {key}")
                return config
        
        # 启发式检测
        if any(keyword in model_name_lower for keyword in ["claude", "o1", "qwen", "thinking"]):
            logger.info(f"模型 {model_name} 被检测为支持thinking")
            return ModelCapabilities(supports_thinking=True)
        
        # 默认配置
        logger.info(f"模型 {model_name} 使用默认配置")
        return MODEL_CONFIGS["default"]
    
    def check_connection(self) -> bool:
        """
        检查API连接状态
        
        Returns:
            True如果连接成功，False否则
        """
        try:
            response = self.session.get(
                f"{self.base_url}/v1/models",
                timeout=5
            )
            response.raise_for_status()
            logger.info("OpenAI兼容API连接成功")
            return True
        except requests.exceptions.RequestException as e:
            logger.warning(f"OpenAI兼容API连接失败: {str(e)}")
            return False
    
    def get_available_models(self) -> List[str]:
        """
        获取可用的模型列表
        
        Returns:
            模型名称列表
        """
        try:
            response = self.session.get(
                f"{self.base_url}/v1/models",
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            models = [model.get("id", "") for model in data.get("data", [])]
            logger.info(f"可用模型: {models}")
            return models
        except requests.exceptions.RequestException as e:
            logger.error(f"获取模型列表失败: {str(e)}")
            return []
    
    def generate_vocabulary_card(self, word: str) -> Optional[VocabularyCard]:
        """
        使用LLM生成词汇卡片数据
        
        Args:
            word: 要查询的单词
            
        Returns:
            VocabularyCard对象，如果失败则返回None
        """
        if not word.strip():
            logger.warning("搜索词为空")
            return None
            
        if not self.check_connection():
            logger.warning("跳过LLM生成：连接失败")
            return None
        
        logger.info(f"正在使用LLM生成单词数据: {word} (模型: {self.model_name})")
        
        prompt = self._create_vocabulary_prompt(word)
        
        try:
            response = self._make_completion_request(prompt)
            if response:
                return self._parse_llm_response(response, word)
            return None
        except Exception as e:
            logger.error(f"LLM生成失败: {str(e)}")
            return None
    
    def _create_vocabulary_prompt(self, word: str) -> str:
        """
        创建词汇查询提示词
        
        Args:
            word: 要查询的单词
            
        Returns:
            格式化的提示词
        """
        if self.model_capabilities.supports_thinking:
            # 支持thinking的模型
            prompt = f"""You are a comprehensive English dictionary. For the word "{word}", provide vocabulary information in JSON format.

<think>
Let me analyze the word "{word}" and provide comprehensive vocabulary information including dual pronunciation (British and American).

1. First, I need to determine the standard dictionary form
2. Provide clear definition
3. Create practical example sentence
4. Generate both British and American pronunciations
5. Determine part of speech
6. Ensure all fields are properly filled
</think>

Please respond with this exact JSON structure:

{{
    "word": "standard dictionary form of {word}",
    "definition": "clear primary definition",
    "example": "practical example sentence using the word",
    "pronunciation": "IPA phonetic transcription (British, e.g., /ˈeksəmpl/)",
    "british_pronunciation": "British IPA pronunciation (e.g., /ˈeksəmpl/)",
    "american_pronunciation": "American IPA pronunciation (e.g., /ɪgˈzæmpl/)",
    "audio_url": "",
    "british_audio_url": "",
    "american_audio_url": "",
    "part_of_speech": "noun/verb/adjective/adverb/etc."
}}

Requirements:
- Use the standard dictionary form (e.g., "running" → "run")
- Provide clear, accurate definitions
- Give practical example sentences showing the word in context
- Use proper IPA notation for both British and American pronunciations
- Keep part of speech concise (noun, verb, adjective, adverb, etc.)
- All fields must be filled except audio URLs (MUST be empty strings "")
- NEVER generate audio URLs - leave all audio_url fields as empty strings ""
- Response must be valid JSON only
- Focus on accuracy and educational value
- British pronunciation should be the primary one (with stress marks)
- American pronunciation should reflect US pronunciation differences

Example for word "schedule":
{{
    "word": "schedule",
    "definition": "a plan of procedure, usually written, for a proposed objective",
    "example": "I need to check my schedule for tomorrow's meetings.",
    "pronunciation": "/ˈʃedjuːl/",
    "british_pronunciation": "/ˈʃedjuːl/",
    "american_pronunciation": "/ˈskedjuːl/",
    "audio_url": "",
    "british_audio_url": "",
    "american_audio_url": "",
    "part_of_speech": "noun"
}}

Now provide the JSON for "{word}"."""
        
        else:
            # 普通模型
            prompt = f"""You are a comprehensive English dictionary. For the word "{word}", provide vocabulary information in JSON format.

Please respond with this exact JSON structure:

{{
    "word": "standard dictionary form of {word}",
    "definition": "clear primary definition",
    "example": "practical example sentence using the word",
    "pronunciation": "IPA phonetic transcription (British, e.g., /ˈeksəmpl/)",
    "british_pronunciation": "British IPA pronunciation (e.g., /ˈeksəmpl/)",
    "american_pronunciation": "American IPA pronunciation (e.g., /ɪgˈzæmpl/)",
    "audio_url": "",
    "british_audio_url": "",
    "american_audio_url": "",
    "part_of_speech": "noun/verb/adjective/adverb/etc."
}}

Requirements:
- Use the standard dictionary form (e.g., "running" → "run")
- Provide clear, accurate definitions
- Give practical example sentences showing the word in context
- Use proper IPA notation for both British and American pronunciations
- Keep part of speech concise (noun, verb, adjective, adverb, etc.)
- All fields must be filled except audio URLs (MUST be empty strings "")
- NEVER generate audio URLs - leave all audio_url fields as empty strings ""
- Response must be valid JSON only
- Focus on accuracy and educational value
- British pronunciation should be the primary one (with stress marks)
- American pronunciation should reflect US pronunciation differences

Example for word "schedule":
{{
    "word": "schedule",
    "definition": "a plan of procedure, usually written, for a proposed objective",
    "example": "I need to check my schedule for tomorrow's meetings.",
    "pronunciation": "/ˈʃedjuːl/",
    "british_pronunciation": "/ˈʃedjuːl/",
    "american_pronunciation": "/ˈskedjuːl/",
    "audio_url": "",
    "british_audio_url": "",
    "american_audio_url": "",
    "part_of_speech": "noun"
}}

Now provide the JSON for "{word}"."""

        return prompt
    
    def _make_completion_request(self, prompt: str) -> Optional[str]:
        """
        发送completion请求到API
        
        Args:
            prompt: 提示词
            
        Returns:
            LLM响应文本，如果失败则返回None
        """
        messages = []
        
        # 添加系统提示词（如果支持）
        if self.model_capabilities.supports_system_prompt:
            messages.append({
                "role": "system",
                "content": "You are a comprehensive English dictionary. Always respond with valid JSON containing accurate vocabulary information. Be precise and educational."
            })
        
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": self.model_capabilities.temperature,
            "max_tokens": self.model_capabilities.max_tokens,
        }
        
        # 添加额外参数（根据模型需要）
        if not self.model_capabilities.supports_thinking:
            payload.update({
                "top_p": 1.0,
                "frequency_penalty": 0.0,
                "presence_penalty": 0.0
            })
        
        # 某些模型需要JSON格式指示
        if self.model_capabilities.requires_json_format:
            payload["response_format"] = {"type": "json_object"}
        
        try:
            response = self.session.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            if "choices" in data and len(data["choices"]) > 0:
                content = data["choices"][0]["message"]["content"]
                logger.debug(f"LLM响应: {content[:100]}...")
                return content
            else:
                logger.error("LLM响应格式错误")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"LLM请求失败: {str(e)}")
            return None
    
    def _parse_llm_response(self, response: str, original_word: str) -> Optional[VocabularyCard]:
        """
        解析LLM响应并创建VocabularyCard对象，支持thinking和非thinking模型
        
        Args:
            response: LLM响应文本
            original_word: 原始输入的单词
            
        Returns:
            VocabularyCard对象，如果解析失败则返回None
        """
        try:
            # 清理响应文本
            response = response.strip()
            
            # 移除可能的markdown代码块标记
            if response.startswith("```json"):
                response = response[7:]
            elif response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            
            # 处理thinking标签（用于支持thinking的模型）
            if self.model_capabilities.supports_thinking and "<think>" in response:
                # 找到</think>标签后的内容
                think_end = response.find("</think>")
                if think_end != -1:
                    response = response[think_end + 8:].strip()
            
            # 尝试多种方式提取JSON
            json_candidates = self._extract_json_candidates(response)
            
            # 尝试解析每个候选JSON
            for json_str in json_candidates:
                try:
                    data = json.loads(json_str)
                    
                    # 验证必要字段
                    if self._validate_json_data(data):
                        # 处理主要音频URL
                        audio_url = data.get("audio_url", "")
                        audio_url = self._clean_audio_url(audio_url)
                        
                        # 处理英式音频URL
                        british_audio_url = data.get("british_audio_url", "")
                        british_audio_url = self._clean_audio_url(british_audio_url)
                        
                        # 处理美式音频URL
                        american_audio_url = data.get("american_audio_url", "")
                        american_audio_url = self._clean_audio_url(american_audio_url)
                        
                        # 如果没有有效音频URL且启用了TTS，则生成TTS URL
                        word = data.get("word", original_word)
                        
                        # 生成主要音频（英式）
                        if not audio_url and self.enable_tts and self.tts_generator:
                            british_pronunciation = data.get("british_pronunciation", data.get("pronunciation", ""))
                            audio_url = self.tts_generator.generate_audio_url(word, british_pronunciation, "en-GB")
                            if audio_url:
                                logger.info(f"为单词 {word} 生成了主要TTS音频URL")
                        
                        # 生成英式音频
                        if not british_audio_url and self.enable_tts and self.tts_generator:
                            british_pronunciation = data.get("british_pronunciation", data.get("pronunciation", ""))
                            british_audio_url = self.tts_generator.generate_audio_url(word, british_pronunciation, "en-GB")
                            if british_audio_url:
                                logger.info(f"为单词 {word} 生成了英式TTS音频URL")
                        
                        # 生成美式音频
                        if not american_audio_url and self.enable_tts and self.tts_generator:
                            american_pronunciation = data.get("american_pronunciation", "")
                            if american_pronunciation:
                                american_audio_url = self.tts_generator.generate_audio_url(word, american_pronunciation, "en-US")
                                if american_audio_url:
                                    logger.info(f"为单词 {word} 生成了美式TTS音频URL")
                        
                        card = VocabularyCard(
                            word=data.get("word", original_word),
                            definition=data.get("definition", ""),
                            example=data.get("example", ""),
                            pronunciation=data.get("pronunciation", ""),
                            audio_filename=audio_url,  # 暂时存储URL，稍后会被下载转换为文件名
                            part_of_speech=data.get("part_of_speech", ""),
                            original_word=original_word,
                            # 双重发音数据
                            british_pronunciation=data.get("british_pronunciation", data.get("pronunciation", "")),
                            american_pronunciation=data.get("american_pronunciation", ""),
                            british_audio_filename=british_audio_url,
                            american_audio_filename=american_audio_url
                        )
                        
                        logger.info(f"成功生成词汇卡片（双重发音）: {original_word} → {card.word}")
                        return card
                        
                except json.JSONDecodeError:
                    continue
            
            logger.error("响应中未找到有效的JSON")
            logger.debug(f"原始响应: {response[:500]}...")
            return None
                
        except Exception as e:
            logger.error(f"解析LLM响应时发生异常: {str(e)}")
            logger.debug(f"原始响应: {response[:500]}...")
            return None
    
    def _extract_json_candidates(self, response: str) -> List[str]:
        """
        从响应中提取JSON候选项
        
        Args:
            response: 响应文本
            
        Returns:
            JSON候选字符串列表
        """
        json_candidates = []
        
        # 方法1：找到最后一个完整的JSON对象
        start = response.rfind('{')
        end = response.rfind('}') + 1
        if start != -1 and end != 0 and start < end:
            json_candidates.append(response[start:end])
        
        # 方法2：找到第一个JSON对象
        start = response.find('{')
        end = response.find('}', start) + 1
        if start != -1 and end != 0 and start < end:
            candidate = response[start:end]
            if candidate not in json_candidates:
                json_candidates.append(candidate)
        
        # 方法3：使用正则表达式查找所有可能的JSON对象
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.findall(json_pattern, response, re.DOTALL)
        for match in matches:
            if match not in json_candidates:
                json_candidates.append(match)
        
        # 方法4：处理多行JSON（带换行符）
        lines = response.split('\n')
        json_lines = []
        in_json = False
        brace_count = 0
        
        for line in lines:
            line = line.strip()
            if '{' in line:
                in_json = True
                json_lines.append(line)
                brace_count += line.count('{') - line.count('}')
            elif in_json:
                json_lines.append(line)
                brace_count += line.count('{') - line.count('}')
                if brace_count <= 0:
                    candidate = '\n'.join(json_lines)
                    if candidate not in json_candidates:
                        json_candidates.append(candidate)
                    json_lines = []
                    in_json = False
                    brace_count = 0
        
        return json_candidates
    
    def _validate_json_data(self, data: Dict[str, Any]) -> bool:
        """
        验证JSON数据是否包含必要字段
        
        Args:
            data: 解析后的JSON数据
            
        Returns:
            True如果数据有效，False否则
        """
        # 必须包含word或definition字段
        if not ("word" in data or "definition" in data):
            return False
        
        # 基本字段验证
        required_fields = ["word", "definition", "example", "pronunciation", "part_of_speech"]
        for field in required_fields:
            if field not in data:
                logger.warning(f"缺少字段: {field}")
                # 不直接返回False，允许部分字段缺失
        
        return True
    
    def _clean_audio_url(self, audio_url: str) -> str:
        """
        清理和验证音频URL
        
        Args:
            audio_url: 原始音频URL
            
        Returns:
            清理后的有效URL，如果无效则返回空字符串
        """
        if not audio_url or not isinstance(audio_url, str):
            return ""
        
        # 移除可能的前缀符号
        if audio_url.startswith('@'):
            audio_url = audio_url[1:]
            logger.warning(f"移除音频URL中的@前缀: {audio_url}")
        
        # 解码HTML实体
        import html
        audio_url = html.unescape(audio_url)
        
        # 基本URL格式验证
        if not (audio_url.startswith('http://') or audio_url.startswith('https://')):
            logger.warning(f"无效的音频URL格式: {audio_url}")
            return ""
        
        # 检查是否是已知的有问题的URL模式
        problematic_patterns = [
            '&amp;',  # 如果仍有HTML编码残留
            '@',      # 如果仍有@符号
        ]
        
        for pattern in problematic_patterns:
            if pattern in audio_url:
                logger.warning(f"检测到有问题的音频URL模式 '{pattern}': {audio_url}")
                return ""
        
        logger.debug(f"音频URL验证通过: {audio_url}")
        return audio_url

    def test_generation(self, word: str = "example") -> bool:
        """
        测试LLM生成功能
        
        Args:
            word: 测试单词
            
        Returns:
            True如果测试成功，False否则
        """
        logger.info(f"测试LLM生成功能，单词: {word} (模型: {self.model_name})")
        
        result = self.generate_vocabulary_card(word)
        
        if result:
            logger.info("LLM生成测试成功")
            logger.debug(f"生成结果: {result}")
            return True
        else:
            logger.error("LLM生成测试失败")
            return False 