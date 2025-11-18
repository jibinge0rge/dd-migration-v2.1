#!/usr/bin/env python3
"""
Streamlit application to compare Client and Product data dictionary configurations.
Shows only common attributes and their exact differences.
"""

import streamlit as st
import json
from pathlib import Path
from typing import Dict, Any, List, Tuple
import copy


def load_json(file_path: Path) -> Dict[str, Any]:
    """Load JSON file and return as dictionary."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Error loading {file_path}: {e}")
        return {}


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
            if val1 != val2:
                return False
        else:
            if val1 != val2:
                return False
    
    return True


def find_dict_differences(dict1: Dict[str, Any], dict2: Dict[str, Any], path: str = "") -> List[str]:
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


def get_common_attributes(client_attrs: Dict[str, Any], product_attrs: Dict[str, Any]) -> Dict[str, Tuple[Dict, Dict, bool, List[str]]]:
    """
    Get common attributes and their comparison results.
    Returns: {attr_name: (client_attr, product_attr, is_exact_match, differences)}
    """
    common_attrs = {}
    
    if not client_attrs or not product_attrs:
        return common_attrs
    
    common_attr_names = set(client_attrs.keys()) & set(product_attrs.keys())
    
    for attr_name in sorted(common_attr_names):
        client_attr = client_attrs[attr_name]
        product_attr = product_attrs[attr_name]
        
        is_exact_match = deep_compare_dicts(client_attr, product_attr)
        differences = find_dict_differences(client_attr, product_attr, attr_name) if not is_exact_match else []
        
        common_attrs[attr_name] = (client_attr, product_attr, is_exact_match, differences)
    
    return common_attrs


def format_json_value(value: Any) -> str:
    """Format a JSON value for display."""
    if isinstance(value, dict):
        return json.dumps(value, indent=2, ensure_ascii=False)
    elif isinstance(value, list):
        return json.dumps(value, indent=2, ensure_ascii=False)
    else:
        return str(value)


def main():
    st.set_page_config(
        page_title="Config Comparison Tool",
        page_icon="🔍",
        layout="wide"
    )
    
    st.title("🔍 Client vs Product Config Comparison")
    st.markdown("Compare data dictionary configurations and view differences in common attributes")
    
    # Get base directory
    base_dir = Path(__file__).parent
    client_dir = base_dir / "Client"
    product_dir = base_dir / "Product"
    
    # Get available files
    client_files = list(client_dir.glob("*__data_dictionary.json"))
    
    if not client_files:
        st.error("No data dictionary files found in Client folder!")
        return
    
    # File selection
    file_names = [f.name for f in client_files]
    selected_file = st.selectbox(
        "Select a file to compare:",
        file_names,
        key="file_selector"
    )
    
    if not selected_file:
        st.stop()
    
    # Load files
    client_file = client_dir / selected_file
    product_file = product_dir / selected_file
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📁 Client Config")
        if client_file.exists():
            client_data = load_json(client_file)
            if client_data:
                st.success(f"✅ Loaded: {len(client_data.get('attributes', {}))} attributes")
            else:
                st.error("Failed to load client file")
                st.stop()
        else:
            st.error(f"File not found: {client_file}")
            st.stop()
    
    with col2:
        st.subheader("📁 Product Config")
        if product_file.exists():
            product_data = load_json(product_file)
            if product_data:
                st.success(f"✅ Loaded: {len(product_data.get('attributes', {}))} attributes")
            else:
                st.error("Failed to load product file")
                st.stop()
        else:
            st.error(f"File not found: {product_file}")
            st.stop()
    
    # Get attributes
    client_attrs = client_data.get('attributes', {})
    product_attrs = product_data.get('attributes', {})
    
    # Find common attributes
    common_attrs = get_common_attributes(client_attrs, product_attrs)
    
    if not common_attrs:
        st.warning("⚠️ No common attributes found between Client and Product configs.")
        st.stop()
    
    # Summary statistics
    st.markdown("---")
    st.subheader("📊 Summary")
    
    exact_matches = sum(1 for _, _, is_match, _ in common_attrs.values() if is_match)
    different_attrs = len(common_attrs) - exact_matches
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Common Attributes", len(common_attrs))
    with col2:
        st.metric("Exact Matches", exact_matches, delta=f"{exact_matches/len(common_attrs)*100:.1f}%")
    with col3:
        st.metric("Different Attributes", different_attrs, delta=f"{different_attrs/len(common_attrs)*100:.1f}%")
    
    # Filter options
    st.markdown("---")
    filter_option = st.radio(
        "Filter attributes:",
        ["All", "Exact Matches Only", "Different Only"],
        horizontal=True,
        key="filter_option"
    )
    
    # Filter common attributes based on selection
    filtered_attrs = {}
    if filter_option == "Exact Matches Only":
        filtered_attrs = {k: v for k, v in common_attrs.items() if v[2]}
    elif filter_option == "Different Only":
        filtered_attrs = {k: v for k, v in common_attrs.items() if not v[2]}
    else:
        filtered_attrs = common_attrs
    
    if not filtered_attrs:
        st.info("No attributes match the selected filter.")
        st.stop()
    
    # Display attributes
    st.markdown("---")
    st.subheader(f"📋 Common Attributes ({len(filtered_attrs)})")
    
    # Attribute selection dropdown
    attr_names = sorted(filtered_attrs.keys())
    selected_attr = st.selectbox(
        "🔍 Select attribute name:",
        ["All"] + attr_names,
        key="attr_selector"
    )
    
    # Filter by selected attribute
    if selected_attr and selected_attr != "All":
        filtered_attrs = {selected_attr: filtered_attrs[selected_attr]}
    
    if not filtered_attrs:
        st.info("No attributes to display.")
        st.stop()
    
    # Display each attribute
    for attr_name, (client_attr, product_attr, is_exact_match, differences) in filtered_attrs.items():
        with st.expander(
            f"{'✅' if is_exact_match else '⚠️'} **{attr_name}** {'(Exact Match)' if is_exact_match else f'({len(differences)} difference(s))'}",
            expanded=not is_exact_match
        ):
            if is_exact_match:
                st.success("These attributes are identical (excluding dashboard_identifier)")
                st.json(client_attr)
            else:
                # Show differences
                st.error(f"**Found {len(differences)} difference(s):**")
                
                # Display differences in a structured way
                for diff in differences:
                    st.markdown(f"- `{diff}`")
                
                # Side by side comparison
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**📄 Client Attribute:**")
                    st.json(client_attr)
                
                with col2:
                    st.markdown("**📄 Product Attribute:**")
                    st.json(product_attr)
                
                # Detailed key-by-key comparison
                st.markdown("**🔍 Key-by-Key Comparison:**")
                
                # Get all keys (excluding dashboard_identifier)
                client_keys = {k: v for k, v in client_attr.items() if k != 'dashboard_identifier'}
                product_keys = {k: v for k, v in product_attr.items() if k != 'dashboard_identifier'}
                all_keys = set(client_keys.keys()) | set(product_keys.keys())
                
                comparison_data = []
                for key in sorted(all_keys):
                    client_val = client_keys.get(key, "❌ Missing")
                    product_val = product_keys.get(key, "❌ Missing")
                    
                    if key not in client_keys:
                        status = "Missing in Client"
                    elif key not in product_keys:
                        status = "Missing in Product"
                    elif client_val == product_val:
                        status = "✅ Match"
                    else:
                        status = "⚠️ Different"
                    
                    comparison_data.append({
                        "Key": key,
                        "Client Value": format_json_value(client_val) if client_val != "❌ Missing" else client_val,
                        "Product Value": format_json_value(product_val) if product_val != "❌ Missing" else product_val,
                        "Status": status
                    })
                
                st.dataframe(comparison_data, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()

