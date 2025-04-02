#!/bin/bash
cd $(dirname "$0")
export PYSDL2_DLL_PATH="/usr/lib/"

./ota.sh
./EmuDrop