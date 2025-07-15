#!/usr/bin/env python3
"""
OpenAI兼容API演示脚本
OpenAI-Compatible API Demo for Anki Vocabulary Automation

展示如何配置和使用各种兼容OpenAI API格式的LLM服务
"""

import sys
import os
import time

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from anki_vocab_automation import VocabularyAutomation, OpenAICompatibleClient
from anki_vocab_automation.config import DATA_SOURCE_STRATEGY

def demo_local_lm_studio():
    """演示LM Studio本地服务"""
    print("🚀 演示1：LM Studio本地服务")
    print("-" * 40)
    
    client = OpenAICompatibleClient(
        base_url="http://localhost:1234",
        api_key="not-needed",
        model_name="local-model",
        timeout=60
    )
    
    print(f"模型配置: {client.model_name}")
    print(f"支持thinking: {client.model_capabilities.supports_thinking}")
    print(f"温度: {client.model_capabilities.temperature}")
    
    if client.check_connection():
        print("✅ 连接成功")
        
        # 获取可用模型
        models = client.get_available_models()
        if models:
            print(f"可用模型: {', '.join(models[:3])}...")
        
        # 测试生成
        test_word = "innovation"
        print(f"\n测试生成单词: {test_word}")
        
        start_time = time.time()
        card = client.generate_vocabulary_card(test_word)
        end_time = time.time()
        
        if card:
            print(f"✅ 生成成功 ({end_time - start_time:.2f}s)")
            print(f"   词汇: {card.word}")
            print(f"   定义: {card.definition[:50]}...")
            print(f"   例句: {card.example[:50]}...")
            print(f"   发音: {card.pronunciation}")
        else:
            print("❌ 生成失败")
    else:
        print("❌ 连接失败")

def demo_openai_api():
    """演示OpenAI API（需要API密钥）"""
    print("\n🚀 演示2：OpenAI API")
    print("-" * 40)
    
    # 注意：这里需要用户自己的API密钥
    api_key = os.getenv("OPENAI_API_KEY", "your-openai-api-key-here")
    
    if api_key == "your-openai-api-key-here":
        print("⚠️  需要设置OPENAI_API_KEY环境变量")
        print("示例配置:")
        print("   export OPENAI_API_KEY=sk-your-key-here")
        return
    
    client = OpenAICompatibleClient(
        base_url="https://api.openai.com",
        api_key=api_key,
        model_name="gpt-4o-mini",
        timeout=30
    )
    
    print(f"模型配置: {client.model_name}")
    print(f"支持thinking: {client.model_capabilities.supports_thinking}")
    
    # 测试生成（实际使用时取消注释）
    print("💡 提示：设置正确的API密钥后可以测试")

def demo_custom_service():
    """演示自定义服务配置"""
    print("\n🚀 演示3：自定义服务配置")
    print("-" * 40)
    
    # 示例：配置不同的服务
    services = [
        {
            "name": "DeepSeek",
            "base_url": "https://api.deepseek.com",
            "model": "deepseek-chat",
            "thinking": False
        },
        {
            "name": "本地Ollama",
            "base_url": "http://localhost:11434",
            "model": "llama3",
            "thinking": False
        },
        {
            "name": "Claude (via proxy)",
            "base_url": "https://api.anthropic.com",
            "model": "claude-3-5-sonnet",
            "thinking": True
        }
    ]
    
    for service in services:
        print(f"\n📊 {service['name']} 配置:")
        print(f"   Base URL: {service['base_url']}")
        print(f"   模型: {service['model']}")
        print(f"   Thinking支持: {service['thinking']}")
        
        client = OpenAICompatibleClient(
            base_url=service["base_url"],
            api_key="your-api-key-here",
            model_name=service["model"],
            timeout=30
        )
        
        print(f"   检测到thinking支持: {client.model_capabilities.supports_thinking}")

def demo_thinking_vs_normal():
    """演示thinking和普通模型的差异"""
    print("\n🚀 演示4：Thinking vs 普通模型")
    print("-" * 40)
    
    test_word = "serendipity"
    
    # 模拟thinking模型
    print("🧠 Thinking模型 (如Qwen、Claude):")
    print("特点：")
    print("- 使用<think>标签进行内部推理")
    print("- 更深入的分析过程")
    print("- 可能生成更准确的结果")
    print("- 响应时间可能较长")
    
    # 模拟普通模型
    print("\n⚡ 普通模型 (如GPT、Llama):")
    print("特点：")
    print("- 直接生成结果")
    print("- 响应速度较快")
    print("- 适合批量处理")
    print("- 可能需要更精确的prompt")

