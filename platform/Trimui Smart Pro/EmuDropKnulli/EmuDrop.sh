#!/bin/bash
export PYSDL2_DLL_PATH="/usr/lib/"

APP_DIR=$(dirname "$0")
cd $APP_DIR

python -B ./scripts/main_updater.py
if [ $? -eq 1 ]; then
    exit 1
fi


export ROMS_DIR="/userdata/roms/"
export IMGS_DIR="$ROMS_DIR/{SYSTEM}/images/{IMAGE_NAME}-image.png"
export EXECUTABLES_DIR="$APP_DIR/assets/executables/"

./EmuDrop