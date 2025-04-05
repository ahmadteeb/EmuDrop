"""
Main application module for the Game Downloader.

This module contains the core application class that handles the UI, game downloads,
and user interaction for the Game Downloader application.
"""
from __future__ import annotations
from typing import Dict, Optional, List, Any, Tuple
import ctypes
import os
import math
from dataclasses import dataclass
from contextlib import contextmanager

# Third-party imports
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
from utils.download_manager import DownloadManager
from utils.theme import Theme
from ui.loading_screen import LoadingScreen
from ui.confirmation_dialog import ConfirmationDialog
from ui.download_view import DownloadView
from ui.categories_view import CategoriesView
from ui.games_view import GamesView
from ui.keyboard_view import KeyboardView
from ui.alert_dialog import AlertDialog

class SDLError(Exception):
    """Custom exception for SDL-related errors."""
    pass

@dataclass
class ViewState:
    """Class to hold view-related state"""
    mode: str = 'categories'
    previous_mode: Optional[str] = None
    showing_confirmation: bool = False
    showing_keyboard: bool = False
    confirmation_selected: bool = False
    confirmation_type: Optional[str] = None

@dataclass
class NavigationState:
    """Class to hold navigation-related state"""
    category_page: int = 0
    game_page: int = 0
    selected_category: int = 0
    selected_game: int = 0
    keyboard_selected_key: int = 0

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

    # Class variable to store the singleton instance
    instance = None

    def __init__(self) -> None:
        """
        Initialize the application.
        
        Raises:
            SDLError: If SDL initialization or resource loading fails.
            RuntimeError: If other initialization fails.
        """
        # Set the singleton instance
        GameDownloaderApp.instance = self
        
        try:
            # Initialize SDL subsystems
            self._initialize_sdl()

            # Create window and renderer
            self.window = self._create_window()
            self.renderer = self._create_renderer()

            # Initialize managers and resources
            self.texture_manager = TextureManager(self.renderer)
            self.font = self._load_font()
            self.loading_screen = LoadingScreen(
                self.renderer, 
                Config.SCREEN_WIDTH, 
                Config.SCREEN_HEIGHT
            )
            
            # Initialize views
            self._initialize_views()
            
            # Initialize states
            self.view_state = ViewState()
            self.nav_state = NavigationState()
            self.active_downloads: Dict[str, Dict[str, Any]] = {}
            self.game_hold_timer: int = 0
            self.is_image_loaded: bool = False
            self.last_selected_game: int = -1
            self.search_text: str = ""
            self.filtered_games: List[Dict[str, Any]] = []
            self.selected_download: Optional[str] = None  # Track selected download in download view
            
            # Initialize alert manager
            from utils.alert_manager import AlertManager
            AlertManager.get_instance().set_app(self)
            
            # Initialize joystick if available
            self._initialize_joystick()

        except SDLError as e:
            logger.error(f"SDL initialization error: {str(e)}", exc_info=True)
            self.cleanup()
            raise
        except Exception as e:
            logger.error(f"Initialization error: {str(e)}", exc_info=True)
            self.cleanup()
            raise

    @contextmanager
    def _sdl_error_context(self, operation: str):
        """Context manager for handling SDL errors.
        
        Args:
            operation: Description of the SDL operation being performed.
            
        Raises:
            SDLError: If an SDL error occurs during the operation.
        """
        try:
            yield
        except Exception as e:
            error = sdl2.SDL_GetError().decode('utf-8')
            raise SDLError(f"{operation} failed: {error}") from e

    def _initialize_sdl(self) -> None:
        """Initialize SDL subsystems (video, joystick, TTF, and image)."""
        with self._sdl_error_context("SDL initialization"):
            if sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO | sdl2.SDL_INIT_JOYSTICK) < 0:
                raise SDLError(sdl2.SDL_GetError().decode('utf-8'))

        with self._sdl_error_context("SDL_ttf initialization"):
            if sdl2.sdlttf.TTF_Init() < 0:
                raise SDLError(sdl2.sdlttf.TTF_GetError().decode('utf-8'))

        with self._sdl_error_context("SDL_image initialization"):
            img_flags = sdl2.sdlimage.IMG_INIT_PNG
            if sdl2.sdlimage.IMG_Init(img_flags) != img_flags:
                raise SDLError(sdl2.SDL_GetError().decode('utf-8'))

        logger.info("SDL subsystems initialized successfully")

    def _create_window(self) -> sdl2.SDL_Window:
        """Create the application window."""
        with self._sdl_error_context("Window creation"):
            window = sdl2.SDL_CreateWindow(
                b"Game Downloader", 
                sdl2.SDL_WINDOWPOS_CENTERED, 
                sdl2.SDL_WINDOWPOS_CENTERED, 
                Config.SCREEN_WIDTH, 
                Config.SCREEN_HEIGHT, 
                sdl2.SDL_WINDOW_SHOWN | sdl2.SDL_WINDOW_ALLOW_HIGHDPI
            )
            if not window:
                raise SDLError(sdl2.SDL_GetError().decode('utf-8'))
            
        logger.info("Window created successfully")
        return window

    def _create_renderer(self) -> sdl2.SDL_Renderer:
        """Create the SDL renderer, attempting software rendering first."""
        with self._sdl_error_context("Renderer creation"):
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
                raise SDLError(sdl2.SDL_GetError().decode('utf-8'))
                
            renderer_info = sdl2.SDL_RendererInfo()
            sdl2.SDL_GetRendererInfo(renderer, ctypes.byref(renderer_info))
            logger.info(f"Created renderer: {renderer_info.name.decode('utf-8')}")
            
            return renderer

    def _load_font(self) -> sdl2.sdlttf.TTF_Font:
        """Load the application font."""
        font_path = Config.get_font_path()
        if not font_path:
            raise RuntimeError("No suitable font found in configuration")

        with self._sdl_error_context("Font loading"):
            font = sdl2.sdlttf.TTF_OpenFont(font_path.encode('utf-8'), Config.FONT_SIZE)
            if not font:
                raise SDLError(sdl2.sdlttf.TTF_GetError().decode('utf-8'))
            
            logger.info(f"Loaded font: {font_path}")
            return font

    def _initialize_views(self) -> None:
        """Initialize all UI views with required dependencies."""
        try:
            self.categories_view = CategoriesView(self.renderer, self.font, self.texture_manager)
            self.games_view = GamesView(self.renderer, self.font, self.texture_manager)
            self.keyboard_view = KeyboardView(self.renderer, self.font, self.texture_manager)
            self.confirmation_dialog = ConfirmationDialog(self.renderer, self.font, self.texture_manager)
            self.download_view = DownloadView(self.renderer, self.font, self.texture_manager)
            self.alert_dialog = AlertDialog(self.renderer, self.font, self.texture_manager)
            logger.info("All views initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize views", exc_info=True)
            raise RuntimeError(f"View initialization failed: {str(e)}")

    def _initialize_joystick(self) -> None:
        """Initialize joystick if available."""
        try:
            num_joysticks = sdl2.SDL_NumJoysticks()
            logger.info(f"Number of joysticks detected: {num_joysticks}")
            self.joystick = sdl2.SDL_JoystickOpen(0) if num_joysticks > 0 else None
            if self.joystick:
                logger.info("Joystick initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize joystick: {str(e)}")
            self.joystick = None

    def run(self) -> None:
        """Run the main application loop.
        
        This method handles:
        - Event processing
        - State updates
        - Rendering
        - Frame timing
        """
        try:
            running = True
            last_time = sdl2.SDL_GetTicks()
            
            # Show loading screen
            self._simulate_loading()
            
            while running:
                try:
                    # Handle timing
                    current_time = sdl2.SDL_GetTicks()
                    delta_time = current_time - last_time
                    last_time = current_time
                    
                    # Process events
                    running = self._process_events()
                    
                    # Update game state
                    if self.view_state.mode == 'games':
                        self._update_game_image_timer(delta_time)
                    
                    # Update downloads
                    self._update_downloads()
                    
                    # Render frame
                    self._render()
                    
                    # Cap frame rate
                    frame_time = sdl2.SDL_GetTicks() - current_time
                    if frame_time < Config.FRAME_TIME:
                        sdl2.SDL_Delay(Config.FRAME_TIME - frame_time)
                        
                except Exception as e:
                    logger.error(f"Error in main loop: {str(e)}", exc_info=True)
                    # Continue running unless it's a fatal error
                    if isinstance(e, SDLError):
                        running = False
                        
        except Exception as e:
            logger.error(f"Fatal error in main loop: {str(e)}", exc_info=True)
        finally:
            self.cleanup()

    def _process_events(self) -> bool:
        """Process SDL events.
        
        Returns:
            bool: False if application should exit, True otherwise.
        """
        event = sdl2.SDL_Event()
        while sdl2.SDL_PollEvent(ctypes.byref(event)) != 0:
            if event.type == sdl2.SDL_QUIT:
                return False
                
            elif event.type == sdl2.SDL_KEYDOWN:
                try:
                    if not self._handle_physical_keyboard(event.key.keysym.sym):
                        return False
                except Exception as e:
                    logger.error(f"Error handling keyboard input: {str(e)}", exc_info=True)
                    
            elif event.type == sdl2.SDL_JOYBUTTONDOWN:
                try:
                    if not self._handle_controller_button(event.jbutton.button):
                        return False
                except Exception as e:
                    logger.error(f"Error handling controller input: {str(e)}", exc_info=True)
                    
            elif event.type == sdl2.SDL_JOYHATMOTION:
                try:
                    if not self._handle_d_pad_controller_button(event.jhat.value):
                        return False
                except Exception as e:
                    logger.error(f"Error handling d-pad input: {str(e)}", exc_info=True)
                    
        return True

    def _update_downloads(self) -> None:
        """Update status of active downloads."""
        try:
            # Update each active download
            completed_downloads = []
            
            for game_name, download_info in self.active_downloads.items():
                if 'manager' not in download_info:
                    continue
                    
                manager = download_info['manager']
                
                # Update download progress
                if manager.is_downloading:  # This is a property
                    download_info.update({
                        'status': 'downloading',
                        'progress': manager.download_progress,
                        'speed': manager.download_speed,
                        'current_size': manager.current_size,
                        'total_size': manager.total_size,
                        'eta': 0 if manager.download_speed == 0 else (manager.total_size - manager.current_size) / manager.download_speed
                    })
                elif manager.is_extracting:  # check for extraction
                    download_info['status'] = 'extracting'
                elif manager.is_scrapping: # check for scrapping
                    download_info['status'] = 'scrapping'
                elif manager.download_progress == 100:  # Check for completion
                    download_info['status'] = 'complete'
                    completed_downloads.append(game_name)
                elif manager.download_progress == -1:  # Check for error
                    download_info['status'] = 'error'
                    completed_downloads.append(game_name)
                elif manager.cancel_download.is_set():  # Check for cancellation
                    download_info['status'] = 'cancelled'
                    completed_downloads.append(game_name)
                    
            # Remove completed downloads
            for game_name in completed_downloads:
                del self.active_downloads[game_name]
                
        except Exception as e:
            logger.error(f"Error updating downloads: {str(e)}", exc_info=True)

    def _simulate_loading(self) -> None:
        """Show a loading screen while initializing."""
        try:
            loading_stages = [
                ("Initializing SDL", 0.1),
                ("Loading Categories", 0.3),
                ("Loading Game Data", 0.5),
                ("Preparing Textures", 0.8),
                ("Ready", 1.0)
            ]
            
            for stage, progress in loading_stages:
                self.loading_screen.render(progress, stage)
                sdl2.SDL_Delay(Config.LOADING_ANIMATION_SPEED)
                
        except Exception as e:
            logger.error(f"Error showing loading screen: {str(e)}", exc_info=True)

    def _update_game_image_timer(self, delta_time: int) -> None:
        """Update the game image loading timer.
        
        Args:
            delta_time: Time elapsed since last frame in milliseconds.
        """
        if self.last_selected_game != self.nav_state.selected_game:
            # Reset timer when selection changes
            self.game_hold_timer = 0
            self.is_image_loaded = False
            self.last_selected_game = self.nav_state.selected_game
        else:
            # Increment timer while on the same game
            self.game_hold_timer += delta_time
            if self.game_hold_timer >= Config.IMAGE_LOAD_DELAY and not self.is_image_loaded:
                self.is_image_loaded = True

    def _handle_controller_button(self, button):
        if button == Config.CONTROLLER_BUTTON_A:  # A button -> Enter
            return self._handle_input_event(sdl2.SDLK_RETURN)
            
        elif button == Config.CONTROLLER_BUTTON_B:  # B button -> Backspace
            return self._handle_input_event(sdl2.SDLK_BACKSPACE)

        elif button == Config.CONTROLLER_BUTTON_X:
            return self._handle_input_event(sdl2.SDLK_d)
        
        elif button == Config.CONTROLLER_BUTTON_Y:  # Y button -> Spacebar
            if self.view_state.mode == 'games':
                if not self.view_state.showing_keyboard:
                    self.view_state.showing_keyboard = True
                    self.nav_state.keyboard_selected_key = 0
            
        elif button == Config.CONTROLLER_BUTTON_L:  # L button for previous page
            if self.view_state.mode in ['categories', 'games']:
                self._change_page(-1)
                
        elif button == Config.CONTROLLER_BUTTON_R:  # R button for next page
            if self.view_state.mode in ['categories', 'games']:
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
        return self._handle_input_event(key)

    def _handle_input_event(self, key: int) -> bool:
        """Handle keyboard and controller input events.
        
        Args:
            key: The key or button code that was pressed.
            
        Returns:
            bool: False if application should exit, True otherwise.
        """
        from utils.alert_manager import AlertManager
        alert_manager = AlertManager.get_instance()
        
        if alert_manager.is_showing():
            if key == sdl2.SDLK_RETURN or key == sdl2.SDLK_BACKSPACE:
                alert_manager.hide_alert()
            return True
        elif self.view_state.showing_confirmation:
            return self._handle_confirmation_input(key)
        elif self.view_state.showing_keyboard and self.view_state.mode == 'games':
            return self._handle_onscreen_keyboard_input(key)
        else:
            return self._handle_normal_input(key)

    def _handle_confirmation_input(self, key):
        """Handle input when confirmation dialog is showing"""
        if key == sdl2.SDLK_LEFT or key == sdl2.SDLK_RIGHT:
            self.view_state.confirmation_selected = not self.view_state.confirmation_selected
        elif key == sdl2.SDLK_RETURN:
            self._handle_ok_button()
        elif key == sdl2.SDLK_BACKSPACE:
            self.view_state.showing_confirmation = False
            self.view_state.confirmation_type = None
            self.view_state.confirmation_selected = False
        return True

    def _handle_onscreen_keyboard_input(self, key):
        """Handle input when on-screen keyboard is showing"""
        if key == sdl2.SDLK_LEFT:
            current_row, current_pos = self.keyboard_view.get_keyboard_position(self.nav_state.keyboard_selected_key)
            if current_pos > 0:
                self.nav_state.keyboard_selected_key -= 1
        elif key == sdl2.SDLK_RIGHT:
            current_row, current_pos = self.keyboard_view.get_keyboard_position(self.nav_state.keyboard_selected_key)
            if current_pos < len(self.keyboard_view.keyboard_layout[current_row]) - 1:
                self.nav_state.keyboard_selected_key += 1
        elif key == sdl2.SDLK_UP:
            current_row, current_pos = self.keyboard_view.get_keyboard_position(self.nav_state.keyboard_selected_key)
            if current_row > 0:
                prev_row = self.keyboard_view.keyboard_layout[current_row - 1]
                new_pos = min(current_pos, len(prev_row) - 1)
                self.nav_state.keyboard_selected_key -= len(self.keyboard_view.keyboard_layout[current_row])
                self.nav_state.keyboard_selected_key += new_pos - current_pos
        elif key == sdl2.SDLK_DOWN:
            current_row, current_pos = self.keyboard_view.get_keyboard_position(self.nav_state.keyboard_selected_key)
            if current_row < len(self.keyboard_view.keyboard_layout) - 1:
                next_row = self.keyboard_view.keyboard_layout[current_row + 1]
                new_pos = min(current_pos, len(next_row) - 1)
                self.nav_state.keyboard_selected_key += len(self.keyboard_view.keyboard_layout[current_row])
                self.nav_state.keyboard_selected_key += new_pos - current_pos
        elif key == sdl2.SDLK_RETURN:
            # Handle key selection
            current_row, current_pos = self.keyboard_view.get_keyboard_position(self.nav_state.keyboard_selected_key)
            selected_key = self.keyboard_view.keyboard_layout[current_row][current_pos]
            
            if selected_key == '<':
                if self.search_text:
                    self.search_text = self.search_text[:-1]
            elif selected_key == 'Return':
                self.view_state.showing_keyboard = False
            elif selected_key == 'Space':
                self.search_text += ' '
            else:
                self.search_text += selected_key
            
            self._update_filtered_games()
        return True

    def _handle_normal_input(self, key):
        """Handle input in normal navigation mode"""
        # Handle D key for downloads view
        if key == sdl2.SDLK_d:
            if self.view_state.mode != 'download_status':
                self.view_state.previous_mode = self.view_state.mode
                self.view_state.mode = 'download_status'
                # Select first download if any exist
                if self.active_downloads:
                    self.selected_download = next(iter(self.active_downloads))
       
       # Handle Space for keyboard toggle
        elif key == sdl2.SDLK_SPACE and self.view_state.mode == 'games':
            if not self.view_state.showing_keyboard:
                self.view_state.showing_keyboard = True
                self.nav_state.keyboard_selected_key = 0
                    
        elif key == sdl2.SDLK_RETURN:
            if self.view_state.mode == 'download_status':
                # If a download is selected, show cancel confirmation
                if self.selected_download and self.selected_download in self.active_downloads:
                    self.view_state.showing_confirmation = True
                    self.view_state.confirmation_selected = False  # Default to "No"
                    self.view_state.confirmation_type = 'cancel'
            elif self.filtered_games:
                self._handle_ok_button()
            else:
                self._handle_ok_button()
        elif key == sdl2.SDLK_BACKSPACE:
            return self._handle_back_button()
        elif key == sdl2.SDLK_SPACE and self.view_state.mode == 'games':
            if not self.view_state.showing_keyboard:
                self.view_state.showing_keyboard = True
                self.nav_state.keyboard_selected_key = 0
        elif self.view_state.mode == "categories":
            if key in [sdl2.SDLK_UP, sdl2.SDLK_DOWN, sdl2.SDLK_LEFT, sdl2.SDLK_RIGHT]:
                self._handle_categories_navigation(key)
        elif self.view_state.mode == "games" and not self.view_state.showing_keyboard:
            if key == sdl2.SDLK_UP:
                self._navigate_games(-1)
            elif key == sdl2.SDLK_DOWN:
                self._navigate_games(1)
        elif self.view_state.mode == "download_status":
            # Handle up/down navigation in download view
            if key == sdl2.SDLK_UP or key == sdl2.SDLK_DOWN:
                downloads = list(self.active_downloads.keys())
                if not downloads:
                    return True
                
                if self.selected_download is None:
                    # Select first download if none selected
                    self.selected_download = downloads[0]
                else:
                    # Find current index
                    current_idx = downloads.index(self.selected_download)
                    if key == sdl2.SDLK_UP:
                        # Move up
                        new_idx = (current_idx - 1) if current_idx > 0 else len(downloads) - 1
                    else:
                        # Move down
                        new_idx = (current_idx + 1) if current_idx < len(downloads) - 1 else 0
                    self.selected_download = downloads[new_idx]
        return True

    def _handle_categories_navigation(self, key):
        """Handle navigation in categories grid view"""
        total_categories = len(CategoryManager.get_categories())
        if total_categories == 0:
            return

        cards_per_row = 3
        cards_per_page = 9
        current_row = (self.nav_state.selected_category % cards_per_page) // cards_per_row
        current_col = (self.nav_state.selected_category % cards_per_page) % cards_per_row
        current_page = self.nav_state.selected_category // cards_per_page
        total_pages = (total_categories + cards_per_page - 1) // cards_per_page

        if key == sdl2.SDLK_UP:
            # Move up within the current page only
            if current_row > 0:
                new_index = (current_page * cards_per_page) + ((current_row - 1) * cards_per_row) + current_col
                if new_index < total_categories:
                    self.nav_state.selected_category = new_index

        elif key == sdl2.SDLK_DOWN:
            # Move down within the current page only
            if current_row < 2:  # 2 is the last row (0-based)
                new_index = (current_page * cards_per_page) + ((current_row + 1) * cards_per_row) + current_col
                if new_index < total_categories:
                    self.nav_state.selected_category = new_index

        elif key == sdl2.SDLK_LEFT:
            # Move left within the current page
            if current_col > 0:
                new_index = (current_page * cards_per_page) + (current_row * cards_per_row) + (current_col - 1)
                if new_index < total_categories:
                    self.nav_state.selected_category = new_index
            # Move to previous page if at leftmost of current page
            elif current_page > 0:
                new_page = current_page - 1
                new_col = 2  # Rightmost column of previous page
                new_index = (new_page * cards_per_page) + (current_row * cards_per_row) + new_col
                # If position doesn't exist in previous page, move to last valid item
                if new_index >= total_categories:
                    new_index = total_categories - 1
                self.nav_state.selected_category = new_index
                self.nav_state.category_page = new_page

        elif key == sdl2.SDLK_RIGHT:
            # Move right within the current page
            if current_col < 2:  # 2 is the last column (0-based)
                new_index = (current_page * cards_per_page) + (current_row * cards_per_row) + (current_col + 1)
                if new_index < total_categories:
                    self.nav_state.selected_category = new_index
            # Move to next page if at rightmost of current page
            elif current_page < total_pages - 1:
                new_page = current_page + 1
                new_col = 0  # Leftmost column of next page
                new_index = (new_page * cards_per_page) + (current_row * cards_per_row) + new_col
                if new_index < total_categories:
                    self.nav_state.selected_category = new_index
                    self.nav_state.category_page = new_page

    def _handle_ok_button(self):
        """Handle A button press"""
        if self.view_state.showing_confirmation:
            if self.view_state.confirmation_type == 'download':
                if self.view_state.confirmation_selected:  # Yes selected
                    # Start the download
                    self._start_download(self.game_to_download)
                    # Only switch to download status if user presses back or selects from menu
                    self.view_state.showing_confirmation = False
                    self.view_state.confirmation_type = None
                    self.view_state.confirmation_selected = False
                    # Stay in games view to allow selecting more games
                    return
                self.view_state.showing_confirmation = False
                self.view_state.confirmation_type = None
                self.view_state.confirmation_selected = False
            elif self.view_state.confirmation_type == 'cancel':
                if self.view_state.confirmation_selected:  # Yes selected
                    # Cancel only the selected download
                    if self.selected_download and self.selected_download in self.active_downloads:
                        # Get the list of downloads and find current index
                        downloads = list(self.active_downloads.keys())
                        current_idx = downloads.index(self.selected_download)
                        
                        # Cancel the selected download
                        download_info = self.active_downloads[self.selected_download]
                        if 'manager' in download_info:
                            download_info['manager'].cancel()
                        del self.active_downloads[self.selected_download]
                        
                        # Select the previous download (or last one if at top)
                        if self.active_downloads:  # If there are still downloads
                            downloads = list(self.active_downloads.keys())  # Get updated list
                            if current_idx > 0:
                                # Select the previous download
                                self.selected_download = downloads[current_idx - 1]
                            else:
                                # If we were at the top, select the last download
                                self.selected_download = downloads[-1]
                        else:
                            # No more downloads, go back to previous view
                            self.selected_download = None
                            self.view_state.mode = self.view_state.previous_mode or 'games'
                self.view_state.showing_confirmation = False
            return

        if self.view_state.mode == 'categories':
            # Reset search and filtered games when entering a new category
            self.search_text = ""
            self.filtered_games = []
            self.view_state.showing_keyboard = False
            
            self.view_state.mode = 'games'
            self.nav_state.game_page = 0
            self.nav_state.selected_game = 0
            
            # Reset image loading state
            self.game_hold_timer = 0
            self.is_image_loaded = False
            self.last_selected_game = -1
        elif self.view_state.mode == 'games':
            self.view_state.previous_mode = self.view_state.mode
            # Get the appropriate game list and selected game
            if self.filtered_games:
                selected_index = self.nav_state.selected_game
                if 0 <= selected_index < len(self.filtered_games):
                    self.view_state.confirmation_type = 'download'
                    self.view_state.confirmation_selected = False  # Default to "No"
                    self._show_download_confirmation()
            else:
                self._show_download_confirmation()
        elif self.view_state.mode == 'download_status':
            # If there are no active downloads, go back to previous view
            if not self.active_downloads:
                self.view_state.mode = self.view_state.previous_mode or 'games'

    def _handle_back_button(self):
        """Handle B button press"""
        if self.view_state.showing_confirmation:
            # Hide confirmation dialog without action
            self.view_state.showing_confirmation = False
            self.view_state.confirmation_type = None
            self.view_state.confirmation_selected = False
            return True

        if self.view_state.mode == 'download_status':
            # Simply go back to previous view
            self.view_state.mode = self.view_state.previous_mode or 'games'
            self.selected_download = None  # Reset selected download when leaving view
        elif self.view_state.mode == 'games':
            self.view_state.mode = 'categories'
            self.nav_state.game_page = 0
            self.nav_state.selected_game = 0
        elif self.view_state.mode == 'categories':
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
        current_page = self.nav_state.selected_category // Config.CATEGORIES_PER_PAGE
        local_index = self.nav_state.selected_category % Config.CATEGORIES_PER_PAGE
        
        if direction > 0:  # Move right
            # If not at the last category
            if self.nav_state.selected_category < total_categories - 1:
                # If at the last item of current page, move to next page
                if local_index == Config.CATEGORIES_PER_PAGE - 1 and current_page < total_category_pages - 1:
                    self.nav_state.category_page += 1
                    self.nav_state.selected_category = current_page * Config.CATEGORIES_PER_PAGE + Config.CATEGORIES_PER_PAGE
                else:
                    # Move to next category on the same page
                    self.nav_state.selected_category += 1
        else:  # Move left
            # If not at the first category
            if self.nav_state.selected_category > 0:
                # If at the first item of current page, move to previous page
                if local_index == 0 and current_page > 0:
                    self.nav_state.category_page -= 1
                    self.nav_state.selected_category = (current_page - 1) * Config.CATEGORIES_PER_PAGE + (Config.CATEGORIES_PER_PAGE - 1)
                else:
                    # Move to previous category on the same page
                    self.nav_state.selected_category -= 1

    def _navigate_games(self, direction):
        """Navigate through the games list
        
        Args:
            direction: 1 for down, -1 for up
        """
        if self.filtered_games:
            total_games = len(self.filtered_games)
        else:
            current_category = CategoryManager.get_categories()[self.nav_state.selected_category]
            total_games = len(GameManager.get_games_by_category(current_category['id']))

        if total_games == 0:
            return

        new_selected = self.nav_state.selected_game + direction
        
        # Handle wrapping around pages
        if new_selected < 0:
            # Go to last page, last item
            total_pages = (total_games + Config.GAMES_PER_PAGE - 1) // Config.GAMES_PER_PAGE
            self.nav_state.game_page = total_pages - 1
            last_page_items = total_games % Config.GAMES_PER_PAGE
            self.nav_state.selected_game = total_games - 1
        elif new_selected >= total_games:
            # Go to first page, first item
            self.nav_state.game_page = 0
            self.nav_state.selected_game = 0
        else:
            # Normal navigation within or between pages
            new_page = new_selected // Config.GAMES_PER_PAGE
            if new_page != self.nav_state.game_page:
                self.nav_state.game_page = new_page
            self.nav_state.selected_game = new_selected

    def _change_page(self, direction):
        """Change the current page in the appropriate view
        
        Args:
            direction: 1 for next page, -1 for previous page
        """
        if self.view_state.mode == "categories":
            total_categories = len(CategoryManager.get_categories())
            total_pages = (total_categories + Config.CARDS_PER_PAGE - 1) // Config.CARDS_PER_PAGE
            new_page = (self.nav_state.category_page + direction) % total_pages
            self.nav_state.category_page = new_page
            # Update selected category
            self.nav_state.selected_category = new_page * Config.CARDS_PER_PAGE
            
        elif self.view_state.mode == "games":
            if self.filtered_games:
                # Handle pagination for search results
                total_pages = (len(self.filtered_games) + Config.GAMES_PER_PAGE - 1) // Config.GAMES_PER_PAGE
            else:
                # Handle pagination for normal category view
                current_category = CategoryManager.get_categories()[self.nav_state.selected_category]
                total_pages = GameManager.get_total_game_pages(current_category['id'], Config.GAMES_PER_PAGE)
            
            if total_pages > 0:
                new_page = (self.nav_state.game_page + direction) % total_pages
                self.nav_state.game_page = new_page
                # Update selected game
                self.nav_state.selected_game = new_page * Config.GAMES_PER_PAGE

    def _show_download_confirmation(self):
        """Show confirmation dialog for game download"""
        if self.filtered_games:
            game = self.filtered_games[self.nav_state.selected_game]
        else:
            category_id = CategoryManager.get_categories()[self.nav_state.selected_category]['id']
            game = GameManager.get_game(category_id, self.nav_state.selected_game)
        
        if game:
            # Check if game is already downloading
            if game['name'] in self.active_downloads:
                logger.warning(f"Game {game['name']} is already downloading")
                

                # To show an alert with additional information
                self.show_alert(
                    "Download",
                    additional_info=[
                        (game['name'], Theme.TEXT_PRIMARY),
                        ("is already downloading!", Theme.WARNING),
                    ]
                )
                return
            
            # Create temporary download manager to get size
            download_manager = DownloadManager(
                id=game.get('category_id', CategoryManager.get_categories()[self.nav_state.selected_category]['id']),
                game_name=game['name'],
                game_url=game.get('game_url', ''),
            )
            
            # Get game size
            game_size = download_manager.get_game_size()
            game['size'] = game_size  # Store size for later use
            
            # Store game info and show confirmation
            self.game_to_download = game  # Store the game to download
            self.view_state.showing_confirmation = True  # Show the confirmation dialog
            self.view_state.confirmation_selected = False  # Default to "No"
            self.view_state.confirmation_type = 'download'
            
            logger.debug(f"Showing download confirmation for game: {game['name']}")

    def _start_download(self, game: Dict[str, Any]) -> None:
        """Start downloading a game.
        
        Args:
            game: Dictionary containing game information.
            
        Raises:
            RuntimeError: If download initialization fails.
        """
        try:
            if game and game.get('game_url'):
                # Create download manager for the game
                download_manager = DownloadManager(
                    id=CategoryManager.get_categories()[self.nav_state.selected_category]['id'],
                    game_name=game['name'],
                    game_url=game.get('game_url', ''),
                    image_url=game.get('image_url', ''),
                    isExtractable=CategoryManager.get_categories()[self.nav_state.selected_category]['isExtractable']
                )
                
                # Set pre-fetched size if available
                if 'size' in game:
                    download_manager.total_size = game['size']
                
                # Start the download
                download_manager.start_download()
                
                # Add to active downloads
                self.active_downloads[game['name']] = {
                    'manager': download_manager,
                    'status': 'downloading',
                    'progress': 0,
                    'speed': 0,
                    'eta': 0
                }
                
                logger.info(f"Started download for game: {game['name']}")
            else:
                raise RuntimeError("Invalid game data for download")
                
        except Exception as e:
            logger.error(f"Failed to start download for game: {str(e)}", exc_info=True)
            raise RuntimeError(f"Download initialization failed: {str(e)}")

    def _update_filtered_games(self) -> None:
        """Update the filtered games list based on search text."""
        try:
            # Get all games for current category
            current_category = CategoryManager.get_categories()[self.nav_state.selected_category]
            all_games = GameManager.get_games_by_category(current_category['id'])
            
            # Filter games based on search text
            self.filtered_games = list(filter(
                lambda game: self.search_text.lower() in game['name'].lower(), 
                all_games
            ))
            
            # Reset page and selection when search results change
            self.nav_state.game_page = 0
            self.nav_state.selected_game = 0
            
            logger.debug(f"Updated filtered games. Found {len(self.filtered_games)} matches")
            
        except Exception as e:
            logger.error(f"Failed to update filtered games: {str(e)}", exc_info=True)
            self.filtered_games = []

    def _render(self):
        """Render the current application state"""
        try:
            # Clear the screen
            sdl2.SDL_SetRenderDrawColor(self.renderer, *Theme.BG_DARK, 255)
            sdl2.SDL_RenderClear(self.renderer)

            if self.view_state.mode == 'categories':
                self.categories_view.render(
                    self.nav_state.category_page,
                    self.nav_state.selected_category
                )
            elif self.view_state.mode == 'games':
                # Get the current category ID
                current_category_id = CategoryManager.get_categories()[self.nav_state.selected_category]['id']
                
                if self.search_text:
                    # When searching, only show filtered games
                    if self.filtered_games:
                        self.games_view.render(
                            current_category_id,
                            self.nav_state.game_page,
                            self.nav_state.selected_game,
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
                        self.nav_state.game_page,
                        self.nav_state.selected_game,
                        show_image=self.is_image_loaded
                    )

                # Show active downloads count in the corner
                if self.active_downloads:
                    download_count = len(self.active_downloads)
                    download_text = f"Active Downloads: {download_count}"
                    # Calculate position for right alignment
                    text_surface = sdl2.sdlttf.TTF_RenderText_Blended(
                        self.font,
                        download_text.encode('utf-8'),
                        sdl2.SDL_Color(*Theme.TEXT_HIGHLIGHT)
                    )
                    text_width = text_surface.contents.w
                    sdl2.SDL_FreeSurface(text_surface)
                    x_pos = Config.SCREEN_WIDTH - text_width - 20
                    
                    self.games_view.render_text(
                        download_text,
                        x_pos,
                        20,
                        color=Theme.TEXT_HIGHLIGHT,
                        center=False
                    )

                # Render keyboard if showing
                if self.view_state.showing_keyboard:
                    self.keyboard_view.render(
                        self.nav_state.keyboard_selected_key,
                        self.search_text
                    )
            elif self.view_state.mode == 'download_status':
                self.download_view.render(
                    self.active_downloads,
                    self.view_state.showing_confirmation,
                    self.selected_download
                )

            # Render confirmation dialog if active
            if self.view_state.showing_confirmation:
                message = None
                additional_info = []
                
                if self.view_state.confirmation_type == 'cancel':
                    message = "Do you want to cancel the download?"
                elif self.view_state.confirmation_type == 'download' and self.game_to_download:
                    message = f"Do you want to download?"
                    # Add game name and size as additional info
                    additional_info = [
                        (self.game_to_download.get('name', ''), Theme.TEXT_SECONDARY),
                        (f"Size: {DownloadManager.format_size(self.game_to_download.get('size', 0))}", Theme.TEXT_SECONDARY)
                    ]
                
                self.confirmation_dialog.render(
                    message=message,
                    confirmation_selected=self.view_state.confirmation_selected,
                    button_texts=("Yes", "No"),
                    additional_info=additional_info
                )

            # Get alert state from AlertManager
            from utils.alert_manager import AlertManager
            alert_manager = AlertManager.get_instance()
            
            # Render alert dialog if active
            if alert_manager.is_showing():
                self.alert_dialog.render(
                    message=alert_manager.get_message(),
                    additional_info=alert_manager.get_additional_info()
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

    def cleanup(self) -> None:
        """Clean up resources before application exit."""
        try:
            # Clean up downloads
            for download_info in self.active_downloads.values():
                try:
                    if 'manager' in download_info:
                        download_info['manager'].cancel()
                except Exception as e:
                    logger.warning(f"Failed to cancel download: {str(e)}")

            # Clean up SDL resources
            if hasattr(self, 'texture_manager'):
                try:
                    self.texture_manager.cleanup()
                except Exception as e:
                    logger.warning(f"Failed to cleanup texture manager: {str(e)}")

            if hasattr(self, 'font'):
                sdl2.sdlttf.TTF_CloseFont(self.font)
                
            if hasattr(self, 'joystick') and self.joystick:
                sdl2.SDL_JoystickClose(self.joystick)
                
            if hasattr(self, 'renderer'):
                sdl2.SDL_DestroyRenderer(self.renderer)
                
            if hasattr(self, 'window'):
                sdl2.SDL_DestroyWindow(self.window)

            # Quit SDL subsystems
            sdl2.sdlimage.IMG_Quit()
            sdl2.sdlttf.TTF_Quit()
            sdl2.SDL_Quit()
            
            # Clear the singleton instance
            GameDownloaderApp.instance = None
            
            logger.info("Cleanup completed successfully")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}", exc_info=True)
            # Don't re-raise as we're already cleaning up 

    def show_alert(self, message: str, additional_info: Optional[List[Tuple[str, Tuple[int, int, int, int]]]] = None):
        """Show an alert dialog with the given message"""
        from utils.alert_manager import AlertManager
        AlertManager.get_instance().show_alert(message, additional_info) 