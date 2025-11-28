import streamlit as st
import json
import os
from pathlib import Path
import plotly.graph_objects as go
import networkx as nx
from collections import defaultdict
import numpy as np

# Try to import streamlit-agraph for interactive drag-and-drop graph editing
try:
    from streamlit_agraph import agraph, Node, Edge, Config
    HAS_AGRAPH = True
except ImportError:
    HAS_AGRAPH = False

# Page configuration
st.set_page_config(
    page_title="Interactive Graph Editor",
    page_icon="🕸️",
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

def build_agraph_nodes_edges(data):
    """Build nodes and edges for streamlit-agraph"""
    entity_name = list(data.keys())[0]
    entity_data = data[entity_name]
    
    nodes = []
    edges = []
    node_mapping = {}  # Map node IDs to category info
    
    # Color mapping for sections
    section_colors = {
        'common': '#FF6B6B',
        'entity_specific': '#4ECDC4',
        'source_specific': '#95E1D3',
        'enrichment': '#F38181'
    }
    
    # Add entity node
    entity_node = Node(
        id="entity",
        label=entity_name,
        size=40,
        color="#2C3E50",
        shape="diamond"
    )
    nodes.append(entity_node)
    
    # Add section nodes
    for section_name, categories in entity_data.items():
        section_node = Node(
            id=f"section_{section_name}",
            label=section_name.replace('_', ' ').title(),
            size=30,
            color=section_colors.get(section_name, '#95A5A6'),
            shape="square"
        )
        nodes.append(section_node)
        edges.append(Edge(source="entity", target=f"section_{section_name}"))
        
        # Add category nodes
        for category_name, attributes in categories.items():
            cat_node_id = f"cat_{section_name}_{category_name}"
            cat_node = Node(
                id=cat_node_id,
                label=f"{category_name}\n({len(attributes)} attrs)",
                size=25,
                color=section_colors.get(section_name, '#95A5A6'),
                shape="circle"
            )
            nodes.append(cat_node)
            edges.append(Edge(source=f"section_{section_name}", target=cat_node_id))
            
            # Store mapping
            node_mapping[cat_node_id] = {
                'section': section_name,
                'category': category_name,
                'attributes': attributes
            }
    
    return nodes, edges, node_mapping

def create_plotly_network_graph(data):
    """Create an interactive network graph using Plotly"""
    entity_name = list(data.keys())[0]
    entity_data = data[entity_name]
    
    # Create NetworkX graph
    G = nx.Graph()
    
    # Color mapping
    section_colors = {
        'common': '#FF6B6B',
        'entity_specific': '#4ECDC4',
        'source_specific': '#95E1D3',
        'enrichment': '#F38181'
    }
    
    # Add nodes with positions
    pos = {}
    node_info = {}
    node_colors = []
    node_sizes = []
    node_labels = []
    node_texts = []
    
    # Entity node
    G.add_node('entity', type='entity')
    pos['entity'] = (0, 0)
    node_info['entity'] = {'type': 'entity', 'name': entity_name}
    node_colors.append('#2C3E50')
    node_sizes.append(50)
    node_labels.append(entity_name)
    node_texts.append(f"Entity: {entity_name}")
    
    # Section nodes (arranged in a circle around entity)
    section_nodes = {}
    num_sections = len(entity_data)
    angle_step = 2 * np.pi / num_sections if num_sections > 0 else 0
    
    for idx, (section_name, categories) in enumerate(entity_data.items()):
        angle = idx * angle_step
        x = 2 * np.cos(angle)
        y = 2 * np.sin(angle)
        section_nodes[section_name] = (x, y)
        
        G.add_node(section_name, type='section')
        pos[section_name] = (x, y)
        node_info[section_name] = {'type': 'section', 'name': section_name}
        node_colors.append(section_colors.get(section_name, '#95A5A6'))
        node_sizes.append(35)
        node_labels.append(section_name.replace('_', ' ').title())
        node_texts.append(f"Section: {section_name}")
        
        G.add_edge('entity', section_name)
    
    # Category nodes (arranged around their sections)
    category_info = {}
    
    for section_name, categories in entity_data.items():
        section_pos = section_nodes[section_name]
        num_categories = len(categories)
        cat_angle_step = 2 * np.pi / num_categories if num_categories > 0 else 0
        
        for cat_idx, (category_name, attributes) in enumerate(categories.items()):
            cat_angle = cat_idx * cat_angle_step
            cat_x = section_pos[0] + 1.5 * np.cos(cat_angle)
            cat_y = section_pos[1] + 1.5 * np.sin(cat_angle)
            
            cat_node_id = f"{section_name}::{category_name}"
            G.add_node(cat_node_id, type='category', section=section_name, category=category_name)
            pos[cat_node_id] = (cat_x, cat_y)
            category_info[cat_node_id] = {
                'section': section_name,
                'category': category_name,
                'attributes': attributes
            }
            node_info[cat_node_id] = {
                'type': 'category',
                'section': section_name,
                'category': category_name
            }
            node_colors.append(section_colors.get(section_name, '#95A5A6'))
            node_sizes.append(25)
            node_labels.append(category_name)
            node_texts.append(f"Category: {category_name}<br>Attributes: {len(attributes)}")
            
            G.add_edge(section_name, cat_node_id)
    
    # Get edge coordinates
    edge_x = []
    edge_y = []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
    
    # Create edge trace
    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=2, color='#888'),
        hoverinfo='none',
        mode='lines'
    )
    
    # Get node coordinates
    node_x = [pos[node][0] for node in G.nodes()]
    node_y = [pos[node][1] for node in G.nodes()]
    
    # Create node trace
    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode='markers+text',
        hoverinfo='text',
        text=node_labels,
        textposition="middle center",
        hovertext=node_texts,
        marker=dict(
            size=node_sizes,
            color=node_colors,
            line=dict(width=2, color='white')
        )
    )
    
    # Create figure
    fig = go.Figure(
        data=[edge_trace, node_trace],
        layout=go.Layout(
            title='Interactive Category-Attribute Graph<br><sub>Click category nodes to edit</sub>',
            titlefont_size=16,
            showlegend=False,
            hovermode='closest',
            margin=dict(b=20, l=5, r=5, t=40),
            annotations=[dict(
                text="💡 Tip: Click on category nodes below to edit their attributes",
                showarrow=False,
                xref="paper", yref="paper",
                x=0.005, y=-0.002,
                xanchor="left", yanchor="bottom",
                font=dict(color="#888", size=12)
            )],
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            plot_bgcolor='white',
            height=700,
            clickmode='event+select'
        )
    )
    
    return fig, category_info, node_info

