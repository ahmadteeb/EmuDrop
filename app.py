"""
Main application module for the Game Downloader.

This module contains the core application class that handles the UI, game downloads,
and user interaction for the Game Downloader application.
"""
from typing import Dict, Optional, Tuple, Union, List
import ctypes
import os
import math

# SDL imports
import sdl2
import sdl2.ext
import sdl2.sdlttf
import sdl2.sdlimage

# Local imports
from utils.config import Config
from data.categories import CategoryManager
from data.games import GameManager
from utils.logger import logger
from utils.texture_manager import TextureManager
from ui.loading_screen import LoadingScreen
from utils.download_manager import DownloadManager
from utils.theme import Theme
from ui.confirmation_dialog import ConfirmationDialog
from ui.download_view import DownloadView
from ui.categories_view import CategoriesView
from ui.games_view import GamesView
from ui.keyboard_view import KeyboardView

class GameDownloaderApp:
    """
    Main application class for the game downloader.
    
    This class manages the application lifecycle, including:
    - SDL initialization and cleanup
    - Window and renderer management
    - User input handling
    - Game downloading and status tracking
    - UI rendering and state management
    """

    def __init__(self) -> None:
        """
        Initialize the application.
        
        Raises:
            RuntimeError: If SDL initialization or resource loading fails.
        """
        try:
            # Initialize SDL subsystems
            self._initialize_sdl()

            # Create window and renderer
            self.window: sdl2.SDL_Window = self._create_window()
            self.renderer: sdl2.SDL_Renderer = self._create_renderer()

            # Initialize loading screen
            self.loading_screen = LoadingScreen(
                self.renderer, 
                Config.SCREEN_WIDTH, 
                Config.SCREEN_HEIGHT
            )

            # Initialize managers
            self.texture_manager = TextureManager(self.renderer)
            self.font: sdl2.sdlttf.TTF_Font = self._load_font()
            
            # Initialize views
            self.categories_view = CategoriesView(self.renderer, self.font, self.texture_manager)
            self.games_view = GamesView(self.renderer, self.font, self.texture_manager)
            self.keyboard_view = KeyboardView(self.renderer, self.font, self.texture_manager)
            self.confirmation_dialog = ConfirmationDialog(self.renderer, self.font, self.texture_manager)
            self.download_view = DownloadView(self.renderer, self.font, self.texture_manager)
            
            # Initialize application state
            self._initialize_state()

            # Initialize download tracking
            self.active_downloads: Dict[str, Dict] = {}

        except Exception as e:
            logger.error(f"Initialization error: {str(e)}", exc_info=True)
            self.cleanup()
            raise

    def _initialize_sdl(self) -> None:
        """
        Initialize SDL subsystems (video, joystick, TTF, and image).
        
        Raises:
            RuntimeError: If any SDL subsystem fails to initialize.
        """
        # Video and joystick initialization
        if sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO | sdl2.SDL_INIT_JOYSTICK) < 0:
            error = sdl2.SDL_GetError().decode('utf-8')
            logger.error(f"SDL initialization failed: {error}")
            raise RuntimeError(f"SDL initialization failed: {error}")

        # TTF initialization
        if sdl2.sdlttf.TTF_Init() < 0:
            error = sdl2.sdlttf.TTF_GetError().decode('utf-8')
            logger.error(f"SDL_ttf initialization failed: {error}")
            raise RuntimeError(f"SDL_ttf initialization failed: {error}")

        # Image initialization
        img_flags = sdl2.sdlimage.IMG_INIT_PNG
        if sdl2.sdlimage.IMG_Init(img_flags) != img_flags:
            error = sdl2.SDL_GetError().decode('utf-8')
            logger.error(f"SDL_image initialization failed: {error}")
            raise RuntimeError(f"SDL_image initialization failed: {error}")

        logger.info("SDL subsystems initialized successfully")

    def _create_window(self) -> sdl2.SDL_Window:
        """
        Create the application window.
        
        Returns:
            sdl2.SDL_Window: The created window instance.
            
        Raises:
            RuntimeError: If window creation fails.
        """
        window = sdl2.SDL_CreateWindow(
            b"Game Downloader", 
            sdl2.SDL_WINDOWPOS_CENTERED, 
            sdl2.SDL_WINDOWPOS_CENTERED, 
            Config.SCREEN_WIDTH, 
            Config.SCREEN_HEIGHT, 
            sdl2.SDL_WINDOW_SHOWN | sdl2.SDL_WINDOW_ALLOW_HIGHDPI
        )
        
        if not window:
            error = sdl2.SDL_GetError().decode('utf-8')
            logger.error(f"Window creation failed: {error}")
            raise RuntimeError(f"Window creation failed: {error}")
            
        logger.info("Window created successfully")
        return window

    def _create_renderer(self) -> sdl2.SDL_Renderer:
        """
        Create the SDL renderer, attempting software rendering first.
        
        Returns:
            sdl2.SDL_Renderer: The created renderer instance.
            
        Raises:
            RuntimeError: If both software and hardware rendering fail.
        """
        # Try software renderer first (better for low-power devices)
        renderer_flags = sdl2.SDL_RENDERER_SOFTWARE | sdl2.SDL_RENDERER_PRESENTVSYNC
        renderer = sdl2.SDL_CreateRenderer(self.window, -1, renderer_flags)
        
        if not renderer:
            # Log warning and try hardware acceleration as fallback
            logger.warning("Software renderer failed, attempting hardware acceleration")
            renderer = sdl2.SDL_CreateRenderer(
                self.window, 
                -1,
                sdl2.SDL_RENDERER_ACCELERATED | sdl2.SDL_RENDERER_PRESENTVSYNC
            )
        
        if not renderer:
            error = sdl2.SDL_GetError().decode('utf-8')
            logger.error(f"Renderer creation failed: {error}")
            raise RuntimeError(f"Renderer creation failed: {error}")
            
        renderer_info = sdl2.SDL_RendererInfo()
        sdl2.SDL_GetRendererInfo(renderer, ctypes.byref(renderer_info))
        logger.info(f"Created renderer: {renderer_info.name.decode('utf-8')}")
        
        return renderer

    def _load_font(self) -> sdl2.sdlttf.TTF_Font:
        """
        Load the application font.
        
        Returns:
            sdl2.sdlttf.TTF_Font: The loaded font instance.
            
        Raises:
            RuntimeError: If font loading fails.
        """
        font_path = Config.get_font_path()
        if not font_path:
            logger.error("No suitable font found in configuration")
            raise RuntimeError("No suitable font found")

        font = sdl2.sdlttf.TTF_OpenFont(font_path.encode('utf-8'), Config.FONT_SIZE)
        if not font:
            error = sdl2.sdlttf.TTF_GetError().decode('utf-8')
            logger.error(f"Font loading failed: {error}")
            raise RuntimeError(f"Font loading failed: {error}")
        
        logger.info(f"Loaded font: {font_path}")
        return font

    def _initialize_state(self) -> None:
        """
        Initialize application state variables.
        
        This includes:
        - Joystick/controller setup
        - Navigation state (current page, selection)
        - View mode tracking
        - Game image loading state
        - Confirmation dialog state
        - Keyboard and search state
        """
        # Joystick initialization
        num_joysticks = sdl2.SDL_NumJoysticks()
        logger.info(f"Number of joysticks detected: {num_joysticks}")
        self.joystick: Optional[sdl2.SDL_Joystick] = (
            sdl2.SDL_JoystickOpen(0) if num_joysticks > 0 else None
        )

        # Navigation state
        self.current_category_page: int = 0
        self.current_game_page: int = 0
        self.selected_category: int = 0
        self.selected_game: int = 0
        
        # View mode tracking
        self.view_mode: str = 'categories'  # 'categories', 'games', or 'download_status'
        self.previous_view_mode: Optional[str] = None
        
        # Game image loading state
        self.game_hold_timer: int = 0
        self.is_image_loaded: bool = False
        self.last_selected_game: int = -1
        
        # Confirmation dialog state
        self.showing_confirmation: bool = False
        self.confirmation_selected: bool = False
        self.confirmation_type: Optional[str] = None
        self.game_to_download: Optional[Dict] = None

        # Keyboard and search state
        self.showing_keyboard: bool = False
        self.search_text: str = ""
        self.filtered_games: List[Dict] = []
        self.keyboard_selected_key: int = 0  # Index of selected key on keyboard

    def run(self) -> None:
        """
        Main application run loop.
        
        This method:
        1. Shows the loading screen
        2. Enters the main event loop
        3. Handles timing and frame rate control
        4. Updates the display
        
        The loop continues until the application is closed or encounters an error.
        """
        try:
            # Show loading screen with progress
            self._simulate_loading()

            # Initialize loop variables
            running = True
            last_time = sdl2.SDL_GetTicks()
            frame_delay = 1000 // Config.FPS_LIMIT_LOW_POWER
            
            # Main loop
            while running:
                # Frame timing
                frame_start = sdl2.SDL_GetTicks()
                current_time = sdl2.SDL_GetTicks()
                delta_time = current_time - last_time
                last_time = current_time
                
                # Process events and update state
                running = self._handle_events()
                
                # Update game image loading timer
                if self.view_mode == 'games':
                    self._update_game_image_timer(delta_time)
                
                # Render frame
                self._render()
                
                # Frame rate control
                frame_time = sdl2.SDL_GetTicks() - frame_start
                if frame_time < frame_delay:
                    sdl2.SDL_Delay(frame_delay - frame_time)

        except Exception as e:
            logger.error(f"Runtime error in main loop: {str(e)}", exc_info=True)
            raise
        finally:
            self.cleanup()

    def _update_game_image_timer(self, delta_time: int) -> None:
        """
        Update the game image loading timer.
        
        Args:
            delta_time: Time elapsed since last frame in milliseconds.
        """
        if self.last_selected_game != self.selected_game:
            # Reset timer when selection changes
            self.game_hold_timer = 0
            self.is_image_loaded = False
            self.last_selected_game = self.selected_game
        else:
            # Increment timer while on the same game
            self.game_hold_timer += delta_time
            if self.game_hold_timer >= 500 and not self.is_image_loaded:  # 500ms delay
                self.is_image_loaded = True

    def _simulate_loading(self):
        """Simulate loading stages with progress updates"""
        loading_stages = [
            ("Initializing SDL", 0.1),
            ("Loading Categories", 0.3),
            ("Loading Game Data", 0.5),
            ("Preparing Textures", 0.8),
            ("Ready", 1.0)
        ]

        for stage, progress in loading_stages:
            self.loading_screen.render(progress, stage)
            sdl2.SDL_Delay(500)  # Brief pause to show progress

    def _handle_events(self):
        """Handle SDL events"""
        event = sdl2.SDL_Event()
        while sdl2.SDL_PollEvent(ctypes.byref(event)) != 0:
            if event.type == sdl2.SDL_QUIT:
                return False
            
            # Handle controller button events
            if event.type == sdl2.SDL_JOYBUTTONDOWN:
                if self._handle_controller_button(event.jbutton.button) is False:
                    return False
            
            # Handle controller d-pad button events
            elif event.type == sdl2.SDL_JOYHATMOTION:
                if self._handle_d_pad_controller_button(event.jhat.value) is False:
                    return False
                
            # Handle physical keyboard input
            elif event.type == sdl2.SDL_KEYDOWN:
                if self._handle_physical_keyboard(event.key.keysym.sym) is False:
                    return False

        return True

    def _handle_controller_button(self, button):
        if button == Config.CONTROLLER_BUTTON_A:  # A button -> Enter
            return self._handle_input_event(sdl2.SDLK_RETURN)
            
        elif button == Config.CONTROLLER_BUTTON_B:  # B button -> Backspace
            return self._handle_input_event(sdl2.SDLK_BACKSPACE)
            
        elif button == Config.CONTROLLER_BUTTON_Y:  # Y button -> Spacebar
            if self.view_mode == 'games':
                if not self.showing_keyboard:
                    self.showing_keyboard = True
                    self.keyboard_selected_key = 0
            
        elif button == Config.CONTROLLER_BUTTON_L:  # L button for previous page
            if self.view_mode in ['categories', 'games']:
                self._change_page(-1)
                
        elif button == Config.CONTROLLER_BUTTON_R:  # R button for next page
            if self.view_mode in ['categories', 'games']:
                self._change_page(1)      
        return True

    def _handle_d_pad_controller_button(self, button):
        # Handle D-pad buttons
        if button == Config.CONTROLLER_BUTTON_UP:
            return self._handle_input_event(sdl2.SDLK_UP)
            
        elif button == Config.CONTROLLER_BUTTON_DOWN:
            return self._handle_input_event(sdl2.SDLK_DOWN)
            
        elif button == Config.CONTROLLER_BUTTON_LEFT:
            return self._handle_input_event(sdl2.SDLK_LEFT)
            
        elif button == Config.CONTROLLER_BUTTON_RIGHT:
            return self._handle_input_event(sdl2.SDLK_RIGHT)
        
    def _handle_physical_keyboard(self, key):
        """Handle physical keyboard inputs
        
        Args:
            key: SDL keyboard key code
            
        Returns:
            bool: False if application should exit, True otherwise
        """
        # Handle ESC key for exit
        if key == sdl2.SDLK_ESCAPE:
            return False
            
        # Handle arrow keys
        if key in [sdl2.SDLK_UP, sdl2.SDLK_DOWN, sdl2.SDLK_LEFT, sdl2.SDLK_RIGHT]:
            return self._handle_input_event(key)
            
        # Handle Enter/Return
        if key == sdl2.SDLK_RETURN:
            return self._handle_input_event(sdl2.SDLK_RETURN)
            
        # Handle Backspace
        if key == sdl2.SDLK_BACKSPACE:
            return self._handle_input_event(sdl2.SDLK_BACKSPACE)
            
        # Handle Space for keyboard toggle
        if key == sdl2.SDLK_SPACE and self.view_mode == 'games':
            if not self.showing_keyboard:
                self.showing_keyboard = True
                self.keyboard_selected_key = 0
                
        return True

    def _handle_input_event(self, key):
        """Handle common input logic for both keyboard and controller
        
        Args:
            key: SDL keyboard key code that the input maps to
            
        Returns:
            bool: False if application should exit, True otherwise
        """
        if self.showing_confirmation:
            return self._handle_confirmation_input(key)
        elif self.showing_keyboard and self.view_mode == 'games':
            return self._handle_onscreen_keyboard_input(key)
        else:
            return self._handle_normal_input(key)

    def _handle_confirmation_input(self, key):
        """Handle input when confirmation dialog is showing"""
        if key == sdl2.SDLK_LEFT or key == sdl2.SDLK_RIGHT:
            self.confirmation_selected = not self.confirmation_selected
        elif key == sdl2.SDLK_RETURN:
            self._handle_ok_button()
        elif key == sdl2.SDLK_BACKSPACE:
            self.showing_confirmation = False
            self.game_to_download = None
        return True

    def _handle_onscreen_keyboard_input(self, key):
        """Handle input when on-screen keyboard is showing"""
        if key == sdl2.SDLK_LEFT:
            current_row, current_pos = self.keyboard_view.get_keyboard_position(self.keyboard_selected_key)
            if current_pos > 0:
                self.keyboard_selected_key -= 1
        elif key == sdl2.SDLK_RIGHT:
            current_row, current_pos = self.keyboard_view.get_keyboard_position(self.keyboard_selected_key)
            if current_pos < len(self.keyboard_view.keyboard_layout[current_row]) - 1:
                self.keyboard_selected_key += 1
        elif key == sdl2.SDLK_UP:
            current_row, current_pos = self.keyboard_view.get_keyboard_position(self.keyboard_selected_key)
            if current_row > 0:
                prev_row = self.keyboard_view.keyboard_layout[current_row - 1]
                new_pos = min(current_pos, len(prev_row) - 1)
                self.keyboard_selected_key -= len(self.keyboard_view.keyboard_layout[current_row])
                self.keyboard_selected_key += new_pos - current_pos
        elif key == sdl2.SDLK_DOWN:
            current_row, current_pos = self.keyboard_view.get_keyboard_position(self.keyboard_selected_key)
            if current_row < len(self.keyboard_view.keyboard_layout) - 1:
                next_row = self.keyboard_view.keyboard_layout[current_row + 1]
                new_pos = min(current_pos, len(next_row) - 1)
                self.keyboard_selected_key += len(self.keyboard_view.keyboard_layout[current_row])
                self.keyboard_selected_key += new_pos - current_pos
        elif key == sdl2.SDLK_RETURN:
            # Handle key selection
            current_row, current_pos = self.keyboard_view.get_keyboard_position(self.keyboard_selected_key)
            selected_key = self.keyboard_view.keyboard_layout[current_row][current_pos]
            
            if selected_key == '<':
                if self.search_text:
                    self.search_text = self.search_text[:-1]
            elif selected_key == 'Return':
                self.showing_keyboard = False
            elif selected_key == 'Space':
                self.search_text += ' '
            else:
                self.search_text += selected_key
            
            self._update_filtered_games()
        return True

    def _handle_normal_input(self, key):
        """Handle input in normal navigation mode"""
        if key == sdl2.SDLK_RETURN:
            if self.filtered_games:
                self._handle_ok_button()
            else:
                self._handle_ok_button()
        elif key == sdl2.SDLK_BACKSPACE:
            return self._handle_back_button()
        elif key == sdl2.SDLK_SPACE and self.view_mode == 'games':
            if not self.showing_keyboard:
                self.showing_keyboard = True
                self.keyboard_selected_key = 0
        elif self.view_mode == "categories":
            if key in [sdl2.SDLK_UP, sdl2.SDLK_DOWN, sdl2.SDLK_LEFT, sdl2.SDLK_RIGHT]:
                self._handle_categories_navigation(key)
        elif self.view_mode == "games" and not self.showing_keyboard:
            if key == sdl2.SDLK_UP:
                self._navigate_games(-1)
            elif key == sdl2.SDLK_DOWN:
                self._navigate_games(1)
        return True

    def _handle_categories_navigation(self, key):
        """Handle navigation in categories grid view"""
        total_categories = len(CategoryManager.get_categories())
        if total_categories == 0:
            return

        cards_per_row = 3
        cards_per_page = 9
        current_row = (self.selected_category % cards_per_page) // cards_per_row
        current_col = (self.selected_category % cards_per_page) % cards_per_row
        current_page = self.selected_category // cards_per_page
        total_pages = (total_categories + cards_per_page - 1) // cards_per_page

        if key == sdl2.SDLK_UP:
            # Move up within the current page only
            if current_row > 0:
                new_index = (current_page * cards_per_page) + ((current_row - 1) * cards_per_row) + current_col
                if new_index < total_categories:
                    self.selected_category = new_index

        elif key == sdl2.SDLK_DOWN:
            # Move down within the current page only
            if current_row < 2:  # 2 is the last row (0-based)
                new_index = (current_page * cards_per_page) + ((current_row + 1) * cards_per_row) + current_col
                if new_index < total_categories:
                    self.selected_category = new_index

        elif key == sdl2.SDLK_LEFT:
            # Move left within the current page
            if current_col > 0:
                new_index = (current_page * cards_per_page) + (current_row * cards_per_row) + (current_col - 1)
                if new_index < total_categories:
                    self.selected_category = new_index
            # Move to previous page if at leftmost of current page
            elif current_page > 0:
                new_page = current_page - 1
                new_col = 2  # Rightmost column of previous page
                new_index = (new_page * cards_per_page) + (current_row * cards_per_row) + new_col
                # If position doesn't exist in previous page, move to last valid item
                if new_index >= total_categories:
                    new_index = total_categories - 1
                self.selected_category = new_index
                self.current_category_page = new_page

        elif key == sdl2.SDLK_RIGHT:
            # Move right within the current page
            if current_col < 2:  # 2 is the last column (0-based)
                new_index = (current_page * cards_per_page) + (current_row * cards_per_row) + (current_col + 1)
                if new_index < total_categories:
                    self.selected_category = new_index
            # Move to next page if at rightmost of current page
            elif current_page < total_pages - 1:
                new_page = current_page + 1
                new_col = 0  # Leftmost column of next page
                new_index = (new_page * cards_per_page) + (current_row * cards_per_row) + new_col
                if new_index < total_categories:
                    self.selected_category = new_index
                    self.current_category_page = new_page

    def _handle_ok_button(self):
        """Handle A button press"""
        if self.showing_confirmation:
            if self.confirmation_type == 'download':
                if self.confirmation_selected:  # Yes selected
                    # Start the download
                    self._start_download(self.game_to_download)
                    self.view_mode = 'download_status'
                self.showing_confirmation = False
                self.game_to_download = None
            elif self.confirmation_type == 'cancel':
                if self.confirmation_selected:  # Yes selected
                    # Cancel downloads and go back
                    for download_manager in self.active_downloads.values():
                        download_manager.cancel()
                    self.active_downloads.clear()
                    self.view_mode = self.previous_view_mode or 'games'
                self.showing_confirmation = False
            return

        if self.view_mode == 'categories':
            # Reset search and filtered games when entering a new category
            self.search_text = ""
            self.filtered_games = []
            self.showing_keyboard = False
            
            self.view_mode = 'games'
            self.current_game_page = 0
            self.selected_game = 0
            
            # Reset image loading state
            self.game_hold_timer = 0
            self.is_image_loaded = False
            self.last_selected_game = -1
        elif self.view_mode == 'games':
            self.previous_view_mode = self.view_mode
            # Get the appropriate game list and selected game
            if self.filtered_games:
                selected_index = self.selected_game
                if 0 <= selected_index < len(self.filtered_games):
                    self.game_to_download = self.filtered_games[selected_index]
                    self._show_download_confirmation()
            else:
                self._show_download_confirmation()
        elif self.view_mode == 'download_status':
            # If there are no active downloads, go back to previous view
            if not self.active_downloads:
                self.view_mode = self.previous_view_mode or 'games'

    def _handle_back_button(self):
        """Handle B button press"""
        if self.showing_confirmation:
            # Hide confirmation dialog without action
            self.showing_confirmation = False
            self.game_to_download = None
            return True

        if self.view_mode == 'download_status' and self.active_downloads:
            # Show cancel confirmation dialog
            self.showing_confirmation = True
            self.confirmation_selected = False  # Default to "No"
            self.confirmation_type = 'cancel'
            return True
        elif self.view_mode == 'download_status':
            self.view_mode = self.previous_view_mode or 'games'
        elif self.view_mode == 'games':
            self.view_mode = 'categories'
            self.current_game_page = 0
            self.selected_game = 0
        elif self.view_mode == 'categories':
            # Exit the application when in categories view
            return False
        return True

    def _navigate_categories(self, direction):
        """
        Navigate through categories with improved logic
        
        :param direction: Navigation direction (-1 for left, 1 for right)
        """
        total_categories = len(CategoryManager.get_categories())
        total_category_pages = CategoryManager.get_total_pages(Config.CATEGORIES_PER_PAGE)
        
        # Determine the current page and local index within the page
        current_page = self.selected_category // Config.CATEGORIES_PER_PAGE
        local_index = self.selected_category % Config.CATEGORIES_PER_PAGE
        
        if direction > 0:  # Move right
            # If not at the last category
            if self.selected_category < total_categories - 1:
                # If at the last item of current page, move to next page
                if local_index == Config.CATEGORIES_PER_PAGE - 1 and current_page < total_category_pages - 1:
                    self.current_category_page += 1
                    self.selected_category = current_page * Config.CATEGORIES_PER_PAGE + Config.CATEGORIES_PER_PAGE
                else:
                    # Move to next category on the same page
                    self.selected_category += 1
        else:  # Move left
            # If not at the first category
            if self.selected_category > 0:
                # If at the first item of current page, move to previous page
                if local_index == 0 and current_page > 0:
                    self.current_category_page -= 1
                    self.selected_category = (current_page - 1) * Config.CATEGORIES_PER_PAGE + (Config.CATEGORIES_PER_PAGE - 1)
                else:
                    # Move to previous category on the same page
                    self.selected_category -= 1

    def _navigate_games(self, direction):
        """Navigate through the games list
        
        Args:
            direction: 1 for down, -1 for up
        """
        if self.filtered_games:
            total_games = len(self.filtered_games)
        else:
            current_category = CategoryManager.get_categories()[self.selected_category]
            total_games = len(GameManager.get_games_by_category(current_category['id']))

        if total_games == 0:
            return

        new_selected = self.selected_game + direction
        
        # Handle wrapping around pages
        if new_selected < 0:
            # Go to last page, last item
            total_pages = (total_games + Config.GAMES_PER_PAGE - 1) // Config.GAMES_PER_PAGE
            self.current_game_page = total_pages - 1
            last_page_items = total_games % Config.GAMES_PER_PAGE
            self.selected_game = total_games - 1
        elif new_selected >= total_games:
            # Go to first page, first item
            self.current_game_page = 0
            self.selected_game = 0
        else:
            # Normal navigation within or between pages
            new_page = new_selected // Config.GAMES_PER_PAGE
            if new_page != self.current_game_page:
                self.current_game_page = new_page
            self.selected_game = new_selected

    def _change_page(self, direction):
        """Change the current page in the appropriate view
        
        Args:
            direction: 1 for next page, -1 for previous page
        """
        if self.view_mode == "categories":
            total_categories = len(CategoryManager.get_categories())
            total_pages = (total_categories + Config.CARDS_PER_PAGE - 1) // Config.CARDS_PER_PAGE
            new_page = (self.current_category_page + direction) % total_pages
            self.current_category_page = new_page
            # Update selected category
            self.selected_category = new_page * Config.CARDS_PER_PAGE
            
        elif self.view_mode == "games":
            if self.filtered_games:
                # Handle pagination for search results
                total_pages = (len(self.filtered_games) + Config.GAMES_PER_PAGE - 1) // Config.GAMES_PER_PAGE
            else:
                # Handle pagination for normal category view
                current_category = CategoryManager.get_categories()[self.selected_category]
                total_pages = GameManager.get_total_game_pages(current_category['id'], Config.GAMES_PER_PAGE)
            
            if total_pages > 0:
                new_page = (self.current_game_page + direction) % total_pages
                self.current_game_page = new_page
                # Update selected game
                self.selected_game = new_page * Config.GAMES_PER_PAGE

    def _show_download_confirmation(self):
        """Show confirmation dialog for game download"""
        if self.filtered_games:
            game = self.filtered_games[self.selected_game]
        else:
            category_id = CategoryManager.get_categories()[self.selected_category]['id']
            game = GameManager.get_game(category_id, self.selected_game)
        
        if game:
            # Check if game is already downloading
            if game['name'] in self.active_downloads:
                logger.warning(f"Game {game['name']} is already downloading")
                return
            
            # Create temporary download manager to get size
            download_manager = DownloadManager(
                id=game.get('category_id', CategoryManager.get_categories()[self.selected_category]['id']),
                game_name=game['name'],
                game_url=game.get('game_url', '')
            )
            
            # Get game size
            game_size = download_manager.get_game_size()
            game['size'] = game_size  # Store size for later use
            
            # Store game info and show confirmation
            self.game_to_download = game
            self.showing_confirmation = True
            self.confirmation_selected = False  # Default to "No"
            self.confirmation_type = 'download'

    def _start_download(self, game):
        """Start downloading the selected game"""
        if not game:
            return
            
        try:
            # Create download manager for the game
            download_manager = DownloadManager(
                id=CategoryManager.get_categories()[self.selected_category]['id'],
                game_name=game['name'],
                game_url=game.get('game_url', '')
            )
            
            # Set pre-fetched size if available
            if 'size' in game:
                download_manager.total_size = game['size']
            
            # Start download
            if download_manager.start_download():
                # Track active download with initial status
                self.active_downloads[game['name']] = download_manager
                logger.info(f"Started downloading: {game['name']}")
            else:
                logger.error(f"Failed to start download for: {game['name']}")
        
        except Exception as e:
            logger.error(f"Download error for {game['name']}: {e}")

    def _render(self):
        """Render the current application state"""
        try:
            # Clear the screen
            sdl2.SDL_SetRenderDrawColor(self.renderer, *Theme.BG_DARK, 255)
            sdl2.SDL_RenderClear(self.renderer)

            if self.view_mode == 'categories':
                self.categories_view.render(
                    self.current_category_page,
                    self.selected_category
                )
            elif self.view_mode == 'games':
                # Get the current category ID
                current_category_id = CategoryManager.get_categories()[self.selected_category]['id']
                
                if self.search_text:
                    # When searching, only show filtered games
                    if self.filtered_games:
                        self.games_view.render(
                            current_category_id,
                            self.current_game_page,
                            self.selected_game,
                            show_image=self.is_image_loaded,
                            games_override=self.filtered_games
                        )
                    else:
                        # Show "No matches found" message when search has no results
                        self.games_view.render_text(
                            "No matches found",
                            Config.SCREEN_WIDTH // 2,
                            Config.SCREEN_HEIGHT // 2 - 30,
                            color=(200, 200, 200),
                            center=True
                        )
                else:
                    # Normal game list rendering when not searching
                    self.games_view.render(
                        current_category_id,
                        self.current_game_page,
                        self.selected_game,
                        show_image=self.is_image_loaded
                    )

                # Render keyboard if showing
                if self.showing_keyboard:
                    self.keyboard_view.render(
                        self.keyboard_selected_key,
                        self.search_text
                    )
            elif self.view_mode == 'download_status':
                self.download_view.render(
                    self.active_downloads,
                    self.showing_confirmation
                )

            # Render confirmation dialog if active
            if self.showing_confirmation:
                message = None
                additional_info = []
                
                if self.confirmation_type == 'cancel':
                    message = "Do you want to cancel the download?"
                elif self.confirmation_type == 'download' and self.game_to_download:
                    message = f"Do you want to download?"
                    # Add game name and size as additional info
                    additional_info = [
                        (self.game_to_download.get('name', ''), Theme.TEXT_SECONDARY),
                        (f"Size: {DownloadManager.format_size(self.game_to_download.get('size', 0))}", Theme.TEXT_SECONDARY)
                    ]
                
                self.confirmation_dialog.render(
                    message=message,
                    confirmation_selected=self.confirmation_selected,
                    button_texts=("Yes", "No"),
                    additional_info=additional_info
                )

            # Present the rendered frame
            sdl2.SDL_RenderPresent(self.renderer)

        except Exception as e:
            logger.error(f"Error in render: {str(e)}", exc_info=True)
            raise

    def _wrap_text(self, text, max_width):
        """
        Wrap text to fit within a given width
        
        :param text: Text to wrap
        :param max_width: Maximum width in pixels
        :return: List of wrapped text lines
        """
        words = text.split()
        lines = []
        current_line = []
        current_width = 0
        space_width = 0
        
        # Calculate space width once
        if words and len(words) > 1:
            space_text = sdl2.sdlttf.TTF_RenderText_Blended(
                self.font,
                " ".encode('utf-8'),
                sdl2.SDL_Color(255, 255, 255)
            )
            space_width = space_text.contents.w
            sdl2.SDL_FreeSurface(space_text)
        
        for word in words:
            # Measure word width
            word_surface = sdl2.sdlttf.TTF_RenderText_Blended(
                self.font,
                word.encode('utf-8'),
                sdl2.SDL_Color(255, 255, 255)
            )
            word_width = word_surface.contents.w
            sdl2.SDL_FreeSurface(word_surface)
            
            # Check if adding this word exceeds max width
            if current_line and current_width + space_width + word_width > max_width:
                lines.append(' '.join(current_line))
                current_line = [word]
                current_width = word_width
            else:
                if current_line:  # Add space width if not the first word in line
                    current_width += space_width
                current_line.append(word)
                current_width += word_width
        
        # Add the last line
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines

    def _update_filtered_games(self):
        """Update the filtered games list based on search text"""
        if not self.search_text:
            self.filtered_games = []
            return
        
        # Get all games for current category
        current_category = CategoryManager.get_categories()[self.selected_category]
        all_games = GameManager.get_games_by_category(current_category['id'])
        
        # Filter games based on search text
        
        self.filtered_games = list(filter(lambda game: self.search_text.lower() in game['name'].lower(), all_games))        
        # Reset page and selection when search results change
        self.current_game_page = 0
        self.selected_game = 0

    def cleanup(self) -> None:
        """
        Clean up and release all SDL resources.
        
        This method ensures proper cleanup of:
        - Joystick
        - Font
        - Renderer
        - Window
        - SDL subsystems
        
        It is safe to call this method multiple times.
        """
        logger.info("Starting cleanup...")
        
        # Close joystick if open
        if hasattr(self, 'joystick') and self.joystick:
            sdl2.SDL_JoystickClose(self.joystick)
            self.joystick = None
            logger.debug("Closed joystick")
        
        # Close font if loaded
        if hasattr(self, 'font') and self.font:
            sdl2.sdlttf.TTF_CloseFont(self.font)
            self.font = None
            logger.debug("Closed font")
        
        # Destroy renderer if created
        if hasattr(self, 'renderer') and self.renderer:
            sdl2.SDL_DestroyRenderer(self.renderer)
            self.renderer = None
            logger.debug("Destroyed renderer")
        
        # Destroy window if created
        if hasattr(self, 'window') and self.window:
            sdl2.SDL_DestroyWindow(self.window)
            self.window = None
            logger.debug("Destroyed window")
        
        # Quit SDL subsystems
        sdl2.sdlimage.IMG_Quit()
        sdl2.sdlttf.TTF_Quit()
        sdl2.SDL_Quit()
        logger.info("Cleanup completed successfully") 