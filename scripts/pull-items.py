import zipfile
import os
import json
import re
import shutil
import xml.etree.ElementTree as ET
from xml.dom import minidom

# Game version
version_file = 'D:/SteamLibrary/steamapps/common/KingdomComeDeliverance2/whdlversions.json'
version_file_output_path = './scripts/KCD2/whdlversions.json'

# Tables.pak for item xmls
tables_pak = 'D:/SteamLibrary/steamapps/common/KingdomComeDeliverance2/Data/Tables.pak'
tables_pak_output_path = './scripts/KCD2/Data/Tables.pak/'
tables_files = {
    'dice_badge_subtype': 'Libs/Tables/item/dice_badge_subtype.xml',
    'dice_badge_type': 'Libs/Tables/item/dice_badge_type.xml',
    'document_class': 'Libs/Tables/item/document_class.xml',
    'equipment_part': 'Libs/Tables/item/equipment_part.xml',
    'equipment_slot': 'Libs/Tables/item/equipment_slot.xml',
    'item': 'Libs/Tables/item/item.xml',
    'item_category': 'Libs/Tables/item/item_category.xml',
    'item_horse': 'Libs/Tables/item/item__horse.xml',
    'item_rewards': 'Libs/Tables/item/item__rewards.xml',
    'item_unique': 'Libs/Tables/item/item__unique.xml',
}

# English_xml.pak for ui_name to Name
english_localization_pak = 'D:/SteamLibrary/steamapps/common/KingdomComeDeliverance2/Localization/English_xml.pak'
english_localization_output_path = './scripts/KCD2/Localization/English_xml.pak/'
localization_files = {
    'text_ui_items': 'text_ui_items.xml'
}

# IPL_GameData.pak for icons
compressed_icons = 'D:/SteamLibrary/steamapps/common/KingdomComeDeliverance2/Data/IPL_GameData.pak'
icons_output_path = './scripts/KCD2/Data/IPL_GameData.pak/'
dds_icons = 'Libs/UI/Textures/Icons'

# Define the relative path where you want to save the manipulated files
relative_output_path = './scripts/KCD2'

# Ensure the output directory exists
os.makedirs(relative_output_path, exist_ok=True)

# Initialize the KCD2 data structure
kcd2_data = {
    "version": {},
    "categories": {},
    "equipment_slots": {},
    "weapon_class": {},
    "armor_class:": {},
    "dice_badges": {},
    "items": {},
    "icons": {}
}

# Initialize the KCD2 files structure
kcd2_files = {}

def copy_and_extract_files():
    def copy_version_file():
        copied_version_file = os.path.join(relative_output_path, 'whdlversions.json').replace('\\', '/')
        shutil.copy(version_file, copied_version_file)
        print(f"Copied version file to {copied_version_file}")
        return copied_version_file

    def extract_files_from_pak(pak_path, files, output_path):
        with zipfile.ZipFile(pak_path, 'r') as pak:
            for key, file in files.items():
                try:
                    file_path = os.path.join(output_path, file.replace('Libs/Tables/', '')).replace('\\', '/')
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    with pak.open(file) as source, open(file_path, 'wb') as target:
                        target.write(source.read())
                    print(f"Extracted {file} to {file_path}")
                    kcd2_files[key] = file_path
                except Exception as e:
                    print(f"Error extracting {file} from {pak_path}: {e}")

    copied_version_file = copy_version_file()
    extract_files_from_pak(tables_pak, tables_files, tables_pak_output_path)
    extract_files_from_pak(english_localization_pak, localization_files, english_localization_output_path)

def get_version(version_file):
    version_pattern = re.compile(r'^\d+(\.\d+)*$')
    try:
        with open(version_file, 'r', encoding='utf-8') as vf:
            version_info = json.load(vf)
            branch_name = version_info["Preset"]["Branch"]["Name"]
            version_number = '.'.join(branch_name.split('_')[1:])
            if not version_pattern.match(version_number):
                raise ValueError(f"Invalid version format: {version_number}")
            print(f"Extracted version information: {version_number}")
            return {"release": version_number}
    except (FileNotFoundError, json.JSONDecodeError, KeyError, ValueError) as e:
        print(f"Error extracting version information: {e}")
        return {}

