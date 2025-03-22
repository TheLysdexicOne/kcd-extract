from pathlib import Path
from build_json import get_version_info

def main():
    # Define the data directory relative to the current script
    base_dir = Path(__file__).resolve().parent.parent  # Adjust to your project structure
    data_dir = base_dir / "src/data"

    # Test the get_version_info function
    try:
        version = get_version_info(data_dir)
        print(f"Extracted version: {version}")
    except FileNotFoundError as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()