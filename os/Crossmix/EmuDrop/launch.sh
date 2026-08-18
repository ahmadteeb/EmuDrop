#!/bin/bash
APP_DIR=$(dirname "$0")
cd $APP_DIR

chmod -R 777 .

export PYSDL2_DLL_PATH="/usr/trimui/lib/"
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/mnt/SDCARD/System/lib/
export INFOSCREEN="/mnt/SDCARD/System/usr/trimui/scripts/infoscreen.sh"

$INFOSCREEN -m "Checking internet connection..." -t 0.2

if ping -c 1 8.8.8.8 > /dev/null 2>&1; then
    $INFOSCREEN -m "Internet connection detected." -t 0.1
else 
    $INFOSCREEN -m "No internet connection. Press B to exit." -k B
    exit
fi

./app_ota.sh
./db_ota.sh

echo performance >/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
echo 1608000 >/sys/devices/system/cpu/cpu0/cpufreq/scaling_min_freq
echo 1 > /tmp/stay_awake #keep screen awake

export ROMS_DIR="/mnt/SDCARD/Roms/"
export IMGS_DIR="/mnt/SDCARD/Imgs/{SYSTEM}/{IMAGE_NAME}.png"
export EXECUTABLES_DIR="$APP_DIR/assets/executables/"

./EmuDrop
rm /tmp/stay_awake