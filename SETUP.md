# EmuDrop Cross-Compilation & Setup

## Prerequisites

Docker with QEMU binfmt registration for ARM64 emulation.

```bash
# Register QEMU (one-time)
docker run --rm --privileged multiarch/qemu-user-static --reset -p yes
```

## Build a Release

```bash
make -C tools/toolchain release DEVICE="Powkiddy RGB30" TARGET_OS=ROCKNIX
make -C tools/toolchain release DEVICE="Trimui Smart Pro" TARGET_OS=Knulli
make -C tools/toolchain release DEVICE="Trimui Smart Pro" TARGET_OS=Crossmix
make -C tools/toolchain release DEVICE="Trimui Smart Pro" TARGET_OS=StockOS
```

This produces `dist/` with the OS-specific layout. For example, ROCKNIX:

```
dist/
├── EmuDrop.sh           ← ES launcher (sits at ports root)
└── EmuDrop/
    ├── EmuDrop          ← ARM64 PyInstaller binary
    ├── db_ota.sh        ← OTA catalog updater
    ├── icon.png         ← ES icon
    └── assets/
        ├── executables/ ← 7z, chdman, etc.
        ├── fonts/       ← arial.ttf
        ├── images/      ← console icons, default image
        ├── settings.json ← device config (screen res, key mapping)
        └── systems.json ← system mappings
```

## Device Installation

### ROCKNIX (Powkiddy RGB30)

ES scans `/storage/roms/ports/` for `.sh` files at root level only.

```bash
export device=192.168.1.xxx
ssh root@$device rm -rf /storage/roms/ports/EmuDrop*
scp -r dist/* root@$device:/storage/roms/ports/
ssh root@$device 'chmod +x /storage/roms/ports/EmuDrop.sh'
# Restart ES or reboot
```

### Knulli

```bash
export device=192.168.1.xxx
ssh root@$device rm -rf /userdata/roms/pygame/EmuDrop*
scp -r dist/* root@$device:/userdata/roms/pygame/
# Restart ES or reboot
```

### Crossmix / Stock OS (Trimui Smart Pro)

```bash
export device=192.168.1.xxx
ssh root@$device rm -rf /mnt/SDCARD/Apps/EmuDrop*
scp -r dist/* root@$device:/mnt/SDCARD/Apps/EmuDrop/
# Restart ES or reboot
```

## Directory Structure

```
device/                  ← hardware-specific config (one folder per device)
├── Powkiddy RGB30/
│   ├── settings.json    ← screen res, key mapping, OS field
│   └── systems.json     ← system name mappings
└── Trimui Smart Pro/
    ├── settings.json
    └── systems.json

os/                      ← OS-specific files; os/<TARGET_OS>/ is the dist/ root
├── ROCKNIX/
│   ├── EmuDrop.sh       ← at dist/ root (ports level)
│   └── EmuDrop/         ← binary, assets, scripts
│       ├── db_ota.sh
│       └── icon.png
├── Knulli/
│   └── EmuDrop/
│       ├── EmuDrop.pygame
│       ├── EmuDropKeyConfig.pygame
│       ├── icon.png
│       └── scripts/
├── Crossmix/
│   └── EmuDrop/
│       ├── launch.sh
│       ├── app_ota.sh
│       ├── db_ota.sh
│       ├── config.json
│       └── icon.png
└── StockOS/
    └── EmuDrop/
        ├── launch.sh
        ├── app_ota.sh
        ├── db_ota.sh
        ├── config.json
        └── icon.png
```

## Files

| File | Purpose |
|------|---------|
| `EmuDrop.sh` | Shell launcher (Wayland, OTA, binary exec) |
| `db_ota.sh` | Catalog DB updater via GitHub releases |
| `assets/settings.json` | OS config, screen resolution, key mapping |
| `EmuDrop` | ARM64 PyInstaller binary |
