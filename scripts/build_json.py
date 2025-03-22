import os
import json
from logger import logger
from pathlib import Path
import xml.etree.ElementTree as ET
from data_extract import main as data_extraction
from helper import load_json, save_json, load_data_json, save_data_json, parse_xml, extract_stats, extract_attr
from templates.data_json_mappings import item_stats_mapping, item_attr_mapping


def get_version_info(data_dir):
    """Calculate the version from version.json, check it against latest_version.json, and create the directory."""
    version_file = data_dir / "version.json"
    latest_version_file = data_dir / "latest_version.json"

    # Ensure version.json exists
    if not version_file.exists():
        raise FileNotFoundError(f"Version file not found: {version_file}")

    # Load version.json
    version_data = load_json(version_file)

    # Calculate the new version
    new_version = version_data['Preset']['Branch']['Name'].replace('release_', '').replace('_', '.')
    new_version_path = data_dir / new_version

    # Check if latest_version.json exists and compare versions
    if latest_version_file.exists():
        latest_version_data = load_json(latest_version_file)
        if latest_version_data['Branch']['version'] == new_version:
            logger.info(f"Version {new_version} matches the latest version. No action needed.")
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
    new_version_path.mkdir(parents=True, exist_ok=True)
    logger.info(f"New version is {new_version}. Created folder {new_version_path}")
    return new_version

def export_versioned_data(kcd2_xmls, kcd2_icons, output_dir):
    """Save kcd2_xmls and kcd2_icons to the versioned output directory."""
    kcd2_xmls_path = output_dir / "kcd2_xmls.json"
    kcd2_icons_path = output_dir / "kcd2_icons.json"

    with open(kcd2_xmls_path, 'w') as f:
        json.dump(kcd2_xmls, f, indent=4)

    with open(kcd2_icons_path, 'w') as f:
        json.dump(kcd2_icons, f, indent=4)

    logger.info(f"Saved kcd2_xmls to {os.path.relpath(kcd2_xmls_path)}")
    logger.info(f"Saved kcd2_icons to {os.path.relpath(kcd2_icons_path)}")

def initialize_data_json(version, output_dir):
    """
    Create a new data.json file using the base_data.json template.
    """
    logger.info("Creating a new data.json file from base_data.json...")

    # Path to the base_data.json template
    base_data_path = Path(__file__).resolve().parent / "templates/base_data.json"

    # Load the base_data.json template
    if not base_data_path.exists():
        raise FileNotFoundError(f"Base data.json template not found: {base_data_path}")

    with open(base_data_path, 'r') as f:
        data = json.load(f)

    # Update the version in the data structure
    data["version"]["base"] = version

    # Save the new data.json file
    data_json_path = output_dir / "data.json"
    with open(data_json_path, 'w') as f:
        json.dump(data, f, indent=4)

    logger.info(f"New data.json created at {os.path.relpath(data_json_path)}")
    return data_json_path

def xml_equipment_slot(kcd2_xmls, output_dir):
    """Process equipment slot XML data and populate the Armor item_type in data.json."""
    logger.info("Processing equipment slot XML data...")

    # Parse the equipment_slot.xml file
    equipment_slot_path = Path(kcd2_xmls.get("equipment_slot"))
    root = parse_xml(equipment_slot_path)

    # Extract relevant data for Armor
    armor_slots = []
    for slot in root.findall(".//EquipmentSlot"):
        armor_slot = {
            "id": int(slot.get("Id")),
            "name": slot.get("Name"),
            "ui_body_part_id": slot.get("UIBodyPartId"),
            "ui_slot": slot.get("UISlot"),
            "filters": slot.get("ArmorTypes", "").split() if slot.get("ArmorTypes") else []
        }

        # Add missing filters for specific IDs
        if armor_slot["id"] == 13:  # Horse Torso
            armor_slot["filters"].extend(["Caparison", "Harness"])
        elif armor_slot["id"] == 14:  # Horse Head
            armor_slot["filters"].extend(["Bridle", "Chanfron"])
        elif armor_slot["id"] == 16:  # Horse Saddle
            armor_slot["filters"].extend(["Saddle"])

        # If filters are still empty, append the ui_slot value
        if not armor_slot["filters"] and armor_slot["ui_slot"]:
            armor_slot["filters"].append(armor_slot["ui_slot"])

        armor_slots.append(armor_slot)

    # Sort armor slots by ID
    armor_slots = sorted(armor_slots, key=lambda x: x["id"])

    # Load and update data.json
    data, data_json_path = load_data_json(output_dir)
    data["item_types"]["armor"]["armorType"] = armor_slots
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
    melee_weapons = [
        {
            "id": int(weapon.get("id")),
            "name": weapon.get("name"),
            "skill": weapon.get("skill"),
            "equip_slot": weapon.get("equip_slot")
        }
        for weapon in weapon_root.findall(".//MeleeWeaponClass")
    ]

    missile_weapons = [
        {
            "id": int(weapon.get("id")),
            "name": weapon.get("name"),
            "skill": weapon.get("skill"),
            "equip_slot": weapon.get("equip_slot"),
            "ammo_class": ammo_class_mapping.get(weapon.get("ammo_class"), "Unknown")
        }
        for weapon in weapon_root.findall(".//MissileWeaponClass")
    ]

    # Load and update data.json
    data, data_json_path = load_data_json(output_dir)
    data["item_types"]["weapons"]["MeleeWeaponClass"]["weapons"] = melee_weapons
    data["item_types"]["weapons"]["MissileWeaponClass"]["weapons"] = missile_weapons
    save_data_json(data, data_json_path)

