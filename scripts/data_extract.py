import os
import json
from datetime import datetime
from logger import logger
import extract_xml
import extract_icon
from pathlib import Path
import shutil

def main():
    # Load game path from config
    config_file = Path(__file__).resolve().parent.parent / "config" / "game_path.json"
    with open(config_file, 'r') as f:
        config = json.load(f)
    game_path = Path(config["game_path"])

    # Define base paths
    base_dir = Path(__file__).resolve().parent.parent
    log_dir = base_dir / 'src/logs'
    data_dir = base_dir / 'src/data'
    xml_dir = data_dir / 'xml'
    icons_dir = data_dir / 'icons'

    # Ensure output directories exist
    log_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    xml_dir.mkdir(parents=True, exist_ok=True)
    icons_dir.mkdir(parents=True, exist_ok=True)

    # Initialize dictionaries
    kcd2_xmls = {}
    kcd2_icons = {}

    # Compare version files
    game_version_file = game_path / 'whdlversions.json'
    data_version_file = data_dir / 'version.json'

    try:
        with open(game_version_file, 'r') as f:
            game_version_data = json.load(f)
        
        if data_version_file.exists():
            with open(data_version_file, 'r') as f:
                data_version_data = json.load(f)

            if game_version_data.get('Preset') == data_version_data.get('Preset'):
                logger.info("Preset dictionaries in version files are identical.")
            else:
                logger.info("Preset dictionaries in version files are different. Updating version file.")
                shutil.copy(game_version_file, data_version_file)
                logger.info(f"Copied version file from {game_version_file} to {data_version_file}")
        else:
            logger.info("Data version file does not exist. Copying game version file.")
            shutil.copy(game_version_file, data_version_file)
            logger.info(f"Copied version file from {game_version_file} to {data_version_file}")
    except Exception as e:
        logger.error(f"Error during version file comparison: {e}")

    # Build kcd2_xmls from existing data
    for root, _, files in os.walk(xml_dir):
        for file in files:
            if file.endswith('.xml'):
                file_path = os.path.join(root, file)
                XmlId = os.path.splitext(os.path.basename(file_path))[0].replace('__', '_')
                kcd2_xmls[XmlId] = os.path.relpath(file_path, base_dir).replace('\\', '/')

    # Build kcd2_icons from existing data
    for root, _, files in os.walk(icons_dir):
        for file in files:
            if file.endswith('.webp'):
                file_path = os.path.join(root, file)
                IconId = os.path.splitext(os.path.basename(file_path))[0].replace('_icon', '')
                kcd2_icons[IconId] = os.path.relpath(file_path, base_dir).replace('\\', '/')

    # Write the initial dictionaries to log files in the logs folder
    with open(log_dir / 'kcd2_xmls_init.json', 'w') as f:
        json.dump(kcd2_xmls, f, indent=4)

    with open(log_dir / 'kcd2_icons_init.json', 'w') as f:
        json.dump(kcd2_icons, f, indent=4)

    # Run XML extraction
    try:
        logger.info("Starting XML extraction process.")
        copied_files, skipped_files, failed_files, kcd2_xmls = extract_xml.extract_files(logger, kcd2_xmls)
        summary_processed_xml = f"Summary of processed XML files: Success: {copied_files}, Skipped: {skipped_files}, Fail: {failed_files}"
        logger.info(summary_processed_xml)
    except Exception as e:
        logger.error(f"Error during XML extraction: {e}")

    # Run icon extraction
    try:
        logger.info("Starting icon extraction process.")
        merge_success_count, merge_fail_count, convert_success_count, convert_fail_count, convert_skipped_count, kcd2_icons = extract_icon.process_icons(logger, kcd2_icons)
        summary_merge_dds = f"Summary of merged DDS files: Success: {merge_success_count}, Skipped: 0, Fail: {merge_fail_count}"
        summary_convert_dds = f"Summary of converted DDS files: Success: {convert_success_count}, Skipped: {convert_skipped_count}, Fail: {convert_fail_count}"
        final_success_count = convert_success_count + merge_success_count
        final_fail_count = convert_fail_count + merge_fail_count - merge_success_count
        logger.info(summary_merge_dds)
        logger.info(summary_convert_dds)
    except Exception as e:
        logger.error(f"Error during icon extraction: {e}")

    # Write the dictionaries to log files in the logs folder
    with open(log_dir / 'kcd2_xmls.json', 'w') as f:
        json.dump(kcd2_xmls, f, indent=4)

    with open(log_dir / 'kcd2_icons.json', 'w') as f:
        json.dump(kcd2_icons, f, indent=4)

    # Create a summary table
    summary_table = (
        f"{'End of Extraction Log'}\n"
        f"{'='*50}\n"
        f"{'Summary':^50}\n"
        f"{'='*50}\n"
        f"{'Operation':<20}{'Success':<10}{'Skipped':<10}{'Fail':<10}\n"
        f"{'-'*50}\n"
        f"{'Processed XML':<20}{copied_files:<10}{skipped_files:<10}{failed_files:<10}\n"
        f"{'Converted DDS':<20}{convert_success_count:<10}{convert_skipped_count:<10}{convert_fail_count:<10}\n"
        f"{'Fixed DDS':<20}{merge_success_count:<10}{0:<10}{merge_fail_count:<10}\n"
        f"{'Final DDS':<20}{final_success_count:<10}{convert_skipped_count:<10}{final_fail_count:<10}\n"
        f"{'='*50}\n"
    )

    logger.info(summary_table)

    return kcd2_xmls, kcd2_icons

if __name__ == "__main__":
    main()