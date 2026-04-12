#!/usr/bin/env python3
"""
Test script to log actual prompts sent to the AI model.
This helps verify that no OpenRouter references are included in prompts.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from ai_agent.external_integration.model_runner import ModelRunner, ModelRequest, TaskType

def test_prompts():
    """Test and log prompts for all task types"""
    
    print("=" * 80)
    print("PROMPT TESTING - Checking for OpenRouter references")
    print("=" * 80)
    
    # Create model runner
    model_runner = ModelRunner(provider="openrouter", model="google/gemini-flash-1.5:free")
    
    # Test each task type
    task_types = [
        TaskType.PHASE1_COMMAND_SUGGESTION,
        TaskType.PHASE2_COMMAND_EXTRACTION,
        TaskType.PHASE4_LOG_EVALUATION,
        TaskType.PHASE5_SUMMARY_GENERATION,
    ]
    
    for task_type in task_types:
        print(f"\n{'=' * 80}")
        print(f"Task Type: {task_type.value}")
        print(f"{'=' * 80}")
        
        # Create a test request
        request = ModelRequest(
            task_type=task_type,
            prompt="test instruction",
            context={
                "user_prompt": "test instruction",
                "os_info": "macOS",
                "phase_1_output": "example phase 1 output",
                "full_terminal_log_so_far": "example terminal log",
                "full_terminal_log": "example terminal log",
            },
            max_tokens=1000,
            temperature=0.7
        )
        
        # Get the formatted prompt
        prompt = model_runner._format_prompt(request)
        print(f"\nFormatted Prompt:")
        print("-" * 80)
        print(prompt)
        print("-" * 80)
        
        # Get system instructions
        system_instructions = model_runner._get_system_instructions(task_type)
        print(f"\nSystem Instructions:")
        print("-" * 80)
        print(system_instructions)
        print("-" * 80)
        
        # Check for OpenRouter references
        combined_text = prompt.lower() + " " + system_instructions.lower()
        if "openrouter" in combined_text:
            print(f"\n⚠️  WARNING: OpenRouter reference found in {task_type.value}!")
        else:
            print(f"\n✓ No OpenRouter references found in {task_type.value}")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    test_prompts()
