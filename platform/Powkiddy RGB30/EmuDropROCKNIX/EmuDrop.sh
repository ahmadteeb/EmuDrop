#!/bin/bash
APP_DIR=$(dirname "$0")
cd "$APP_DIR"

chmod -R 777 "$APP_DIR/EmuDrop"

# ROCKNIX uses SwayWM (Wayland) + Mali G52 GPU
export SDL_VIDEODRIVER=wayland
export SDL_RENDER_DRIVER=opengles2
export PYSDL2_DLL_PATH="/usr/lib/"
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/lib/

echo "Checking internet connection..."
if ping -c 1 8.8.8.8 > /dev/null 2>&1; then
    echo "Internet connection detected."
else
    echo "No internet connection."
    exit 1
fi

./EmuDrop/db_ota.sh

#echo performance >/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
#echo 1608000 >/sys/devices/system/cpu/cpu0/cpufreq/scaling_min_freq
#echo 1 > /tmp/stay_awake

export ROMS_DIR="/storage/roms/"
export IMGS_DIR="/storage/roms/{SYSTEM}/images/{IMAGE_NAME}-image.png"
export EXECUTABLES_DIR="$APP_DIR/EmuDrop/assets/executables/"

./EmuDrop/EmuDrop
#rm /tmp/stay_awake
