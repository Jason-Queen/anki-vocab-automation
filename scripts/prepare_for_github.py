#!/usr/bin/env python3
"""
GitHub上传准备脚本
Script to prepare the project for GitHub upload
"""

import os
import sys
import subprocess
from pathlib import Path

def run_command(cmd, description):
    """运行命令并显示结果"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} 成功")
            return True
        else:
            print(f"❌ {description} 失败: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ {description} 异常: {str(e)}")
        return False

def check_git_installed():
    """检查Git是否安装"""
    return run_command("git --version", "检查Git版本")

def init_git_repo():
    """初始化Git仓库"""
    if not os.path.exists('.git'):
        if not run_command("git init", "初始化Git仓库"):
            return False
    
    # 配置Git用户信息（如果没有设置）
    run_command("git config user.name || git config user.name 'Jason-Queen'", "设置Git用户名")
    run_command("git config user.email || git config user.email 'Jason-Queen@users.noreply.github.com'", "设置Git邮箱")
    
    return True

def add_files():
    """添加文件到Git"""
    return run_command("git add .", "添加文件到Git")

def create_initial_commit():
    """创建初始提交"""
    return run_command('git commit -m "Initial commit: Anki Vocabulary Automation v2.0"', "创建初始提交")

def display_next_steps():
    """显示下一步操作"""
    print("\n🎉 项目已准备就绪！")
    print("\n📋 接下来的步骤：")
    print("1. 在GitHub上创建新的仓库")
    print("2. 复制仓库URL")
    print("3. 运行以下命令：")
    print("   git remote add origin https://github.com/Jason-Queen/anki-vocab-automation.git")
    print("   git branch -M main")
    print("   git push -u origin main")
    print("\n🔗 需要更新的链接：")
    print("- README.md 和 README_CN.md 中的 'your-username' 替换为您的GitHub用户名")
    print("- 更新所有GitHub链接指向您的实际仓库")

def main():
    """主函数"""
    print("🚀 GitHub上传准备脚本")
    print("=" * 50)
    
    # 检查Git
    if not check_git_installed():
        print("❌ 请先安装Git")
        sys.exit(1)
    
    # 初始化Git仓库
    if not init_git_repo():
        print("❌ Git仓库初始化失败")
        sys.exit(1)
    
    # 添加文件
    if not add_files():
        print("❌ 文件添加失败")
        sys.exit(1)
    
    # 创建初始提交
    if not create_initial_commit():
        print("❌ 初始提交创建失败")
        sys.exit(1)
    
    # 显示下一步
    display_next_steps()

if __name__ == "__main__":
    main() 