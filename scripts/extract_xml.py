import os
import zipfile
import json
from pathlib import Path

# Load game path from config
config_file = Path(__file__).resolve().parent.parent / "config" / "game_path.json"
with open(config_file, 'r') as f:
    config = json.load(f)
game_path = Path(config["game_path"])

# Define paths
tables_pak = game_path / 'Data' / 'Tables.pak'
english_localization_pak = game_path / 'Localization' / 'English_xml.pak'

# Define base paths
base_dir = Path(__file__).resolve().parent.parent
output_dir = base_dir / 'src/data/xml'

# Ensure output directories exist
output_dir.mkdir(parents=True, exist_ok=True)

# Initialize the KCD2 files structure
kcd2_xmls = {}

def extract_files(logger, kcd2_xmls):
    copied_files = 0
    skipped_files = 0
    failed_files = 0

    logger.info("Processing PAK files...")

    # Define the list of pak files to process
    pak_files = [
        (english_localization_pak, 'text_ui_items.xml', output_dir / 'text_ui_items.xml'),
        (tables_pak, 'Libs/Tables/item/', output_dir)
    ]

    for pak_file, prefix, output_path in pak_files:
        logger.info(f"Processing PAK file: {os.path.basename(pak_file)}")
        with zipfile.ZipFile(pak_file, 'r') as pak:
            for file in pak.namelist():
                if file.startswith(prefix) and file.endswith('.xml') and 'preset' not in file.lower():
                    relative_path = file.replace(prefix, '')
                    file_path = (output_path / relative_path).as_posix()
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    extracted_file_path = (output_path / relative_path).as_posix()
                    
                    # Replace double underscores with a single underscore in the filename
                    XmlId = os.path.splitext(os.path.basename(file_path))[0].replace('__', '_')
                    file_path = file_path.replace('__', '_')
                    extracted_file_path = extracted_file_path.replace('__', '_')
                    
                    if XmlId in kcd2_xmls:
                        skipped_files += 1
                        logger.debug(f"Skipped extracting (already exists): {os.path.relpath(file_path, base_dir)}")
                        continue

                    try:
                        with pak.open(file) as source, open(file_path, 'wb') as target:
                            target.write(source.read())
                        kcd2_xmls[XmlId] = os.path.relpath(file_path, base_dir).replace('\\', '/')
                        copied_files += 1
                        logger.debug(f"Extracted {file} from {pak_file} to {os.path.relpath(file_path, base_dir)}")
                    except Exception as e:
                        failed_files += 1
                        logger.error(f"Failed to extract {file} from {pak_file} to {os.path.relpath(file_path, base_dir)}: {e}")

    return copied_files, skipped_files, failed_files, kcd2_xmls