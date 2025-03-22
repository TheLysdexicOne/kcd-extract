import os
import json
from pathlib import Path
from logger import logger
import xml.etree.ElementTree as ET

#############################
#  GET LATEST VERSION DATA  #
#############################

def get_latest_version_data(output_dir):
    """Load kcd2_xmls.json from the specified output directory."""
    kcd2_xmls_path = output_dir / "kcd2_xmls.json"

    if not kcd2_xmls_path.exists():
        raise FileNotFoundError(f"Missing kcd2_xmls.json in {os.path.relpath(output_dir)}")

    with open(kcd2_xmls_path, 'r') as f:
        kcd2_xmls = json.load(f)

    logger.info(f"Loaded data from output directory: {os.path.relpath(output_dir)}")
    return kcd2_xmls

##########################
#  INITIALIZE DATA JSON  #
##########################

def xml_process_initialize_data_json(version, output_dir):
    """Initialize or overwrite the data.json structure."""
    data = {
        "version": {
            "base": version
        },
        "categories": [],  # To be populated later
        "item_types": {},  # To be populated later
        "items": []  # To be populated by other functions
    }

    # Save the default structure to data.json
    data_json_path = output_dir / "data.json"
    with open(data_json_path, 'w') as f:
        json.dump(data, f, indent=4)
    logger.info(f"Initialized or overwritten data.json at {os.path.relpath(data_json_path)}")

    return data_json_path

#####################
#  XML CATEGORIES  #
#####################

def xml_categories(kcd2_xmls, output_dir):
    """Process and populate categories and item_types in data.json."""
    logger.info("Processing categories...")

    # Define the explicit list of item elements to pull
    categories = [
        "MeleeWeapon",
        "MissileWeapon",
        "Armor",
        "Hood",
        "Die",
        "DiceBadge"
    ]

    # Define the detailed item types
    item_types = {
        "weapons": {
            "name": "Weapons",
            "weaponClass": [],  # WeaponClasses will be populated later in xml_weapon()
            "MeleeWeaponClass": {
                "id": "MeleeWeapon",
                "name": "Melee Weapons",
                "weapons": []
            },
            "MissileWeaponClass": {
                "id": "MissileWeapon",
                "name": "Ranged Weapons",
                "weapons": []
            }
        },
        "armor": {
            "name": "Armor",
            "armorType": []  # Subcategories will be populated later using xml_equipment_slot()
        },
        "dice": {
            "name": "Dice",
            "diceBadge": [
                {
                    "id": "Die",
                    "name": "Die"
                },
                {
                    "id": "DiceBadge",
                    "name": "Dice Badge",
                    "diceBadgeType": {},
                    "diceBadgeSubType": {}
                }
            ]
        }
    }

    # Load existing data.json
    data_json_path = output_dir / "data.json"
    if not data_json_path.exists():
        raise FileNotFoundError(f"data.json not found in {os.path.relpath(output_dir)}")

    with open(data_json_path, 'r') as f:
        data = json.load(f)

    # Update categories and item_types
    data["categories"] = categories
    data["item_types"] = item_types

    # Save updated data.json
    with open(data_json_path, 'w') as f:
        json.dump(data, f, indent=4)

    logger.info(f"Categories and item_types updated in {os.path.relpath(data_json_path)}")

########################
#  XML EQUIPMENT SLOT  #
########################

