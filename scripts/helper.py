import json
import xml.etree.ElementTree as ET
from pathlib import Path
from logger import logger

def load_json(file_path):
    """Load JSON data from a file."""
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    with open(file_path, 'r') as f:
        return json.load(f)

def save_json(data, file_path):
    """Save JSON data to a file."""
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4)
    logger.info(f"Saved JSON data to {file_path}")

def load_data_json(output_dir):
    """Load the data.json file."""
    data_json_path = output_dir / "data.json"
    if not data_json_path.exists():
        raise FileNotFoundError(f"data.json not found in {data_json_path}")
    with open(data_json_path, 'r') as f:
        return json.load(f), data_json_path

def save_data_json(data, data_json_path):
    """Save the updated data.json file."""
    with open(data_json_path, 'w') as f:
        json.dump(data, f, indent=4)
    logger.info(f"Updated data.json saved at {data_json_path}")

def parse_xml(file_path):
    """Parse an XML file and return the root element."""
    if not file_path.exists():
        raise FileNotFoundError(f"XML file not found: {file_path}")
    return ET.parse(file_path).getroot()

def extract_stats(item, item_type, item_stat_mapping):
    """Extract only the required attributes for the given item_type."""
    stats_to_extract = item_stat_mapping.get(item_type, item_stat_mapping["default"])
    return {stat: item.get(stat) for stat in stats_to_extract if item.get(stat) is not None}

def extract_attr(item, item_attr_mapping):
    """Extract consistent attributes shared across all items."""
    return {attr: item.get(attr) for attr in item_attr_mapping if item.get(attr) is not None}