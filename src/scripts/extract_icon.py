import os
import re
import shutil
import zipfile
import subprocess
import json
from PIL import Image
from pathlib import Path
from constants.dir_constants import GAME_DIR

# Define paths
compressed_icons = GAME_DIR / 'Data' / 'IPL_GameData.pak'

# Define base paths
base_dir = Path(__file__).resolve().parent.parent.parent
dds_unsplitter_path = base_dir / 'src/bin/DDS-Unsplitter.exe'
texconv_path = base_dir / 'src/bin/texconv.exe'  # Path to texconv.exe

output_dir = base_dir / 'src/data/icons'
temp_dds_dir = output_dir / 'temp'
conv_dds_dir = temp_dds_dir / 'conv'

# Ensure output directories exist
output_dir.mkdir(parents=True, exist_ok=True)
temp_dds_dir.mkdir(parents=True, exist_ok=True)
conv_dds_dir.mkdir(parents=True, exist_ok=True)

def is_empty_directory_tree(directory):
    for root, _, files in os.walk(directory):
        if files:
            return False
    return True

def process_icons(logger, kcd2_icons):
    merge_success_count = 0
    merge_fail_count = 0
    convert_success_count = 0
    convert_fail_count = 0
    convert_skipped_count = 0

    def extract_icons_from_pak():
        nonlocal convert_skipped_count
        logger.info("Processing Icons...")
        with zipfile.ZipFile(compressed_icons, 'r') as pak:
            for file in pak.namelist():
                if file.startswith('Libs/UI/Textures/Icons/Items/'):
                    file_path = (temp_dds_dir / os.path.relpath(file, 'Libs/UI/Textures/Icons/Items')).as_posix()
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    IconId = re.sub(r'\.[^.]+$', '', os.path.splitext(os.path.basename(file_path))[0].replace('_icon', ''))
                    if IconId in kcd2_icons:
                        logger.debug(f"Skipped extracting (already exists): {os.path.relpath(file_path, base_dir)}")
                        convert_skipped_count += 1
                        continue

                    with pak.open(file) as source, open(file_path, 'wb') as target:
                        target.write(source.read())
                    logger.debug(f"Extracted {file} to {os.path.relpath(file_path, base_dir)}")

    def convert_dds_to_webp(directory):
        nonlocal convert_success_count, convert_fail_count, convert_skipped_count
        logger.info(f"Converting DDS files to WEBP format in {directory}...")
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith('.dds') and not any(char.isdigit() for char in file.split('.')[-1]):
                    dds_file_path = os.path.join(root, file)
                    IconId = os.path.splitext(os.path.basename(file))[0].replace('_icon', '')
                    webp_file_path = (output_dir / os.path.relpath(dds_file_path, directory)).with_suffix('.webp').as_posix()
                    os.makedirs(os.path.dirname(webp_file_path), exist_ok=True)
                    try:
                        with Image.open(dds_file_path) as img:
                            img.save(webp_file_path, 'WEBP')
                        kcd2_icons[IconId] = os.path.relpath(webp_file_path, base_dir).replace('\\', '/')
                        os.remove(dds_file_path)  # Delete the original file after successful conversion
                        logger.debug(f"Successfully converted {os.path.basename(dds_file_path)} to {os.path.basename(webp_file_path)} using Pillow")
                        convert_success_count += 1
                    except Exception as e:
                        logger.error(f"Failed to convert {os.path.basename(dds_file_path)} to {os.path.basename(webp_file_path)} using Pillow: {e}")
                        convert_fail_count += 1

    def use_dds_unsplitter():
        nonlocal merge_success_count, merge_fail_count
        logger.info("Using DDS-Unsplitter on failed DDS Files...")
        for root, _, files in os.walk(temp_dds_dir):
            for file in files:
                if file.endswith('.dds'):
                    dds_file_path = os.path.join(root, file)
                    try:
                        process = subprocess.Popen([str(dds_unsplitter_path), dds_file_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        for line in process.stdout:
                            logger.debug(f"DDS-Unsplitter.exe - {line.decode().strip()}")
                        for line in process.stderr:
                            logger.debug(f"DDS-Unsplitter.exe - {line.decode().strip()}")
                        process.wait()
                        if process.returncode != 0:
                            raise subprocess.CalledProcessError(process.returncode, process.args)
                        logger.info(f"Successfully merged {os.path.basename(dds_file_path)} using DDS-Unsplitter.exe")
                        merge_success_count += 1

                        # Delete any .dds.[0-9] files
                        for i in range(10):
                            part_file = f"{dds_file_path}.{i}"
                            if os.path.exists(part_file):
                                os.remove(part_file)
                    except subprocess.CalledProcessError as e:
                        logger.error(f"Failed to merge {os.path.basename(dds_file_path)} using DDS-Unsplitter: {e}")
                        merge_fail_count += 1

    def convert_merged_dds_to_bc7_unorm():
        nonlocal convert_success_count, convert_fail_count
        logger.info("Converting merged DDS files to BC7_UNORM format...")
        for file in os.listdir(temp_dds_dir):
            dds_file_path = os.path.join(temp_dds_dir, file)
            if os.path.isfile(dds_file_path) and file.endswith('.dds'):
                try:
                    texconv_command = [str(texconv_path), '-f', 'BC7_UNORM', '-y', '-o', str(conv_dds_dir), str(dds_file_path)]
                    process = subprocess.Popen(texconv_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    for line in process.stdout:
                        logger.debug(f"texconv.exe - {line.decode().strip()}")
                    for line in process.stderr:
                        logger.debug(f"texconv.exe - {line.decode().strip()}")
                    process.wait()
                    if process.returncode != 0:
                        raise subprocess.CalledProcessError(process.returncode, process.args)
                    logger.info(f"Successfully converted {os.path.basename(dds_file_path)} to BC7_UNORM format using texconv.exe")
                    logger.debug(f"texconv.exe - Command: {' '.join(texconv_command)}")
                    os.remove(dds_file_path)  # Delete the original file after successful conversion
                    convert_success_count += 1
                except Exception as e:
                    logger.error(f"Failed to convert {os.path.basename(dds_file_path)} to BC7_UNORM using texconv.exe: {e}")
                    convert_fail_count += 1

    extract_icons_from_pak()

    # Check if there are files in temp_dds_dir before proceeding
    if not is_empty_directory_tree(temp_dds_dir):
        convert_dds_to_webp(temp_dds_dir)
        
        # Check if there are files in temp_dds_dir before proceeding with unsplitter
        if not is_empty_directory_tree(temp_dds_dir):
            use_dds_unsplitter()
            convert_merged_dds_to_bc7_unorm()
            convert_dds_to_webp(conv_dds_dir)

    # If all conversions are successful, delete the temp_dds directory if it is empty
    if convert_fail_count == 0 and is_empty_directory_tree(temp_dds_dir):
        shutil.rmtree(temp_dds_dir)

    return (merge_success_count, merge_fail_count, 
            convert_success_count, convert_fail_count, 
            convert_skipped_count, kcd2_icons)