def xml_equipment_slot(kcd2_xmls, output_dir):
    """Process equipment slot XML data and populate the Armor item_type in data.json."""
    logger.info("Processing equipment slot XML data...")

    # Locate the equipment_slot.xml file
    equipment_slot_path = Path(kcd2_xmls.get("equipment_slot"))
    if not equipment_slot_path.exists():
        raise FileNotFoundError(f"equipment_slot.xml not found at {os.path.relpath(equipment_slot_path)}")

    # Parse the XML file
    tree = ET.parse(equipment_slot_path)
    root = tree.getroot()

    # Extract relevant data for Armor
    armor_slots = []
    for slot in root.findall(".//EquipmentSlot"):
        armor_slot = {
            "id": int(slot.get("Id")),  # Convert ID to integer for proper sorting
            "name": slot.get("Name"),
            "ui_body_part_id": slot.get("UIBodyPartId"),
            "ui_slot": slot.get("UISlot"),
            "filters": slot.get("ArmorTypes", "").split() if slot.get("ArmorTypes") else []
        }

        # If armor_types is empty, add UISlot to armor_types
        if not armor_slot["filters"] and armor_slot["ui_slot"]:
            armor_slot["filters"].append(armor_slot["ui_slot"])

        # Add missing filters for specific IDs
        if armor_slot["id"] == 13:  # Horse Torso
            armor_slot["filters"].extend(["Caparison", "Harness"])
        elif armor_slot["id"] == 14:  # Horse Head
            armor_slot["filters"].extend(["Bridle", "Chanfron"])
        elif armor_slot["id"] == 16:  # Horse Saddle
            armor_slot["filters"].append("Saddle")

        armor_slots.append(armor_slot)

    # Sort armor slots by ID
    armor_slots = sorted(armor_slots, key=lambda x: x["id"])

    # Load existing data.json
    data_json_path = output_dir / "data.json"
    if not data_json_path.exists():
        raise FileNotFoundError(f"data.json not found in {os.path.relpath(output_dir)}")

    with open(data_json_path, 'r') as f:
        data = json.load(f)

    # Update the Armor item_type in data.json
    data["item_types"]["armor"]["armorType"] = armor_slots

    # Save updated data.json
    with open(data_json_path, 'w') as f:
        json.dump(data, f, indent=4)

    logger.info(f"Armor equipment slots updated and sorted in {os.path.relpath(data_json_path)}")

#####################
#  XML WEAPON INFO  #
#####################

def xml_weapon_info(kcd2_xmls, output_dir):
    """Process weapon XML data and populate the Weapons item_type in data.json."""
    logger.info("Processing weapon XML data...")

    # Locate the weapon_class.xml file
    weapon_class_path = Path(kcd2_xmls.get("weapon_class"))
    if not weapon_class_path.exists():
        raise FileNotFoundError(f"weapon_class.xml not found at {os.path.relpath(weapon_class_path)}")

    # Locate the ammo_class.xml file
    ammo_class_path = Path(kcd2_xmls.get("ammo_class"))
    if not ammo_class_path.exists():
        raise FileNotFoundError(f"ammo_class.xml not found at {os.path.relpath(ammo_class_path)}")

    # Parse the ammo_class.xml file to create a mapping of ammo_class_id to ammo_class_name
    ammo_class_tree = ET.parse(ammo_class_path)
    ammo_class_root = ammo_class_tree.getroot()
    ammo_class_mapping = {
        ammo.get("ammo_class_id"): ammo.get("ammo_class_name")
        for ammo in ammo_class_root.findall(".//ammo_class")
    }

    # Parse the weapon_class.xml file
    weapon_class_tree = ET.parse(weapon_class_path)
    weapon_class_root = weapon_class_tree.getroot()

    # Extract MeleeWeaponClass data
    melee_weapons = []
    for weapon in weapon_class_root.findall(".//MeleeWeaponClass"):
        melee_weapons.append({
            "id": int(weapon.get("id")),
            "name": weapon.get("name"),
            "skill": weapon.get("skill"),
            "equip_slot": weapon.get("equip_slot")
        })

    # Extract MissileWeaponClass data
    missile_weapons = []
    for weapon in weapon_class_root.findall(".//MissileWeaponClass"):
        ammo_class_id = weapon.get("ammo_class")
        ammo_class_name = ammo_class_mapping.get(ammo_class_id, "Unknown")
        missile_weapons.append({
            "id": int(weapon.get("id")),
            "name": weapon.get("name"),
            "skill": weapon.get("skill"),
            "equip_slot": weapon.get("equip_slot"),
            "ammo_class": ammo_class_name
        })

    # Load existing data.json
    data_json_path = output_dir / "data.json"
    if not data_json_path.exists():
        raise FileNotFoundError(f"data.json not found in {os.path.relpath(output_dir)}")

    with open(data_json_path, 'r') as f:
        data = json.load(f)

    # Update the Weapons item_type in data.json
    data["item_types"]["weapons"]["MeleeWeaponClass"]["weapons"] = melee_weapons
    data["item_types"]["weapons"]["MissileWeaponClass"]["weapons"] = missile_weapons

    # Save updated data.json
    with open(data_json_path, 'w') as f:
        json.dump(data, f, indent=4)

    logger.info(f"Weapons data updated in {os.path.relpath(data_json_path)}")

################
#  XML Dice  #
################

