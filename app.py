#!/usr/bin/env python3
"""
应用程序启动脚本
Application launcher for Anki Vocabulary Automation
"""

import sys
import os
from pathlib import Path

# 添加src目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))


def print_dependency_install_hint(include_test_tools=False):
    """显示基于 uv 的依赖安装提示。"""
    sync_command = "uv sync --extra test" if include_test_tools else "uv sync"
    print("请先使用 uv 安装项目依赖:")
    print(f"  {sync_command}")
    print("然后使用以下命令运行程序:")
    print("  uv run python app.py")


def create_config_file():
    """创建配置文件"""
    config_env_path = project_root / "config.env"
    example_path = project_root / "config.env.example"

    if config_env_path.exists():
        print("配置文件已存在: config.env")
        return True

    if example_path.exists():
        # 复制示例文件
        import shutil

        shutil.copy(example_path, config_env_path)
        print("已创建配置文件: config.env")
        print("请编辑config.env文件，填入您的实际配置值")
        return True
    else:
        print("❌ 找不到配置模板文件: config.env.example")
        return False


def set_data_source_strategy():
    """设置数据源优先级"""
    strategies = {
        "1": ("collins_only", "仅使用Collins API"),
        "2": ("llm_only", "仅使用LLM"),
        "3": ("collins_first", "优先使用Collins API，失败时使用LLM"),
        "4": ("llm_first", "优先使用LLM，失败时使用Collins API"),
    }

    print("\n数据源优先级设置:")
    print("=" * 40)
    for key, (strategy, description) in strategies.items():
        print(f"{key}. {description}")

    while True:
        choice = input("\n请选择数据源策略 (1-4): ").strip()
        if choice in strategies:
            strategy, description = strategies[choice]

            # 设置环境变量
            os.environ["DATA_SOURCE_STRATEGY"] = strategy

            # 更新配置文件
            update_config_file("DATA_SOURCE_STRATEGY", strategy)

            print(f"✅ 数据源策略已设置为: {description}")
            return strategy
        else:
            print("无效选择，请输入1-4")


