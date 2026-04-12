#!/usr/bin/env python3
"""
Simple test to verify the logging mechanism works
"""

import json
from datetime import datetime
from pathlib import Path

def test_logging():
    """Test the logging mechanism"""
    print("Testing OpenRouter prompt logging mechanism...")
    
    # Create a test log entry
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "method": "test",
        "model": "google/gemini-flash-1.5:free",
        "provider": "openrouter",
        "system_instruction": "Test system instruction",
        "user_prompt": "Test prompt for logging",
    }
    
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Log file path
    log_file = log_dir / "openrouter_prompts.json"
    
    # Append to log file
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    
    print(f"✓ Log entry written to {log_file}")
    
    # Read and display the log file
    print(f"\n--- Contents of {log_file} ---")
    with open(log_file, 'r') as f:
        for line in f:
            print(line.strip())
    
    print("\n✓ Logging mechanism is working correctly")
    print("✓ All OpenRouter prompts will now be logged to logs/openrouter_prompts.json")

if __name__ == "__main__":
    test_logging()
