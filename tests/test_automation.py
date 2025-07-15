#!/usr/bin/env python3
"""
测试脚本：验证Anki词汇自动化功能
Test script for Anki Vocabulary Automation
"""

import sys
import os
from pathlib import Path

# 添加src目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

from anki_vocab_automation import VocabularyAutomation, CollinsAPI, HTMLParser, AnkiConnect, VocabularyCard
from anki_vocab_automation.config import COLLINS_API_KEY

def test_collins_api():
    """测试Collins API功能"""
    print("=" * 50)
    print("测试 Collins API 功能")
    print("=" * 50)
    
    # 检查API密钥
    if not COLLINS_API_KEY:
        print("跳过Collins API测试：未配置API密钥")
        return False
    
    collins = CollinsAPI(COLLINS_API_KEY)
    
    # 测试API密钥
    if not collins.check_api_key():
        print("✗ API密钥无效")
        return False
    
    print("✓ API密钥有效")
    
    # 测试单词列表
    test_words = ["hello", "world", "test", "inspection", "running"]
    
    success_count = 0
    for word in test_words:
        print(f"\n正在测试单词: {word}")
        response_data = collins.search_word(word)
        
        if response_data:
            print(f"✓ 成功获取 {word} 的响应数据")
            print(f"  响应数据类型: {type(response_data)}")
            success_count += 1
        else:
            print(f"✗ 无法获取 {word} 的响应数据")
    
    print(f"\n总计: {success_count}/{len(test_words)} 个单词查询成功")
    return success_count > 0

def test_html_parser():
    """测试HTML解析功能"""
    print("\n" + "=" * 50)
    print("测试 HTML 解析功能")
    print("=" * 50)
    
    # 检查API密钥
    if not COLLINS_API_KEY:
        print("跳过HTML解析测试：未配置API密钥")
        return False
    
    collins = CollinsAPI(COLLINS_API_KEY)
    parser = HTMLParser()
    
    # 测试解析
    test_word = "hello"
    response_data = collins.search_word(test_word)
    
    if response_data:
        card = parser.parse_collins_response(response_data, test_word)
        
        if card:
            print(f"✓ 成功解析单词: {test_word}")
            print(f"  标准形式: {card.word}")
            print(f"  定义: {card.definition[:100]}...")
            print(f"  例句: {card.example[:100]}...")
            print(f"  发音: {card.pronunciation}")
            print(f"  词性: {card.part_of_speech}")
            print(f"  音频URL: {card.audio_url}")
            
            # 测试数据验证
            try:
                card_dict = card.to_dict()
                print(f"✓ 数据格式转换成功")
                return True
            except Exception as e:
                print(f"✗ 数据格式转换失败: {e}")
                return False
        else:
            print(f"✗ 解析失败: {test_word}")
            return False
    else:
        print(f"✗ 无法获取响应数据: {test_word}")
        return False

def test_anki_connect():
    """测试Anki Connect连接"""
    print("\n" + "=" * 50)
    print("测试 Anki Connect 连接")
    print("=" * 50)
    
    anki = AnkiConnect()
    
    # 测试连接
    if anki.check_connection():
        print("✓ Anki Connect 连接成功")
        
        # 测试卡牌组
        if anki.ensure_deck_exists():
            print("✓ 卡牌组创建/验证成功")
            
            # 测试重复检查
            duplicate = anki.find_duplicate("test_word_12345")
            print(f"✓ 重复检查功能正常 (结果: {duplicate})")
            
            # 测试获取字段名称
            fields = anki.get_model_field_names()
            if fields:
                print(f"✓ 模型字段获取成功: {fields}")
            else:
                print("! 模型字段获取失败，可能是模型不存在")
            
            return True
        else:
            print("✗ 卡牌组创建/验证失败")
            return False
    else:
        print("✗ Anki Connect 连接失败")
        return False

def test_full_workflow():
    """测试完整工作流程"""
    print("\n" + "=" * 50)
    print("测试完整工作流程")
    print("=" * 50)
    
    # 检查API密钥
    if not COLLINS_API_KEY:
        print("跳过完整工作流程测试：未配置API密钥")
        return False
    
    # 初始化自动化流程
    automation = VocabularyAutomation(COLLINS_API_KEY)
    
    # 测试单词
    test_word = "example"
    print(f"正在测试完整流程，单词: {test_word}")
    
    try:
        # 测试单个单词处理
        result = automation.process_single_word_test(test_word)
        
        if result:
            print("✓ 完整流程测试成功")
            print(f"  成功处理单词: {test_word}")
            return True
        else:
            print("✗ 完整流程测试失败")
            return False
            
    except Exception as e:
        print(f"✗ 完整流程测试异常: {str(e)}")
        return False

def test_data_integrity():
    """测试数据完整性"""
    print("\n" + "=" * 50)
    print("测试数据完整性")
    print("=" * 50)
    
    # 测试配置文件
    try:
        from anki_vocab_automation.config import (
            COLLINS_API_KEY,
            DECK_NAME,
            MODEL_NAME,
            WORD_LIST_FILE,
            LOG_FILE
        )
        print("✓ 配置文件导入成功")
        
        # 检查关键配置
        if DECK_NAME:
            print(f"✓ 卡牌组名称: {DECK_NAME}")
        else:
            print("✗ 卡牌组名称未配置")
            return False
        
        if MODEL_NAME:
            print(f"✓ 模型名称: {MODEL_NAME}")
        else:
            print("✗ 模型名称未配置")
            return False
        
        # 检查文件路径
        if WORD_LIST_FILE.exists():
            print(f"✓ 单词列表文件存在: {WORD_LIST_FILE}")
        else:
            print(f"! 单词列表文件不存在: {WORD_LIST_FILE}")
        
        return True
        
    except ImportError as e:
        print(f"✗ 配置文件导入失败: {e}")
        return False

def main():
    """主测试函数"""
    print("Anki 词汇自动化测试脚本 v2.0")
    print("请确保:")
    print("1. 已配置有效的Collins API密钥")
    print("2. Anki正在运行")
    print("3. AnkiConnect插件已安装")
    print("4. 已创建或导入'Vocabulary Learning'卡牌模板")
    print()
    
    input("按回车键开始测试...")
    
    # 运行测试
    tests = [
        ("数据完整性", test_data_integrity),
        ("Collins API", test_collins_api),
        ("HTML解析", test_html_parser),
        ("Anki Connect", test_anki_connect),
        ("完整工作流程", test_full_workflow),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name} 测试异常: {str(e)}")
            results.append((test_name, False))
    
    # 显示结果
    print("\n" + "=" * 50)
    print("测试结果总结")
    print("=" * 50)
    
    passed = 0
    for test_name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n总计: {passed}/{len(results)} 项测试通过")
    
    if passed == len(results):
        print("🎉 所有测试通过！系统可以正常使用。")
    else:
        print("⚠️  部分测试失败，请检查配置和环境。")
        
    return passed == len(results)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 