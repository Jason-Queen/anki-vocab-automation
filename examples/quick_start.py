#!/usr/bin/env python3
"""
Quick Start Example for Anki Vocabulary Automation

This script demonstrates how to use the Anki Vocabulary Automation
package to process a few sample words.
"""

import sys
import os

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from anki_vocab_automation import VocabularyAutomation, CollinsAPI, HTMLParser

def quick_demo():
    """Demonstrate basic functionality with a few words"""
    
    print("🚀 Anki Vocabulary Automation - Quick Demo")
    print("=" * 50)
    
    # Sample words to test
    sample_words = ["hello", "investigation", "bidirectional"]
    
    # Initialize components
    api = CollinsAPI()
    parser = HTMLParser()
    
    print(f"📚 Testing {len(sample_words)} sample words...\n")
    
    for word in sample_words:
        print(f"🔍 Processing: {word}")
        
        # Get data from Collins API
        response_data = api.search_word(word)
        
        if response_data:
            dictionary = response_data.get('dictionary', 'unknown')
            print(f"   ✅ Found in {dictionary} dictionary")
            
            # Parse the response
            card = parser.parse_collins_response(response_data, word)
            
            if card:
                print(f"   📖 Standard form: {card.word}")
                print(f"   🔊 Pronunciation: {card.pronunciation}")
                print(f"   📝 Definition: {card.definition[:60]}...")
                print(f"   💬 Example: {card.example[:60]}...")
                print(f"   🎵 Audio: {'Yes' if card.audio_url else 'No'}")
            else:
                print("   ❌ Failed to parse response")
        else:
            print("   ❌ Not found in any dictionary")
            
        print()
    
    print("✨ Demo completed!")
    print("\nTo process your own words:")
    print("1. Add words to data/New_Words.txt")
    print("2. Run: python app.py")
    print("3. Choose option 1 to process all words")

if __name__ == "__main__":
    quick_demo() 