def xml_dice(kcd2_xmls, output_dir):
    """Process dice badge XML data and populate the Dice item_type in data.json."""
    logger.info("Processing dice badge XML data...")

    # Locate the dice_badge_type.xml and dice_badge_subtype.xml files
    dice_badge_type_path = Path(kcd2_xmls.get("dice_badge_type"))
    dice_badge_subtype_path = Path(kcd2_xmls.get("dice_badge_subtype"))

    if not dice_badge_type_path.exists():
        raise FileNotFoundError(f"dice_badge_type.xml not found at {os.path.relpath(dice_badge_type_path)}")
    if not dice_badge_subtype_path.exists():
        raise FileNotFoundError(f"dice_badge_subtype.xml not found at {os.path.relpath(dice_badge_subtype_path)}")

    # Parse the dice_badge_type.xml file
    dice_badge_type_tree = ET.parse(dice_badge_type_path)
    dice_badge_type_root = dice_badge_type_tree.getroot()
    dice_badge_types = {
        int(type_.get("dice_badge_type_id")): type_.get("dice_badge_type_name")
        for type_ in dice_badge_type_root.findall(".//dice_badge_type")
    }

    # Parse the dice_badge_subtype.xml file
    dice_badge_subtype_tree = ET.parse(dice_badge_subtype_path)
    dice_badge_subtype_root = dice_badge_subtype_tree.getroot()
    dice_badge_subtypes = {
        int(subtype.get("dice_badge_subtype_id")): subtype.get("dice_badge_subtype_name")
        for subtype in dice_badge_subtype_root.findall(".//dice_badge_subtype")
    }

    # Load existing data.json
    data_json_path = output_dir / "data.json"
    if not data_json_path.exists():
        raise FileNotFoundError(f"data.json not found in {os.path.relpath(output_dir)}")

    with open(data_json_path, 'r') as f:
        data = json.load(f)

    # Update the Dice item_type in data.json
    dice_badge = data["item_types"]["dice"]["diceBadge"]
    for badge in dice_badge:
        if badge["id"] == "DiceBadge":
            badge["diceBadgeType"] = dice_badge_types
            badge["diceBadgeSubType"] = dice_badge_subtypes
            break

    # Save updated data.json
    with open(data_json_path, 'w') as f:
        json.dump(data, f, indent=4)

    logger.info(f"Dice badge data updated in {os.path.relpath(data_json_path)}")

################
#  XML Items  #
################

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
                        "type": item_type,
                        "id": item.get("Id"),
                        "name": item.get("Name"),
                        "attributes": {key: item.get(key) for key in item.keys() if key not in ["Id", "Name"]}
                    }
                    items.append(item_data)
                    item_lookup[item_data["id"]] = item_data

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

                        # Create a new item based on the source item, overriding attributes with the alias
                        alias_data = {
                            "type": source_item["type"],
                            "id": item.get("Id"),
                            "name": item.get("Name"),
                            "attributes": source_item["attributes"].copy()  # Start with source attributes
                        }
                        # Overwrite attributes with those from the alias
                        alias_data["attributes"].update({key: item.get(key) for key in item.keys() if key not in ["Id", "Name", "SourceItemId"]})

                        # Add the alias as a new item
                        items.append(alias_data)
                        item_lookup[alias_data["id"]] = alias_data

            logger.info(f"Processed items from {file_key} ({os.path.relpath(file_path)})")
        except ET.ParseError as e:
            logger.warning(f"Failed to parse {file_key} ({os.path.relpath(file_path)}): {e}")

    # Update the Items category in data.json
    data["items"] = items

    # Save updated data.json
    with open(data_json_path, 'w') as f:
        json.dump(data, f, indent=4)

    logger.info(f"Items data updated in {os.path.relpath(data_json_path)}")

##########
#  MAIN  #
##########

def main(output_dir):
    """Main function to handle XML processing."""

    # Load xml dictionary
    kcd2_xmls = get_latest_version_data(output_dir)

    # Process XML data
    xml_categories(kcd2_xmls, output_dir)
    xml_equipment_slot(kcd2_xmls, output_dir)
    xml_weapon_info(kcd2_xmls, output_dir)
    xml_dice(kcd2_xmls, output_dir)
    xml_items(kcd2_xmls, output_dir)

if __name__ == "__main__":
    version = '1.2'
    base_dir = Path(__file__).resolve().parent.parent
    data_dir = base_dir / 'src/data'
    output_dir = data_dir / version

    # Initialize json
    xml_process_initialize_data_json(version, output_dir)

    # Run Main
    main(output_dir)