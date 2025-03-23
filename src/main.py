import os
import json
from pathlib import Path
from typing import Dict, List
import xml.etree.ElementTree as ET
from collections import OrderedDict
from utils.logger import logger
from services.data_extract import data_extract
from services.helper import load_json, save_json, parse_xml, load_data_json, save_data_json, ensure_file_exists, should_filter_item, extract_data, get_subcategory
from templates.data_json_mappings import construct_item_data, item_stats_mapping, item_attr_mapping, stat_transform, attr_transform

def get_version_info(data_dir: Path) -> str:
    """
    Calculate the version from version.json, check it against latest_version.json, and create the directory.
    """
    version_file = data_dir / "version.json"
    latest_version_file = data_dir / "latest_version.json"

    # Ensure version.json exists
    if not version_file.exists():
        raise FileNotFoundError(f"Version file not found: {version_file}")

    # Load version.json
    version_data = load_json(version_file)

    # Extract and format the new version
    new_version = version_data['Preset']['Branch']['Name'].replace('release_', '').replace('_', '.')
    new_version_dir = data_dir / new_version

    # Check if latest_version.json exists and compare versions
    if latest_version_file.exists():
        latest_version_data = load_json(latest_version_file)
        if latest_version_data['Branch']['version'] == new_version:
            logger.info(f"Version {new_version} matches the latest version. No changes required.")
            return new_version

    # Update latest_version.json and create the new version directory
    latest_version_data = {
        "Assembly": version_data['Assembly'],
        "Branch": {
            **version_data['Preset']['Branch'],
            "version": new_version
        }
    }
    save_json(latest_version_data, latest_version_file)
    new_version_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"New version {new_version} detected. Created directory: {new_version_dir}")
    return new_version

def export_versioned_data(kcd2_xmls: Dict[str, str], kcd2_icons: Dict[str, str], output_dir: Path) -> None:
    """
    Save kcd2_xmls and kcd2_icons to the versioned output directory.
    """
    kcd2_xmls_file = output_dir / "kcd2_xmls.json"
    kcd2_icons_file = output_dir / "kcd2_icons.json"

    # Save XMLs and icons data
    for data, file, label in [(kcd2_xmls, kcd2_xmls_file, "kcd2_xmls"), (kcd2_icons, kcd2_icons_file, "kcd2_icons")]:
        with open(file, 'w') as f:
            json.dump(data, f, indent=4)
        logger.info(f"Saved {label} to {os.path.relpath(file)}")

def initialize_data_json(version: str, output_dir: Path) -> Path:
    """
    Create a new data.json file using the base_data.json template.
    """
    logger.info("Initializing a new data.json file from base_data.json...")

    # Path to the base_data.json template
    base_data_file = Path(__file__).resolve().parent / "templates/base_data.json"

    # Ensure the base template exists
    if not base_data_file.exists():
        raise FileNotFoundError(f"Base data.json template not found: {base_data_file}")

    # Load the base template
    with open(base_data_file, 'r') as f:
        base_data = json.load(f)

    # Update the version in the data structure
    base_data["version"]["base"] = version

    # Save the new data.json file
    data_json_file = output_dir / "data.json"
    with open(data_json_file, 'w') as f:
        json.dump(base_data, f, indent=4)

    logger.info(f"New data.json created at {os.path.relpath(data_json_file)}")
    return data_json_file

def xml_equipment_slot(kcd2_xmls, output_dir):
    """Process equipment slot XML data and populate the Armor item_type in data.json."""
    logger.info("Processing equipment slot XML data...")

    # Parse the equipment_slot.xml file
    equipment_slot_path = Path(kcd2_xmls.get("equipment_slot"))
    root = parse_xml(equipment_slot_path)

    # Extract relevant data for Armor
    armor_types = []
    for slot in root.findall(".//EquipmentSlot"):
        armor_slot = {
            "Id": int(slot.get("Id")),
            "Name": slot.get("Name"),
            "UIBodyPartId": slot.get("UIBodyPartId"),
            "UISlot": slot.get("UISlot"),
            "filters": slot.get("ArmorTypes", "").split() if slot.get("ArmorTypes") else []
        }

        # Add missing filters for specific IDs
        if armor_slot["Name"] == "horse_torso":  # Horse Torso
            armor_slot["filters"].extend(["Caparison", "Harness"])
        elif armor_slot["Name"] == "horse_head":  # Horse Head
            armor_slot["filters"].extend(["Bridle", "Chanfron"])
        elif armor_slot["Name"] == "horse_saddle":  # Horse Saddle
            armor_slot["filters"].extend(["Saddle"])

        # If filters are still empty, append the UISlot value
        if not armor_slot["filters"] and armor_slot["UISlot"]:
            armor_slot["filters"].append(armor_slot["UISlot"])

        # Skip adding the armor slot if UISlot is null
        if not armor_slot["UISlot"]:
            continue

        armor_types.append(armor_slot)

    # Sort armor slots by ID
    armor_types = sorted(armor_types, key=lambda x: x["Id"])

    # Load and update data.json
    data, data_json_path = load_data_json(output_dir)
    data["armor_types"] = armor_types
    save_data_json(data, data_json_path)

