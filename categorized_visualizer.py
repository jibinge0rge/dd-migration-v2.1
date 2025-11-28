import streamlit as st
import json
import os
from pathlib import Path
import plotly.graph_objects as go
import plotly.express as px
from collections import defaultdict
import shutil

# Page configuration
st.set_page_config(
    page_title="Categorized Attributes Visualizer",
    page_icon="📊",
    layout="wide"
)

# Constants
CATEGORIZED_DIR = Path("Client/categorized")
MODIFIED_DIR = Path("Client/categorized/modified")

# Ensure modified directory exists
MODIFIED_DIR.mkdir(parents=True, exist_ok=True)

def load_json_file(file_path):
    """Load JSON file and return data"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Error loading file: {e}")
        return None

def save_json_file(file_path, data):
    """Save data to JSON file"""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        st.error(f"Error saving file: {e}")
        return False

def get_all_attributes_by_category(data):
    """Extract all attributes organized by category"""
    result = {}
    entity_name = list(data.keys())[0]
    entity_data = data[entity_name]
    
    for section_name, categories in entity_data.items():
        for category_name, attributes in categories.items():
            full_category = f"{section_name} > {category_name}"
            result[full_category] = attributes
    return result, entity_name

def create_sunburst_chart(data):
    """Create a sunburst chart visualization"""
    entity_name = list(data.keys())[0]
    entity_data = data[entity_name]
    
    # Build hierarchical data
    labels = [entity_name]
    parents = [""]
    values = [0]
    
    for section_name, categories in entity_data.items():
        labels.append(section_name)
        parents.append(entity_name)
        section_total = 0
        
        for category_name, attributes in categories.items():
            labels.append(category_name)
            parents.append(section_name)
            attr_count = len(attributes)
            values.append(attr_count)
            section_total += attr_count
            
            # Add individual attributes
            for attr in attributes:
                labels.append(attr)
                parents.append(category_name)
                values.append(1)
        
        values[labels.index(section_name)] = section_total
    
    values[0] = sum(v for i, v in enumerate(values) if parents[i] == entity_name)
    
    fig = go.Figure(go.Sunburst(
        labels=labels,
        parents=parents,
        values=values,
        branchvalues="total",
        hovertemplate='<b>%{label}</b><br>Attributes: %{value}<extra></extra>',
    ))
    
    fig.update_layout(
        title="Category Hierarchy Visualization",
        height=800,
        margin=dict(t=50, l=0, r=0, b=0)
    )
    
    return fig

def create_bar_chart(data):
    """Create a bar chart showing attribute counts per category"""
    entity_name = list(data.keys())[0]
    entity_data = data[entity_name]
    
    categories = []
    counts = []
    sections = []
    
    for section_name, categories_dict in entity_data.items():
        for category_name, attributes in categories_dict.items():
            categories.append(category_name)
            counts.append(len(attributes))
            sections.append(section_name)
    
    fig = px.bar(
        x=categories,
        y=counts,
        color=sections,
        title="Attributes per Category",
        labels={"x": "Category", "y": "Number of Attributes", "color": "Section"},
        height=600
    )
    fig.update_xaxes(tickangle=45)
    fig.update_layout(showlegend=True)
    
    return fig

def get_all_categories(data):
    """Get all unique category names across sections"""
    entity_name = list(data.keys())[0]
    entity_data = data[entity_name]
    categories = set()
    for section_name, categories_dict in entity_data.items():
        categories.update(categories_dict.keys())
    return sorted(list(categories))

def get_all_sections(data):
    """Get all section names"""
    entity_name = list(data.keys())[0]
    return list(data[entity_name].keys())

def move_attribute(data, attribute_name, from_category_path, to_section, to_category):
    """Move an attribute from one category to another"""
    entity_name = list(data.keys())[0]
    entity_data = data[entity_name]
    
    # Parse from_category_path (format: "section > category")
    from_section, from_category = from_category_path.split(" > ", 1)
    
    # Remove from old location
    if from_section in entity_data and from_category in entity_data[from_section]:
        if attribute_name in entity_data[from_section][from_category]:
            entity_data[from_section][from_category].remove(attribute_name)
            # Remove empty category
            if not entity_data[from_section][from_category]:
                del entity_data[from_section][from_category]
    
    # Add to new location
    if to_section not in entity_data:
        entity_data[to_section] = {}
    if to_category not in entity_data[to_section]:
        entity_data[to_section][to_category] = []
    
    if attribute_name not in entity_data[to_section][to_category]:
        entity_data[to_section][to_category].append(attribute_name)
    
    return data

def get_original_file_path(filename):
    """Get path to original file"""
    return CATEGORIZED_DIR / filename

def get_modified_file_path(filename):
    """Get path to modified file"""
    return MODIFIED_DIR / filename

def main():
    st.title("📊 Categorized Attributes Visualizer")
    st.markdown("Visualize and edit categorized attribute configurations")
    
    # Get list of JSON files
    json_files = [f for f in os.listdir(CATEGORIZED_DIR) if f.endswith('.json')]
    
    if not json_files:
        st.error("No JSON files found in Client/categorized directory")
        return
    
    # File selection
    selected_file = st.sidebar.selectbox("Select File", json_files)
    
    # Load original file
    original_path = get_original_file_path(selected_file)
    modified_path = get_modified_file_path(selected_file)
    
    # Check if modified version exists
    has_modified = modified_path.exists()
    
    # Load data (prefer modified if exists, otherwise original)
    if has_modified and st.sidebar.checkbox("Load Modified Version", value=False):
        data = load_json_file(modified_path)
        file_source = "modified"
    else:
        data = load_json_file(original_path)
        file_source = "original"
    
    if data is None:
        return
    
    st.sidebar.info(f"Currently viewing: **{file_source}** version")
    
    # Initialize session state
    if 'data' not in st.session_state or st.session_state.get('current_file') != selected_file:
        st.session_state.data = json.loads(json.dumps(data))  # Deep copy
        st.session_state.current_file = selected_file
        st.session_state.original_data = json.loads(json.dumps(data))  # Deep copy
    
    # Update session state if file changed
    if st.session_state.current_file != selected_file:
        st.session_state.data = json.loads(json.dumps(data))
        st.session_state.current_file = selected_file
        st.session_state.original_data = json.loads(json.dumps(data))
    
    # Sidebar actions
    st.sidebar.markdown("---")
    st.sidebar.subheader("Actions")
    
    if st.sidebar.button("🔄 Revert to Original"):
        st.session_state.data = json.loads(json.dumps(st.session_state.original_data))
        st.rerun()
    
    if st.sidebar.button("💾 Save to Modified"):
        if save_json_file(modified_path, st.session_state.data):
            st.sidebar.success("Saved to modified directory!")
            st.rerun()
    
    # Main content tabs
    tab1, tab2, tab3 = st.tabs(["📈 Visualization", "✏️ Edit Categories", "📋 View Data"])
    
    with tab1:
        st.header("Visualization")
        
        viz_type = st.radio("Visualization Type", ["Sunburst Chart", "Bar Chart"], horizontal=True)
        
        if viz_type == "Sunburst Chart":
            fig = create_sunburst_chart(st.session_state.data)
            st.plotly_chart(fig, use_container_width=True)
        else:
            fig = create_bar_chart(st.session_state.data)
            st.plotly_chart(fig, use_container_width=True)
        
        # Statistics
        entity_name = list(st.session_state.data.keys())[0]
        entity_data = st.session_state.data[entity_name]
        
        col1, col2, col3, col4 = st.columns(4)
        
        total_attributes = sum(
            len(attrs) 
            for section in entity_data.values() 
            for attrs in section.values()
        )
        total_categories = sum(
            len(categories) 
            for categories in entity_data.values()
        )
        total_sections = len(entity_data)
        
        with col1:
            st.metric("Total Attributes", total_attributes)
        with col2:
            st.metric("Total Categories", total_categories)
        with col3:
            st.metric("Total Sections", total_sections)
        with col4:
            st.metric("Entity", entity_name)
    
    with tab2:
        st.header("Edit Categories")
        
        entity_name = list(st.session_state.data.keys())[0]
        entity_data = st.session_state.data[entity_name]
        
        # Get all categories with their full paths
        all_categories = {}
        for section_name, categories in entity_data.items():
            for category_name, attributes in categories.items():
                full_path = f"{section_name} > {category_name}"
                all_categories[full_path] = {
                    'section': section_name,
                    'category': category_name,
                    'attributes': attributes
                }
        
        # Attribute movement interface
        st.subheader("Move Attributes Between Categories")
        
        if all_categories:
            # Source category selection
            source_category = st.selectbox(
                "Select Source Category",
                options=list(all_categories.keys())
            )
            
            if source_category:
                source_info = all_categories[source_category]
                source_attributes = source_info['attributes']
                
                if source_attributes:
                    # Attribute selection
                    selected_attribute = st.selectbox(
                        "Select Attribute to Move",
                        options=source_attributes
                    )
                    
                    # Destination selection
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        all_sections = get_all_sections(st.session_state.data)
                        dest_section = st.selectbox(
                            "Destination Section",
                            options=all_sections,
                            index=all_sections.index(source_info['section']) if source_info['section'] in all_sections else 0
                        )
                    
                    with col2:
                        # Get categories in selected section
                        dest_categories = list(entity_data[dest_section].keys())
                        # Allow creating new category
                        new_category_name = st.text_input("Or Create New Category")
                        if new_category_name:
                            dest_category = new_category_name
                        else:
                            dest_category = st.selectbox(
                                "Destination Category",
                                options=dest_categories,
                                index=0 if dest_categories else None
                            )
                    
                    if st.button("➡️ Move Attribute"):
                        if selected_attribute and dest_section and dest_category:
                            st.session_state.data = move_attribute(
                                st.session_state.data,
                                selected_attribute,
                                source_category,
                                dest_section,
                                dest_category
                            )
                            st.success(f"Moved '{selected_attribute}' to {dest_section} > {dest_category}")
                            st.rerun()
                else:
                    st.info("This category has no attributes to move.")
        
        # Category management
        st.subheader("Category Management")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Rename Category")
            rename_section = st.selectbox(
                "Select Section",
                options=get_all_sections(st.session_state.data),
                key="rename_section"
            )
            
            if rename_section:
                rename_categories = list(entity_data[rename_section].keys())
                rename_category = st.selectbox(
                    "Select Category to Rename",
                    options=rename_categories,
                    key="rename_category"
                )
                
                new_category_name = st.text_input("New Category Name", key="new_category_name")
                
                if st.button("✏️ Rename Category") and new_category_name:
                    if new_category_name not in entity_data[rename_section]:
                        entity_data[rename_section][new_category_name] = entity_data[rename_section][rename_category]
                        del entity_data[rename_section][rename_category]
                        st.success(f"Renamed category to '{new_category_name}'")
                        st.rerun()
                    else:
                        st.error("Category name already exists in this section!")
        
        with col2:
            st.markdown("### Delete Category")
            delete_section = st.selectbox(
                "Select Section",
                options=get_all_sections(st.session_state.data),
                key="delete_section"
            )
            
            if delete_section:
                delete_categories = list(entity_data[delete_section].keys())
                delete_category = st.selectbox(
                    "Select Category to Delete",
                    options=delete_categories,
                    key="delete_category"
                )
                
                if st.button("🗑️ Delete Category", type="primary"):
                    if delete_category in entity_data[delete_section]:
                        # Move attributes to a default category or delete them
                        attributes_to_move = entity_data[delete_section][delete_category]
                        if attributes_to_move:
                            st.warning(f"This category has {len(attributes_to_move)} attributes. They will be moved to 'Uncategorized'.")
                            if 'Uncategorized' not in entity_data[delete_section]:
                                entity_data[delete_section]['Uncategorized'] = []
                            entity_data[delete_section]['Uncategorized'].extend(attributes_to_move)
                        
                        del entity_data[delete_section][delete_category]
                        st.success(f"Deleted category '{delete_category}'")
                        st.rerun()
    
    with tab3:
        st.header("View Data Structure")
        
        entity_name = list(st.session_state.data.keys())[0]
        entity_data = st.session_state.data[entity_name]
        
        # Expandable sections
        for section_name, categories in entity_data.items():
            with st.expander(f"📁 {section_name} ({len(categories)} categories)"):
                for category_name, attributes in categories.items():
                    st.markdown(f"**{category_name}** ({len(attributes)} attributes)")
                    st.code(", ".join(attributes), language=None)
        
        # Download JSON
        st.markdown("---")
        json_str = json.dumps(st.session_state.data, indent=4, ensure_ascii=False)
        st.download_button(
            label="📥 Download Current Configuration (JSON)",
            data=json_str,
            file_name=selected_file,
            mime="application/json"
        )

if __name__ == "__main__":
    main()

