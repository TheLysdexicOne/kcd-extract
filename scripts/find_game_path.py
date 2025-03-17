import os
import json
from pathlib import Path
import winreg

def find_steam_path():
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam")
        steam_path, _ = winreg.QueryValueEx(key, "InstallPath")
        return steam_path
    except Exception as e:
        print(f"Error finding Steam path: {e}")
        return None

def find_game_path(steam_path, game_name):
    library_folders = [steam_path]
    try:
        with open(os.path.join(steam_path, "steamapps", "libraryfolders.vdf")) as f:
            data = f.read()
            for line in data.splitlines():
                if "path" in line:
                    library_path = line.split('"')[3].replace('\\\\', '\\')
                    library_folders.append(library_path)
    except Exception as e:
        print(f"Error reading libraryfolders.vdf: {e}")

    for library in library_folders:
        game_path = Path(library) / "steamapps" / "common" / game_name
        if game_path.exists():
            return game_path

    return None

def main():
    game_name = "KingdomComeDeliverance2"
    config_path = Path(__file__).resolve().parent.parent / "config"
    config_path.mkdir(parents=True, exist_ok=True)
    config_file = config_path / "game_path.json"

    steam_path = find_steam_path()
    if not steam_path:
        print("Steam path not found.")
        return

    game_path = find_game_path(steam_path, game_name)
    if not game_path:
        print(f"{game_name} not found.")
        return

    with open(config_file, 'w') as f:
        json.dump({"game_path": str(game_path)}, f, indent=4)
    print(f"Game path saved to {config_file}")

if __name__ == "__main__":
    main()