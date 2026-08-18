#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

REPO="ahmadteeb/EmuDrop"
VERSION_FILE="version.txt"
API_URL="https://api.github.com/repos/$REPO/tags"
DB_FILE_NAME="catalog.db"

get_local_version() {
    if [[ -f "$VERSION_FILE" && -f "assets/$DB_FILE_NAME" ]]; then
        sed -n '2p' "$VERSION_FILE" | tr -d '[:space:]'
    else
        echo "v0.0.0"
    fi
}

get_latest_version() {
    local latest_version=$(curl -s -k "$API_URL" | grep -o '"name": "[^"]*' | grep '\-db' | head -n 1 | cut -d '"' -f 4)
    if [[ ! $latest_version =~ ^v ]]; then
        latest_version="v$latest_version"
    fi
    echo "${latest_version%-db}"
}

download_latest_release() {
    local version="$1"
    local url="https://github.com/$REPO/releases/download/$version-db/catalog-$version.db"
    echo "Downloading the latest release from: $url"
    if ! curl -L -k -o $DB_FILE_NAME "$url"; then
        echo "Error downloading the release."
        exit 1
    fi
}

clean_local_files() {
    echo "Cleaning local db file if exists"
    rm -f "assets/$DB_FILE_NAME"
}

move_db_file() {
    echo "Moving db file to assets"
    mv $DB_FILE_NAME "assets/$DB_FILE_NAME"
}

update_version_file() {
    touch $VERSION_FILE
    while [ $(wc -l < $VERSION_FILE) -lt 2 ]; do
        echo "" >> $VERSION_FILE
    done
    sed -i "2s/.*/$latest_version/" "$VERSION_FILE"
}

echo "Checking for update for database"

local_version=$(get_local_version)
latest_version=$(get_latest_version)

echo "Local version: $local_version"
echo "Latest version: $latest_version"

if [[ "$local_version" == "$latest_version" ]]; then
    echo "You are already on the latest version: $latest_version"
else
    echo "New update available: $latest_version"
    echo "Please wait, this may take a few moments..."
    download_latest_release "$latest_version"
    clean_local_files
    move_db_file
    update_version_file
    echo "Database update complete."
fi
