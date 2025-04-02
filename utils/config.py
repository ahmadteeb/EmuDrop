import os
import sys

class Config:
    """Application configuration settings"""
    
    # Application metadata
    APP_NAME = "EmuDrop" 
    
    # Screen settings
    SCREEN_WIDTH = 1280
    SCREEN_HEIGHT = 720
    FPS_LIMIT_LOW_POWER = 30  # Lower FPS limit for devices like Trimui Smart Pro

    # Directory paths
    BASE_DIR = os.path.abspath(os.path.dirname(sys.argv[0]))
    ASSETS_DIR = os.path.join(BASE_DIR, 'assets')
    DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")  # For temporary downloads
    ROMS_DIR = '/mnt/SDCARD/Roms/'
    IMGS_DIR = '/mnt/SDCARD/Imgs/'
    
    # Asset subdirectories
    IMAGES_DIR = os.path.join(ASSETS_DIR, 'images')
    IMAGES_CONTROLS_DIR = os.path.join(IMAGES_DIR, 'controls')
    IMAGES_CONSOLES_DIR = os.path.join(IMAGES_DIR, 'consoles')
    IMAGES_CACHE_DIR = os.path.join(IMAGES_DIR, 'cache')
    FONTS_DIR = os.path.join(ASSETS_DIR, 'fonts')
    DEFAULT_IMAGE_PATH = os.path.join(IMAGES_DIR, 'default_game.png')

    # Font settings
    FONT_SIZE = 24
    FONT_NAME = "arial.ttf"

    # Logging settings
    LOG_FILE = f'{APP_NAME}.log'
    LOG_LEVEL = 'INFO'

    # UI Layout settings
    CATEGORIES_PER_PAGE = 4
    GAMES_PER_PAGE = 6
    CARDS_PER_ROW = 3
    CARDS_PER_PAGE = 9
    
    # Card dimensions
    CARD_WIDTH = 250
    CARD_HEIGHT = 180
    CARD_IMAGE_HEIGHT = 120
    GRID_SPACING = 10

    # Game list settings
    GAME_LIST_ITEM_HEIGHT = 80
    GAME_LIST_SPACING = 12
    GAME_LIST_WIDTH = 450
    GAME_LIST_START_Y = 120
    GAME_LIST_IMAGE_SIZE = 400
    GAME_LIST_CARD_PADDING = 20
    GAME_LIST_SPACING_BETWEEN = 120

    # Control guide settings
    CONTROL_SIZE = 75
    CONTROL_SPACING = 80
    CONTROL_MARGIN = 80
    CONTROL_BOTTOM_MARGIN = 60

    # Dialog settings
    DIALOG_WIDTH = 600
    DIALOG_HEIGHT = 300
    DIALOG_PADDING = 40
    DIALOG_LINE_HEIGHT = 30
    DIALOG_TITLE_MARGIN = 40
    DIALOG_MESSAGE_MARGIN = 50
    DIALOG_BUTTON_Y = 220
    DIALOG_BUTTON_X = 250
    DIALOG_BUTTON_WIDTH = 100

    # Image cache settings
    IMAGE_CACHE_MAX_SIZE_MB = 500
    IMAGE_DOWNLOAD_MAX_RETRIES = 3
    IMAGE_DOWNLOAD_RETRY_DELAYS = [1, 3, 5]  # Delays between retries in seconds
    IMAGE_DOWNLOAD_TIMEOUT = (30, 30)  # (connect timeout, read timeout)
    
    # Controller button mapping (Trimui Smart Pro)
    CONTROLLER_BUTTON_A = 1      
    CONTROLLER_BUTTON_B = 0      
    CONTROLLER_BUTTON_X = 3      
    CONTROLLER_BUTTON_Y = 2      
    CONTROLLER_BUTTON_L = 4      
    CONTROLLER_BUTTON_R = 5      
    CONTROLLER_BUTTON_SELECT = 6 
    CONTROLLER_BUTTON_START = 7  
    
    # D-pad button mappings
    CONTROLLER_BUTTON_UP = 1     
    CONTROLLER_BUTTON_DOWN = 4   
    CONTROLLER_BUTTON_LEFT = 8  
    CONTROLLER_BUTTON_RIGHT = 2 

    # Animation settings
    ANIMATION_DURATION = 300  # milliseconds
    LOADING_ANIMATION_SPEED = 100  # milliseconds per frame

    @classmethod
    def get_font_path(cls):
        """Find a suitable font file"""
        font_files = [
            os.path.join(cls.FONTS_DIR, cls.FONT_NAME),
            # Add more fallback fonts if needed
        ]
        
        for font_path in font_files:
            if os.path.exists(font_path):
                return font_path
        
        return None 