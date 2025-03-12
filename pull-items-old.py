import zipfile
import os
import json
import xml.etree.ElementTree as ET
import re

# Game version
version_file = 'D:/SteamLibrary/steamapps/common/KingdomComeDeliverance2/whdlversions.json'

# Tables.pak for item xmls
tables_pak = 'D:/SteamLibrary/steamapps/common/KingdomComeDeliverance2/Data/Tables.pak'
xml_files = {
    'item': 'Libs/Tables/item/item.xml',
    'item_category': 'Libs/Tables/item/item_category.xml',
    'item_horse': 'Libs/Tables/item/item__horse.xml',
    'item_rewards': 'Libs/Tables/item/item__rewards.xml',
    'equipment_slot': 'Libs/Tables/item/equipment_slot.xml',
    'equipment_part': 'Libs/Tables/item/equipment_part.xml',
    'weapon_class': 'Libs/Tables/item/weapon_class.xml',
    'dice_badge_type': 'Libs/Tables/item/dice_badge_type.xml',
    'dice_badge_subtype': 'Libs/Tables/item/dice_badge_subtype.xml'
}


# English_xml.pak for ui_name to Name
english_localization_pak = 'D:/SteamLibrary/steamapps/common/KingdomComeDeliverance2/Localization/English_xml.pak'
xml_text_ui_items = 'text_ui_items.xml'

# IPL_GameData.pak for icons
compressed_icons = 'D:/SteamLibrary/steamapps/common/KingdomComeDeliverance2/Data/IPL_GameData.pak'
dds_icons = 'Libs/UI/Textures/Icons'

# Define the relative path where you want to save the manipulated files
relative_output_path = './data'

# Ensure the output directory exists
os.makedirs(relative_output_path, exist_ok=True)

# Initialize the KCD2 data structure
kcd2_data = {
    "version": {},
    "categories": [],
    "equipment_slots": {},
    "weapon_classes": {},
    "dice_badges": {},
    "items": {},
    "icons": {}
}

def extract_version_info(version_file):
    version_pattern = re.compile(r'^\d+(\.\d+)*$')
    try:
        with open(version_file, 'r', encoding='utf-8') as vf:
            version_info = json.load(vf)
            branch_name = version_info["Preset"]["Branch"]["Name"]
            version_number = '.'.join(branch_name.split('_')[1:])
            if not version_pattern.match(version_number):
                raise ValueError(f"Invalid version format: {version_number}")
            return {"release": version_number}
    except (FileNotFoundError, json.JSONDecodeError, KeyError, ValueError) as e:
        print(f"Error extracting version information: {e}")
        return {}

def extract_category_info(tables_pak, xml_files):
    relevant_categories = {
        "melee_weapon", "missile_weapon", "armor", "dice_badge", 
        "document", "helmet", "hood", "quick_slot_container"
    }
    categories = []
    try:
        with zipfile.ZipFile(tables_pak, 'r') as zp:
            with zp.open(xml_files['item_category']) as xml:
                tree = ET.parse(xml)
                root = tree.getroot()
                for item_category in root.findall('.//item_category'):
                    category_name = item_category.get('item_category_name')
                    if category_name in relevant_categories:
                        category_id = item_category.get('item_category_id')
                        categories.append({
                            "id": category_id,
                            "name": category_name
                        })
    except (FileNotFoundError, zipfile.BadZipFile, ET.ParseError, KeyError) as e:
        print(f"Error extracting category information: {e}")
    return categories

def extract_equipment_slot_info(tables_pak, xml_files):
    equipment_slots = []
    try:
        with zipfile.ZipFile(tables_pak, 'r') as zp:
            with zp.open(xml_files['equipment_slot']) as xml:
                tree = ET.parse(xml)
                root = tree.getroot()
                for equipment_slot in root.findall('.//EquipmentSlot'):
                    slot_info = {
                        "Id": equipment_slot.get('Id'),
                        "UISlot": equipment_slot.get('UISlot')
                    }
                    if slot_info["UISlot"] is not None:
                        armor_types = equipment_slot.get('ArmorTypes')
                        if armor_types:
                            slot_info["ArmorTypes"] = armor_types.split()
                        equipment_slots.append(slot_info)
    except (FileNotFoundError, zipfile.BadZipFile, ET.ParseError, KeyError) as e:
        print(f"Error extracting equipment slot information: {e}")
    return equipment_slots

def extract_weapon_class_info(tables_pak, xml_files):
    weapon_classes = []
    try:
        with zipfile.ZipFile(tables_pak, 'r') as zp:
            with zp.open(xml_files['weapon_class']) as xml:
                tree = ET.parse(xml)
                root = tree.getroot()
                for weapon_class in root.findall('.//MeleeWeaponClass') + root.findall('.//MissileWeaponClass'):
                    class_info = {
                        "id": weapon_class.get('id'),
                        "name": weapon_class.get('name'),
                        "skill": weapon_class.get('skill')
                    }
                    weapon_classes.append(class_info)
    except (FileNotFoundError, zipfile.BadZipFile, ET.ParseError, KeyError) as e:
        print(f"Error extracting weapon class information: {e}")
    return weapon_classes

def extract_dice_badge_info(tables_pak, xml_files):
    dice_badges = []
    try:
        with zipfile.ZipFile(tables_pak, 'r') as zp:
            with zp.open(xml_files['dice_badge_type']) as xml:
                tree = ET.parse(xml)
                root = tree.getroot()
                for dice_badge_type in root.findall('.//dice_badge_type'):
                    type_info = {
                        "type": dice_badge_type.get('dice_badge_type_id'),
                        "name": dice_badge_type.get('dice_badge_type_name'),
                        "subtypes": []
                    }
                    # Extract subtypes for this type
                    with zp.open(xml_files['dice_badge_subtype']) as subtype_xml:
                        subtype_tree = ET.parse(subtype_xml)
                        subtype_root = subtype_tree.getroot()
                        for dice_badge_subtype in subtype_root.findall('.//dice_badge_subtype'):
                            subtype_info = {
                                "subtype": dice_badge_subtype.get('dice_badge_subtype_id'),
                                "name": dice_badge_subtype.get('dice_badge_subtype_name')
                            }
                            type_info["subtypes"].append(subtype_info)
                    dice_badges.append(type_info)
    except (FileNotFoundError, zipfile.BadZipFile, ET.ParseError, KeyError) as e:
        print(f"Error extracting dice badge information: {e}")
    return dice_badges



# Extract version information
kcd2_data["version"] = extract_version_info(version_file)

# Extract category information
kcd2_data["categories"] = extract_category_info(tables_pak, xml_files)

# Extract equipment slots information
kcd2_data["equipment_slots"] = extract_equipment_slot_info(tables_pak, xml_files)

# Extract weapon class information
kcd2_data["weapon_classes"] = extract_weapon_class_info(tables_pak, xml_files)

# Extract dice badge information
kcd2_data["dice_badges"] = extract_dice_badge_info(tables_pak, xml_files)

# Extract items


# Save the extracted and manipulated data to a JSON file
output_json_path = os.path.join(relative_output_path, 'data.json')
try:
    with open(output_json_path, 'w', encoding='utf-8') as json_file:
        json.dump(kcd2_data, json_file, indent=4)
    print("Files have been extracted, manipulated, and saved to the relative path.")
except IOError as e:
    print(f"Error saving data to JSON file: {e}")