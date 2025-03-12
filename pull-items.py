import zipfile
import os
import json
import re
import shutil
import xml.etree.ElementTree as ET
from xml.dom import minidom

# Game version
version_file = 'D:/SteamLibrary/steamapps/common/KingdomComeDeliverance2/whdlversions.json'
version_file_output_path = './src/KCD2/whdlversions.json'

# Tables.pak for item xmls
tables_pak = 'D:/SteamLibrary/steamapps/common/KingdomComeDeliverance2/Data/Tables.pak'
tables_pak_output_path = './src/KCD2/Data/Tables.pak/'
xml_files = {
    'item': 'Libs/Tables/item/item.xml',
    'item_horse': 'Libs/Tables/item/item__horse.xml',
    'item_rewards': 'Libs/Tables/item/item__rewards.xml',
    'item_category': 'Libs/Tables/item/item_category.xml',
    'equipment_slot': 'Libs/Tables/item/equipment_slot.xml',
    'equipment_part': 'Libs/Tables/item/equipment_part.xml',
    'weapon_class': 'Libs/Tables/item/weapon_class.xml',
    'dice_badge_type': 'Libs/Tables/item/dice_badge_type.xml',
    'dice_badge_subtype': 'Libs/Tables/item/dice_badge_subtype.xml'
}

# English_xml.pak for ui_name to Name
english_localization_pak = 'D:/SteamLibrary/steamapps/common/KingdomComeDeliverance2/Localization/English_xml.pak'
english_localization_output_path = './src/KCD2/Localization/English_xml.pak/'
xml_text_ui_items = 'text_ui_items.xml'

# IPL_GameData.pak for icons
compressed_icons = 'D:/SteamLibrary/steamapps/common/KingdomComeDeliverance2/Data/IPL_GameData.pak'
icons_output_path = './src/KCD2/Data/IPL_GameData.pak/'
dds_icons = 'Libs/UI/Textures/Icons'

# Define the relative path where you want to save the manipulated files
relative_output_path = './src/KCD2'

# Ensure the output directory exists
os.makedirs(relative_output_path, exist_ok=True)

# Initialize the KCD2 data structure
kcd2_data = {
    "version": {},
    "categories": {},
    "equipment_slots": {},
    "weapon_classes": {},
    "dice_badges": {},
    "items": {},
    "icons": {}
}

# Initialize the KCD2 files structure
kcd2_files = {}

def copy_and_extract_files():
    # Copy the version file to the output directory
    copied_version_file = os.path.join(relative_output_path, 'whdlversions.json').replace('\\', '/')
    shutil.copy(version_file, copied_version_file)
    print(f"Copied version file to {copied_version_file}")

    # Extract XML files from Tables.pak
    with zipfile.ZipFile(tables_pak, 'r') as pak:
        for key, file in xml_files.items():
            try:
                file_path = os.path.join(tables_pak_output_path, file.replace('Libs/Tables/', '')).replace('\\', '/')
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with pak.open(file) as source, open(file_path, 'wb') as target:
                    target.write(source.read())
                print(f"Extracted {file} to {file_path}")
                kcd2_files[key] = file_path
            except Exception as e:
                print(f"Error extracting {file} from {tables_pak}: {e}")

    # Extract text_ui_items.xml from English_xml.pak
    with zipfile.ZipFile(english_localization_pak, 'r') as pak:
        try:
            file_path = os.path.join(english_localization_output_path, xml_text_ui_items).replace('\\', '/')
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with pak.open(xml_text_ui_items) as source, open(file_path, 'wb') as target:
                target.write(source.read())
            print(f"Extracted {xml_text_ui_items} to {file_path}")
            kcd2_files['text_ui_items'] = file_path
        except Exception as e:
            print(f"Error extracting {xml_text_ui_items} from {english_localization_pak}: {e}")

    # Extract version information from the copied version file
    version_info = get_version(copied_version_file)
    kcd2_data["version"] = version_info

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
    # Paths to the extracted XML files
    item_file = kcd2_files.get('item')
    item_horse_file = kcd2_files.get('item_horse')
    item_rewards_file = kcd2_files.get('item_rewards')

    # Parse the XML files
    item_tree = ET.parse(item_file)
    item_horse_tree = ET.parse(item_horse_file)
    item_rewards_tree = ET.parse(item_rewards_file)

    # Get the root elements
    item_root = item_tree.getroot()
    item_horse_root = item_horse_tree.getroot()
    item_rewards_root = item_rewards_tree.getroot()

    # Merge the <ItemClasses> elements
    item_classes = item_root.find('ItemClasses')
    item_horse_classes = item_horse_root.find('ItemClasses')
    item_rewards_classes = item_rewards_root.find('ItemClasses')

    for elem in item_horse_classes:
        elem.tag = 'Horse' if elem.tag == 'Armor' else elem.tag
        item_classes.append(elem)

    for elem in item_rewards_classes:
        item_classes.append(elem)

    # Ensure the output directory exists
    output_dir = './src/Data'
    os.makedirs(output_dir, exist_ok=True)

    # Write the merged XML to a new file with pretty print
    output_file = os.path.join(output_dir, 'items_merged.xml').replace('\\', '/')
    xml_str = ET.tostring(item_tree.getroot(), encoding='utf-8')
    pretty_xml_as_str = minidom.parseString(xml_str).toprettyxml(indent="    ")
    pretty_xml_as_str = re.sub(r'\n\s*\n', '\n', pretty_xml_as_str)  # Remove excess blank lines
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(pretty_xml_as_str)
    print(f"Merged items written to {output_file}")

