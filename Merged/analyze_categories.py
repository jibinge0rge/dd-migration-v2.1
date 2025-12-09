import json

# Read the JSON file (same directory)
with open('tp-ddv2_1.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Initialize the result structure
result = {}

# List of entities to process
entities_to_process = ['Host', 'Vulnerability', 'Person', 'Identity']

# Iterate through each entity in config
for entity_key, entity_data in data.get('config', {}).items():
    # Only process the specified entities
    if entity_key not in entities_to_process:
        continue
    
    # Initialize entity structure - will dynamically add groups
    entity_result = {}
    
    # Get attributes for this entity
    attributes = entity_data.get('attributes', {})
    
    # Iterate through each attribute
    for attr_name, attr_data in attributes.items():
        # Only include attributes that do NOT have a "category" field
        if 'category' not in attr_data:
            # Get the group value (default to 'common' if not present)
            group = attr_data.get('group', 'common')
            
            # Initialize the group list if it doesn't exist
            if group not in entity_result:
                entity_result[group] = []
            
            # Add attribute name to the appropriate group
            entity_result[group].append(attr_name)
    
    # Sort the lists for consistency
    for group in entity_result:
        entity_result[group].sort()
    
    # Only add entity if it has at least one attribute without category
    if any(entity_result.values()):
        result[entity_key] = entity_result

# Write the result to a new JSON file (same directory)
with open('grouped_by_category.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

print("Analysis complete! Output saved to 'grouped_by_category.json'")
print(f"\nFound {len(result)} entities with attributes without category:")
for entity in result.keys():
    print(f"  - {entity}:")
    for group, fields in result[entity].items():
        print(f"      {group}: {len(fields)} attributes")