def move_attribute(data, attribute_name, from_section, from_category, to_section, to_category):
    """Move an attribute from one category to another"""
    entity_name = list(data.keys())[0]
    entity_data = data[entity_name]
    
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

def get_all_sections(data):
    """Get all section names"""
    entity_name = list(data.keys())[0]
    return list(data[entity_name].keys())

def main():
    st.title("🕸️ Interactive Graph Editor")
    st.markdown("**Edit categories and attributes directly on the graph**")
    
    # Get list of JSON files
    json_files = [f for f in os.listdir(CATEGORIZED_DIR) if f.endswith('.json')]
    
    if not json_files:
        st.error("No JSON files found in Client/categorized directory")
        return
    
    # File selection
    selected_file = st.sidebar.selectbox("Select File", json_files)
    
    # Load original file
    original_path = CATEGORIZED_DIR / selected_file
    modified_path = MODIFIED_DIR / selected_file
    
    # Check if modified version exists
    has_modified = modified_path.exists()
    
    # Load data
    if has_modified and st.sidebar.checkbox("Load Modified Version", value=False):
        data = load_json_file(modified_path)
        file_source = "modified"
    else:
        data = load_json_file(original_path)
        file_source = "original"
    
    if data is None:
        return
    
    st.sidebar.info(f"Currently viewing: **{file_source}** version")
    
    # Graph type selection
    if HAS_AGRAPH:
        graph_type = st.sidebar.radio(
            "Graph Type",
            ["Interactive (Drag & Drop)", "Static (Plotly)"],
            help="Interactive mode supports drag-and-drop editing"
        )
    else:
        graph_type = "Static (Plotly)"
        st.sidebar.info("💡 Install streamlit-agraph for drag-and-drop: `pip install streamlit-agraph`")
    
    # Initialize session state
    if 'data' not in st.session_state or st.session_state.get('current_file') != selected_file:
        st.session_state.data = json.loads(json.dumps(data))  # Deep copy
        st.session_state.current_file = selected_file
        st.session_state.original_data = json.loads(json.dumps(data))  # Deep copy
        st.session_state.selected_category = None
        st.session_state.selected_node = None
    
    # Update session state if file changed
    if st.session_state.current_file != selected_file:
        st.session_state.data = json.loads(json.dumps(data))
        st.session_state.current_file = selected_file
        st.session_state.original_data = json.loads(json.dumps(data))
        st.session_state.selected_category = None
        st.session_state.selected_node = None
    
    # Sidebar actions
    st.sidebar.markdown("---")
    st.sidebar.subheader("Actions")
    
    if st.sidebar.button("🔄 Revert to Original"):
        st.session_state.data = json.loads(json.dumps(st.session_state.original_data))
        st.session_state.selected_category = None
        st.session_state.selected_node = None
        st.rerun()
    
    if st.sidebar.button("💾 Save to Modified"):
        if save_json_file(modified_path, st.session_state.data):
            st.sidebar.success("Saved to modified directory!")
            st.rerun()
    
    # Display graph based on type
    entity_name = list(st.session_state.data.keys())[0]
    entity_data = st.session_state.data[entity_name]
    
    if graph_type == "Interactive (Drag & Drop)" and HAS_AGRAPH:
        # Use streamlit-agraph for interactive drag-and-drop
        st.subheader("Interactive Graph (Drag nodes to rearrange)")
        
        nodes, edges, node_mapping = build_agraph_nodes_edges(st.session_state.data)
        
        config = Config(
            width=1200,
            height=800,
            directed=False,
            physics=True,
            hierarchical=False,
            nodeHighlightBehavior=True,
            highlightColor="#F7A7A6",
            collapsible=False,
            node={'labelProperty': 'label'},
            link={'labelProperty': 'label', 'renderLabel': False}
        )
        
        # Render graph and get selected node
        selected_node = agraph(nodes=nodes, edges=edges, config=config)
        
        if selected_node:
            st.session_state.selected_node = selected_node
            # Extract category info from selected node
            if selected_node in node_mapping:
                cat_info = node_mapping[selected_node]
                st.session_state.selected_category = f"{cat_info['section']} > {cat_info['category']}"
    else:
        # Use Plotly graph
        st.subheader("Interactive Graph")
        st.markdown("**Click on category nodes in the graph to view and edit their attributes**")
        
        fig, category_info, node_info = create_plotly_network_graph(st.session_state.data)
        
        # Render plotly chart
        st.plotly_chart(fig, use_container_width=True, key="main_graph")
    
    # Category editing interface
    st.markdown("---")
    st.subheader("Edit Category Attributes")
    
    # Get all categories for selection
    all_categories = []
    for section_name, categories in entity_data.items():
        for category_name in categories.keys():
            all_categories.append(f"{section_name} > {category_name}")
    
    if all_categories:
        # Category selector (pre-select if node was clicked)
        default_idx = 0
        if st.session_state.selected_category and st.session_state.selected_category in all_categories:
            default_idx = all_categories.index(st.session_state.selected_category)
        
        selected_category_path = st.selectbox(
            "Select Category to Edit",
            options=all_categories,
            index=default_idx,
            key="category_selector"
        )
        
        if selected_category_path:
            section_name, category_name = selected_category_path.split(" > ", 1)
            attributes = entity_data[section_name][category_name]
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"**Category:** {category_name}")
                st.markdown(f"**Section:** {section_name}")
                st.markdown(f"**Number of Attributes:** {len(attributes)}")
                
                # Display attributes in an editable list
                st.markdown("### Attributes in this Category")
                
                # Create a container for each attribute with move/delete options
                attributes_to_remove = []
                
                for idx, attr in enumerate(attributes):
                    with st.container():
                        attr_col1, attr_col2, attr_col3 = st.columns([3, 1, 1])
                        
                        with attr_col1:
                            st.text(attr)
                        
                        with attr_col2:
                            # Move attribute button
                            if st.button("Move", key=f"move_{idx}_{attr}"):
                                st.session_state[f"move_mode_{attr}"] = True
                        
                        with attr_col3:
                            # Delete attribute button
                            if st.button("Delete", key=f"delete_{idx}_{attr}"):
                                attributes_to_remove.append(attr)
                
                # Handle attribute removal
                if attributes_to_remove:
                    for attr in attributes_to_remove:
                        entity_data[section_name][category_name].remove(attr)
                    if not entity_data[section_name][category_name]:
                        del entity_data[section_name][category_name]
                    st.success(f"Removed {len(attributes_to_remove)} attribute(s)")
                    st.rerun()
                
                # Move attribute interface
                for attr in attributes:
                    if st.session_state.get(f"move_mode_{attr}", False):
                        st.markdown(f"**Moving:** {attr}")
                        
                        move_col1, move_col2, move_col3 = st.columns(3)
                        
                        with move_col1:
                            all_sections = get_all_sections(st.session_state.data)
                            move_section = st.selectbox(
                                "To Section",
                                options=all_sections,
                                index=all_sections.index(section_name) if section_name in all_sections else 0,
                                key=f"move_section_{attr}"
                            )
                        
                        with move_col2:
                            move_categories = list(entity_data[move_section].keys())
                            move_category = st.selectbox(
                                "To Category",
                                options=move_categories,
                                key=f"move_category_{attr}"
                            )
                        
                        with move_col3:
                            if st.button("Confirm Move", key=f"confirm_move_{attr}"):
                                st.session_state.data = move_attribute(
                                    st.session_state.data,
                                    attr,
                                    section_name,
                                    category_name,
                                    move_section,
                                    move_category
                                )
                                st.session_state[f"move_mode_{attr}"] = False
                                st.success(f"Moved '{attr}' to {move_section} > {move_category}")
                                st.rerun()
                            
                            if st.button("Cancel", key=f"cancel_move_{attr}"):
                                st.session_state[f"move_mode_{attr}"] = False
                                st.rerun()
            
            with col2:
                st.markdown("### Quick Actions")
                
                # Add new attribute
                st.markdown("#### Add Attribute")
                new_attr = st.text_input("Attribute Name", key="new_attribute")
                if st.button("➕ Add Attribute"):
                    if new_attr and new_attr not in attributes:
                        entity_data[section_name][category_name].append(new_attr)
                        st.success(f"Added '{new_attr}'")
                        st.rerun()
                    elif new_attr in attributes:
                        st.error("Attribute already exists in this category")
                
                # Rename category
                st.markdown("#### Rename Category")
                new_category_name = st.text_input("New Name", value=category_name, key="rename_category")
                if st.button("✏️ Rename"):
                    if new_category_name and new_category_name != category_name:
                        if new_category_name not in entity_data[section_name]:
                            entity_data[section_name][new_category_name] = entity_data[section_name][category_name]
                            del entity_data[section_name][category_name]
                            st.success(f"Renamed to '{new_category_name}'")
                            st.rerun()
                        else:
                            st.error("Category name already exists")
                
                # Create new category in same section
                st.markdown("#### Create New Category")
                new_cat_name = st.text_input("Category Name", key="new_category")
                if st.button("➕ Create"):
                    if new_cat_name:
                        if new_cat_name not in entity_data[section_name]:
                            entity_data[section_name][new_cat_name] = []
                            st.success(f"Created category '{new_cat_name}'")
                            st.rerun()
                        else:
                            st.error("Category already exists")
    
    # Statistics
    st.markdown("---")
    st.subheader("Statistics")
    
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

if __name__ == "__main__":
    main()
