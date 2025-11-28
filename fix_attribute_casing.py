#!/usr/bin/env python3
"""
Script to fix casing of caption and description for each attribute using AI.
- Uses OpenAI or Gemini to fix casing
- Ensures all descriptions end with '.'
- Processes files from Client/DD v2.1
"""

import json
import copy
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
import time
import os

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv is optional, will use os.getenv directly

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


def write_log(log_file: Path, message: str):
    """Write a message to the log file."""
    with open(log_file, 'a', encoding='utf-8') as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{timestamp}] {message}\n")


def load_json(file_path: Path) -> Dict[str, Any]:
    """Load JSON file and return as dictionary."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(file_path: Path, data: Dict[str, Any], indent: int = 4):
    """Save dictionary as JSON file with proper formatting."""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)


def ensure_description_ends_with_period(description: str) -> str:
    """Ensure description ends with a period. Returns the fixed description."""
    if not description:
        return description
    
    description = description.strip()
    if not description:
        return description
    
    # If it doesn't end with punctuation, add a period
    if not description[-1] in '.!?':
        return description + '.'
    
    return description


def fix_casing_with_gemini(text: str, field_type: str, api_key: str) -> str:
    """
    Use Gemini AI to fix casing of text (caption or description).
    field_type should be 'caption' or 'description'.
    """
    prompt = f"""You are a text editor expert. Fix the casing and grammar of the following {field_type} text.
    
Original {field_type}: {text}

Rules:
- For captions: Use proper title case (e.g., "Internal IP Address", "OS Major Version")
- For descriptions: Use proper sentence case (e.g., "The internal IPv4 address of the host.")
- Maintain technical terms and acronyms correctly (e.g., "IP", "OS", "IPv4", "API")
- Keep the meaning and content exactly the same, only fix casing and grammar

Respond with ONLY the corrected {field_type} text, nothing else. Do not include quotes or any other text."""

    try:
        # Configure Gemini
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')
        
        # Generate response
        response = model.generate_content(prompt)
        fixed_text = response.text.strip()
        
        # Remove quotes if present
        if fixed_text.startswith('"') and fixed_text.endswith('"'):
            fixed_text = fixed_text[1:-1]
        elif fixed_text.startswith("'") and fixed_text.endswith("'"):
            fixed_text = fixed_text[1:-1]
        
        return fixed_text
        
    except Exception as e:
        # On error, return original text
        return text


def fix_casing_with_openai(text: str, field_type: str, api_key: str) -> str:
    """
    Use OpenAI to fix casing of text (caption or description).
    field_type should be 'caption' or 'description'.
    """
    prompt = f"""You are a text editor expert. Fix the casing and grammar of the following {field_type} text.
    
Original {field_type}: {text}

Rules:
- For captions: Use proper title case (e.g., "Internal IP Address", "OS Major Version")
- For descriptions: Use proper sentence case (e.g., "The internal IPv4 address of the host.")
- Maintain technical terms and acronyms correctly (e.g., "IP", "OS", "IPv4", "API")
- Keep the meaning and content exactly the same, only fix casing and grammar