def update_config_file(key, value):
    """更新配置文件中的设置"""
    config_env_path = project_root / "config.env"

    if not config_env_path.exists():
        print("配置文件不存在，正在创建...")
        if not create_config_file():
            return False

    try:
        # 读取现有配置
        lines = []
        with open(config_env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # 更新配置
        updated = False
        for i, line in enumerate(lines):
            if line.strip().startswith(f"{key}="):
                lines[i] = f"{key}={value}\n"
                updated = True
                break

        # 如果没有找到配置项，则添加
        if not updated:
            lines.append(f"{key}={value}\n")

        # 写入文件
        with open(config_env_path, "w", encoding="utf-8") as f:
            f.writelines(lines)

        return True
    except Exception as e:
        print(f"更新配置文件失败: {e}")
        return False


def display_current_config():
    """显示当前配置"""
    try:
        from anki_vocab_automation.config import display_config

        display_config()
    except ImportError as e:
        print(f"无法加载配置: {e}")
        print_dependency_install_hint()
    except Exception as e:
        print(f"显示配置失败: {e}")


def validate_current_config():
    """验证当前配置"""
    try:
        from anki_vocab_automation.config import validate_config

        errors = validate_config()
        if errors:
            print("\n配置验证失败:")
            for error in errors:
                print(f"❌ {error}")
            return False
        else:
            print("\n✅ 配置验证通过")
            return True
    except ImportError as e:
        print(f"无法加载配置: {e}")
        print_dependency_install_hint()
        return False
    except Exception as e:
        print(f"验证配置失败: {e}")
        return False


def check_anki_environment():
    """检查和设置Anki环境"""
    print("\n" + "=" * 50)
    print("🔧 Anki环境检查")
    print("=" * 50)

    try:
        from anki_vocab_automation.anki_connect import AnkiConnect

        # 创建AnkiConnect实例并检查环境
        anki_client = AnkiConnect()
        success = anki_client.setup_environment()

        if success:
            print("\n✅ 所有检查通过！可以开始使用词汇自动化功能。")
        else:
            print("\n❌ 环境检查失败，请解决上述问题后重试。")

        return success

    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        print_dependency_install_hint()
        return False
    except Exception as e:
        print(f"❌ 环境检查时出错: {e}")
        import traceback

        traceback.print_exc()
        return False


def configure_collins_api():
    """配置Collins API"""
    print("\n" + "=" * 50)
    print("📚 Collins API配置向导")
    print("=" * 50)

    print("Collins Dictionary API 提供高质量的词典数据。")
    print("获取API密钥请访问: https://www.collinsdictionary.com/api")
    print()

    # 获取当前配置
    try:
        from anki_vocab_automation.config import COLLINS_API_KEY

        current_key = COLLINS_API_KEY
        if current_key:
            print(f"当前API密钥: {current_key[:10]}...（已隐藏）")
        else:
            print("当前API密钥: 未配置")
    except ImportError:
        current_key = ""
        print("当前API密钥: 未配置")

    # 获取新的API密钥
    print("\n请输入Collins API密钥:")
    print("（留空跳过，输入'remove'删除现有密钥）")

    new_key = input("API密钥: ").strip()

    if new_key == "":
        print("❌ 配置已取消")
        return
    elif new_key.lower() == "remove":
        # 删除现有密钥
        update_config_file("COLLINS_API_KEY", "")
        print("✅ Collins API密钥已删除")
        return

    # 验证API密钥格式（通常Collins API密钥有特定格式）
    if len(new_key) < 10:
        print("❌ API密钥似乎太短，请检查是否正确")
        return

    # 测试API密钥
    print("\n🔍 测试API密钥...")
    try:
        # 临时设置API密钥进行测试
        os.environ["COLLINS_API_KEY"] = new_key

        from anki_vocab_automation.collins_api import CollinsAPI

        collins_api = CollinsAPI(new_key)

        # 测试一个常见单词
        test_word = "test"
        print(f"正在测试单词: {test_word}")

        result = collins_api.search_word(test_word)
        if result:
            print("✅ API密钥测试成功")

            # 确认保存配置
            confirm = input("\n确认保存Collins API配置? (y/N): ").strip().lower()
            if confirm in ["y", "yes"]:
                # 确保配置文件存在
                create_config_file()

                # 更新配置
                update_config_file("COLLINS_API_KEY", new_key)
                print("✅ Collins API配置已保存")

                # 询问是否设置为Collins优先
                collins_priority = input("\n是否设置为优先使用Collins API? (y/N): ").strip().lower()
                if collins_priority in ["y", "yes"]:
                    update_config_file("DATA_SOURCE_STRATEGY", "collins_first")
                    print("✅ 已设置为Collins优先模式")
                else:
                    print("ℹ️  保持当前数据源设置")
            else:
                print("❌ 配置已取消")
        else:
            print("❌ API密钥测试失败，请检查密钥是否正确")

    except Exception as e:
        print(f"❌ API密钥测试失败: {str(e)}")
        print("请检查API密钥是否正确，或稍后再试")


def get_available_models(base_url, api_key="not-needed", provider="openai_compat"):
    """动态获取可用模型"""
    try:
        from anki_vocab_automation.llm_client import list_models_for_backend

        return list_models_for_backend(
            provider=provider,
            base_url=base_url,
            api_key=api_key,
            timeout=10,
        )
    except Exception as e:
        print(f"⚠️  获取模型列表失败: {str(e)}")
        return []


def get_loaded_models(base_url, api_key="not-needed", provider="openai_compat"):
    """获取当前已加载模型（仅适用于本地后端）"""
    try:
        from anki_vocab_automation.llm_client import list_loaded_models_for_backend

        return list_loaded_models_for_backend(
            provider=provider,
            base_url=base_url,
            api_key=api_key,
            timeout=10,
        )
    except Exception as e:
        print(f"⚠️  获取已加载模型失败: {str(e)}")
        return []


def configure_llm_service():
    """配置LLM服务"""
    print("\n" + "=" * 50)
    print("🤖 LLM服务配置向导")
    print("=" * 50)

    # 预定义的服务配置
    services = {
        "1": {
            "name": "OpenAI",
            "provider": "openai",
            "api_mode": "chat",
            "base_url": "https://api.openai.com/v1",
            "api_key_prefix": "sk" + "-",
            "models": ["gpt-4o", "gpt-4o-mini", "gpt-4", "gpt-3.5-turbo"],
            "default_model": "gpt-4o-mini",
        },
        "2": {
            "name": "Anthropic Claude",
            "provider": "anthropic",
            "api_mode": "messages",
            "base_url": "https://api.anthropic.com",
            "api_key_prefix": "sk" + "-ant-",
            "models": ["claude-3-5-sonnet-20241022", "claude-3-haiku-20240307", "claude-3-opus-20240229"],
            "default_model": "claude-3-5-sonnet-20241022",
        },
        "3": {
            "name": "LM Studio (本地)",
            "provider": "lmstudio",
            "api_mode": "auto",
            "base_url": "http://localhost:1234",
            "api_key_prefix": "not-needed",
            "models": [],  # 动态获取
            "default_model": "",
        },
        "4": {
            "name": "Ollama (本地)",
            "provider": "ollama",
            "api_mode": "auto",
            "base_url": "http://localhost:11434",
            "api_key_prefix": "not-needed",
            "models": [],  # 动态获取
            "default_model": "",
        },
    }

    print("\n请选择LLM服务:")
    for key, service in services.items():
        print(f"{key}. {service['name']}")
    print("5. 自定义服务")
    print("0. 返回主菜单")

    choice = input("\n请输入选择 (0-5): ").strip()

    if choice == "0":
        return
    elif choice == "5":
        # 自定义服务
        print("\n🔧 自定义LLM服务配置")
        print("自定义服务默认按 OpenAI 兼容 Chat API 配置。")
        provider = "openai_compat"
        api_mode = "chat"
        base_url = input("请输入Base URL: ").strip()
        api_key = input("请输入API Key: ").strip()
        model_name = input("请输入Model Name: ").strip()

        if not all([base_url, api_key, model_name]):
            print("❌ 所有字段都是必需的")
            return

    elif choice in services:
        service = services[choice]
        provider = service["provider"]
        api_mode = service["api_mode"]
        print(f"\n🔧 配置 {service['name']}")

        base_url = service["base_url"]
        print(f"Base URL: {base_url}")
        if provider in ["lmstudio", "ollama"]:
            print("接口模式: 自动（gpt-oss 走 Responses，其余模型走 Chat + JSON Schema）")

        # 获取API密钥
        if service["api_key_prefix"] == "not-needed":
            api_key = "not-needed"
            print("API Key: 不需要 (本地服务)")
        else:
            while True:
                api_key = input(f"请输入API Key (以 {service['api_key_prefix']} 开头): ").strip()
                if api_key.startswith(service["api_key_prefix"]) or api_key == "":
                    break
                print(f"❌ API Key 应该以 {service['api_key_prefix']} 开头")

        # 选择模型
        available_models = service["models"]

        # 对于本地服务，尝试动态获取模型
        loaded_models = []
        if service["name"] in ["LM Studio (本地)", "Ollama (本地)"]:
            print(f"\n🔍 正在获取 {service['name']} 可用模型...")
            dynamic_models = get_available_models(base_url, api_key, provider=provider)
            loaded_models = get_loaded_models(base_url, api_key, provider=provider)

            if dynamic_models:
                available_models = dynamic_models
                print(f"✅ 找到 {len(available_models)} 个可用模型")
            else:
                print("⚠️  无法获取模型列表，将使用默认选项")
                available_models = []

            if loaded_models:
                print(f"✅ 当前已加载模型: {', '.join(loaded_models)}")
            else:
                print("⚠️  当前没有已加载模型；留空自动选择将无法生成")

        # 显示可用模型
        if available_models:
            print("\n可用模型:")
            for i, model in enumerate(available_models, 1):
                marker = " (已加载)" if model in loaded_models else ""
                print(f"{i}. {model}{marker}")

            print(f"{len(available_models) + 1}. 自定义模型名称")

            if provider in ["lmstudio", "ollama"]:
                prompt = f"\n请选择模型 (1-{len(available_models) + 1}, 回车=自动使用当前已加载模型): "
            else:
                prompt = f"\n请选择模型 (1-{len(available_models) + 1}, 回车使用默认): "
            model_choice = input(prompt).strip()

            if model_choice == "":
                model_name = service["default_model"]
            elif model_choice.isdigit():
                choice_num = int(model_choice)
                if 1 <= choice_num <= len(available_models):
                    model_name = available_models[choice_num - 1]
                elif choice_num == len(available_models) + 1:
                    # 自定义模型名称
                    model_name = input("请输入自定义模型名称: ").strip()
                    if not model_name:
                        if provider in ["lmstudio", "ollama"]:
                            print("ℹ️  模型名称留空，将自动使用当前已加载模型")
                        else:
                            print("❌ 模型名称不能为空，使用默认模型")
                        model_name = service["default_model"]
                else:
                    print("❌ 无效选择，使用默认模型")
                    model_name = service["default_model"]
            else:
                print("❌ 无效选择，使用默认模型")
                model_name = service["default_model"]
        else:
            # 没有可用模型，直接让用户输入
            print("\n📝 请输入模型名称:")
            if provider in ["lmstudio", "ollama"]:
                model_name = input("模型名称 (回车=自动使用当前已加载模型): ").strip()
            else:
                model_name = input(f"模型名称 (回车使用默认 '{service['default_model']}'): ").strip()
                if not model_name:
                    model_name = service["default_model"]

    else:
        print("❌ 无效选择")
        return

    # 确认配置
    print("\n📋 配置摘要:")
    service_name = services[choice]["name"] if choice in services else "自定义"
    print(f"服务: {service_name}")
    print(f"Provider: {provider}")
    print(f"API Mode: {api_mode}")
    print(f"Base URL: {base_url}")
    print(f"API Key: {'已设置' if api_key and api_key != 'not-needed' else '不需要'}")
    if model_name:
        print(f"Model: {model_name}")
    elif provider in ["lmstudio", "ollama"]:
        print("Model: (自动使用当前已加载模型)")
    else:
        print("Model: (未设置)")

    confirm = input("\n确认保存配置? (y/N): ").strip().lower()
    if confirm in ["y", "yes"]:
        # 确保配置文件存在
        create_config_file()

        # 更新配置
        update_config_file("LLM_PROVIDER", provider)
        update_config_file("LLM_API_MODE", api_mode)
        update_config_file("LLM_BASE_URL", base_url)
        update_config_file("LLM_API_KEY", api_key)
        update_config_file("LLM_MODEL_NAME", model_name)

        print("✅ LLM配置已保存")

        # 询问是否设置为LLM优先
        llm_priority = input("\n是否设置为优先使用LLM? (y/N): ").strip().lower()
        if llm_priority in ["y", "yes"]:
            update_config_file("DATA_SOURCE_STRATEGY", "llm_first")
            print("✅ 已设置为LLM优先模式")

    else:
        print("❌ 配置已取消")


def display_menu():
    """显示菜单选项"""
    print("\n" + "=" * 50)
    print("Anki 词汇自动化工具 v2.0")
    print("=" * 50)

    print("\n可用选项:")
    print("1. 运行自动化脚本（单线程）")
    print("2. 运行并发处理（推荐用于大词汇表）")
    print("3. 测试第一个单词")
    print("4. 配置Collins API")
    print("5. 配置LLM服务")
    print("6. 设置数据源优先级")
    print("7. 查看当前配置")
    print("8. 创建配置文件")
    print("9. 检查Anki环境")
    print("10. 运行完整测试")
    print("11. 查看帮助")
    print("12. 退出")


def main():
    """主函数"""
    display_menu()

    while True:
        choice = input("\n请选择 (1-12): ").strip()

        if choice == "1":
            print("\n启动自动化脚本（单线程）...")
            if not validate_current_config():
                print("配置验证失败，请先修复配置问题")
                display_menu()
                continue

            # 在运行主程序前先检查Anki环境
            if not check_anki_environment():
                print("❌ Anki环境检查失败，请先解决问题再运行")
                display_menu()
                continue

            try:
                from anki_vocab_automation.main import main as automation_main

                automation_main()
            except ImportError as e:
                print(f"导入失败: {e}")
                print_dependency_install_hint()
            except Exception as e:
                print(f"运行失败: {e}")
                import traceback

                traceback.print_exc()
            break

        elif choice == "2":
            print("\n启动并发处理...")
            if not validate_current_config():
                print("配置验证失败，请先修复配置问题")
                display_menu()
                continue

            # 在运行前先检查Anki环境
            if not check_anki_environment():
                print("❌ Anki环境检查失败，请先解决问题再运行")
                display_menu()
                continue

            # 获取并发参数
            try:
                max_workers = input("请输入最大并发线程数 (默认4): ").strip()
                max_workers = int(max_workers) if max_workers else 4
                max_workers = max(1, min(max_workers, 8))  # 限制在1-8之间

                rate_limit = input("请输入速率限制 (每秒请求数，默认2.0): ").strip()
                rate_limit = float(rate_limit) if rate_limit else 2.0
                rate_limit = max(0.1, min(rate_limit, 10.0))  # 限制在0.1-10之间

                print(f"并发配置: 最大线程数={max_workers}, 速率限制={rate_limit}/s")

            except ValueError:
                print("❌ 输入格式错误，使用默认配置: 线程数=4, 速率=2.0/s")
                max_workers = 4
                rate_limit = 2.0

            try:
                from anki_vocab_automation.main import VocabularyAutomation, read_word_list

                # 读取单词列表
                word_list = read_word_list()
                if not word_list:
                    print("❌ 无法读取单词列表或列表为空")
                    print("请检查 data/New_Words.txt 文件")
                    display_menu()
                    continue

                # 创建自动化实例
                automation = VocabularyAutomation()

                # 使用并发处理
                automation.process_word_list_concurrent(word_list, max_workers, rate_limit)

            except ImportError as e:
                print(f"导入失败: {e}")
                print_dependency_install_hint()
            except Exception as e:
                print(f"运行失败: {e}")
                import traceback

                traceback.print_exc()
            break

        elif choice == "3":
            print("\n测试第一个单词...")
            if not validate_current_config():
                print("配置验证失败，请先修复配置问题")
                display_menu()
                continue

            # 在测试前先检查Anki环境
            if not check_anki_environment():
                print("❌ Anki环境检查失败，请先解决问题再测试")
                display_menu()
                continue

            try:
                from anki_vocab_automation.main import VocabularyAutomation, read_word_list
                from anki_vocab_automation.config import DATA_SOURCE_STRATEGY

                # 读取单词列表
                word_list = read_word_list()
                if not word_list:
                    print("❌ 无法读取单词列表或列表为空")
                    print("请检查 data/New_Words.txt 文件")
                    display_menu()
                    continue

                first_word = word_list[0]
                print(f"测试单词: {first_word}")
                print(f"数据源策略: {DATA_SOURCE_STRATEGY}")

                # 创建自动化实例
                automation = VocabularyAutomation()

                # 测试单个单词
                success = automation.process_single_word_test(first_word)

                if success:
                    print(f"✅ 成功处理单词: {first_word}")
                else:
                    print(f"❌ 处理单词失败: {first_word}")
                    print("请检查:")
                    print("1. Anki是否正在运行")
                    print("2. AnkiConnect插件是否已安装")
                    print("3. 是否创建了'Vocabulary'卡牌模板")
                    print("4. 数据源配置是否正确")

            except ImportError as e:
                print(f"导入失败: {e}")
                print_dependency_install_hint()
            except Exception as e:
                print(f"测试失败: {e}")
                import traceback

                traceback.print_exc()

            display_menu()
            continue

        elif choice == "4":
            print("\n配置Collins API")
            configure_collins_api()
            display_menu()
            continue

        elif choice == "5":
            print("\n配置LLM服务")
            configure_llm_service()
            display_menu()
            continue

        elif choice == "6":
            print("\n设置数据源优先级")
            set_data_source_strategy()
            display_menu()
            continue

        elif choice == "7":
            print("\n查看当前配置")
            display_current_config()
            display_menu()
            continue

        elif choice == "8":
            print("\n创建配置文件")
            create_config_file()
            display_menu()
            continue

        elif choice == "9":
            print("\n检查Anki环境")
            check_anki_environment()
            display_menu()
            continue

        elif choice == "10":
            print("\n启动完整测试...")
            try:
                from tests.test_automation import main as test_main

                test_main()
            except ImportError as e:
                print(f"导入失败: {e}")
                print_dependency_install_hint(include_test_tools=True)
            except Exception as e:
                print(f"测试失败: {e}")

            display_menu()
            continue

        elif choice == "11":
            print("\n使用帮助:")
            print("=" * 50)
            print("1. 首次使用：")
            print("   - 选择'8'创建配置文件")
            print("   - 选择'9'检查Anki环境")
            print("   - 选择'4'配置Collins API (可选)")
            print("   - 选择'5'配置LLM服务 (推荐)")
            print("   - 选择'6'设置数据源优先级")
            print("   - 选择'7'查看当前配置")
            print()
            print("2. 处理模式选择：")
            print("   - 选择'1': 单线程处理（适合小词汇表，<50词）")
            print("   - 选择'2': 并发处理（推荐用于大词汇表，50+词）")
            print()
            print("3. Agent/Codex 直接使用：")
            print("   - 可直接运行: uv run anki-vocab --entry 'clarify｜I asked the teacher to clarify the lesson.'")
            print("   - 可批量粘贴: printf 'clarify｜...\\nschedule｜...\\n' | uv run anki-vocab --stdin --concurrent")
            print("   - 支持分隔符: TAB、全角｜、半角|")
            print("   - 直连模式固定只走 LLM，不使用 Collins API")
            print()
            print("4. 数据源策略说明：")
            print("   - collins_only: 仅使用Collins API")
            print("   - llm_only: 仅使用LLM")
            print("   - collins_first: 优先Collins API，失败时使用LLM")
            print("   - llm_first: 优先LLM，失败时使用Collins API")
            print()
            print("5. 并发处理配置：")
            print("   - 最大线程数: 建议2-4，取决于网络和API限制")
            print("   - 速率限制: 每秒请求数，避免触发API限制")
            print("   - 小词汇表: 线程数=2, 速率=1.0/s")
            print("   - 大词汇表: 线程数=4, 速率=2.0/s")
            print()
            print("6. TTS音频生成：")
            print("   - 当使用LLM生成卡片时，自动使用TTS生成发音音频")
            print("   - 推荐主路径是 OpenAI 兼容远程TTS 服务")
            print("   - Google / Microsoft / ResponsiveVoice 仅作为可选 legacy URL 兼容回退")
            print("   - 配置 TTS_OPENAI_COMPAT_BASE_URL 后会优先使用本地/远程 openai_compat TTS")
            print("   - 在config.env中配置ENABLE_TTS_FALLBACK=true启用")
            print()
            print("7. 环境变量配置：")
            print("   - LLM_PROVIDER: 后端类型 (openai/anthropic/lmstudio/ollama/openai_compat)")
            print("   - LLM_API_MODE: 接口模式 (responses/chat/messages)")
            print("   - COLLINS_API_KEY: Collins API密钥")
            print("   - LLM_BASE_URL: LLM服务地址")
            print("   - LLM_API_KEY: LLM API密钥")
            print("   - LLM_MODEL_NAME: LLM模型名称")
            print("   - LLM_PROMPT_VERSION: 提示词版本 (revised/baseline)")
            print("   - DATA_SOURCE_STRATEGY: 数据源策略")
            print("   - ENABLE_TTS_FALLBACK: 是否启用TTS音频")
            print("   - TTS_OPENAI_COMPAT_BASE_URL: 远程TTS服务地址（推荐）")
            print("   - TTS_SERVICE: 可选 legacy URL TTS 回退（google/microsoft/responsivevoice）")
            print()
            print("8. 支持的LLM服务：")
            print("   - OpenAI: https://api.openai.com/v1")
            print("   - Anthropic Claude: https://api.anthropic.com")
            print("   - LM Studio: http://localhost:1234 (自动规范到 /v1)")
            print("   - Ollama: http://localhost:11434 (自动规范到 /v1)")
            print("   - 其他第三方兼容后端: 先按 OpenAI Chat 兼容模式配置")
            print("   💡 建议：使用'5'选项进行图形化配置")
            print()
            print("9. 常见问题：")
            print("   - 确保Anki正在运行并安装了AnkiConnect插件")
            print("   - 确保data/New_Words.txt中有要处理的输入")
            print("   - 推荐格式: 单词<TAB>原句、单词｜原句 或 单词|原句；旧的纯单词格式仍可用")
            print("   - 使用'9'选项自动检查和创建Anki环境")
            print("   - 检查网络连接和API密钥")
            print("   - 并发处理出错时可降低线程数和速率限制")
            print()
            print("详细说明请查看README.md文件")

            display_menu()
            continue

        elif choice == "12":
            print("\n再见！")
            break

        else:
            print("❌ 无效选择，请输入1-12")
            display_menu()
            continue


if __name__ == "__main__":
    main()
