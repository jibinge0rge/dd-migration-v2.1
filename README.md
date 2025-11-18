# Data Dictionary Migration Tool v2.1

A Python tool for converting and migrating data dictionary configurations from Client to DD v2.1 format. This tool compares Client and Product configurations, removes common keys, and handles attribute-level comparisons with interactive confirmation.

## Features

- **Automatic Common Key Removal**: Identifies and removes common parent keys between Client and Product configs (except `attributes`)
- **Attribute Comparison**: Compares attributes between Client and Product configs, ignoring `dashboard_identifier` differences
- **Interactive Confirmation**: Provides two processing modes:
  - Process entire categories at once
  - Process attributes one by one
- **VRA/CCM Cleanup**: Automatically removes VRA and CCM subkeys from `dashboard_identifier` in attributes
- **Comprehensive Logging**: Creates detailed log files for each processed file, tracking all user actions and script operations
- **Menu-Driven Interface**: Easy-to-use menu system for processing files

## Requirements

- Python 3.6 or higher
- Standard library only (no external dependencies for conversion script)
- Streamlit (for comparison web app - optional)

## Project Structure

```
Dictionary/
├── Client/                          # Client configuration files
│   ├── *__data_dictionary.json      # Client data dictionary files
│   └── DD v2.1/                     # Output directory (created automatically)
│       ├── *__data_dictionary.json  # Converted output files
│       └── *.log                    # Log files for each conversion
├── Product/                         # Product configuration files
│   └── *__data_dictionary.json      # Product data dictionary files
├── convert_to_dd_v2.1.py            # Main conversion script
├── compare_configs.py                # Streamlit web app for comparing configs
├── requirements.txt                  # Python dependencies
└── README.md                        # This file
```

## Usage

### Running the Script

```bash
python convert_to_dd_v2.1.py
```

### Menu Options

1. **Process all files**: Converts all `*__data_dictionary.json` files in the Client folder
2. **Process one file**: Select a specific file from a list to convert
3. **Exit**: Quit the application

### Processing Flow

1. **File Loading**: Loads Client and corresponding Product configuration files
2. **Common Key Detection**: Finds common parent keys (excluding `attributes`)
3. **Common Key Removal**: Removes common keys from Client config
4. **VRA/CCM Cleanup**: Removes VRA and CCM from `dashboard_identifier` in attributes
5. **Attribute Comparison**: Compares common attributes between Client and Product:
   - **Category 1 (Exact Matches)**: Attributes identical in both (excluding `dashboard_identifier`)
   - **Category 2 (Different)**: Attributes with differences between Client and Product
6. **Interactive Confirmation**: Prompts for user confirmation before removing attributes
7. **Output Generation**: Saves converted file to `Client/DD v2.1/` directory

### Processing Modes

When attributes require confirmation, you can choose:

- **Mode 1 (Whole Category)**: Process all attributes in a category with a single y/n response
- **Mode 2 (One by One)**: Review and confirm each attribute individually

### Log Files

Each conversion creates a detailed log file (`{filename}.log`) in the output directory containing:
- Timestamped entries for all actions
- User responses and selections
- Script operations (removals, keeps, modifications)
- Summary of changes

## Key Features Explained

### Common Key Removal

The script identifies top-level keys that exist in both Client and Product configs (except `attributes`) and removes them from the Client output. This keeps only Client-specific keys.

### Attribute Comparison

Attributes are compared while ignoring `dashboard_identifier` differences:
- **Exact Match**: All other keys and values are identical → Can be removed (Category 1)
- **Different**: Has differences in other keys/values → Needs review (Category 2)

### Dashboard Identifier Cleanup

Automatically removes `VRA` and `CCM` subkeys from `dashboard_identifier` in all attributes, as these are dashboard-specific configurations.

## Example Workflow

```
1. Run: python convert_to_dd_v2.1.py
2. Select: "1. Process all files"
3. For each file:
   - Review common keys found
   - Review attributes requiring confirmation
   - Select processing mode (1 or 2)
   - Confirm removals (y/n)
4. Check output in Client/DD v2.1/
5. Review log files for detailed audit trail
```

## Web Application (Streamlit)

A web-based comparison tool is available to visually compare Client and Product configurations.

### Running the Streamlit App

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run compare_configs.py
```

### Features

- **Visual Comparison**: Side-by-side view of Client and Product attributes
- **Common Attributes Only**: Shows only attributes that exist in both configs
- **Difference Highlighting**: Clearly marks exact matches vs. differences
- **Detailed Diff View**: Shows exact key-by-key differences
- **Search Functionality**: Search for specific attributes
- **Filtering Options**: View all, exact matches only, or different attributes only
- **Interactive Interface**: Expandable sections for each attribute

### Usage

1. Select a data dictionary file from the dropdown
2. View summary statistics (total common, exact matches, differences)
3. Filter by match type or search for specific attributes
4. Expand any attribute to see detailed comparison
5. Review key-by-key differences in tabular format

## Output

- **Converted Files**: Saved to `Client/DD v2.1/` with same filenames
- **Log Files**: One `.log` file per converted file with complete action history

## Notes

- The script creates the output directory automatically if it doesn't exist
- Log files are overwritten on each run (fresh log for each conversion)
- Original Client files are not modified
- If a Product file doesn't exist, the script will skip comparison but still process the Client file

## Troubleshooting

- **No Product file found**: The script will continue but skip attribute comparison
- **Keyboard interrupt**: Press Ctrl+C to cancel - all attributes will be kept
- **Invalid input**: The script will prompt again for valid input

## License

This tool is provided as-is for internal use.

