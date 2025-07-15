#!/usr/bin/env python3
"""
Repository Check Script
Validates that the project is ready for GitHub upload
"""

import os
import sys
from pathlib import Path

def check_sensitive_files():
    """Check for sensitive files that shouldn't be in the repo"""
    print("🔍 Checking for sensitive files...")
    
    sensitive_files = [
        "config.env",
        "anki_vocab_automation.log",
        ".env"
    ]
    
    found_sensitive = []
    for file in sensitive_files:
        if os.path.exists(file):
            found_sensitive.append(file)
    
    if found_sensitive:
        print(f"❌ Found sensitive files: {found_sensitive}")
        return False
    else:
        print("✅ No sensitive files found")
        return True

def check_required_files():
    """Check for required files"""
    print("\n📋 Checking for required files...")
    
    required_files = [
        "README.md",
        "LICENSE",
        "requirements.txt",
        "pyproject.toml",
        ".gitignore",
        "config.env.example"
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Missing required files: {missing_files}")
        return False
    else:
        print("✅ All required files present")
        return True

def check_project_structure():
    """Check project structure"""
    print("\n🏗️  Checking project structure...")
    
    required_dirs = [
        "src/anki_vocab_automation",
        "tests",
        "examples",
        "scripts",
        "data",
        "templates"
    ]
    
    missing_dirs = []
    for dir_path in required_dirs:
        if not os.path.exists(dir_path):
            missing_dirs.append(dir_path)
    
    if missing_dirs:
        print(f"❌ Missing directories: {missing_dirs}")
        return False
    else:
        print("✅ Project structure is correct")
        return True

def check_gitignore():
    """Check .gitignore file"""
    print("\n🚫 Checking .gitignore...")
    
    if not os.path.exists(".gitignore"):
        print("❌ .gitignore file missing")
        return False
    
    with open(".gitignore", "r") as f:
        gitignore_content = f.read()
    
    required_patterns = [
        "venv/",
        "*.log",
        "config.env",
        "__pycache__/",
        ".DS_Store"
    ]
    
    missing_patterns = []
    for pattern in required_patterns:
        if pattern not in gitignore_content:
            missing_patterns.append(pattern)
    
    if missing_patterns:
        print(f"❌ Missing .gitignore patterns: {missing_patterns}")
        return False
    else:
        print("✅ .gitignore file is complete")
        return True

def scan_for_api_keys():
    """Scan for potential API keys"""
    print("\n🔐 Scanning for API keys...")
    
    found_issues = []
    
    for root, dirs, files in os.walk("."):
        # Skip virtual environment and git directories
        dirs[:] = [d for d in dirs if d not in ['.git', 'venv', '__pycache__']]
        
        for file in files:
            if file.endswith(('.py', '.md', '.txt', '.yaml', '.yml', '.json')):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                        # Check for Collins API key patterns (50+ chars starting with letters/numbers)
                        import re
                        collins_pattern = r'[A-Za-z0-9]{50,}'
                        collins_matches = re.findall(collins_pattern, content)
                        for match in collins_matches:
                            # Skip if it's clearly a placeholder or example
                            if not any(placeholder in match for placeholder in ['your', 'example', 'placeholder', 'test']):
                                # Skip if it's in a comment or example
                                lines = content.split('\n')
                                for i, line in enumerate(lines):
                                    if match in line and not line.strip().startswith('#') and 'sk-your-' not in line:
                                        found_issues.append(f"Potential Collins API key in {filepath}:{i+1}")
                        
                        # Check for actual sk- keys (not placeholders)
                        if "sk-" in content and "sk-your-" not in content:
                            lines = content.split('\n')
                            for i, line in enumerate(lines):
                                if "sk-" in line and "sk-your-" not in line and not line.strip().startswith('#'):
                                    found_issues.append(f"Potential API key in {filepath}:{i+1}")
                                    
                except Exception as e:
                    print(f"Warning: Could not read {filepath}: {e}")
    
    if found_issues:
        print(f"❌ Found potential issues: {found_issues}")
        return False
    else:
        print("✅ No API keys found")
        return True

def check_example_files():
    """Check example files are appropriate"""
    print("\n📚 Checking example files...")
    
    example_files = [
        "config.env.example",
        "data/New_Words.txt",
        "examples/sample_words.txt"
    ]
    
    for file in example_files:
        if os.path.exists(file):
            print(f"✅ {file} exists")
        else:
            print(f"⚠️  {file} missing (optional)")
    
    return True

def main():
    """Main check function"""
    print("🚀 Repository Check for GitHub Upload")
    print("=" * 50)
    
    checks = [
        check_sensitive_files,
        check_required_files,
        check_project_structure,
        check_gitignore,
        scan_for_api_keys,
        check_example_files
    ]
    
    all_passed = True
    for check in checks:
        if not check():
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All checks passed! Repository is ready for GitHub upload.")
        print("\nNext steps:")
        print("1. git add .")
        print("2. git commit -m 'Initial commit'")
        print("3. git push origin main")
    else:
        print("❌ Some checks failed. Please fix the issues above.")
        sys.exit(1)

if __name__ == "__main__":
    main() 