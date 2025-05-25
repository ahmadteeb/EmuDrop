import requests
import urllib3
import shutil
from pathlib import Path

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Constants
REPO = "ahmadteeb/EmuDrop"
VERSION_FILE = "version.txt"
API_URL = f"https://api.github.com/repos/{REPO}/tags"
DB_FILE_NAME = "catalog.db"

def get_local_version():
    try:
        with open(VERSION_FILE, 'r') as f:
            lines = f.readlines()
            if len(lines) >= 2:
                version = lines[1].strip()
                return version if version else "v0.0.0"
            return "v0.0.0"
    except FileNotFoundError:
        return "v0.0.0"

def get_latest_version():
    try:
        response = requests.get(API_URL, verify=False)
        tags = response.json()
        for tag in tags:
            version = tag['name']
            if version.endswith('-db'):
                version = version[:-3]  # Remove '-db' suffix
                if not version.startswith('v'):
                    version = f"v{version}"
                return version
        return "v0.0.0"
    except Exception as e:
        print(f"Error getting latest version: {e}")
        return "v0.0.0"

def download_latest_release(version):
    url = f"https://github.com/{REPO}/releases/download/{version}-db/catalog-{version}.db"
    try:
        response = requests.get(url, verify=False, stream=True)
        response.raise_for_status()
        with open(DB_FILE_NAME, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"Error downloading release: {e}")
        return False

def clean_local_files():
    db_path = Path("assets") / DB_FILE_NAME
    if db_path.exists():
        db_path.unlink()

def move_db_file():
    assets_dir = Path("assets")
    assets_dir.mkdir(exist_ok=True)
    shutil.move(DB_FILE_NAME, assets_dir / DB_FILE_NAME)

def update_version_file(version):
    # Ensure the file exists and has at least 2 lines
    lines = []
    try:
        with open(VERSION_FILE, 'r') as f:
            lines = f.read().split('\n')
            lines[1] = f"{version}"
            
    except (FileNotFoundError, IndexError):
        lines.append(f"{version}")
        
    finally:
        with open(VERSION_FILE, 'w') as f:
            f.write('\n'.join(lines))
        

def run(infoScreen):
    
    infoScreen.show_message("Checking for update for database")
    
    local_version = get_local_version()
    latest_version = get_latest_version()
    
    print(f"Local version: {local_version}")
    print(f"Latest version: {latest_version}")
    
    if local_version == latest_version:
        infoScreen.show_message(f"You are already on the latest version: {latest_version}", 0.25)
    else:
        infoScreen.show_message(f"New update available: {latest_version}", 0.5)
        infoScreen.show_message("Please wait, this may take a few moments...")
        
        if download_latest_release(latest_version):
            clean_local_files()
            move_db_file()
            update_version_file(latest_version)
            infoScreen.show_message("Database update complete.", 0.25)
        else:
            infoScreen.show_message("Error downloading update. Please try again later.", 1)