def xml_weapon_info(kcd2_xmls, output_dir):
    """Process weapon XML data and populate the Weapons item_type in data.json."""
    logger.info("Processing weapon XML data...")

    # Parse the weapon_class.xml and ammo_class.xml files
    weapon_class_path = Path(kcd2_xmls.get("weapon_class"))
    ammo_class_path = Path(kcd2_xmls.get("ammo_class"))
    weapon_root = parse_xml(weapon_class_path)
    ammo_root = parse_xml(ammo_class_path)

    # Create a mapping of ammo_class_id to ammo_class_name
    ammo_class_mapping = {
        ammo.get("ammo_class_id"): ammo.get("ammo_class_name")
        for ammo in ammo_root.findall(".//ammo_class")
    }

    # Extract MeleeWeaponClass and MissileWeaponClass data
    weapon_types = sorted(
        [
            {
                "id": int(weapon.get("id")),
                "name": weapon.get("name"),
                "type": weapon.tag.replace("Class", ""),
                "skill": weapon.get("skill"),
                "equip_slot": weapon.get("equip_slot"),
                **({"ammo": ammo_class_mapping.get(weapon.get("ammo_class"))} if weapon.tag == "MissileWeaponClass" else {})
            }
            for weapon in weapon_root.findall(".//MeleeWeaponClass") + weapon_root.findall(".//MissileWeaponClass")
        ],
        key=lambda x: x["id"]
    )

    # Load and update data.json
    data, data_json_path = load_data_json(output_dir)
    data["weapon_types"] = weapon_types
    save_data_json(data, data_json_path)

def xml_dice(kcd2_xmls, output_dir):
    """Process dice badge XML data and populate the Dice item_type in data.json."""
    logger.info("Processing dice badge XML data...")

    # Parse the dice_badge_type.xml and dice_badge_subtype.xml files
    dice_badge_type_root = parse_xml(Path(kcd2_xmls.get("dice_badge_type")))
    dice_badge_subtype_root = parse_xml(Path(kcd2_xmls.get("dice_badge_subtype")))

    # Extract dice badge types and subtypes
    dice_badge_types = {
        int(type_.get("dice_badge_type_id")): type_.get("dice_badge_type_name")
        for type_ in dice_badge_type_root.findall(".//dice_badge_type")
    }
    dice_badge_subtypes = {
        int(subtype.get("dice_badge_subtype_id")): subtype.get("dice_badge_subtype_name")
        for subtype in dice_badge_subtype_root.findall(".//dice_badge_subtype")
    }

    # Load and update data.json
    data, data_json_path = load_data_json(output_dir)
    data["dice_badges"]["types"] = dice_badge_types
    data["dice_badges"]["subtypes"] = dice_badge_subtypes
    save_data_json(data, data_json_path)

from collections import OrderedDict  # Add this import at the top of the file
from typing import Dict, List

