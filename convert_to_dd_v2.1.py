#!/usr/bin/env python3
"""
Conversion script to create DD v2.1 files from Client dictionaries.
- Finds common parent keys between Client and Product
- Removes duplicate parent keys from Client (except 'attributes')
- Always keeps 'attributes' from Client
- Creates output in Client/DD v2.1/ folder
"""

import json
import copy
from pathlib import Path
from typing import Dict, Any, Set
from datetime import datetime


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


def find_common_parent_keys(client_data: Dict[str, Any], product_data: Dict[str, Any]) -> Set[str]:
    """Find common parent keys between Client and Product (excluding 'attributes')."""
    client_keys = set(client_data.keys())
    product_keys = set(product_data.keys())
    
    # Find common keys, but exclude 'attributes'
    common_keys = client_keys.intersection(product_keys)
    common_keys.discard('attributes')
    
    return common_keys


def deep_compare_dicts(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> bool:
    """
    Compare two dictionaries deeply, ignoring key order.
    Excludes 'dashboard_identifier' from comparison.
    Returns True if they are exactly the same, False otherwise.
    """
    if not isinstance(dict1, dict) or not isinstance(dict2, dict):
        return dict1 == dict2
    
    # Create copies without dashboard_identifier for comparison
    dict1_filtered = {k: v for k, v in dict1.items() if k != 'dashboard_identifier'}
    dict2_filtered = {k: v for k, v in dict2.items() if k != 'dashboard_identifier'}
    
    if set(dict1_filtered.keys()) != set(dict2_filtered.keys()):
        return False
    
    for key in dict1_filtered.keys():
        val1 = dict1_filtered[key]
        val2 = dict2_filtered[key]
        
        if isinstance(val1, dict) and isinstance(val2, dict):
            if not deep_compare_dicts(val1, val2):
                return False
        elif isinstance(val1, list) and isinstance(val2, list):
            # Compare lists (order matters for lists)
            if val1 != val2:
                return False
        else:
            if val1 != val2:
                return False
    
    return True


def find_dict_differences(dict1: Dict[str, Any], dict2: Dict[str, Any], path: str = "") -> list:
    """
    Find differences between two dictionaries.
    Excludes 'dashboard_identifier' from comparison.
    Returns a list of difference descriptions.
    """
    differences = []
    
    if not isinstance(dict1, dict) or not isinstance(dict2, dict):
        if dict1 != dict2:
            differences.append(f"{path}: Client='{dict1}' vs Product='{dict2}'")
        return differences
    
    # Filter out dashboard_identifier for comparison
    dict1_filtered = {k: v for k, v in dict1.items() if k != 'dashboard_identifier'}
    dict2_filtered = {k: v for k, v in dict2.items() if k != 'dashboard_identifier'}
    
    all_keys = set(dict1_filtered.keys()) | set(dict2_filtered.keys())
    
    for key in all_keys:
        current_path = f"{path}.{key}" if path else key
        
        if key not in dict1_filtered:
            differences.append(f"{current_path}: Missing in Client, Product has '{dict2_filtered[key]}'")
        elif key not in dict2_filtered:
            differences.append(f"{current_path}: Missing in Product, Client has '{dict1_filtered[key]}'")
        else:
            val1 = dict1_filtered[key]
            val2 = dict2_filtered[key]
            
            if isinstance(val1, dict) and isinstance(val2, dict):
                differences.extend(find_dict_differences(val1, val2, current_path))
            elif isinstance(val1, list) and isinstance(val2, list):
                if val1 != val2:
                    differences.append(f"{current_path}: Lists differ - Client={val1}, Product={val2}")
            else:
                if val1 != val2:
                    differences.append(f"{current_path}: Client='{val1}' vs Product='{val2}'")
    
    return differences


def compare_and_remove_common_attributes(client_attrs: Dict[str, Any], 
                                         product_attrs: Dict[str, Any],
                                         file_name: str,
                                         log_file: Path) -> Dict[str, Any]:
    """
    Compare common attributes between Client and Product.
    Ask for confirmation before removing exact matches.
    Returns the cleaned attributes dictionary.
    """
    if not product_attrs:
        return client_attrs
    
    common_attr_names = set(client_attrs.keys()) & set(product_attrs.keys())
    
    if not common_attr_names:
        print("  No common attributes found to compare")
        write_log(log_file, "SCRIPT: No common attributes found to compare")
        return client_attrs
    
    exact_matches = []
    different_attrs = []
    
    # First pass: categorize attributes
    for attr_name in sorted(common_attr_names):
        client_attr = client_attrs[attr_name]
        product_attr = product_attrs[attr_name]
        
        if deep_compare_dicts(client_attr, product_attr):
            exact_matches.append(attr_name)
        else:
            differences = find_dict_differences(client_attr, product_attr, attr_name)
            different_attrs.append((attr_name, differences))
    
    total_requires_confirmation = len(exact_matches) + len(different_attrs)
    
    if total_requires_confirmation == 0:
        print("  No attributes require confirmation")
        write_log(log_file, "SCRIPT: No attributes require confirmation")
        return client_attrs
    
    # Show summary
    print(f"\n  SUMMARY: {total_requires_confirmation} attribute(s) require confirmation")
    print(f"  {'-'*66}")
    
    write_log(log_file, f"SCRIPT: Found {total_requires_confirmation} attribute(s) requiring confirmation")
    write_log(log_file, f"SCRIPT: Category 1 (Exact matches): {len(exact_matches)} attribute(s)")
    write_log(log_file, f"SCRIPT: Category 2 (Different): {len(different_attrs)} attribute(s)")
    
    # Category 1: Remove from Client (exact matches)
    if exact_matches:
        print(f"\n  Category 1: REMOVE FROM CLIENT ({len(exact_matches)} attribute(s))")
        print(f"  These are identical in Client and Product:")
        for attr_name in exact_matches:
            print(f"    - {attr_name}")
        write_log(log_file, f"SCRIPT: Category 1 attributes: {', '.join(exact_matches)}")
    
    # Category 2: Keep in Client (different attributes)
    if different_attrs:
        print(f"\n  Category 2: KEEP IN CLIENT ({len(different_attrs)} attribute(s))")
        print(f"  These have differences between Client and Product:")
        for attr_name, differences in different_attrs:
            print(f"    - {attr_name} ({len(differences)} difference(s))")
        write_log(log_file, f"SCRIPT: Category 2 attributes: {', '.join([name for name, _ in different_attrs])}")
    
    # Ask processing mode
    print(f"\n  Processing options:")
    print(f"    1. Process each category as a whole (y/n for entire category)")
    print(f"    2. Process one by one (y/n for each attribute)")
    
    while True:
        try:
            mode = input(f"\n  Select processing mode (1 or 2): ").strip()
            if mode in ['1', '2']:
                write_log(log_file, f"USER: Selected processing mode {mode} ({'whole category' if mode == '1' else 'one by one'})")
                break
            else:
                print("  Invalid choice. Please enter 1 or 2.")
        except KeyboardInterrupt:
            print("\n  Cancelled. Keeping all attributes.")
            write_log(log_file, "USER: Cancelled (KeyboardInterrupt) - Keeping all attributes")
            return client_attrs
    
    # Process Category 1: Remove from Client (exact matches)
    if exact_matches:
        if mode == '1':
            # Process as whole
            print(f"\n  Category 1: REMOVE FROM CLIENT ({len(exact_matches)} attribute(s))")
            response = input(f"  Remove all {len(exact_matches)} exact match(es) from Client? (y/n): ").strip().lower()
            write_log(log_file, f"USER: Category 1 - Remove all {len(exact_matches)}? Response: {response}")
            
            if response == 'y':
                for attr_name in exact_matches:
                    del client_attrs[attr_name]
                print(f"  Removed {len(exact_matches)} exact match(es) from Client")
                write_log(log_file, f"SCRIPT: Removed {len(exact_matches)} exact match(es): {', '.join(exact_matches)}")
            else:
                print(f"  Kept {len(exact_matches)} exact match(es) in Client")
                write_log(log_file, f"SCRIPT: Kept {len(exact_matches)} exact match(es) in Client")
        else:
            # Process one by one
            print(f"\n  Category 1: REMOVE FROM CLIENT - Processing one by one")
            removed_count = 0
            removed_attrs = []
            kept_attrs = []
            for attr_name in exact_matches:
                response = input(f"  Remove '{attr_name}' from Client? (y/n): ").strip().lower()
                write_log(log_file, f"USER: Category 1 - Remove '{attr_name}'? Response: {response}")
                if response == 'y':
                    del client_attrs[attr_name]
                    removed_count += 1
                    removed_attrs.append(attr_name)
                    print(f"    Removed '{attr_name}'")
                else:
                    kept_attrs.append(attr_name)
                    print(f"    Kept '{attr_name}'")
            print(f"  Summary: Removed {removed_count} of {len(exact_matches)} attribute(s)")
            if removed_attrs:
                write_log(log_file, f"SCRIPT: Removed {removed_count} attribute(s): {', '.join(removed_attrs)}")
            if kept_attrs:
                write_log(log_file, f"SCRIPT: Kept {len(kept_attrs)} attribute(s): {', '.join(kept_attrs)}")
    
    # Process Category 2: Keep in Client (different attributes)
    if different_attrs:
        if mode == '1':
            # Process as whole
            print(f"\n  Category 2: KEEP IN CLIENT ({len(different_attrs)} attribute(s))")
            print(f"  These attributes have differences. Showing first 3:")
            for idx, (attr_name, differences) in enumerate(different_attrs[:3]):
                print(f"\n    {attr_name}:")
                for diff in differences[:3]:
                    print(f"      - {diff}")
                if len(differences) > 3:
                    print(f"      ... and {len(differences) - 3} more")
            
            if len(different_attrs) > 3:
                print(f"\n    ... and {len(different_attrs) - 3} more attribute(s)")
            
            response = input(f"\n  Keep all {len(different_attrs)} different attribute(s) in Client? (y/n): ").strip().lower()
            write_log(log_file, f"USER: Category 2 - Keep all {len(different_attrs)}? Response: {response}")
            
            if response == 'y':
                print(f"  Kept {len(different_attrs)} attribute(s) in Client")
                write_log(log_file, f"SCRIPT: Kept {len(different_attrs)} different attribute(s) in Client")
            else:
                removed_count = 0
                removed_attrs = []
                for attr_name, _ in different_attrs:
                    del client_attrs[attr_name]
                    removed_attrs.append(attr_name)
                    removed_count += 1
                print(f"  Removed {removed_count} attribute(s) from Client")
                write_log(log_file, f"SCRIPT: Removed {removed_count} different attribute(s): {', '.join(removed_attrs)}")
        else:
            # Process one by one
            print(f"\n  Category 2: KEEP IN CLIENT - Processing one by one")
            kept_count = 0
            kept_attrs = []
            removed_attrs = []
            for attr_name, differences in different_attrs:
                print(f"\n    Attribute: {attr_name}")
                print(f"    Differences ({len(differences)}):")
                for diff in differences[:5]:
                    print(f"      - {diff}")
                if len(differences) > 5:
                    print(f"      ... and {len(differences) - 5} more difference(s)")
                
                response = input(f"\n    Keep '{attr_name}' in Client? (y/n): ").strip().lower()
                write_log(log_file, f"USER: Category 2 - Keep '{attr_name}'? Response: {response}")
                if response == 'y':
                    kept_count += 1
                    kept_attrs.append(attr_name)
                    print(f"      Kept '{attr_name}'")
                else:
                    del client_attrs[attr_name]
                    removed_attrs.append(attr_name)
                    print(f"      Removed '{attr_name}'")
            print(f"  Summary: Kept {kept_count} of {len(different_attrs)} attribute(s)")
            if kept_attrs:
                write_log(log_file, f"SCRIPT: Kept {kept_count} attribute(s): {', '.join(kept_attrs)}")
            if removed_attrs:
                write_log(log_file, f"SCRIPT: Removed {len(removed_attrs)} attribute(s): {', '.join(removed_attrs)}")
    
    return client_attrs


def remove_vra_ccm_from_dashboard_identifier(attributes: Dict[str, Any]) -> int:
    """
    Remove 'VRA' and 'CCM' subkeys from dashboard_identifier in attributes.
    Returns count of attributes modified.
    """
    modified_count = 0
    
    for attr_name, attr_data in attributes.items():
        if isinstance(attr_data, dict) and 'dashboard_identifier' in attr_data:
            dashboard_id = attr_data['dashboard_identifier']
            if isinstance(dashboard_id, dict):
                # Check if VRA or CCM exist before removing
                has_vra = 'VRA' in dashboard_id
                has_ccm = 'CCM' in dashboard_id
                
                # Remove VRA and CCM if they exist
                if has_vra:
                    del dashboard_id['VRA']
                if has_ccm:
                    del dashboard_id['CCM']
                
                # Count as modified if at least one was removed
                if has_vra or has_ccm:
                    modified_count += 1
    
    return modified_count


def convert_file(client_file: Path, product_file: Path, output_file: Path, file_num: int, total_files: int):
    """Convert a single file by removing common parent keys (except attributes)."""
    # Create log file path (same name as output file but with .log extension)
    log_file = output_file.parent / f"{output_file.stem}.log"
    
    # Initialize log file (overwrite on each run)
    with open(log_file, 'w', encoding='utf-8') as f:
        f.write(f"Conversion Log for: {client_file.name}\n")
        f.write(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("="*70 + "\n\n")
    
    print(f"\n{'='*70}")
    print(f"[{file_num}/{total_files}] Processing: {client_file.name}")
    print(f"{'='*70}")
    write_log(log_file, f"SCRIPT: Starting conversion of {client_file.name}")
    
    # Load both files
    print("  Loading Client file...", end=" ", flush=True)
    client_data = load_json(client_file)
    client_keys_count = len(client_data.keys())
    print(f"OK ({client_keys_count} top-level keys)")
    write_log(log_file, f"SCRIPT: Loaded Client file with {client_keys_count} top-level keys")
    
    product_data = None
    if product_file.exists():
        print("  Loading Product file...", end=" ", flush=True)
        product_data = load_json(product_file)
        product_keys_count = len(product_data.keys())
        print(f"OK ({product_keys_count} top-level keys)")
        write_log(log_file, f"SCRIPT: Loaded Product file with {product_keys_count} top-level keys")
        
        # Find common parent keys (excluding 'attributes')
        print("  Finding common parent keys...", end=" ", flush=True)
        common_keys = find_common_parent_keys(client_data, product_data)
        print(f"OK Found {len(common_keys)} common keys")
        write_log(log_file, f"SCRIPT: Found {len(common_keys)} common parent keys: {', '.join(sorted(common_keys)) if common_keys else 'none'}")
        
        if common_keys:
            print(f"  Removing common keys: {', '.join(sorted(common_keys))}")
            write_log(log_file, f"SCRIPT: Removing common parent keys: {', '.join(sorted(common_keys))}")
        else:
            print("  No common keys to remove (excluding 'attributes')")
    else:
        print(f"  WARNING: No matching Product file found, skipping common key removal")
        write_log(log_file, f"SCRIPT: WARNING - No matching Product file found")
        common_keys = set()
    
    # Create output structure
    print("  Building output structure...", end=" ", flush=True)
    output_data = {}
    
    # Copy Client keys, but exclude common keys (always keep 'attributes')
    removed_count = 0
    kept_count = 0
    removed_keys = []
    for key, value in client_data.items():
        if key == 'attributes':
            # Always keep attributes, make deep copy so we can modify it
            output_data[key] = copy.deepcopy(value)
            kept_count += 1
        elif key not in common_keys:
            # Keep Client-specific keys (not in common)
            output_data[key] = value
            kept_count += 1
        else:
            # Skip common keys (they are removed)
            removed_count += 1
            removed_keys.append(key)
    
    print(f"OK (Kept: {kept_count}, Removed: {removed_count})")
    if removed_keys:
        write_log(log_file, f"SCRIPT: Removed {removed_count} common parent key(s): {', '.join(removed_keys)}")
    write_log(log_file, f"SCRIPT: Kept {kept_count} top-level key(s) in output")
    
    # Remove VRA and CCM from dashboard_identifier in attributes
    if 'attributes' in output_data:
        print("  Removing VRA and CCM from dashboard_identifier...", end=" ", flush=True)
        modified_attrs = remove_vra_ccm_from_dashboard_identifier(output_data['attributes'])
        print(f"OK (Modified {modified_attrs} attribute(s))")
        write_log(log_file, f"SCRIPT: Removed VRA/CCM from dashboard_identifier in {modified_attrs} attribute(s)")
        
        # Compare common attributes with Product
        if product_data and 'attributes' in product_data:
            print("\n  Comparing attributes with Product config...")
            write_log(log_file, "SCRIPT: Starting attribute comparison with Product config")
            output_data['attributes'] = compare_and_remove_common_attributes(
                output_data['attributes'],
                product_data['attributes'],
                client_file.name,
                log_file
            )
    
    # Save output file
    print(f"  Saving to: {output_file.name}...", end=" ", flush=True)
    save_json(output_file, output_data)
    print("OK")
    write_log(log_file, f"SCRIPT: Saved output file: {output_file.name}")
    
    # Finalize log
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write("\n" + "="*70 + "\n")
        f.write(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    print(f"  Successfully converted: {client_file.name}")
    print(f"  Log file: {log_file.name}")


def display_menu(client_files: list) -> int:
    """Display menu and get user choice."""
    print(f"\n{'='*70}")
    print("CONVERSION MENU")
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


def display_file_list(client_files: list) -> int:
    """Display list of files and get user selection."""
    print(f"\n{'='*70}")
    print("AVAILABLE FILES")
    print(f"{'='*70}")
    for idx, file_path in enumerate(client_files, 1):
        print(f"{idx}. {file_path.name}")
    print(f"{len(client_files) + 1}. Back to main menu")
    print(f"{'='*70}")
    
    while True:
        try:
            choice = input(f"\nSelect a file (1-{len(client_files) + 1}): ").strip()
            choice_num = int(choice)
            if 1 <= choice_num <= len(client_files) + 1:
                return choice_num
            else:
                print(f"Invalid choice. Please enter a number between 1 and {len(client_files) + 1}.")
        except ValueError:
            print("Invalid input. Please enter a number.")
        except KeyboardInterrupt:
            print("\n\nReturning to main menu...")
            return len(client_files) + 1


def process_files(client_files: list, product_dir: Path, output_dir: Path, 
                  files_to_process: list = None):
    """Process the selected files."""
    if files_to_process is None:
        files_to_process = client_files
    
    processed = 0
    skipped = 0
    total_files = len(files_to_process)
    
    print(f"\nProcessing {total_files} file(s)...\n")
    
    for idx, client_file in enumerate(files_to_process, 1):
        # Find corresponding Product file
        product_file = product_dir / client_file.name
        
        # Create output file path
        output_file = output_dir / client_file.name
        
        try:
            convert_file(client_file, product_file, output_file, idx, total_files)
            processed += 1
        except Exception as e:
            print(f"\n{'='*70}")
            print(f"[{idx}/{total_files}] ERROR processing: {client_file.name}")
            print(f"{'='*70}")
            print(f"  Error: {e}")
            skipped += 1
    
    print(f"\n{'='*70}")
    print(f"CONVERSION SUMMARY")
    print(f"{'='*70}")
    print(f"  Successfully processed: {processed} file(s)")
    if skipped > 0:
        print(f"  Failed/Skipped: {skipped} file(s)")
    print(f"  Output directory: {output_dir}")
    print(f"{'='*70}\n")


def main():
    """Main conversion function."""
    # Define paths
    base_dir = Path(__file__).parent
    client_dir = base_dir / "Client"
    product_dir = base_dir / "Product"
    output_dir = client_dir / "DD v2.1"
    
    # Create output directory
    output_dir.mkdir(exist_ok=True)
    print(f"Created output directory: {output_dir}")
    
    # Get all JSON files in Client directory
    client_files = list(client_dir.glob("*__data_dictionary.json"))
    
    if not client_files:
        print("No data dictionary files found in Client folder!")
        return
    
    print(f"Found {len(client_files)} file(s) in Client folder")
    
    # Main menu loop
    while True:
        choice = display_menu(client_files)
        
        if choice == 1:
            # Process all files
            process_files(client_files, product_dir, output_dir)
            input("\nPress Enter to continue...")
        
        elif choice == 2:
            # Process one file
            file_choice = display_file_list(client_files)
            
            if file_choice == len(client_files) + 1:
                # Back to main menu
                continue
            
            selected_file = client_files[file_choice - 1]
            process_files(client_files, product_dir, output_dir, [selected_file])
            input("\nPress Enter to continue...")
        
        elif choice == 3:
            # Exit
            print("\nExiting... Goodbye!")
            break


if __name__ == "__main__":
    main()

