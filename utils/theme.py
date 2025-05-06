class Theme:
    """Modern UI theme configuration"""
    
    # Background colors
    BG_DARK = (18, 18, 24, 255)  # Dark background
    BG_DARKER = (12, 12, 16, 255)  # Darker background for gradient
    
    # Card colors
    CARD_BG = (28, 28, 36)  # Card background
    CARD_SELECTED = (38, 38, 48)  # Selected card background
    CARD_BORDER = (48, 48, 64)  # Card border
    SELECTION_BG = (45, 45, 60)  # Selected item background
    
    # Text colors
    TEXT_PRIMARY = (255, 255, 255)  # Primary text color
    TEXT_SECONDARY = (180, 180, 200)  # Secondary text color
    TEXT_ACCENT = (130, 160, 255)  # Accent text color
    TEXT_TITLE = (230, 230, 255)  # Title text color
    TEXT_PLACEHOLDER = (100, 100, 120)  # Placeholder text color
    TEXT_DISABLED = (150, 150, 150)  # Disabled text color
    TEXT_HIGHLIGHT = (255, 200, 100)  # Highlighted text color
    
    # UI effects
    SHADOW_COLOR = (0, 0, 0, 60)  # Shadow with alpha
    GLOW_COLOR = (100, 130, 255, 30)  # Glow effect with alpha
    OVERLAY_COLOR = (0, 0, 0, 180)  # Semi-transparent overlay
    
    # Spacing and sizing
    SPACING = 20  # Default spacing between elements
    CARD_PADDING = 15  # Padding inside cards
    BORDER_RADIUS = 8  # Border radius for rounded corners
    
    # Animation constants
    ANIMATION_SPEED = 0.3  # Animation duration in seconds
    HOVER_SCALE = 1.05  # Scale factor for hover effects
    
    # Loading screen colors
    LOADING_BG = BG_DARKER
    LOADING_SPINNER = TEXT_ACCENT
    LOADING_PROGRESS = (100, 130, 255)
    LOADING_PROGRESS_BG = (38, 38, 48)
    
    # Button styles
    BUTTON_BG = (60, 80, 255)
    BUTTON_TEXT = TEXT_PRIMARY
    BUTTON_BORDER = (80, 100, 255)
    BUTTON_DISABLED_BG = (70, 70, 70)
    
    # Input field styles
    INPUT_BG = (28, 28, 36)
    INPUT_BORDER = CARD_BORDER
    INPUT_TEXT = TEXT_PRIMARY
    INPUT_PLACEHOLDER = (100, 100, 120)
    
    # Dialog styles
    DIALOG_BG = (40, 40, 40)
    DIALOG_BORDER = (80, 80, 80)
    DIALOG_SHADOW = SHADOW_COLOR
    DIALOG_TITLE = TEXT_PRIMARY
    DIALOG_MESSAGE = (200, 200, 200)
    
    # Progress bar styles
    PROGRESS_BAR_BG = (50, 50, 50)
    PROGRESS_BAR_FILL = (180, 180, 200)
    PROGRESS_BAR_BORDER = (100, 100, 100)
    PROGRESS_BAR_TEXT = (200, 200, 200)
    
    # Status colors
    SUCCESS = (0, 255, 100)
    ERROR = (255, 100, 100)
    WARNING = (255, 180, 100)
    INFO = TEXT_ACCENT
    
    # Confirmation dialog colors
    CONFIRM_YES_SELECTED = SUCCESS
    CONFIRM_YES_UNSELECTED = TEXT_DISABLED
    CONFIRM_NO_SELECTED = SUCCESS
    CONFIRM_NO_UNSELECTED = TEXT_DISABLED
    
    # Keyboard styles
    KEYBOARD_KEY_BG = (60, 60, 60)
    KEYBOARD_KEY_SELECTED = (80, 140, 240)
    KEYBOARD_KEY_BORDER = (80, 80, 80)
    KEYBOARD_KEY_TEXT = (200, 200, 200)
    KEYBOARD_KEY_TEXT_SELECTED = (255, 255, 255)
    KEYBOARD_SPECIAL_KEY_BG = (55, 55, 55)
    KEYBOARD_SPECIAL_KEY_BORDER = (120, 120, 120)
    
    # Spinner animation
    SPINNER_COLOR = (0, 150, 255)
    
    # Scroll bar colors
    SCROLL_BAR_BG = (40, 40, 40, 255)  # Dark background for scroll bar
    SCROLL_BAR_THUMB = (80, 80, 80, 255)  # Thumb color for scroll bar
    SCROLL_BAR_BORDER = (60, 60, 60, 255)  # Border color for scroll bar
    
    @staticmethod
    def get_hover_color(base_color):
        """Brighten a color for hover effects"""
        return tuple(min(255, c + 20) for c in base_color)
    
    @staticmethod
    def get_pressed_color(base_color):
        """Darken a color for pressed effects"""
        return tuple(max(0, c - 20) for c in base_color)
    
    @staticmethod
    def get_disabled_color(base_color):
        """Desaturate a color for disabled state"""
        gray = sum(base_color) // 3
        return tuple(int(c * 0.7 + gray * 0.3) for c in base_color)