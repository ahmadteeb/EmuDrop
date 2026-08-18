# Uses monkeyx/retro_builder:arm64 as base image
#FROM monkeyx/retro_builder:arm64
FROM python:3.13.5-slim

# Remove problematic kitware repo and install QEMU + pip
RUN rm -f /etc/apt/sources.list.d/kitware* && \
    apt-get update && apt-get install -y \
    binutils \
    qemu-user-static \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install -r requirements.txt

VOLUME /root/workspace
WORKDIR /root/workspace

# Starting the container with Bash
CMD ["/bin/bash"]