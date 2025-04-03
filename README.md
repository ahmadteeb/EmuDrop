# EmuDrop

A modern, user-friendly game ROM downloader application developed for Trimui Smart Pro using Python and SDL2. This application provides a sleek interface for browsing and downloading retro game ROMs with a controller-friendly design.

## Features

- 🎮 Controller Support: Full gamepad support for easy navigation
- ⌨️ On-screen Keyboard: Virtual keyboard for search functionality
- 📱 Modern UI: Clean and intuitive interface built with SDL2
- 🗂️ Category Management: Browse games by platform/category
- ⬇️ Download Management: Track and manage game downloads
- 🖼️ Rom Imgs Scrapping: Built-in image cover scrapper
- 🔍 Search Functionality: Find games quickly
- 📺 Game Preview: View game information and images
- 🎯 Progress Tracking: Visual feedback for downloads
- 💾 Multi-format Support: Handles various ROM formats and compression
- 🔄 Auto Updates: Built-in OTA updates for seamless app maintenance

## Requirements

- Python 3.6+
- SDL2 and its dependencies
- Required Python packages (listed in requirements.txt)

## Installation
1. Download the latest release.

2. Extract the downloaded file to:
    - /mnt/SDCARD/Apps/

## Cross-Compiling

1. Clone the repository:
```bash
git clone [repository-url]
cd EmuDrop
```

2. Using WSL2 run the docker container inside tools directory and place the code inside workspace:
```bash
sudo make shell
```

3. Cross compiling the app to Trimui Smart Pro:
```bash
pyinstaller --onefile --noconsole --name EmuDrop main.py
```
4. Place the EmuDrop file from dist/ directory platform/Trimui Smart Pro/EmuDrop
```bash
cp dist/EmuDrop/ platform/Trimui Smart Pro/EmuDrop
```

5. Copy EmuDrop directory to /mnt/SDCARD/Apps/

## Testing

1. Start the application:
```bash
python main.py
```

2. Navigation:
   - Use arrow keys or controller D-pad to navigate menus
   - Press Enter/A to select
   - Press Esc/B to return to previous menu
   - Use the on-screen keyboard for search

3. Downloading Games:
   - Browse categories or search for specific games
   - Select a game to view details
   - Confirm download when prompted
   - Monitor download progress in the downloads view

## Project Structure

- `app.py`: Main application class and core functionality
- `main.py`: Application entry point
- `ui/`: User interface components
- `utils/`: Utility functions and helpers
- `data/`: Data management and storage
- `platform/`: Platform-specific implementations
- `tools/toolchain`: Toolchain for Trimui Smart Pro using docker image
- `tools/roms scrapper`: Scrapping the Game Roms links from https://www.consoleroms.com.
- `assets/`: Images, fonts, and other resources

## Development

The application is built using:
- PySDL2 for graphics and input handling
- Custom UI components for a controller-friendly interface
- Asynchronous download management
- Efficient resource management with texture caching
- Modular architecture for easy maintenance

## Logging

The application maintains two log files:
- `EmuDrop.log`: General application logs

## Contributing
Contributions are welcome! Please feel free to submit pull requests.

## Acknowledgments

- SDL2 and PySDL2 teams
- Contributors and maintainers
