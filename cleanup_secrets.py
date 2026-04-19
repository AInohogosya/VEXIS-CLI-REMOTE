#!/usr/bin/env python3
"""
Cleanup Personal Information Script
This script helps users easily remove sensitive information from their system.
"""

import os
import shutil
from pathlib import Path
import sys

def print_header(text):
    """Print a formatted header"""
    print(f"\n{'=' * 60}")
    print(f"  {text}")
    print(f"{'=' * 60}\n")

def print_success(text):
    """Print success message"""
    print(f"✓ {text}")

def print_warning(text):
    """Print warning message"""
    print(f"⚠ {text}")

def print_error(text):
    """Print error message"""
    print(f"✗ {text}")

def cleanup_config_yaml():
    """Remove sensitive data from config.yaml"""
    config_path = Path("config.yaml")
    if not config_path.exists():
        print_warning("config.yaml not found - skipping")
        return False
    
    print("Found config.yaml - removing sensitive data...")
    
    # Read the config
    with open(config_path, 'r') as f:
        lines = f.readlines()
    
    # Remove sensitive lines
    cleaned_lines = []
    skip_next = False
    for i, line in enumerate(lines):
        if skip_next:
            skip_next = False
            continue
        
        # Check for sensitive keys
        if any(key in line.lower() for key in ['bot_token', 'api_hash', 'phone', 'authorized_users']):
            # Replace with placeholder
            if ':' in line:
                indent = len(line) - len(line.lstrip())
                key = line.split(':')[0].strip()
                if key == 'bot_token':
                    cleaned_lines.append(' ' * indent + f'{key}: ""\n')
                elif key == 'api_hash':
                    cleaned_lines.append(' ' * indent + f'{key}: "YOUR_API_HASH_HERE"\n')
                elif key == 'phone':
                    cleaned_lines.append(' ' * indent + f'{key}: "YOUR_PHONE_NUMBER"\n')
                elif key == 'authorized_users':
                    cleaned_lines.append(' ' * indent + f'{key}: []\n')
                    skip_next = True  # Skip the list content
                else:
                    cleaned_lines.append(line)
            else:
                cleaned_lines.append(line)
        else:
            cleaned_lines.append(line)
    
    # Write back
    with open(config_path, 'w') as f:
        f.writelines(cleaned_lines)
    
    print_success("Removed sensitive data from config.yaml")
    return True

def cleanup_telegram_sessions():
    """Remove Telegram session files"""
    session_dirs = [
        Path.home() / ".vexis" / "telegram_sessions",
        Path("telegram_sessions")
    ]
    
    cleaned = False
    for session_dir in session_dirs:
        if session_dir.exists():
            print(f"Removing Telegram sessions from {session_dir}...")
            shutil.rmtree(session_dir)
            print_success(f"Removed {session_dir}")
            cleaned = True
    
    if not cleaned:
        print_warning("No Telegram sessions found - skipping")
    
    return cleaned

def cleanup_cache_files():
    """Remove cache and temporary files"""
    cache_paths = [
        Path(".vexis"),
        Path("vexis.log"),
        Path("environment_report.json")
    ]
    
    cleaned = False
    for path in cache_paths:
        if path.exists():
            if path.is_file():
                print(f"Removing {path}...")
                path.unlink()
                print_success(f"Removed {path}")
                cleaned = True
            elif path.is_dir():
                print(f"Removing directory {path}...")
                shutil.rmtree(path)
                print_success(f"Removed {path}")
                cleaned = True
    
    if not cleaned:
        print_warning("No cache files found - skipping")
    
    return cleaned

def main():
    """Main cleanup function"""
    print_header("VEXIS-CLI Personal Information Cleanup")
    
    print("This script will remove the following sensitive information:")
    print("  • API keys and tokens from config.yaml")
    print("  • Phone numbers from config.yaml")
    print("  • Telegram session files")
    print("  • Cache and log files")
    print()
    
    response = input("Do you want to continue? (y/N): ").strip().lower()
    if response not in ['y', 'yes']:
        print("Cleanup cancelled.")
        return
    
    print("\nStarting cleanup...\n")
    
    # Cleanup config.yaml
    cleanup_config_yaml()
    
    # Cleanup Telegram sessions
    cleanup_telegram_sessions()
    
    # Cleanup cache files
    cleanup_cache_files()
    
    print_header("Cleanup Complete")
    print("All sensitive information has been removed.")
    print("\nNext steps:")
    print("  1. Review config.yaml to ensure all sensitive data is removed")
    print("  2. Use environment variables for API keys (see README)")
    print("  3. Commit changes to Git if desired")
    print()

if __name__ == "__main__":
    main()
