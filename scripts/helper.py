import os
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from logger import logger

def load_json(file_path):
    """Load JSON data from a file."""
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {os.path.relpath(file_path)}")
    with open(file_path, 'r') as f:
        return json.load(f)

def save_json(data, file_path):
    """Save JSON data to a file."""
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4)
    logger.info(f"Saved JSON data to {os.path.relpath(file_path)}")

def load_data_json(output_dir):
    """Load the data.json file."""
    data_json_path = output_dir / "data.json"
    if not data_json_path.exists():
        raise FileNotFoundError(f"data.json not found in {os.path.relpath(data_json_path)}")
    with open(data_json_path, 'r') as f:
        return json.load(f), data_json_path

def save_data_json(data, data_json_path):
    """Save the updated data.json file."""
    with open(data_json_path, 'w') as f:
        json.dump(data, f, indent=4)
    logger.info(f"Updated data.json saved at {os.path.relpath(data_json_path)}")

def parse_xml(file_path):
    """Parse an XML file and return the root element."""
    if not file_path.exists():
        raise FileNotFoundError(f"XML file not found: {os.path.relpath(file_path)}")
    return ET.parse(file_path).getroot()

def extract_stats(item, item_type, item_stat_mapping, item_transformations, data):
    """Extract and transform stats for the given item_type, ensuring all stats are integers."""
    # Combine default stats with specific stats for the item_type
    stats_to_extract = item_stat_mapping.get("default", []) + item_stat_mapping.get(item_type, [])
    raw_stats = {stat: item.get(stat) for stat in stats_to_extract if item.get(stat) is not None}

    # Convert stats to integers where possible
    int_stats = {}
    for stat, value in raw_stats.items():
        try:
            float_value = float(value)  # Convert to float first
            # If the float value is a whole number, store it as an int; otherwise, keep it as a float
            int_stats[stat] = int(float_value) if float_value.is_integer() else float_value
        except ValueError:
            logger.warning(f"Failed to convert stat '{stat}' with value '{value}' to a number. Skipping...")
            continue

    # Apply transformations
    transformed_stats = apply_transformations(int_stats, item_transformations, data)

    # Combine raw stats with transformed stats
    return {**int_stats, **transformed_stats}

def extract_attr(item, item_type, item_attr_mapping, attr_transform, data):
    """Extract consistent attributes shared across all items and specific attributes for the given item_type."""
    # Combine default attributes with specific attributes for the item_type
    attrs_to_extract = item_attr_mapping.get("default", []) + item_attr_mapping.get(item_type, [])
    raw_attrs = {attr: item.get(attr) for attr in attrs_to_extract if item.get(attr) is not None}

    # Apply transformations
    transformed_attrs = apply_transformations(raw_attrs, attr_transform, data)

    # Remove original attributes that were transformed
    for original_attr, (required_attrs, _) in attr_transform.items():
        for required_attr in required_attrs:
            if required_attr in raw_attrs:
                raw_attrs.pop(required_attr)

    # Combine raw attributes with transformed attributes
    return {**raw_attrs, **transformed_attrs}

def apply_transformations(attributes, transformations, data):
    """Apply transformations to the extracted attributes."""
    transformed = {}
    for key, (required_attrs, formula) in transformations.items():
        # Check if all required attributes are present
        if all(attr in attributes for attr in required_attrs):
            try:
                # Apply the formula, passing the data dictionary
                result = formula(attributes, data)
                if isinstance(result, dict):
                    # If the result is a dictionary, merge it into the transformed attributes
                    transformed.update(result)
                else:
                    # Otherwise, store the result as a single attribute
                    transformed[key] = result
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to apply transformation for '{key}': {e}")
                continue
    return transformed

def should_filter_item(item):
    """Determine if an item should be filtered out."""
    icon_id = item.get("IconId", "").lower()
    ui_info = item.get("UIInfo", "").lower()
    return icon_id in {"trafficcone", "trafficcone"} or ui_info == "ui_in_warning"

def get_subcategory(item_type):
    """Determine the subcategory for an item."""
    return (
        "weapons" if item_type in {"MeleeWeapon", "MissileWeapon"} else
        "armors" if item_type == "Armor" else
        "dice" if item_type == "Die" else
        "dice_badges" if item_type == "DiceBadge" else None
    )