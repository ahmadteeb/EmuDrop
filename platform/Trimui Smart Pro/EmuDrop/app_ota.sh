#!/bin/bash

# Repository name in the format "owner/repo"
REPO="ahmadteeb/EmuDrop"

# Local version file
VERSION_FILE="version.txt"

# GitHub API URL for tags
API_URL="https://api.github.com/repos/$REPO/tags"

# Expected ZIP file name in the release
ZIP_FILE_NAME="EmuDrop.zip"

# Function to get the local version
get_local_version() {
    if [[ -f "$VERSION_FILE" ]]; then
        sed -n '1p' "$VERSION_FILE" | tr -d '[:space:]'
    else
        echo "v0.0.0" # Default version if the file does not exist
    fi
}

# Function to get the latest version from GitHub
get_latest_version() {
    local latest_version=$(curl -s -k "$API_URL" | grep -o '"name": "[^"]*' | grep -v '\-db' | head -n 1 | cut -d '"' -f 4)
    # If the version does not start with 'v', add the 'v'
    if [[ ! $latest_version =~ ^v ]]; then
        latest_version="v$latest_version"
    fi
    echo "$latest_version"
}

# Function to download the latest release
download_latest_release() {
    local version="$1"
    local url="https://github.com/$REPO/releases/download/$version/$ZIP_FILE_NAME"

    echo "Downloading the latest release from: $url"
    if ! curl -L -k -o latest_release.zip "$url"; then
        echo "Error downloading the release. The file was not deleted."
        exit 1
    fi
}

# Function to clean local files, except ZIP and ota.sh
clean_local_files() {
    echo "Cleaning local files (except ZIP)..."
    find . ! -name latest_release.zip ! -name '.' -exec rm -rf {} +
}

# Function to extract the new version
extract_new_version() {
    echo "Extracting new version..."
    unzip -o latest_release.zip -d temp_extract

    # Move all extracted files to the root of the project
    mv temp_extract/*/* . 2>/dev/null || true

    # Remove the temporary folder
    rm -rf temp_extract

    echo "Removing the ZIP file..."
    rm -f latest_release.zip
}

update_version_file() {
    touch $VERSION_FILE
    # Add empty lines until at least 1 exist
    while [ $(wc -l < $VERSION_FILE) -lt 1 ]; do
        echo "" >> $VERSION_FILE
    done
    
    sed -i "1s/.*/$latest_version/" "$VERSION_FILE"

}

# Main flow
$INFOSCREEN -m "Checking for update for EmuDrop"

local_version=$(get_local_version)
latest_version=$(get_latest_version)

echo "Local version: $local_version"
echo "Latest version: $latest_version"

if [[ "$local_version" == "$latest_version" ]]; then
    $INFOSCREEN -m "You are already on the latest version: $latest_version"
else
    $INFOSCREEN -m "New update available: $latest_version" -t 0.1
    $INFOSCREEN -m "Please wait, this may take a few moments..."
    download_latest_release "$latest_version"
    clean_local_files
    extract_new_version
    update_version_file
    $INFOSCREEN -m "EmuDrop update complete."
fi