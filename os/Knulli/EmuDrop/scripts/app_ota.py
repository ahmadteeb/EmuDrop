import os
import requests
import urllib3
import zipfile
import shutil
from pathlib import Path

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Constants
REPO = "ahmadteeb/EmuDrop"
VERSION_FILE = "version.txt"
API_URL = f"https://api.github.com/repos/{REPO}/tags"
ZIP_FILE_NAME = "EmuDropKnulli.zip"

def get_local_version():
    try:
        with open(VERSION_FILE, 'r') as f:
            version = f.readline().strip()
            return version if version else "v0.0.0"
    except FileNotFoundError:
        return "v0.0.0"

def get_latest_version():
    try:
        response = requests.get(API_URL, verify=False)
        tags = response.json()
        for tag in tags:
            version = tag['name']
            if not version.endswith('-db'):
                if not version.startswith('v'):
                    version = f"v{version}"
                return version
        return "v0.0.0"
    except Exception as e:
        print(f"Error getting latest version: {e}")
        return "v0.0.0"

def download_latest_release(version):
    url = f"https://github.com/{REPO}/releases/download/{version}/{ZIP_FILE_NAME}"
    try:
        response = requests.get(url, verify=False, stream=True)
        response.raise_for_status()
        with open("latest_release.zip", 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"Error downloading release: {e}")
        return False

def clean_local_files():
    current_dir = Path('.')
    for item in current_dir.iterdir():
        if item.name not in ['latest_release.zip']:
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)

def extract_new_version():
    try:
        temp_dir = 'temp_extract'
        with zipfile.ZipFile("latest_release.zip", 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        # Move files from temp_extract to current directory
        temp_dir = Path("temp_extract")
        for item in temp_dir.glob("*/*"):
            shutil.move(str(item), item.name)
        
        # Clean up
        shutil.rmtree("temp_extract")
        os.remove("latest_release.zip")
    except Exception as e:
        print(f"Error extracting files: {e}")

def update_version_file(version):
    # Ensure the file exists and has at least 2 lines
    lines = []
    try:
        with open(VERSION_FILE, 'r') as f:
            lines = f.read().split('\n')
            lines[0] = f"{version}"
            
    except (FileNotFoundError, IndexError):
        lines.append(f"{version}")
        
    finally:
        with open(VERSION_FILE, 'w') as f:
            f.write('\n'.join(lines))

def run(infoScreen):
    infoScreen.show_message("Checking for update for EmuDrop")
    
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
            extract_new_version()
            update_version_file(latest_version)
            infoScreen.show_message("EmuDrop update complete.", 0.25)
        else:
            infoScreen.show_message("Error downloading update. Please try again later.", 1)