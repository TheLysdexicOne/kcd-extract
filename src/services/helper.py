import os
import json
from pathlib import Path
from utils.logger import logger
from functools import lru_cache
from typing import Dict, List, Union, Tuple, Callable
import xml.etree.ElementTree as ET

def ensure_file_exists(file_dir, description="File"):
    """Ensure that a file exists, or raise a FileNotFoundError."""
    if not file_dir.exists():
        raise FileNotFoundError(f"{description} not found: {os.path.relpath(file_dir)}")

def load_json(file_dir):
    """Load JSON data from a file."""
    if not file_dir.exists():
        raise FileNotFoundError(f"File not found: {os.path.relpath(file_dir)}")
    with open(file_dir, 'r') as f:
        return json.load(f)

def save_json(data, file_dir):
    """Save JSON data to a file."""
    with open(file_dir, 'w') as f:
        json.dump(data, f, indent=4)
    logger.info(f"Saved JSON data to {os.path.relpath(file_dir)}")

def load_data_json(output_dir):
    """Load the data.json file."""
    data_json_file = output_dir / "data.json"
    ensure_file_exists(data_json_file, "data.json")
    with open(data_json_file, 'r') as f:
        return json.load(f), data_json_file

def save_data_json(data, data_json_file):
    """Save the updated data.json file."""
    with open(data_json_file, 'w') as f:
        json.dump(data, f, indent=4)
    logger.info(f"Updated data.json saved at {os.path.relpath(data_json_file)}")

@lru_cache(maxsize=None)
def parse_xml(file_path):
    """Parse an XML file and return the root element."""
    ensure_file_exists(file_path, "XML file")
    return ET.parse(file_path).getroot()

def extract_data(
    item: ET.Element,
    item_type: str,
    mapping: Dict[str, List[str]],
    transformations: Dict[str, tuple],
    data: dict
) -> Dict[str, Union[str, int, float]]:
    """Extract and transform data (attributes or stats) for the given item_type."""
    to_extract = mapping.get("default", []) + mapping.get(item_type, [])
    raw_data: Dict[str, Union[str, int, float]] = {}  # Explicitly annotate type

    # Extract raw data and convert numeric values
    for key in to_extract:
        value = item.get(key)
        if value is not None:
            try:
                # Convert to float first, then to int if it's a whole number
                numeric_value = float(value)
                raw_data[key] = int(numeric_value) if numeric_value.is_integer() else numeric_value
            except ValueError:
                # Keep as string if it cannot be converted to a number
                raw_data[key] = value

    logger.debug(f"Raw data before transformations: {raw_data}")

    # Apply transformations
    transformed_data = apply_transformations(raw_data, transformations, data)

    # Remove original attributes that were transformed
    for _, (required_keys, _) in transformations.items():
        for required_key in required_keys:
            raw_data.pop(required_key, None)

    # Combine raw data with transformed data
    return {**raw_data, **transformed_data}

def apply_transformations(
    attributes: Dict[str, Union[str, int, float]],
    transformations: Dict[str, Tuple[List[str], Callable[[Dict[str, Union[str, int, float]], dict], Union[dict, int, float]]]],
    data: dict
) -> Dict[str, Union[str, int, float]]:
    """Apply transformations to the extracted attributes."""
    transformed = {}
    for key, (required_attrs, formula) in transformations.items():
        # Check if all required attributes are present
        if any(attr in attributes for attr in required_attrs):  # Adjusted to check if any required attribute exists
            try:
                # Apply the formula, passing the data dictionary
                result = formula(attributes, data)
                if isinstance(result, dict):
                    # If the result is a dictionary, merge it into the transformed attributes
                    transformed.update(result)
                else:
                    # Otherwise, store the result as a single attribute
                    transformed[key] = result
                logger.debug(f"Transformation applied for '{key}': {result}")
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to apply transformation for '{key}': {e}")
                continue
        else:
            logger.debug(f"Skipping transformation for '{key}': Missing required attributes {required_attrs}")
    return transformed

def should_filter_item(item):
    """Determine if an item should be filtered out."""
    icon_id = item.get("IconId", "").lower()
    ui_info = item.get("UIInfo", "").lower()
    return icon_id in {"trafficcone", "trafficcone"} or ui_info == "ui_in_warning"

# Define the subcategory mapping at the module level
subcategory_mapping = {
    "MeleeWeapon": "weapons",
    "MissileWeapon": "weapons",
    "Armor": "armors",
    "Die": "dice",
    "DiceBadge": "dice_badges"
}

def get_subcategory(item_type: str) -> Union[str, None]:
    """Determine the subcategory for an item."""
    return subcategory_mapping.get(item_type)