def demo_integration_workflow():
    """演示完整的集成工作流"""
    print("\n🚀 演示5：完整集成工作流")
    print("-" * 40)
    
    try:
        # 使用当前配置创建自动化实例
        automation = VocabularyAutomation()
        
        print(f"当前数据源策略: {DATA_SOURCE_STRATEGY}")
        print(f"LLM模型: {automation.llm_client.model_name}")
        print(f"LLM thinking支持: {automation.llm_client.model_capabilities.supports_thinking}")
        
        # 测试词汇列表
        test_words = ["resilience", "paradigm", "ubiquitous"]
        
        print(f"\n测试单词列表: {test_words}")
        
        for word in test_words:
            print(f"\n处理单词: {word}")
            card = automation._get_vocabulary_card(word)
            
            if card:
                print(f"✅ 成功 - {card.word}")
                print(f"   定义: {card.definition[:40]}...")
            else:
                print("❌ 失败")
        
        print(f"\n统计信息:")
        print(f"Collins使用: {automation.stats['collins_used']}")
        print(f"LLM使用: {automation.stats['llm_used']}")
        
    except Exception as e:
        print(f"❌ 演示异常: {str(e)}")

def demo_configuration_guide():
    """配置指南"""
    print("\n🚀 演示6：配置指南")
    print("-" * 40)
    
    print("📋 常用服务配置:")
    
    configs = [
        {
            "服务": "OpenAI",
            "LLM_BASE_URL": "https://api.openai.com",
            "LLM_API_KEY": "sk-your-openai-key",
            "LLM_MODEL_NAME": "gpt-4o",
            "备注": "需要付费API密钥"
        },
        {
            "服务": "LM Studio",
            "LLM_BASE_URL": "http://localhost:1234",
            "LLM_API_KEY": "not-needed",
            "LLM_MODEL_NAME": "local-model",
            "备注": "本地运行，免费"
        },
        {
            "服务": "Ollama",
            "LLM_BASE_URL": "http://localhost:11434",
            "LLM_API_KEY": "not-needed",
            "LLM_MODEL_NAME": "llama3",
            "备注": "本地运行，需要安装Ollama"
        },
        {
            "服务": "DeepSeek",
            "LLM_BASE_URL": "https://api.deepseek.com",
            "LLM_API_KEY": "sk-your-deepseek-key",
            "LLM_MODEL_NAME": "deepseek-chat",
            "备注": "中文友好，性价比高"
        }
    ]
    
    for config in configs:
        print(f"\n{config['服务']}:")
        for key, value in config.items():
            if key != "服务":
                print(f"  {key}: {value}")
    
    print("\n🔧 配置步骤:")
    print("1. 编辑 src/anki_vocab_automation/config.py")
    print("2. 设置对应的LLM_*配置项")
    print("3. 选择合适的DATA_SOURCE_STRATEGY")
    print("4. 重启应用")

def main():
    """主演示函数"""
    print("🚀 OpenAI兼容API演示")
    print("=" * 60)
    print("支持的服务类型:")
    print("- OpenAI (GPT-4, GPT-3.5等)")
    print("- LM Studio (本地模型)")
    print("- Anthropic Claude (通过代理)")
    print("- DeepSeek, Moonshot等国产API")
    print("- Ollama等本地部署方案")
    print("- 任何兼容OpenAI API格式的服务")
    print("=" * 60)
    
    # 运行演示
    demo_local_lm_studio()
    demo_openai_api()
    demo_custom_service()
    demo_thinking_vs_normal()
    demo_integration_workflow()
    demo_configuration_guide()
    
    print("\n✨ 演示完成！")
    print("\n📚 更多信息:")
    print("- 查看 src/anki_vocab_automation/config.py 了解配置选项")
    print("- 运行 python test_openai_compatible.py 进行测试")
    print("- 查看 README.md 了解详细文档")

if __name__ == "__main__":
    main() 