#!/usr/bin/env python3
"""
Update categories in DD v2.1 files based on categorized attributes.
Reads categorized attributes from Client/categorized/ folder and updates
the corresponding files in Client/DD v2.1/ folder.
"""

import json
from pathlib import Path
from typing import Dict, Any
from datetime import datetime


def load_json(file_path: Path) -> Dict[str, Any]:
    """Load JSON file and return as dictionary."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(file_path: Path, data: Dict[str, Any], indent: int = 4):
    """Save dictionary as JSON file with proper formatting."""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)


def extract_entity_name(filename: str) -> str:
    """
    Extract entity name from filename.
    Example: 'host__data_dictionary_categorized_attributes.json' -> 'host'
    """
    # Remove extension and split by '__'
    name_without_ext = filename.replace('.json', '').replace('_categorized_attributes', '').replace('__data_dictionary', '')
    return name_without_ext.lower()


def load_categorized_mapping(categorized_file: Path) -> Dict[str, str]:
    """
    Load categorized attributes file and create a mapping of attribute_name -> category.
    
    Input structure: {entity_name: {group_key: {category: [attribute_names]}}}
    Output: {attribute_name: category}
    """
    categorized_data = load_json(categorized_file)
    
    # The structure is {entity_name: {group_key: {category: [attributes]}}}
    # We need to flatten this to {attribute_name: category}
    attribute_to_category = {}
    
    for entity_name, groups in categorized_data.items():
        for group_key, categories in groups.items():
            for category, attribute_names in categories.items():
                for attr_name in attribute_names:
                    if attr_name in attribute_to_category:
                        # If attribute appears in multiple categories, keep the last one
                        # (or you could log a warning)
                        print(f"  WARNING: Attribute '{attr_name}' appears in multiple categories. Using '{category}'")
                    attribute_to_category[attr_name] = category
    
    return attribute_to_category


def update_dd_file(dd_file: Path, attribute_to_category: Dict[str, str], log_messages: list) -> tuple:
    """
    Update categories in a DD v2.1 file based on the categorized mapping.
    
    Returns:
        (dd_data, updated_count, not_found_count, already_set_count) - data dict and counts
    """
    dd_data = load_json(dd_file)
    
    if 'attributes' not in dd_data:
        log_messages.append(f"  WARNING: No 'attributes' key found in {dd_file.name}")
        return dd_data, 0, 0, 0
    
    attributes = dd_data['attributes']
    updated_count = 0
    not_found_count = 0
    already_set_count = 0
    
    for attr_name, category in attribute_to_category.items():
        if attr_name in attributes:
            attr_data = attributes[attr_name]
            
            # Check if category is already set and matches
            current_category = attr_data.get('category', '')
            if current_category == category:
                already_set_count += 1
                continue
            
            # Update the category
            attr_data['category'] = category
            updated_count += 1
            log_messages.append(f"  Updated '{attr_name}': category = '{category}'")
        else:
            not_found_count += 1
            log_messages.append(f"  WARNING: Attribute '{attr_name}' not found in {dd_file.name}")
    
    return dd_data, updated_count, not_found_count, already_set_count


def find_matching_dd_file(categorized_file: Path, dd_dir: Path) -> Path:
    """
    Find the matching DD v2.1 file for a categorized file.
    
    Example:
        categorized_file: Client/categorized/host__data_dictionary_categorized_attributes.json
        returns: Client/DD v2.1/host__data_dictionary.json
    """
    # Extract the base name: host__data_dictionary_categorized_attributes.json -> host__data_dictionary.json
    base_name = categorized_file.stem.replace('_categorized_attributes', '')
    dd_filename = f"{base_name}.json"
    dd_file = dd_dir / dd_filename
    
    return dd_file


def main():
    """Main function to update categories in DD v2.1 files."""
    # Define paths
    base_dir = Path(__file__).parent
    client_dir = base_dir / "Client"
    categorized_dir = client_dir / "categorized"
    dd_dir = client_dir / "DD v2.1"
    
    # Check if directories exist
    if not categorized_dir.exists():
        print(f"ERROR: Categorized directory not found: {categorized_dir}")
        return
    
    if not dd_dir.exists():
        print(f"ERROR: DD v2.1 directory not found: {dd_dir}")
        return
    
    # Get all categorized files
    categorized_files = list(categorized_dir.glob("*_categorized_attributes.json"))
    
    if not categorized_files:
        print(f"No categorized attribute files found in {categorized_dir}")
        return
    
    print(f"Found {len(categorized_files)} categorized file(s)")
    print(f"{'='*70}\n")
    
    total_updated = 0
    total_not_found = 0
    total_already_set = 0
    processed_files = 0
    
    # Process each categorized file
    for categorized_file in sorted(categorized_files):
        entity_name = extract_entity_name(categorized_file.name)
        print(f"Processing: {categorized_file.name}")
        print(f"  Entity: {entity_name}")
        
        # Load categorized mapping
        try:
            attribute_to_category = load_categorized_mapping(categorized_file)
            print(f"  Found {len(attribute_to_category)} categorized attribute(s)")
        except Exception as e:
            print(f"  ERROR: Failed to load categorized file: {e}")
            continue
        
        if not attribute_to_category:
            print(f"  SKIPPED: No categorized attributes found")
            continue
        
        # Find matching DD v2.1 file
        dd_file = find_matching_dd_file(categorized_file, dd_dir)
        
        if not dd_file.exists():
            print(f"  WARNING: Matching DD v2.1 file not found: {dd_file.name}")
            continue
        
        # Update the DD v2.1 file
        log_messages = []
        try:
            dd_data, updated, not_found, already_set = update_dd_file(dd_file, attribute_to_category, log_messages)
            
            if updated > 0:
                # Save the updated file
                save_json(dd_file, dd_data)
                print(f"  Updated {updated} attribute(s) in {dd_file.name}")
            
            if already_set > 0:
                print(f"  {already_set} attribute(s) already had correct category")
            
            if not_found > 0:
                print(f"  WARNING: {not_found} attribute(s) not found in DD v2.1 file")
            
            total_updated += updated
            total_not_found += not_found
            total_already_set += already_set
            processed_files += 1
            
            # Show detailed log if there were updates or warnings
            if log_messages and (updated > 0 or not_found > 0):
                print("  Details:")
                for msg in log_messages[:10]:  # Show first 10 messages
                    print(f"    {msg}")
                if len(log_messages) > 10:
                    print(f"    ... and {len(log_messages) - 10} more")
        
        except Exception as e:
            print(f"  ERROR: Failed to update {dd_file.name}: {e}")
            continue
        
        print()
    
    # Summary
    print(f"{'='*70}")
    print(f"UPDATE SUMMARY")
    print(f"{'='*70}")
    print(f"  Processed files: {processed_files}")
    print(f"  Attributes updated: {total_updated}")
    print(f"  Attributes already set: {total_already_set}")
    if total_not_found > 0:
        print(f"  Attributes not found: {total_not_found}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()