def merge_items():
    def parse_xml_files():
        item_file = kcd2_files.get('item')
        item_horse_file = kcd2_files.get('item_horse')
        item_rewards_file = kcd2_files.get('item_rewards')
        item_unique_file = kcd2_files.get('item_unique')

        item_tree = ET.parse(item_file)
        item_horse_tree = ET.parse(item_horse_file)
        item_rewards_tree = ET.parse(item_rewards_file)
        item_unique_tree = ET.parse(item_unique_file)

        return item_tree, item_horse_tree, item_rewards_tree, item_unique_tree

    def merge_item_classes(item_root, item_horse_root, item_rewards_root, item_unique_root):
        item_classes = item_root.find('ItemClasses')
        item_horse_classes = item_horse_root.find('ItemClasses')
        item_rewards_classes = item_rewards_root.find('ItemClasses')
        item_unique_classes = item_unique_root.find('ItemClasses')

        for elem in item_horse_classes:
            elem.tag = 'Horse' if elem.tag == 'Armor' else elem.tag
            item_classes.append(elem)

        for elem in item_rewards_classes:
            item_classes.append(elem)

        for elem in item_unique_classes:
            item_classes.append(elem)

    def handle_item_aliases(item_root):
        item_aliases = item_root.findall('.//ItemAlias')
        parent_map = {c: p for p in item_root.iter() for c in p}
        aliases_to_remove = []

        alias_dict = {}
        for item_alias in item_aliases:
            source_item_id = item_alias.get('SourceItemId')
            if source_item_id:
                if source_item_id not in alias_dict:
                    alias_dict[source_item_id] = []
                alias_dict[source_item_id].append(item_alias)
            else:
                aliases_to_remove.append(item_alias)

        for source_item_id, aliases in alias_dict.items():
            target_element = item_root.find(f".//*[@Id='{source_item_id}']")
            if target_element is not None:
                for alias in aliases:
                    for attr, value in target_element.attrib.items():
                        if attr not in alias.attrib:
                            alias.attrib[attr] = value
                    parent = parent_map[alias]
                    parent.append(alias)
            else:
                aliases_to_remove.extend(aliases)

        for item_alias in aliases_to_remove:
            parent = parent_map[item_alias]
            parent.remove(item_alias)

    def write_pretty_xml(tree, output_file):
        xml_str = ET.tostring(tree.getroot(), encoding='utf-8')
        pretty_xml_as_str = minidom.parseString(xml_str).toprettyxml(indent="    ")
        pretty_xml_as_str = re.sub(r'\n\s*\n', '\n', pretty_xml_as_str)  # Remove excess blank lines
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(pretty_xml_as_str)
        print(f"Merged items written to {output_file}")

    item_tree, item_horse_tree, item_rewards_tree, item_unique_tree = parse_xml_files()
    item_root = item_tree.getroot()
    item_horse_root = item_horse_tree.getroot()
    item_rewards_root = item_rewards_tree.getroot()
    item_unique_root = item_unique_tree.getroot()

    merge_item_classes(item_root, item_horse_root, item_rewards_root, item_unique_root)
    handle_item_aliases(item_root)

    output_dir = './src/Data'
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, 'items_merged.xml').replace('\\', '/')
    write_pretty_xml(item_tree, output_file)

def purge_items_and_attributes():
    def remove_elements(root, elements_to_remove):
        for item_classes in root.findall('.//ItemClasses'):
            for elem in list(item_classes):
                if elem.tag in elements_to_remove or elem.get('UIName') == 'ui_nm_torch' or (elem.get('IconId') and elem.get('IconId').lower() == 'trafficcone'):
                    item_classes.remove(elem)

    def remove_document_children(root):
        for document in root.findall('.//Document'):
            for child in list(document):
                document.remove(child)
            document.text = None

    def remove_attributes(root, attributes_to_remove):
        for elem in root.iter():
            for attr in attributes_to_remove:
                if attr in elem.attrib:
                    del elem.attrib[attr]

    def write_pretty_xml(tree, output_file):
        xml_str = ET.tostring(tree.getroot(), encoding='utf-8')
        pretty_xml_as_str = minidom.parseString(xml_str).toprettyxml(indent="    ")
        pretty_xml_as_str = re.sub(r'\n\s*\n', '\n', pretty_xml_as_str)
        pretty_xml_as_str = re.sub(r'<Document></Document>', '<Document />', pretty_xml_as_str)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(pretty_xml_as_str)
        print(f"Purged items written to {output_file}")

    merged_file = './src/Data/items_merged.xml'
    tree = ET.parse(merged_file)
    root = tree.getroot()

    elements_to_remove = ['NPCTool', 'MiscItem', 'Food', 'Herb', 'PickableItem', 'Poison', 'AlchemyBase', 'Ointment', 'Ammo', 'CraftingMaterial']
    attributes_to_remove = ['SocialClassId', 'WealthLevel', 'IsBreakable', 'BrokenItemClassId', 'FadeCoef', 'VisibilityCoef', 'Model', 'PickpocketInPouch', 'RPGBuffWeight']

    remove_elements(root, elements_to_remove)
    remove_document_children(root)
    remove_attributes(root, attributes_to_remove)

    output_file = os.path.join('./src/Data', 'items_purged.xml').replace('\\', '/')
    write_pretty_xml(tree, output_file)

    item_classes = root.find('ItemClasses')
    if item_classes is not None:
        unique_elements = set(elem.tag for elem in item_classes)
        for elem_name in unique_elements:
            print(elem_name)

def build_json():
    # Extract version information from the copied version file
    copied_version_file = os.path.join(relative_output_path, 'whdlversions.json').replace('\\', '/')
    version_info = get_version(copied_version_file)
    kcd2_data["version"] = version_info

    # Ensure the output directory for data.json exists
    output_json_dir = os.path.dirname('./src/Data/data.json')
    os.makedirs(output_json_dir, exist_ok=True)

    # Save the extracted and manipulated data to a JSON file
    output_json_path = os.path.join('./src/Data/data.json').replace('\\', '/')
    try:
        with open(output_json_path, 'w', encoding='utf-8') as json_file:
            json.dump(kcd2_data, json_file, indent=4)
        print("data.json has been built.")
    except IOError as e:
        print(f"Error saving data to JSON file: {e}")

# Perform the copy and extraction operations
copy_and_extract_files()

# Merge the items
merge_items()

# Purge unnecessary elements and attributes
purge_items_and_attributes()

# Build the JSON file
build_json()

print(kcd2_files)