def purge_items():
    # Path to the merged XML file
    merged_file = './src/Data/items_merged.xml'

    # Parse the merged XML file
    tree = ET.parse(merged_file)
    root = tree.getroot()

    # Elements to remove
    elements_to_remove = ['NPCTool', 'MiscItem', 'Food', 'Herb', 'PickableItem', 'Poison', 'AlchemyBase', 'Ointment', 'Ammo', 'CraftingMaterial']

    # Remove specified elements
    for item_classes in root.findall('.//ItemClasses'):
        for elem in list(item_classes):
            if elem.tag in elements_to_remove or elem.get('UIName') == 'ui_nm_torch':
                item_classes.remove(elem)

    # Remove child elements of <Document> and convert to self-closing tags
    for document in root.findall('.//Document'):
        for child in list(document):
            document.remove(child)
        document.text = None

    # Sort elements alphabetically by tag name
    for item_classes in root.findall('.//ItemClasses'):
        item_classes[:] = sorted(item_classes, key=lambda child: child.tag)

    # Handle ItemAlias elements
    item_aliases = root.findall('.//ItemAlias')
    parent_map = {c: p for p in root.iter() for c in p}
    aliases_to_remove = []

    # Create a dictionary to store aliases by their SourceItemId
    alias_dict = {}
    for item_alias in item_aliases:
        source_item_id = item_alias.get('SourceItemId')
        if source_item_id:
            if source_item_id not in alias_dict:
                alias_dict[source_item_id] = []
            alias_dict[source_item_id].append(item_alias)
        else:
            aliases_to_remove.append(item_alias)

    # Insert aliases directly below their matching items
    for source_item_id, aliases in alias_dict.items():
        target_element = root.find(f".//*[@Id='{source_item_id}']")
        if target_element is not None:
            parent = parent_map[target_element]
            target_index = list(parent).index(target_element) + 1
            for alias in aliases:
                parent.remove(alias)  # Remove from current position
                parent.insert(target_index, alias)
        else:
            aliases_to_remove.extend(aliases)

    # Remove ItemAlias elements that do not have a matching partner
    for item_alias in aliases_to_remove:
        parent = parent_map[item_alias]
        parent.remove(item_alias)

    # Write the purged XML to a new file with pretty print
    output_file = os.path.join('./src/Data', 'items_purged.xml').replace('\\', '/')
    xml_str = ET.tostring(root, encoding='utf-8')
    pretty_xml_as_str = minidom.parseString(xml_str).toprettyxml(indent="    ")
    pretty_xml_as_str = re.sub(r'\n\s*\n', '\n', pretty_xml_as_str)  # Remove excess blank lines
    pretty_xml_as_str = re.sub(r'<Document></Document>', '<Document />', pretty_xml_as_str)  # Convert to self-closing tags
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(pretty_xml_as_str)
    print(f"Purged items written to {output_file}")

    # Output unique element names under ItemClasses to the console
    item_classes = root.find('ItemClasses')
    if item_classes is not None:
        unique_elements = set(elem.tag for elem in item_classes)
        for elem_name in unique_elements:
            print(elem_name)

def purge_elements():
    # Path to the purged XML file
    purged_file = './src/Data/items_purged.xml'

    # Parse the purged XML file
    tree = ET.parse(purged_file)
    root = tree.getroot()

    # Elements to remove
    elements_to_remove = ['Visibility', 'Noise', 'SocialClassID', 'WealthLevel']

    # Remove specified elements
    for item_classes in root.findall('.//ItemClasses'):
        for elem in list(item_classes):
            if elem.tag in elements_to_remove:
                item_classes.remove(elem)

    # Write the updated XML to the same file with pretty print
    xml_str = ET.tostring(root, encoding='utf-8')
    pretty_xml_as_str = minidom.parseString(xml_str).toprettyxml(indent="    ")
    pretty_xml_as_str = re.sub(r'\n\s*\n', '\n', pretty_xml_as_str)  # Remove excess blank lines
    pretty_xml_as_str = re.sub(r'<Document></Document>', '<Document />', pretty_xml_as_str)  # Convert to self-closing tags
    with open(purged_file, 'w', encoding='utf-8') as f:
        f.write(pretty_xml_as_str)
    print(f"Updated items written to {purged_file}")

# Perform the copy and extraction operations
copy_and_extract_files()

# Merge the items
merge_items()

# Purge unnecessary elements
purge_items()

# Purge specific elements
purge_elements()

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

print(kcd2_files)