Respond with ONLY the corrected {field_type} text, nothing else. Do not include quotes or any other text."""

    try:
        # Initialize OpenAI client
        client = OpenAI(api_key=api_key)
        
        # Generate response
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": f"You are a text editor expert. Respond with only the corrected {field_type} text, nothing else."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=200
        )
        
        fixed_text = response.choices[0].message.content.strip()
        
        # Remove quotes if present
        if fixed_text.startswith('"') and fixed_text.endswith('"'):
            fixed_text = fixed_text[1:-1]
        elif fixed_text.startswith("'") and fixed_text.endswith("'"):
            fixed_text = fixed_text[1:-1]
        
        return fixed_text
        
    except Exception as e:
        # On error, return original text
        return text


def process_file(file_path: Path, file_num: int, total_files: int, 
                 ai_provider: str = 'gemini', api_key: str = None):
    """
    Process a single file to fix casing of captions and descriptions.
    
    Args:
        file_path: Path to the JSON file to process
        file_num: Current file number
        total_files: Total number of files
        ai_provider: 'openai' or 'gemini'
        api_key: API key for the selected provider
    """
    # Create log folder inside the file's directory
    file_dir = file_path.parent
    log_folder = file_dir / "log"
    log_folder.mkdir(parents=True, exist_ok=True)
    
    # Create log file path in log folder
    log_file = log_folder / f"{file_path.stem}_casing_fix.log"
    
    # Initialize log file (overwrite on each run)
    with open(log_file, 'w', encoding='utf-8') as f:
        f.write(f"Casing Fix Log for: {file_path.name}\n")
        f.write(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"AI Provider: {ai_provider.upper()}\n")
        f.write("="*70 + "\n\n")
    
    print(f"\n{'='*70}")
    print(f"[{file_num}/{total_files}] Processing: {file_path.name}")
    print(f"{'='*70}")
    write_log(log_file, f"SCRIPT: Starting casing fix for {file_path.name}")
    
    # Load file
    print("  Loading file...", end=" ", flush=True)
    data = load_json(file_path)
    
    if 'attributes' not in data:
        print("SKIPPED (No 'attributes' key found)")
        write_log(log_file, "SCRIPT: No 'attributes' key found, skipping file")
        return
    
    attributes = data['attributes']
    total_attrs = len(attributes)
    print(f"OK ({total_attrs} attributes)")
    write_log(log_file, f"SCRIPT: Loaded file with {total_attrs} attributes")
    
    # Process attributes
    caption_fixed_count = 0
    description_fixed_count = 0
    description_period_fixed_count = 0
    caption_changes = []
    description_changes = []
    
    print(f"  Processing {total_attrs} attribute(s) with {ai_provider.upper()}...")
    write_log(log_file, f"SCRIPT: Processing {total_attrs} attributes with {ai_provider.upper()}")
    
    for idx, (attr_name, attr_data) in enumerate(attributes.items(), 1):
        # Show progress
        progress_pct = (idx / total_attrs) * 100
        progress_bar_length = 40
        filled_length = int(progress_bar_length * idx // total_attrs)
        bar = '█' * filled_length + '░' * (progress_bar_length - filled_length)
        print(f"\r  [{bar}] {idx}/{total_attrs} ({progress_pct:.1f}%) - Processing: {attr_name[:50]}", end='', flush=True)
        
        modified = False
        
        # Fix caption if it exists
        if 'caption' in attr_data and isinstance(attr_data['caption'], str) and attr_data['caption'].strip():
            original_caption = attr_data['caption']
            
            # Fix casing using AI
            if ai_provider.lower() == 'openai':
                fixed_caption = fix_casing_with_openai(original_caption, 'caption', api_key)
            else:  # gemini
                fixed_caption = fix_casing_with_gemini(original_caption, 'caption', api_key)
            
            if fixed_caption != original_caption:
                attr_data['caption'] = fixed_caption
                caption_fixed_count += 1
                modified = True
                caption_changes.append(f"{attr_name}: '{original_caption}' -> '{fixed_caption}'")
                write_log(log_file, f"SCRIPT: Fixed caption for '{attr_name}': '{original_caption}' -> '{fixed_caption}'")
        
        # Fix description if it exists
        if 'description' in attr_data and isinstance(attr_data['description'], str) and attr_data['description'].strip():
            original_description = attr_data['description']
            
            # Fix casing using AI
            if ai_provider.lower() == 'openai':
                fixed_description = fix_casing_with_openai(original_description, 'description', api_key)
            else:  # gemini
                fixed_description = fix_casing_with_gemini(original_description, 'description', api_key)
            
            # Ensure description ends with period
            fixed_description = ensure_description_ends_with_period(fixed_description)
            
            # Check if description changed (either casing or period)
            description_changed = False
            if fixed_description != original_description:
                description_changed = True
            
            # Check if period was added
            period_added = False
            if original_description.strip() and not original_description.strip()[-1] in '.!?':
                if fixed_description.endswith('.'):
                    period_added = True
            
            if description_changed:
                attr_data['description'] = fixed_description
                description_fixed_count += 1
                modified = True
                if period_added:
                    description_period_fixed_count += 1
                
                change_msg = f"{attr_name}: '{original_description}' -> '{fixed_description}'"
                if period_added:
                    change_msg += " [period added]"
                description_changes.append(change_msg)
                write_log(log_file, f"SCRIPT: Fixed description for '{attr_name}': '{original_description}' -> '{fixed_description}'")
        
        # Rate limiting: delay after every 30 attributes
        if idx > 0 and idx % 30 == 0:
            print(f"\n  Rate limit: Waiting 60 seconds after processing {idx} attribute(s)...")
            write_log(log_file, f"SCRIPT: Rate limit delay - waiting 60 seconds after {idx} attributes")
            time.sleep(60)
            print("  Resuming...\n")
    
    # Clear progress line and show completion
    print(f"\r  [{'█' * progress_bar_length}] {total_attrs}/{total_attrs} (100.0%) - Completed!{' ' * 50}")
    
    # Save file if any changes were made
    if caption_fixed_count > 0 or description_fixed_count > 0:
        print(f"  Saving file...", end=" ", flush=True)
        save_json(file_path, data)
        print("OK")
        write_log(log_file, f"SCRIPT: Saved file with changes")
    else:
        print("  No changes needed")
        write_log(log_file, f"SCRIPT: No changes needed")
    
    # Summary
    print(f"\n  Summary:")
    print(f"    Captions fixed: {caption_fixed_count}")
    print(f"    Descriptions fixed: {description_fixed_count}")
    print(f"    Periods added: {description_period_fixed_count}")
    print(f"    Log file: {log_file.name}")
    
    write_log(log_file, f"SCRIPT: Summary - Captions fixed: {caption_fixed_count}, Descriptions fixed: {description_fixed_count}, Periods added: {description_period_fixed_count}")
    
    if caption_changes:
        write_log(log_file, f"SCRIPT: Caption changes ({len(caption_changes)}):")
        for change in caption_changes[:10]:  # Log first 10
            write_log(log_file, f"SCRIPT:   {change}")
        if len(caption_changes) > 10:
            write_log(log_file, f"SCRIPT:   ... and {len(caption_changes) - 10} more caption changes")
    
    if description_changes:
        write_log(log_file, f"SCRIPT: Description changes ({len(description_changes)}):")
        for change in description_changes[:10]:  # Log first 10
            write_log(log_file, f"SCRIPT:   {change}")
        if len(description_changes) > 10:
            write_log(log_file, f"SCRIPT:   ... and {len(description_changes) - 10} more description changes")
    
    # Finalize log
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write("\n" + "="*70 + "\n")
        f.write(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    print(f"  Successfully processed: {file_path.name}")


def display_menu(files: list) -> int:
    """Display menu and get user choice."""
    print(f"\n{'='*70}")
    print("CASING FIX MENU")
    print(f"{'='*70}")
    print("1. Process all files")
    print("2. Process one file (select from list)")
    print("3. Exit")
    print(f"{'='*70}")
    
    while True:
        try:
            choice = input("\nEnter your choice (1-3): ").strip()
            if choice in ['1', '2', '3']:
                return int(choice)
            else:
                print("Invalid choice. Please enter 1, 2, or 3.")
        except KeyboardInterrupt:
            print("\n\nExiting...")
            return 3
        except Exception as e:
            print(f"Invalid input. Please enter a number (1-3).")


def display_file_list(files: list) -> int:
    """Display list of files and get user selection."""
    print(f"\n{'='*70}")
    print("AVAILABLE FILES")
    print(f"{'='*70}")
    for idx, file_path in enumerate(files, 1):
        print(f"{idx}. {file_path.name}")
    print(f"{len(files) + 1}. Back to main menu")
    print(f"{'='*70}")
    
    while True:
        try:
            choice = input(f"\nSelect a file (1-{len(files) + 1}): ").strip()
            choice_num = int(choice)
            if 1 <= choice_num <= len(files) + 1:
                return choice_num
            else:
                print(f"Invalid choice. Please enter a number between 1 and {len(files) + 1}.")
        except ValueError:
            print("Invalid input. Please enter a number.")
        except KeyboardInterrupt:
            print("\n\nReturning to main menu...")
            return len(files) + 1


def select_ai_provider() -> tuple:
    """
    Select AI provider and return (provider_name, api_key).
    Returns (None, None) if cancelled or no provider available.
    """
    available_providers = []
    if GEMINI_AVAILABLE and os.getenv('GEMINI_API_KEY'):
        available_providers.append('gemini')
    if OPENAI_AVAILABLE and os.getenv('OPENAI_API_KEY'):
        available_providers.append('openai')
    
    if len(available_providers) == 0:
        print("  ERROR: No AI providers available (missing API keys or packages)")
        print("  Please ensure you have either GEMINI_API_KEY or OPENAI_API_KEY set in .env file")
        return None, None
    
    if len(available_providers) == 1:
        # Only one provider available, use it automatically
        provider = available_providers[0]
        api_key = os.getenv('GEMINI_API_KEY') if provider == 'gemini' else os.getenv('OPENAI_API_KEY')
        print(f"  Using {provider.upper()} (only available provider)")
        return provider, api_key
    
    # Multiple providers available - ask user to choose
    print(f"\n  Available AI providers:")
    for idx, provider in enumerate(available_providers, 1):
        print(f"    {idx}. {provider.upper()}")
    
    while True:
        try:
            provider_choice = input(f"  Select AI provider (1-{len(available_providers)}): ").strip()
            provider_num = int(provider_choice)
            if 1 <= provider_num <= len(available_providers):
                provider = available_providers[provider_num - 1]
                api_key = os.getenv('GEMINI_API_KEY') if provider == 'gemini' else os.getenv('OPENAI_API_KEY')
                print(f"  Selected {provider.upper()}")
                return provider, api_key
            else:
                print(f"  Invalid choice. Please enter a number between 1 and {len(available_providers)}.")
        except ValueError:
            print("  Invalid input. Please enter a number.")
        except KeyboardInterrupt:
            print("\n  Cancelled.")
            return None, None


def process_files(files: list, files_to_process: list = None):
    """
    Process the selected files.
    """
    if files_to_process is None:
        files_to_process = files
    
    # Select AI provider once for all files
    ai_provider, api_key = select_ai_provider()
    if not ai_provider or not api_key:
        print("\n  Cannot proceed without AI provider. Exiting.")
        return
    
    processed = 0
    skipped = 0
    total_files = len(files_to_process)
    
    print(f"\nProcessing {total_files} file(s) with {ai_provider.upper()}...\n")
    
    for idx, file_path in enumerate(files_to_process, 1):
        try:
            process_file(file_path, idx, total_files, ai_provider, api_key)
            processed += 1
        except Exception as e:
            print(f"\n{'='*70}")
            print(f"[{idx}/{total_files}] ERROR processing: {file_path.name}")
            print(f"{'='*70}")
            print(f"  Error: {e}")
            skipped += 1
    
    print(f"\n{'='*70}")
    print(f"PROCESSING SUMMARY")
    print(f"{'='*70}")
    print(f"  Successfully processed: {processed} file(s)")
    if skipped > 0:
        print(f"  Failed/Skipped: {skipped} file(s)")
    print(f"{'='*70}\n")


def main():
    """Main function."""
    # Define paths
    base_dir = Path(__file__).parent
    input_dir = base_dir / "Client" / "DD v2.1"
    
    if not input_dir.exists():
        print(f"ERROR: Directory not found: {input_dir}")
        print("Please ensure the 'Client/DD v2.1' directory exists.")
        return
    
    # Get all JSON files in the input directory
    files = list(input_dir.glob("*__data_dictionary.json"))
    
    if not files:
        print(f"No data dictionary files found in {input_dir}!")
        return
    
    print(f"Found {len(files)} file(s) in {input_dir}")
    
    # Main menu loop
    while True:
        choice = display_menu(files)
        
        if choice == 1:
            # Process all files
            process_files(files)
            input("\nPress Enter to continue...")
        
        elif choice == 2:
            # Process one file
            file_choice = display_file_list(files)
            
            if file_choice == len(files) + 1:
                # Back to main menu
                continue
            
            selected_file = files[file_choice - 1]
            process_files(files, [selected_file])
            input("\nPress Enter to continue...")
        
        elif choice == 3:
            # Exit
            print("\nExiting... Goodbye!")
            break


if __name__ == "__main__":
    main()

