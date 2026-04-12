#!/usr/bin/env python3
"""
Test script to verify OpenRouter prompt logging
"""

import sys
import os

# Add api to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'api'))

def test_logging():
    """Test OpenRouter prompt logging"""
    try:
        # Import directly from the module
        import importlib.util
        spec = importlib.util.spec_from_file_location("openrouter_client", "api/openrouter_client.py")
        openrouter_client = importlib.util.module_from_spec(spec)
        sys.modules['openrouter_client'] = openrouter_client
        spec.loader.exec_module(openrouter_client)
        
        OpenRouterLLMClient = openrouter_client.OpenRouterLLMClient
        
        print("Testing OpenRouter prompt logging...")
        
        # Create client (will fail without API key, but that's okay for testing)
        client = OpenRouterLLMClient(api_key="test-key")
        
        # Test the logging method directly
        client._log_prompt(
            prompt="Test prompt for logging",
            system_instruction="Test system instruction",
            model="google/gemini-flash-1.5:free",
            method="test"
        )
        
        print("✓ Logging method executed successfully")
        print("✓ Check logs/openrouter_prompts.json for the logged entry")
        
        # Read and display the log file if it exists
        log_file = "logs/openrouter_prompts.json"
        if os.path.exists(log_file):
            print(f"\n--- Contents of {log_file} ---")
            with open(log_file, 'r') as f:
                for line in f:
                    print(line.strip())
        else:
            print(f"\n✗ Log file not found at {log_file}")
            
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_logging()
