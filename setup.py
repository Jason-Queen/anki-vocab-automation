#!/usr/bin/env python3
"""
Setup script for Anki Vocabulary Automation

This script helps users set up the environment and configure the application.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        print(f"   Current version: {sys.version}")
        sys.exit(1)
    else:
        print(f"✅ Python version: {sys.version.split()[0]}")

def setup_virtual_environment():
    """Set up virtual environment"""
    print("\n📦 Setting up virtual environment...")
    
    if not os.path.exists("venv"):
        subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
        print("✅ Virtual environment created")
    else:
        print("✅ Virtual environment already exists")

def install_dependencies():
    """Install required dependencies"""
    print("\n📥 Installing dependencies...")
    
    # Determine pip path based on OS
    if sys.platform == "win32":
        pip_path = "venv/Scripts/pip"
    else:
        pip_path = "venv/bin/pip"
    
    subprocess.run([pip_path, "install", "-r", "requirements.txt"], check=True)
    print("✅ Dependencies installed")

def setup_config():
    """Set up configuration file"""
    print("\n⚙️  Setting up configuration...")
    
    config_path = Path("config.env")
    example_path = Path("config.env.example")
    
    if not config_path.exists():
        if example_path.exists():
            shutil.copy(example_path, config_path)
            print("✅ Configuration file created from template")
            print("⚠️  Please edit config.env to configure your API keys:")
            print("   - COLLINS_API_KEY: Get from https://www.collinsdictionary.com/api")
            print("   - LLM settings: Configure if using LLM services")
        else:
            print("❌ Configuration template not found")
    else:
        print("✅ Configuration file already exists")
        # Check if API key is configured
        with open(config_path, 'r') as f:
            content = f.read()
            if "COLLINS_API_KEY=your_collins_api_key_here" in content:
                print("⚠️  Please configure your Collins API key in config.env")
                print("   Get your API key from: https://www.collinsdictionary.com/api")
            else:
                print("✅ Configuration appears to be set up")

def create_sample_data():
    """Create sample data files"""
    print("\n📝 Setting up sample data...")
    
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    word_file = data_dir / "New_Words.txt"
    if not word_file.exists():
        with open(word_file, 'w') as f:
            f.write("hello\nworld\ninvestigation\nfundamental\n")
        print("✅ Sample word list created")
    else:
        print("✅ Word list already exists")

def check_anki_requirements():
    """Check Anki requirements"""
    print("\n🎯 Anki Requirements Check...")
    print("Please ensure the following:")
    print("1. ✅ Anki desktop application is installed")
    print("2. ✅ AnkiConnect plugin is installed (code: 2055492159)")
    print("3. ✅ Anki is running when you use this tool")
    print("4. ✅ 'Vocabulary' deck and note type exist (will be created automatically)")

def main():
    """Main setup function"""
    print("🚀 Anki Vocabulary Automation Setup v2.0")
    print("=" * 45)
    
    try:
        check_python_version()
        setup_virtual_environment()
        install_dependencies()
        setup_config()
        create_sample_data()
        check_anki_requirements()
        
        print("\n🎉 Setup completed successfully!")
        print("\nNext steps:")
        print("1. Edit config.env to configure your API keys")
        print("2. Add words to data/New_Words.txt")
        print("3. Start Anki and install AnkiConnect plugin")
        print("4. Run: python app.py")
        print("\nQuick start commands:")
        print("  source venv/bin/activate    # Activate virtual environment")
        print("  python app.py              # Run the application")
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Setup failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 