def xml_items(kcd2_xmls: Dict[str, str], output_dir: Path) -> None:
    """Process item XML data and populate the Items category in data.json."""
    logger.info("Processing item XML data...")

    # Explicitly list the IDs of relevant item XML files
    item_files = ["item", "item_dlc", "item_horse", "item_reward", "item_rewards"]

    # Load existing data.json to get the list of categories and armor_types
    data_json_path = output_dir / "data.json"
    ensure_file_exists(data_json_path, "data.json")

    with open(data_json_path, 'r') as f:
        data = json.load(f)

    # Use the categories list as a filter
    valid_categories = set(data["categories"])

    # Load armor_types into a list of dictionaries
    armor_types = data.get("armor_types", [])

    # Dictionary to store items by subcategory
    categorized_items: Dict[str, List[dict]] = {
        "weapons": [],
        "armors": [],
        "dice": [],
        "dice_badges": []
    }

    # Dictionary to store items by ID for quick lookup
    item_lookup = {}

    # Parse text_ui_items.xml and create a mapping of UIName to ItemName and AltName
    text_ui_items_path = kcd2_xmls.get("text_ui_items")
    if text_ui_items_path is None:
        raise FileNotFoundError("Key 'text_ui_items' is missing in kcd2_xmls.")
    text_ui_items_path = Path(text_ui_items_path)  # Ensure it's a Path object
    if not text_ui_items_path.exists():
        raise FileNotFoundError(f"text_ui_items.xml not found: {os.path.relpath(text_ui_items_path)}")

    text_ui_root = parse_xml(text_ui_items_path)
    text_ui_mapping = {
        row.find("Cell[1]").text: {
            "ItemName": row.find("Cell[3]").text,
            "AltName": row.find("Cell[2]").text
        }
        for row in text_ui_root.findall(".//Row")
        if all(row.find(f"Cell[{i}]") is not None for i in [1, 2, 3])
    }

    # Collect missing files
    missing_files = [file_key for file_key in item_files if file_key not in kcd2_xmls]
    if missing_files:
        logger.warning(f"Missing files: {', '.join(missing_files)}. Skipping...")

    # Process each relevant item file
    for file_key in item_files:
        if file_key not in kcd2_xmls:
            continue  # Skip missing files

        file_path = Path(kcd2_xmls[file_key])
        if not file_path.exists():
            logger.warning(f"File {os.path.relpath(file_path)} does not exist. Skipping...")
            continue

        try:
            tree = ET.parse(file_path)
            root = tree.getroot()

            # Extract items from <ItemClasses>
            for item in root.findall(".//ItemClasses/*"):
                # Handle regular items
                if item.tag in valid_categories:
                    if should_filter_item(item):
                        continue

                    # Determine the item type and subcategory
                    item_type = "Armor" if item.tag in ["Hood", "Helmet"] else item.tag
                    subcategory = get_subcategory(item_type)

                    if subcategory is None:
                        logger.warning(f"Unknown item type: {item_type}. Skipping...")
                        continue

                    # Extract attributes and stats
                    attributes = extract_data(item, item_type, item_attr_mapping, attr_transform, data)
                    stats = extract_data(item, item_type, item_stats_mapping, stat_transform, data)

                    # Assign Type for Armor items based on filters
                    if item_type == "Armor":
                        item_name = attributes.get("Name", "").lower()
                        for armor_type in armor_types:
                            for filter_ in armor_type.get("filters", []):
                                if filter_.lower() in item_name:
                                    attributes["Type"] = armor_type["Id"]
                                    break
                            if "Type" in attributes:  # Stop searching once a match is found
                                break

                    # Use the centralized function to construct item_data
                    item_data = construct_item_data(item, attributes, stats, text_ui_mapping)

                    # Add the item to the appropriate subcategory and lookup dictionary
                    categorized_items[subcategory].append(item_data)
                    item_lookup[item_data["Id"]] = item_data

            logger.info(f"Processed items from {file_key} ({os.path.relpath(file_path)})")
        except ET.ParseError as e:
            logger.warning(f"Failed to parse {file_key} ({os.path.relpath(file_path)}): {e}")

    # Update the Items category in data.json
    data["items"] = categorized_items

    # Save updated data.json
    with open(data_json_path, 'w') as f:
        json.dump(data, f, indent=4)

    logger.info(f"Items data updated in {os.path.relpath(data_json_path)}")

def main():
    """
    Main function to orchestrate the build process.
    """
    # Define base paths
    base_dir = Path(__file__).resolve().parent.parent  # Root directory: kcd-extract/
    data_dir = base_dir / "src/data"  # Data directory: /src/data

    # Extract version number and create output directory
    version = get_version_info(data_dir)
    output_dir = data_dir / version

    # Run and save data extraction
    kcd2_xmls, kcd2_icons = data_extract()
    export_versioned_data(kcd2_xmls, kcd2_icons, output_dir)

    # Initialize a new data.json file
    data_json_path = initialize_data_json(version, output_dir)

    # Process XML data
    xml_equipment_slot(kcd2_xmls, output_dir)
    xml_weapon_info(kcd2_xmls, output_dir)
    xml_dice(kcd2_xmls, output_dir)
    xml_items(kcd2_xmls, output_dir)

    # Log completion
    logger.info(f"Build process completed successfully. data.json created at {os.path.relpath(data_json_path)}")

if __name__ == "__main__":
    main()