def xml_dice(kcd2_xmls, output_dir):
    """Process dice badge XML data and populate the Dice item_type in data.json."""
    logger.info("Processing dice badge XML data...")

    # Parse the dice_badge_type.xml and dice_badge_subtype.xml files
    dice_badge_type_path = Path(kcd2_xmls.get("dice_badge_type"))
    dice_badge_subtype_path = Path(kcd2_xmls.get("dice_badge_subtype"))
    dice_badge_type_root = parse_xml(dice_badge_type_path)
    dice_badge_subtype_root = parse_xml(dice_badge_subtype_path)

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
    for badge in data["item_types"]["dice"]["diceBadge"]:
        if badge["id"] == "DiceBadge":
            badge["diceBadgeType"] = dice_badge_types
            badge["diceBadgeSubType"] = dice_badge_subtypes
            break
    save_data_json(data, data_json_path)

def xml_items(kcd2_xmls, output_dir):
    """Process item XML data and populate the Items category in data.json."""
    logger.info("Processing item XML data...")

    # Explicitly list the IDs of relevant item XML files
    item_files = ["item", "item_dlc", "item_horse", "item_reward", "item_rewards"]

    # Load existing data.json to get the list of categories
    data_json_path = output_dir / "data.json"
    if not data_json_path.exists():
        raise FileNotFoundError(f"data.json not found in {os.path.relpath(output_dir)}")

    with open(data_json_path, 'r') as f:
        data = json.load(f)

    # Use the categories list as a filter
    valid_categories = set(data["categories"])

    # Dictionary to store items by ID for quick lookup (to handle ItemAlias)
    item_lookup = {}

    # Process each relevant item file
    items = []
    for file_key in item_files:
        if file_key not in kcd2_xmls:
            logger.warning(f"File ID {file_key} not found in kcd2_xmls. Skipping...")
            continue

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
                    # Apply filters
                    icon_id = item.get("IconId", "").lower()
                    ui_info = item.get("UIInfo", "").lower()
                    if icon_id in {"trafficcone", "trafficcone"} or ui_info == "ui_in_warning":
                        continue

                    # If the element is Hood, treat it as Armor
                    item_type = "Armor" if item.tag == "Hood" else item.tag

                    # Add the item to the list and lookup dictionary
                    item_data = {
                        **extract_attr(item, item_attr_mapping),  # Extract consistent attributes
                        "Type": item_type,
                        "stats": extract_stats(item, item_type, item_stats_mapping)
                    }
                    items.append(item_data)
                    item_lookup[item_data["Id"]] = item_data

                # Handle ItemAlias
                elif item.tag == "ItemAlias":
                    source_item_id = item.get("SourceItemId")
                    if source_item_id in item_lookup:
                        # Get the source item
                        source_item = item_lookup[source_item_id]

                        # Apply filters to the alias itself
                        icon_id = item.get("IconId", "").lower()
                        ui_info = item.get("UIInfo", "").lower()
                        if icon_id in {"trafficcone", "trafficcone"} or ui_info == "ui_in_warning":
                            continue

                        # Create a new item based on the source item, overriding stats with the alias
                        alias_data = {
                            "Type": source_item["Type"],
                            "Id": item.get("Id"),
                            "Name": item.get("Name"),
                            "stats": source_item["stats"].copy()  # Start with source stats
                        }
                        # Overwrite stats with those from the alias
                        alias_data["stats"].update(extract_stats(item, source_item["Type"], item_stats_mapping))

                        # Add the alias as a new item
                        items.append(alias_data)
                        item_lookup[alias_data["Id"]] = alias_data

            logger.info(f"Processed items from {file_key} ({os.path.relpath(file_path)})")
        except ET.ParseError as e:
            logger.warning(f"Failed to parse {file_key} ({os.path.relpath(file_path)}): {e}")

    # Update the Items category in data.json
    data["items"] = items

    # Save updated data.json
    with open(data_json_path, 'w') as f:
        json.dump(data, f, indent=4)

    logger.info(f"Items data updated in {os.path.relpath(data_json_path)}")

def main():
    # Define base paths
    base_dir = Path(__file__).resolve().parent.parent  # Root directory: kcd-extract/
    data_dir = base_dir / "src/data"  # Data directory: /src/data

    # Extract version number and create output directory
    version = get_version_info(data_dir)
    output_dir = data_dir / version

    # Run and save data extraction
    kcd2_xmls, kcd2_icons = data_extraction()
    export_versioned_data(kcd2_xmls, kcd2_icons, output_dir)

    # Initialize a new data.json file
    data_json_path = initialize_data_json(version, output_dir)

    # Step 4: Run XML processing
    xml_equipment_slot(kcd2_xmls, output_dir)
    xml_weapon_info(kcd2_xmls, output_dir)
    xml_dice(kcd2_xmls, output_dir)

    # Process all relevant item XML files
    xml_items(kcd2_xmls, output_dir)
 
    # Step 5: Log completion
    logger.info(f"Build process completed. data.json created at {os.path.relpath(data_json_path)}")

if __name__ == "__main__":
    main()