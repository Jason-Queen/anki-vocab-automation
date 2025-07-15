#!/usr/bin/env python3
"""
跨平台兼容性演示
Cross-Platform Compatibility Demo

这个脚本演示了Anki词汇自动化项目如何在Windows、Linux和macOS上无缝工作。
This script demonstrates how the Anki Vocabulary Automation project works seamlessly across Windows, Linux, and macOS.
"""

import os
import sys
import platform
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

try:
    from anki_vocab_automation.config import ROOT_DIR, WORD_LIST_FILE, LOG_FILE
    from anki_vocab_automation.config import display_config
except ImportError as e:
    print(f"导入错误 (Import Error): {e}")
    print("请确保已安装所有依赖 (Please ensure all dependencies are installed)")
    sys.exit(1)

def display_platform_info():
    """显示平台信息"""
    print("=" * 60)
    print("🌍 跨平台兼容性演示 Cross-Platform Compatibility Demo")
    print("=" * 60)
    
    # 系统信息
    print(f"操作系统 (OS): {platform.system()}")
    print(f"OS 版本 (Version): {platform.version()}")
    print(f"架构 (Architecture): {platform.architecture()[0]}")
    print(f"Python 版本 (Python Version): {platform.python_version()}")
    print(f"Python 实现 (Implementation): {platform.python_implementation()}")
    
    # 平台特定信息
    print(f"\n📂 平台特定信息 (Platform-Specific Info):")
    print(f"sys.platform: {sys.platform}")
    print(f"os.name: {os.name}")
    
    # 路径信息
    print(f"\n📁 路径信息 (Path Information):")
    print(f"项目根目录 (Project Root): {ROOT_DIR}")
    print(f"词汇文件 (Word List): {WORD_LIST_FILE}")
    print(f"日志文件 (Log File): {LOG_FILE}")
    
    # 路径分隔符
    print(f"\n🔗 路径处理 (Path Handling):")
    print(f"路径分隔符 (Path Separator): '{os.sep}'")
    
    # 虚拟环境
    venv_path = project_root / "venv"
    if sys.platform == "win32":
        python_exe = venv_path / "Scripts" / "python.exe"
        pip_exe = venv_path / "Scripts" / "pip.exe"
        activate_script = venv_path / "Scripts" / "activate.bat"
    else:
        python_exe = venv_path / "bin" / "python"
        pip_exe = venv_path / "bin" / "pip"
        activate_script = venv_path / "bin" / "activate"
    
    print(f"\n🐍 虚拟环境 (Virtual Environment):")
    print(f"Python 可执行文件 (Python Executable): {python_exe}")
    print(f"Pip 可执行文件 (Pip Executable): {pip_exe}")
    print(f"激活脚本 (Activation Script): {activate_script}")

def demonstrate_cross_platform_paths():
    """演示跨平台路径处理"""
    print("\n" + "=" * 60)
    print("📂 跨平台路径处理演示 (Cross-Platform Path Handling Demo)")
    print("=" * 60)
    
    # 使用pathlib.Path的跨平台路径
    paths = [
        Path("data") / "New_Words.txt",
        Path("templates") / "Vocabulary_Template.html",
        Path("src") / "anki_vocab_automation" / "config.py",
        Path("logs") / "application.log"
    ]
    
    for path in paths:
        absolute_path = (project_root / path).resolve()
        print(f"相对路径 (Relative): {path}")
        print(f"绝对路径 (Absolute): {absolute_path}")
        print(f"存在 (Exists): {'✅' if absolute_path.exists() else '❌'}")
        print("-" * 50)

def demonstrate_environment_variables():
    """演示环境变量处理"""
    print("\n" + "=" * 60)
    print("🔧 环境变量处理演示 (Environment Variables Demo)")
    print("=" * 60)
    
    env_vars = [
        "COLLINS_API_KEY",
        "LLM_BASE_URL",
        "LLM_MODEL_NAME",
        "DATA_SOURCE_STRATEGY",
        "ANKI_CONNECT_HOST",
        "ANKI_CONNECT_PORT"
    ]
    
    for var in env_vars:
        value = os.getenv(var, "未设置 (Not set)")
        print(f"{var}: {value}")

def demonstrate_dependency_compatibility():
    """演示依赖包兼容性"""
    print("\n" + "=" * 60)
    print("📦 依赖包兼容性演示 (Dependency Compatibility Demo)")
    print("=" * 60)
    
    dependencies = [
        ("requests", "HTTP客户端 (HTTP Client)"),
        ("bs4", "HTML解析器 (HTML Parser)"),
        ("lxml", "XML解析器 (XML Parser)"),
        ("dotenv", "环境变量加载器 (Environment Loader)")
    ]
    
    for module, description in dependencies:
        try:
            __import__(module)
            print(f"✅ {module} - {description}")
        except ImportError:
            print(f"❌ {module} - {description} (未安装 Not installed)")

def main():
    """主函数"""
    try:
        display_platform_info()
        demonstrate_cross_platform_paths()
        demonstrate_environment_variables()
        demonstrate_dependency_compatibility()
        
        print("\n" + "=" * 60)
        print("🎉 跨平台兼容性验证完成！")
        print("🎉 Cross-Platform Compatibility Verification Complete!")
        print("=" * 60)
        
        # 显示配置信息
        print("\n📋 当前配置 (Current Configuration):")
        display_config()
        
    except Exception as e:
        print(f"❌ 错误 (Error): {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 