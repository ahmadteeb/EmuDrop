.PHONY: shell release clean
.PHONY: .check .build

TOOLCHAIN_NAME=emudrop-toolchain
DOCKER := $(shell command -v docker 2> /dev/null)
PODMAN := $(shell command -v podman 2> /dev/null)

.check:
ifdef DOCKER
    TOOL=docker
else ifdef PODMAN
    TOOL=podman
else
    $(error "Docker or Podman must be installed!")
endif

# Repo root relative to this Makefile (tools/toolchain/)
REPO_ROOT := $(abspath $(CURDIR)/../..)

.build: .check Dockerfile
	@$(TOOL) run --rm --privileged multiarch/qemu-user-static --reset -p yes > /dev/null 2>&1 || true
	@if [ -z "$$($(TOOL) images -q $(TOOLCHAIN_NAME))" ]; then \
		echo "Image not found, building..."; \
		$(TOOL) build --platform linux/arm64 -t $(TOOLCHAIN_NAME) .; \
		touch .build; \
	else \
		echo "Image already exists, skipping build."; \
	fi

# Open an interactive shell in the toolchain container
# Note: --privileged is needed for QEMU binfmt registration inside the container
# additional slash at beginning is a hack to work in Windows + Git Bash
shell: .check .build
	$(TOOL) run -it --rm --platform linux/arm64 \
		-v /"$(REPO_ROOT)":/root/workspace:z \
		$(TOOLCHAIN_NAME) bash

# Cross-compile and package a complete release in dist/
#
# Usage:
#   make release DEVICE="Powkiddy RGB30" TARGET_OS=ROCKNIX
#   make release DEVICE="Trimui Smart Pro" TARGET_OS=Knulli
#   make release DEVICE="Trimui Smart Pro" TARGET_OS=Crossmix
#   make release DEVICE="Trimui Smart Pro" TARGET_OS=StockOS
release: .check .build
	@test -n "$(DEVICE)" || { echo "Error: DEVICE is required. Usage: make release DEVICE=... TARGET_OS=..." ; exit 1; }
	@test -n "$(TARGET_OS)" || { echo "Error: TARGET_OS is required. Usage: make release DEVICE=... TARGET_OS=..." ; exit 1; }
	@echo "Building EmuDrop release for $(DEVICE) / $(TARGET_OS)..."
	$(TOOL) run --rm --platform linux/arm64 \
		-v "$(REPO_ROOT):/root/workspace:z" \
		$(TOOLCHAIN_NAME) \
		sh -c "cd /root/workspace && \
			rm -rf dist/* && \
			python3 -m PyInstaller --onefile --noconsole --name EmuDrop main.py && \
			mkdir -p dist/.release && \
			cp -r 'os/$(TARGET_OS)/'* dist/.release/ && \
			mkdir -p dist/.release/EmuDrop/assets && \
			mv dist/EmuDrop dist/.release/EmuDrop/EmuDrop && \
			cp -r assets/* dist/.release/EmuDrop/assets/ && \
			cp 'device/$(DEVICE)/'* dist/.release/EmuDrop/assets/ && \
			rm -rf dist/EmuDrop && \
			mv dist/.release/* dist/ && \
			rmdir dist/.release"
	@echo "Release built in $(REPO_ROOT)/dist/"

clean: .check
	-$(TOOL) rmi $(TOOLCHAIN_NAME)
	rm -f .build $(REPO_ROOT)/EmuDrop.spec
	sudo rm -rf $(REPO_ROOT)/dist $(REPO_ROOT)/build
