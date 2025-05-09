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
import time
import threading
from dataclasses import dataclass
from contextlib import contextmanager

# Third-party imports
import sdl2
import sdl2.sdlttf
import sdl2.sdlimage

# Local imports
from utils.config import Config
from utils.logger import logger
from utils.texture_manager import TextureManager
from utils.download_manager import DownloadManager
from utils.theme import Theme
from utils.alert_manager import AlertManager
from ui.loading_screen import LoadingScreen
from ui.confirmation_dialog import ConfirmationDialog
from ui.download_view import DownloadView
from ui.platforms_view import platformsView
from ui.games_view import GamesView
from ui.keyboard_view import KeyboardView
from ui.alert_dialog import AlertDialog
from ui.sources_view import SourcesView
from data.database import Database

class SDLError(Exception):
    """Custom exception for SDL-related errors."""
    pass

@dataclass
class ViewState:
    """Class to hold view-related state"""
    mode: str = 'platforms'
    previous_mode: Optional[str] = None
    showing_confirmation: bool = False
    showing_keyboard: bool = False
    confirmation_selected: bool = False
    confirmation_type: Optional[str] = None

@dataclass
class NavigationState:
    """Class to hold navigation-related state"""
    platform_page: int = 0
    game_page: int = 0
    selected_platform: int = 0
    selected_game: int = 0
    keyboard_selected_key: int = 0
    source_page: int = 0
    selected_source: int = 0

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
                Config.SCREEN_HEIGHT,
            )
            
            # Initialize views
            self._initialize_views()
            
            # Initialize states
            self.view_state = ViewState()
            self.nav_state = NavigationState()
            self.download_manager = None
            self.downloads: Dict[str, Dict[str, Any]] = {}
            self.game_hold_timer: int = 0
            self.is_image_loaded: bool = False
            self.last_selected_game: int = -1
            self.search_text: str = ""
            self.selected_download: Optional[str] = None  # Track selected download in download view
            self.scroll_offset: int = 0  # Track scroll position in download view
            
            self.database = Database()
            
            # Cache for platforms
            self.cached_platforms = None
            self.cached_games = {}  # Dictionary to cache games by platform_id and source_id
            self.cached_sources = {}
            
            # Initialize alert manager
            self.alert_manager = AlertManager.get_instance()
            self.alert_manager.set_app(self)
            
            self.held_joy_buttons = {}
            self.held_hat_button = sdl2.SDL_HAT_CENTERED
            self.last_hat_time: int = 0
            
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
            # Get the display mode of the primary display
            display_mode = sdl2.SDL_DisplayMode()
            if sdl2.SDL_GetCurrentDisplayMode(0, ctypes.byref(display_mode)) != 0:
                raise SDLError(sdl2.SDL_GetError().decode('utf-8'))
            
            # Update the configuration with the new screen size
            Config.update_screen_size(display_mode.w, display_mode.h)
            
            window = sdl2.SDL_CreateWindow(
                Config.APP_NAME.encode('utf-8'), 
                sdl2.SDL_WINDOWPOS_CENTERED, 
                sdl2.SDL_WINDOWPOS_CENTERED, 
                display_mode.w, 
                display_mode.h, 
                sdl2.SDL_WINDOW_SHOWN | sdl2.SDL_WINDOW_ALLOW_HIGHDPI | sdl2.SDL_WINDOW_RESIZABLE
            )
            if not window:
                raise SDLError(sdl2.SDL_GetError().decode('utf-8'))
            
        logger.info(f"Window created successfully with dimensions: {display_mode.w}x{display_mode.h}")
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
        """Initialize or reinitialize all views with current screen dimensions."""
        # Share the font with all views
        shared_font = self.font
        
        self.platforms_view = platformsView(self.renderer, shared_font)
        self.platforms_view.set_texture_manager(self.texture_manager)
        
        self.games_view = GamesView(self.renderer, shared_font)
        self.games_view.set_texture_manager(self.texture_manager)
        
        self.download_view = DownloadView(self.renderer, shared_font)
        self.download_view.set_texture_manager(self.texture_manager)
        
        self.sources_view = SourcesView(self.renderer, shared_font)
        self.sources_view.set_texture_manager(self.texture_manager)
        
        self.keyboard_view = KeyboardView(self.renderer, shared_font)
        self.keyboard_view.set_texture_manager(self.texture_manager)
        
        self.confirmation_dialog = ConfirmationDialog(self.renderer, shared_font)
        self.confirmation_dialog.set_texture_manager(self.texture_manager)
        
        self.alert_dialog = AlertDialog(self.renderer, shared_font)
        self.alert_dialog.set_texture_manager(self.texture_manager)
        
        self.loading_screen = LoadingScreen(
            self.renderer,
            Config.SCREEN_WIDTH,
            Config.SCREEN_HEIGHT,
            self.font
        )
        self.loading_screen.set_texture_manager(self.texture_manager)
        
        logger.info("Views initialized with current screen dimensions")

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
            elif event.type == sdl2.SDL_WINDOWEVENT:
                self._handle_window_event(event)
            elif event.type == sdl2.SDL_KEYDOWN:
                if not self._handle_input_event(event.key.keysym.sym):
                    return False
            elif event.type == sdl2.SDL_JOYBUTTONDOWN:
                button = event.jbutton.button
                if not self._handle_controller_button(button):
                    return False
                self.held_joy_buttons[button] = time.time()
            elif event.type == sdl2.SDL_JOYBUTTONUP:
                button = event.jbutton.button
                self.held_joy_buttons.pop(button, None)
            elif event.type == sdl2.SDL_JOYHATMOTION:
                button = event.jhat.value
                if not self._handle_d_pad_controller_button(button):
                    return False
                self.held_hat_button = button
                self.last_hat_time = time.time()
        
        now = time.time()
        for button, last_time in self.held_joy_buttons.items():
            if now - last_time >= Config.CONTROLLER_BUTTON_REPEAT_RATE / 1000.0:
                if not self._handle_controller_button(button):
                    return False
                self.held_joy_buttons[button] = now
                
        if self.held_hat_button != sdl2.SDL_HAT_CENTERED:
                if now - self.last_hat_time >= Config.CONTROLLER_BUTTON_REPEAT_RATE / 1000.0:
                    if not self._handle_d_pad_controller_button(self.held_hat_button):
                        return False
                    self.last_hat_time = now
        
        return True
    
    def _handle_window_event(self, event) -> None:
        """Handle window events like resize."""
        if event.window.event == sdl2.SDL_WINDOWEVENT_RESIZED:
            width = event.window.data1
            height = event.window.data2
            Config.update_screen_size(width, height)
            # Reinitialize views with new dimensions
            self._initialize_views()
            logger.info(f"Window resized to: {width}x{height}")

    def _update_downloads(self) -> None:
        """Update status of active downloads."""
        try:
            completed_downloads = []
            active_download_count = DownloadManager.get_active_download_count()
            
            # First pass: identify completed downloads
            for game_name, download_info in self.downloads.items():
                if 'manager' not in download_info:
                    continue
                    
                manager = download_info['manager']
                if manager.status["state"] == "completed":
                    completed_downloads.append(game_name)
                    
            # Second pass: update queue positions and start queued downloads if possible
            queued_downloads = sorted(
                [(name, info) for name, info in self.downloads.items() 
                 if info.get('manager') and info['manager'].status["state"] == "queued"],
                key=lambda x: x[1]['manager'].status["queue_position"]
            )
            
            # Update queue positions
            for position, (name, info) in enumerate(queued_downloads):
                info['manager'].status["queue_position"] = position + 1
            
            # Start queued downloads if we have capacity
            while active_download_count < Config.MAX_CONCURRENT_DOWNLOADS and queued_downloads:
                game_name, download_info = queued_downloads.pop(0)
                manager = download_info['manager']
                if manager.status["state"] == "queued":
                    manager.start_download()
                    active_download_count += 1
                    logger.info(f"Starting queued download: {game_name}")
                    
            # Remove completed downloads
            for game_name in completed_downloads:
                del self.downloads[game_name]
                
                # Update selected download if the completed one was selected
                if game_name == self.selected_download:
                    remaining_downloads = list(self.downloads.keys())
                    if remaining_downloads:
                        self.selected_download = remaining_downloads[0]
                    else:
                        self.selected_download = None
                        self.scroll_offset = 0
                        
        except Exception as e:
            logger.error(f"Error updating downloads: {str(e)}", exc_info=True)

    def _simulate_loading(self) -> None:
        """Show a loading screen while initializing."""
        try:
            loading_stages = [
                ("Initializing SDL", 0.1),
                ("Loading platforms", 0.3),
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
        # Map controller buttons to keyboard events
        button_map = {
            Config.CONTROLLER_BUTTON_A: sdl2.SDLK_RETURN,
            Config.CONTROLLER_BUTTON_B: sdl2.SDLK_BACKSPACE,
            Config.CONTROLLER_BUTTON_X: sdl2.SDLK_d,
            Config.CONTROLLER_BUTTON_SELECT: sdl2.SDLK_s,
            Config.CONTROLLER_BUTTON_START: sdl2.SDLK_p,
            Config.CONTROLLER_BUTTON_Y: sdl2.SDLK_SPACE,
            Config.CONTROLLER_BUTTON_L: sdl2.SDLK_PAGEDOWN,
            Config.CONTROLLER_BUTTON_R: sdl2.SDLK_PAGEUP
        }
        
        if button in button_map:
            return self._handle_input_event(button_map[button])
        return True

    def _handle_d_pad_controller_button(self, button):
        # Map controller buttons to keyboard events
        button_map = {
            Config.CONTROLLER_BUTTON_UP: sdl2.SDLK_UP,
            Config.CONTROLLER_BUTTON_DOWN: sdl2.SDLK_DOWN,
            Config.CONTROLLER_BUTTON_LEFT: sdl2.SDLK_LEFT,
            Config.CONTROLLER_BUTTON_RIGHT: sdl2.SDLK_RIGHT
        }
        
        if button in button_map:
            return self._handle_input_event(button_map[button])
        return True
    
    def _handle_input_event(self, key: int) -> bool:
        """Handle keyboard and controller input events.
        
        Args:
            key: The key or button code that was pressed.
            
        Returns:
            bool: False if application should exit, True otherwise.
        """
        
        # Handle alert dismissal first
        if self.alert_manager.is_showing():
            if key in [sdl2.SDLK_RETURN, sdl2.SDLK_BACKSPACE, Config.CONTROLLER_BUTTON_A, Config.CONTROLLER_BUTTON_B]:
                self.alert_manager.hide_alert()
            return True
        
        # Handle pause/resume for downloads
        if key == sdl2.SDLK_p and self.view_state.mode == 'download_status':
            self._handle_pause_resume()
            return True
        
        # Handle other input states
        if self.view_state.showing_confirmation:
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
            if self.view_state.confirmation_type == 'exit' and self.view_state.confirmation_selected:
                return False
            self._handle_ok_button()
        elif key == sdl2.SDLK_BACKSPACE:
            self.view_state.showing_confirmation = False
            self.view_state.confirmation_selected = False
        return True

    def _handle_onscreen_keyboard_input(self, key):
        """Handle input when on-screen keyboard is showing"""
        current_row, current_pos = self.keyboard_view.get_keyboard_position(self.nav_state.keyboard_selected_key)
        current_row_keys = self.keyboard_view.keyboard_layout[current_row]
        row_length = len(current_row_keys)
        
        # Handle navigation
        if key == sdl2.SDLK_LEFT:
            # Wrap around to the end of the row when going left from the first position
            new_pos = (current_pos - 1) % row_length
            self.nav_state.keyboard_selected_key = self.keyboard_view.get_key_index(current_row, new_pos)
        elif key == sdl2.SDLK_RIGHT:
            # Wrap around to the start of the row when going right from the last position
            new_pos = (current_pos + 1) % row_length
            self.nav_state.keyboard_selected_key = self.keyboard_view.get_key_index(current_row, new_pos)
        elif key == sdl2.SDLK_UP and current_row > 0:
            # Move up to the previous row, maintaining relative position
            prev_row = current_row - 1
            prev_row_length = len(self.keyboard_view.keyboard_layout[prev_row])
            # Calculate proportional position in the new row
            relative_pos = int((current_pos / row_length) * prev_row_length)
            self.nav_state.keyboard_selected_key = self.keyboard_view.get_key_index(prev_row, relative_pos)
        elif key == sdl2.SDLK_DOWN and current_row < len(self.keyboard_view.keyboard_layout) - 1:
            # Move down to the next row, maintaining relative position
            next_row = current_row + 1
            next_row_length = len(self.keyboard_view.keyboard_layout[next_row])
            # Calculate proportional position in the new row
            relative_pos = int((current_pos / row_length) * next_row_length)
            self.nav_state.keyboard_selected_key = self.keyboard_view.get_key_index(next_row, relative_pos)
        
        elif key == sdl2.SDLK_SPACE:
            if self.search_text:
                    self.search_text = self.search_text[:-1]
                    
        elif key == sdl2.SDLK_BACKSPACE:
            self.view_state.showing_keyboard = False
        
        elif key == sdl2.SDLK_RETURN:
            # Handle key selection
            selected_key = current_row_keys[current_pos]
            
            if selected_key == '<':
                if self.search_text:
                    self.search_text = self.search_text[:-1]
            elif selected_key == 'Return':
                self.view_state.showing_keyboard = False
            elif selected_key == 'Space':
                self.search_text += ' '
            elif selected_key == 'Clear':
                self.search_text = ""
            else:
                self.search_text += selected_key
            
            # Reset selection to first item when search changes
            self.nav_state.selected_game = 0
            self.nav_state.game_page = 0
        return True

    def _handle_normal_input(self, key):
        """Handle input in normal navigation mode.
        
        Args:
            key: SDL key code for the pressed key
            
        Returns:
            bool: True to continue processing, False to exit
        """
        # Handle view-specific navigation keys
        if key in [sdl2.SDLK_UP, sdl2.SDLK_DOWN, sdl2.SDLK_LEFT, sdl2.SDLK_RIGHT]:
            self._handle_navigation(key)
            return True
            
        # Handle page navigation
        if key == sdl2.SDLK_PAGEUP:
            self._change_page(1)
            return True
            
        if key == sdl2.SDLK_PAGEDOWN:
            self._change_page(-1)
            return True
            
        # Handle view switching
        if key == sdl2.SDLK_d and self.view_state.mode != 'download_status':
            self._switch_view('download_status')
            return True
            
        if key == sdl2.SDLK_s and self.view_state.mode == 'games':
            self._switch_view('sources')
            return True
            
        # Handle keyboard toggle
        if key == sdl2.SDLK_SPACE and self.view_state.mode == 'games' and not self.view_state.showing_keyboard:
            self.view_state.showing_keyboard = True
            self.nav_state.keyboard_selected_key = 0
            return True
            
        # Handle confirmation and selection
        if key == sdl2.SDLK_RETURN:
            if self.view_state.mode == 'download_status':
                if self.selected_download and self.selected_download in self.downloads:
                    self._show_confirmation('cancel')
            elif self.view_state.mode == 'games':
                self._handle_game_selection()
            else:
                self._handle_ok_button()
            return True
            
        # Handle back navigation
        if key == sdl2.SDLK_BACKSPACE:
            return self._handle_back_button()
            
        return True

    def _change_page(self, direction):
        """Change the current page in the active view.
        
        Args:
            direction: Direction to change page (1 for next, -1 for previous)
        """
        if self.view_state.mode == 'platforms':
            if self.cached_platforms is None:
                self.cached_platforms = self.database.get_platforms()
            total_pages = math.ceil(len(self.cached_platforms) / Config.CARDS_PER_PAGE)
            new_page = (self.nav_state.platform_page + direction) % total_pages
            self.nav_state.platform_page = new_page
            # Set selection to first item of the new page
            self.nav_state.selected_platform = new_page * Config.CARDS_PER_PAGE
            
        elif self.view_state.mode == 'games':
            # Get the appropriate games list
            total_games, games_list = self._get_current_games_list()
            
            if  total_games > 0:
                total_pages = math.ceil(total_games / Config.GAMES_PER_PAGE)
                new_page = (self.nav_state.game_page + direction) % total_pages
                self.nav_state.game_page = new_page
                # Set selection to first item of the new page
                self.nav_state.selected_game =  0
                # Reset image loading state
                self.game_hold_timer = 0
                self.is_image_loaded = False
                self.last_selected_game = self.nav_state.selected_game
            
        elif self.view_state.mode == 'sources':
            # Get sources from cache
            platform_id = self._get_current_platform_id()
            if platform_id not in self.cached_sources:
                self.cached_sources[platform_id] = self.database.get_sources(platform_id)
            all_sources = self.cached_sources[platform_id]
            total_sources = len(all_sources)
            
            if total_sources > 0:
                total_pages = math.ceil(total_sources / Config.CARDS_PER_PAGE)
                new_page = (self.nav_state.source_page + direction) % total_pages
                self.nav_state.source_page = new_page
                # Set selection to first item of the new page
                self.nav_state.selected_source = new_page * Config.CARDS_PER_PAGE

    def _handle_navigation(self, key):
        """Handle navigation based on current view mode.
        
        Args:
            key: SDL key code for the pressed key
        """
        navigation_handlers = {
            'platforms': self._handle_platforms_navigation,
            'sources': self._handle_sources_navigation,
            'games': self._handle_games_navigation,
            'download_status': self._handle_download_navigation
        }
        
        handler = navigation_handlers.get(self.view_state.mode)
        if handler:
            handler(key)

    def _handle_sources_navigation(self, key):
        """Handle navigation in sources view"""
        try:
            platform_id = self._get_current_platform_id()
            if platform_id not in self.cached_sources:
                self.cached_sources[platform_id] = self.database.get_sources(platform_id)
                
            total_sources = len(self.cached_sources[platform_id])
            new_selected = self._handle_grid_navigation(
                key,
                total_sources,
                self.nav_state.selected_source,
                self.nav_state.source_page,
                lambda page: setattr(self.nav_state, 'source_page', page)
            )
            
            if new_selected != self.nav_state.selected_source:
                self.nav_state.selected_source = new_selected
                self.nav_state.source_page = new_selected // Config.CARDS_PER_PAGE
                
        except Exception as e:
            logger.error(f"Error handling sources navigation: {e}", exc_info=True)

    def _handle_platforms_navigation(self, key):
        """Handle navigation in platforms grid view"""
        if self.cached_platforms is None:
            self.cached_platforms = self.database.get_platforms()
            
        total_platforms = len(self.cached_platforms)
        new_selected = self._handle_grid_navigation(
            key,
            total_platforms,
            self.nav_state.selected_platform,
            self.nav_state.platform_page,
            lambda page: setattr(self.nav_state, 'platform_page', page)
        )
        
        if new_selected != self.nav_state.selected_platform:
            self.nav_state.selected_platform = new_selected

    def _handle_download_navigation(self, key):
        """Handle navigation in download status view.
        
        Args:
            key: SDL key code for the pressed key
        """
        if key not in [sdl2.SDLK_UP, sdl2.SDLK_DOWN, sdl2.SDLK_PAGEUP, sdl2.SDLK_PAGEDOWN]:
            return
            
        downloads = list(self.downloads.keys())
        if not downloads:
            return True
            
        if self.selected_download is None:
            self.selected_download = downloads[0]
            return True
            
        current_idx = downloads.index(self.selected_download)
        max_scroll = max(0, len(downloads) - Config.VISIBLE_DOWNLOADS)
        
        if key == sdl2.SDLK_UP:
            # Move selection up
            if current_idx > 0:
                new_idx = current_idx - 1
                # Adjust scroll if needed
                if new_idx < self.scroll_offset:
                    self.scroll_offset = new_idx
                self.selected_download = downloads[new_idx]
                
        elif key == sdl2.SDLK_DOWN:
            # Move selection down
            if current_idx < len(downloads) - 1:
                new_idx = current_idx + 1
                # Adjust scroll if needed
                if new_idx >= self.scroll_offset + Config.VISIBLE_DOWNLOADS:
                    self.scroll_offset = new_idx - (Config.VISIBLE_DOWNLOADS - 1)
                self.selected_download = downloads[new_idx]
                
        elif key == sdl2.SDLK_PAGEUP:
            # Move up by page size
            new_idx = max(0, current_idx - Config.VISIBLE_DOWNLOADS)
            self.selected_download = downloads[new_idx]
            self.scroll_offset = max(0, new_idx - (Config.VISIBLE_DOWNLOADS - 1))
            
        elif key == sdl2.SDLK_PAGEDOWN:
            # Move down by page size
            new_idx = min(len(downloads) - 1, current_idx + Config.VISIBLE_DOWNLOADS)
            self.selected_download = downloads[new_idx]
            self.scroll_offset = min(max_scroll, new_idx)
            
        # Ensure scroll offset stays within valid range
        self.scroll_offset = min(max_scroll, max(0, self.scroll_offset))
        
        return True

    def _switch_view(self, new_mode: str, reset_state: bool = True):
        """Switch to a different view mode and handle state reset.
        
        Args:
            new_mode: The view mode to switch to ('platforms', 'games', 'sources', 'download_status')
            reset_state: Whether to reset the view state
        """
        # Show loading screen only when transitioning from platforms to games
        if self.view_state.mode == 'platforms' and new_mode == 'games':
            # Start loading animation in a separate thread
            def animate_loading():
                while not hasattr(self, '_loading_complete'):
                    self.loading_screen.render(0.5, "Retreiving Games List...")
                    sdl2.SDL_RenderPresent(self.renderer)
                    sdl2.SDL_Delay(Config.LOADING_ANIMATION_SPEED)
            
            # Start animation thread
            animation_thread = threading.Thread(target=animate_loading)
            animation_thread.daemon = True
            animation_thread.start()
            
            # Signal animation thread to stop after a short delay
            # This ensures the loading screen is visible even if games load quickly
            sdl2.SDL_Delay(100)  # Show loading screen for at least 500ms
            self._loading_complete = True
            animation_thread.join()
            delattr(self, '_loading_complete')
        
        self.view_state.previous_mode = self.view_state.mode
        self.view_state.mode = new_mode
        
        if not reset_state:
            return
            
        # Reset state based on new mode
        if new_mode == 'download_status':
            self.selected_download = next(iter(self.downloads)) if self.downloads else None
        elif new_mode == 'platforms':
            self.nav_state.selected_source = 0
            self.nav_state.source_page = 0
            self._reset_game_selection()

    def _reset_game_selection(self) -> None:
        """Reset all game selection state to initial values."""
        self.nav_state.game_page = 0
        self.nav_state.selected_game = 0
        self.search_text = ""
        self.view_state.showing_keyboard = False
        self._reset_game_image_state()

    def _reset_game_image_state(self) -> None:
        """Reset only the game image loading state."""
        self.game_hold_timer = 0
        self.is_image_loaded = False
        self.last_selected_game = self.nav_state.selected_game

    def _handle_games_navigation(self, key):
        """Handle navigation in games view."""
        if self.view_state.showing_keyboard:
            return
            
        if key == sdl2.SDLK_UP:
            self._navigate_games(-1)
        elif key == sdl2.SDLK_DOWN:
            self._navigate_games(1)

    def _handle_ok_button(self):
        """Handle OK button press based on current view mode."""
        if self.view_state.showing_confirmation:
            self._handle_confirmation_ok()
            return

        ok_handlers = {
            'sources': self._handle_source_selection,
            'platforms': self._handle_platform_selection,
            'games': lambda: self._show_confirmation('download'),
            'download_status': lambda: self._switch_view(self.view_state.previous_mode or 'games') if not self.downloads else None
        }
        
        handler = ok_handlers.get(self.view_state.mode)
        if handler:
            handler()

    def _handle_back_button(self):
        """Handle back button press and manage view transitions.
        
        Returns:
            bool: False if application should exit, True otherwise
        """
        if self.view_state.showing_confirmation:
            self._reset_confirmation_state()
            return True

        view_transitions = {
            'sources': 'games',
            'download_status': self.view_state.previous_mode,
            'games': 'platforms',
            'platforms': None  # Exit application
        }

        next_view = view_transitions.get(self.view_state.mode)
        if next_view is None:
            # Show exit confirmation instead of immediately closing
            self._show_confirmation('exit')
            return True
        
        self._switch_view(next_view)
        if self.view_state.mode == 'download_status':
            self.selected_download = None
        return True

    def _reset_confirmation_state(self):
        """Reset confirmation dialog state"""
        self.view_state.showing_confirmation = False
        self.view_state.confirmation_type = None
        self.view_state.confirmation_selected = False

    def _handle_confirmation_ok(self):
        """Handle OK button press in confirmation dialog"""
        if not self.view_state.confirmation_selected:
            self._reset_confirmation_state()
            return
            
        if self.view_state.confirmation_type == 'download':
            self._start_download()
        elif self.view_state.confirmation_type == 'cancel':
            self._cancel_selected_download()
            
        self._reset_confirmation_state()

    def _start_download(self) -> None:
        """Start downloading a game.
        
        Args:
            game: Dictionary containing game information including name, game_url, and image_url.
            
        Raises:
            RuntimeError: If download initialization fails.
        """
        if not self.game_to_download or not self.game_to_download.get('game_url'):
            raise RuntimeError("Invalid game data for download")
            
        game_name = self.game_to_download['name']
        
        # Check if already downloading
        if game_name in self.downloads:
            return
        
        self.download_manager.add_manager()
        
        # Add to active downloads
        self.downloads[game_name] = {
            'manager': self.download_manager,
            'game': self.game_to_download
        }
        
        # Update selected download if none selected
        if self.selected_download is None and self.view_state.mode == 'download_status':
            self.selected_download = game_name
            
        # Check if we should queue or start immediately
        active_downloads = DownloadManager.get_active_download_count()
        if active_downloads >= Config.MAX_CONCURRENT_DOWNLOADS:
            # Queue the download
            logger.info(f"Added game to download queue: {game_name}")
        else:
            # Start download immediately
            self.download_manager.start_download()
            logger.info(f"Started download for game: {game_name}")

    def _cancel_selected_download(self) -> None:
        """Cancel the currently selected download"""
        if not self.selected_download or self.selected_download not in self.downloads:
            return
            
        # Get download manager
        download_info = self.downloads[self.selected_download]
        manager = download_info.get('manager')
        if not manager:
            return
            
        # Cancel download
        manager.cancel()
            
        # Remove from active downloads
        del self.downloads[self.selected_download]
        
        # Update selected download
        remaining_downloads = list(self.downloads.keys())
        if remaining_downloads:
            self.selected_download = remaining_downloads[0]
        else:
            self.selected_download = None
            self.scroll_offset = 0

    def _handle_source_selection(self):
        """Handle source selection"""
        # Only filter games if user presses enter on a source
        if self.view_state.mode == 'sources':
            # Clear the games cache for the new source
            self.cached_games = {}
            self._switch_view('games')

    def _handle_platform_selection(self):
        """Handle platform selection"""
        # Reset search and keyboard state
        self.search_text = ""
        self.view_state.showing_keyboard = False
        
        # Clear the games cache for the new platform
        self.cached_games = {}
        
        self._switch_view('games')

    def _render(self) -> None:
        """Render the current application state."""
        try:
            self._clear_screen()
            self._render_main_view()
            self._render_overlays()
            self._present_frame()
        except Exception as e:
            logger.error(f"Error in render: {str(e)}", exc_info=True)
            raise

    def _clear_screen(self) -> None:
        """Clear the screen with background color."""
        sdl2.SDL_SetRenderDrawColor(self.renderer, *Theme.BG_DARK)
        sdl2.SDL_RenderClear(self.renderer)

    def _present_frame(self) -> None:
        """Present the rendered frame."""
        sdl2.SDL_RenderPresent(self.renderer)

    def _render_main_view(self) -> None:
        """Render the main view based on current mode."""
        render_methods = {
            'platforms': self._render_platforms_view,
            'games': self._render_games_view,
            'download_status': self._render_download_view,
            'sources': self._render_sources_view
        }
        
        render_method = render_methods.get(self.view_state.mode)
        if render_method:
            render_method()

    def _render_platforms_view(self) -> None:
        """Render the platforms view."""
        if self.cached_platforms is None:
            self.cached_platforms = self.database.get_platforms()
            
        self.platforms_view.render(
            self.nav_state.platform_page,
            self.nav_state.selected_platform,
            self.cached_platforms,
            len(self.downloads)
        )

    def _render_games_view(self) -> None:
        """Render the games view with optional keyboard."""
        # Get appropriate games list
        total_games, games_list = self._get_current_games_list()

        # Render games view
        self.games_view.render(
            self.nav_state.game_page,
            total_games,
            self.nav_state.selected_game,
            self.is_image_loaded,
            bool(self.search_text),
            games_list,
            len(self.downloads)
        )
        
        # Render keyboard if active
        if self.view_state.showing_keyboard:
            self.keyboard_view.render(
                self.nav_state.keyboard_selected_key,
                self.search_text
            )

    def _get_current_games_list(self) -> Tuple[int, List[Dict[str, Any]]]:
        """Get the current list of games based on search and filter state.
        
        Returns:
            Tuple containing total games count and list of game dictionaries
        """
        platform_id = self._get_current_platform_id()
        source_id = self.nav_state.selected_source
        
        # Otherwise get all games for the current platform and source
        cache_key = f"{platform_id}_{source_id}_{self.search_text}_{self.nav_state.game_page}"
        
        if cache_key not in self.cached_games:
            self.cached_games.clear()
            
            total_games, games = self.database.get_games(platform_id=platform_id, 
                                                       source_id=source_id, 
                                                       search_text=self.search_text,
                                                       limit=Config.GAMES_PER_PAGE,
                                                       offset=self.nav_state.game_page * Config.GAMES_PER_PAGE
                                                )
            
            self.cached_games[cache_key] = {
                'total_games': total_games,
                'games': games
            }
            
        return self.cached_games[cache_key]['total_games'], self.cached_games[cache_key]['games']

    def _render_download_view(self) -> None:
        """Render the download status view."""
        self.download_view.render(
            self.downloads,
            self.selected_download,
            self.scroll_offset
        )

    def _render_sources_view(self) -> None:
        """Render the sources view."""
        platform_id = self._get_current_platform_id()
        if platform_id not in self.cached_sources:
            self.cached_sources[platform_id] = self.database.get_sources(platform_id)
            
        self.sources_view.render(
            self.nav_state.source_page,
            self.nav_state.selected_source,
            self.cached_sources[platform_id]
        )

    def _render_overlays(self) -> None:
        """Render overlay elements like confirmation dialogs and alerts."""
        if self.view_state.showing_confirmation:
            self._render_confirmation_dialog()

        if self.alert_manager.is_showing():
            self._render_alert()

    def _render_confirmation_dialog(self) -> None:
        """Render the confirmation dialog with appropriate message and info."""
        message, additional_info = self._get_confirmation_content()
        
        self.confirmation_dialog.render(
            message=message,
            confirmation_selected=self.view_state.confirmation_selected,
            button_texts=("Yes", "No"),
            additional_info=additional_info
        )

    def _get_confirmation_content(self) -> Tuple[str, List[Tuple[str, Tuple[int, int, int, int]]]]:
        """Get the content for the confirmation dialog.
        
        Returns:
            Tuple containing message string and list of additional info tuples
        """
        if self.view_state.confirmation_type == 'exit':
            return "Do you want to exit?", []
        
        if self.view_state.confirmation_type == 'cancel':
            return "Do you want to cancel downloading?", [(self.game_to_download.get('name', ''), Theme.TEXT_SECONDARY),]
            
        if self.view_state.confirmation_type == 'download' and self.game_to_download:
            game_size = self.game_to_download.get('size', 0)
            total_space, free_space = DownloadManager.get_disk_space()
            
            # Format the information
            size_text = f"Game Size: 'Geting Game Size..."
            game_size_color = Theme.INFO
            if game_size == -1:
                size_text = f"Game Size: Unknown"
                game_size_color = Theme.WARNING
            elif game_size > 0:
                size_text = f"Game Size: {DownloadManager.format_size(game_size)}"
                game_size_color = Theme.TEXT_SECONDARY
            
            space_text = f"Free Space: {DownloadManager.format_size(free_space)} / {DownloadManager.format_size(total_space)}"
            
            # Determine text color based on available space
            space_color = Theme.TEXT_SECONDARY
            if game_size > free_space:
                space_color = Theme.ERROR
            elif free_space < (total_space * 0.1):  # Less than 10% space left
                space_color = Theme.WARNING
                
            return (
                "Do you want to download?",
                [
                    (self.game_to_download.get('name', ''), Theme.TEXT_SECONDARY),
                    (size_text, game_size_color),
                    (space_text, space_color)
                ]
            )
            
        return "", []

    def _render_alert(self) -> None:
        """Render the alert dialog."""
        self.alert_dialog.render(
            message=self.alert_manager.get_message(),
            additional_info=self.alert_manager.get_additional_info()
        )

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
            for download_info in self.downloads.values():
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
                    
            for image in os.listdir(Config.IMAGES_CACHE_DIR):
                os.remove(os.path.join(Config.IMAGES_CACHE_DIR, image))
            logger.info("Cached imaged cleaned")
            
            if hasattr(self, 'font'):
                sdl2.sdlttf.TTF_CloseFont(self.font)
                
            if hasattr(self, 'joystick') and self.joystick:
                sdl2.SDL_JoystickClose(self.joystick)
                
            if hasattr(self, 'renderer'):
                sdl2.SDL_DestroyRenderer(self.renderer)
                
            if hasattr(self, 'window'):
                sdl2.SDL_DestroyWindow(self.window)

            if hasattr(self, 'database'):
                self.database.close() 
                
            # Quit SDL subsystems
            sdl2.sdlimage.IMG_Quit()
            sdl2.sdlttf.TTF_Quit()
            sdl2.SDL_Quit()

            GameDownloaderApp.instance = None
            logger.info("Cleanup completed successfully")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}", exc_info=True)
            # Don't re-raise as we're already cleaning up 
            
    def _get_current_platform_id(self) -> str:
        """Get the ID of the currently selected platform.
        
        Returns:
            str: The current platform ID or empty string if invalid
        """
        if self.cached_platforms is None:
            self.cached_platforms = self.database.get_platforms()
            
        if 0 <= self.nav_state.selected_platform < len(self.cached_platforms):
            return self.cached_platforms[self.nav_state.selected_platform].get('id', '')
        return ''

    def _navigate_games(self, direction):
        """Navigate through games in the current platform.
        
        Args:
            direction: Direction to navigate (1 for next, -1 for previous)
        """
        # Get the appropriate games list
        total_games, games_list = self._get_current_games_list()
        
        if not games_list or total_games == 0:
            return
            
        # Calculate new position
        new_selected = self.nav_state.selected_game + direction
        
        if new_selected < 0:
            # Going up from first game - go to previous page and select last game
            self._change_page(-1)
            # Get the updated games list after page change
            _, new_games_list = self._get_current_games_list()
            if new_games_list:
                self.nav_state.selected_game = len(new_games_list) - 1
        elif new_selected >= len(games_list):
            # Going down from last game - go to next page and select first game
            self._change_page(1)
            # The _change_page method already sets selected_game to 0
        else:
            self.nav_state.selected_game = new_selected
            
        # Reset only image loading state when navigating
        self._reset_game_image_state()

    def _handle_game_selection(self):
        """Handle game selection in games view."""
        # Get current game list
        total_games, games_list = self._get_current_games_list()
        
        # Check if there are any games and if selection is valid
        if not games_list or self.nav_state.selected_game >= len(games_list):
            return
            
        # Store the game to be downloaded
        self.game_to_download = games_list[self.nav_state.selected_game]
        
        # Check if game is already being downloaded
        if self.game_to_download['name'] in self.downloads:
            self.alert_manager.show_alert(
                "Download in Progress",
                [("This game is already being downloaded.", Theme.TEXT_SECONDARY)]
            )
            return
        
        self.download_manager = DownloadManager(
            game=self.game_to_download
        )
        
        # Start async size check
        self.download_manager.get_game_size_async()
        
        # Show confirmation dialog immediately with "Checking size..."
        self.game_to_download['size'] = 0
        self._show_confirmation("download")
        
        # Update size in background
        def update_size():
            if self.download_manager.wait_for_size(timeout=10):  # Wait up to 10 seconds
                self.game_to_download['size'] = self.download_manager.status["total_size"]
                total_space, free_space = DownloadManager.get_disk_space()
                if self.game_to_download['size'] > free_space:
                    self.view_state.showing_confirmation = False
                    self.alert_manager.show_alert(
                        "Insufficient Disk Space",
                        [
                            (f"Game Size: {DownloadManager.format_size(self.game_to_download['size'])}", Theme.TEXT_SECONDARY),
                            (f"Free Space: {DownloadManager.format_size(free_space)}", Theme.ERROR),
                            ("Please free up some disk space and try again.", Theme.TEXT_SECONDARY)
                        ]
                    )
            else:
                self.game_to_download['size'] = -1
                logger.warning("Failed to get game size or timed out")
        
        update_thread = threading.Thread(target=update_size)
        update_thread.daemon = True
        update_thread.start()

    def _show_confirmation(self, confirmation_type: str) -> None:
        """Show confirmation dialog with specified type.
        
        Args:
            confirmation_type: Type of confirmation ('download' or 'cancel' or 'exit)
        """
        self.view_state.showing_confirmation = True
        self.view_state.confirmation_type = confirmation_type
        self.view_state.confirmation_selected = False

    def _handle_pause_resume(self):
        """Handle pause/resume functionality for downloads"""
        if not self.downloads:
            return
            
        # If a specific download is selected, toggle that one
        if self.selected_download and self.selected_download in self.downloads:
            download_info = self.downloads[self.selected_download]
            if 'manager' in download_info:
                manager = download_info['manager']
                if manager.status["is_paused"]:
                    manager.resume()
                else:
                    manager.pause()
        # Otherwise toggle all active downloads
        else:
            for download_info in self.downloads.values():
                if 'manager' in download_info:
                    manager = download_info['manager']
                    if manager.status["is_paused"]:
                        manager.resume()
                    else:
                        manager.pause()

    def _handle_grid_navigation(self, key, total_items, current_selected, current_page, page_setter=None):
        """Handle navigation in a grid layout.
        
        Args:
            key: SDL key code for the pressed key
            total_items: Total number of items in the grid
            current_selected: Currently selected item index
            current_page: Current page number
            page_setter: Optional callback to set the page number
            
        Returns:
            int: New selected item index
        """
        if total_items == 0:
            return current_selected
            
        current_row = (current_selected % Config.CARDS_PER_PAGE) // Config.CARDS_PER_ROW
        current_col = (current_selected % Config.CARDS_PER_PAGE) % Config.CARDS_PER_ROW
        total_pages = math.ceil(total_items / Config.CARDS_PER_PAGE)
        
        new_index = current_selected
        
        if key == sdl2.SDLK_UP and current_row > 0:
            new_index = (current_page * Config.CARDS_PER_PAGE) + ((current_row - 1) * Config.CARDS_PER_ROW) + current_col
            
        elif key == sdl2.SDLK_DOWN and current_row < 2:  # 2 is the last row (0-based)
            new_index = (current_page * Config.CARDS_PER_PAGE) + ((current_row + 1) * Config.CARDS_PER_ROW) + current_col
            
        elif key == sdl2.SDLK_LEFT:
            if current_col > 0:
                new_index = (current_page * Config.CARDS_PER_PAGE) + (current_row * Config.CARDS_PER_ROW) + (current_col - 1)
            elif current_page > 0:
                new_page = current_page - 1
                new_col = Config.CARDS_PER_ROW - 1  # Rightmost column
                new_index = (new_page * Config.CARDS_PER_PAGE) + (current_row * Config.CARDS_PER_ROW) + new_col
                if new_index >= total_items:
                    new_index = total_items - 1
                if page_setter:
                    page_setter(new_page)
                    
        elif key == sdl2.SDLK_RIGHT:
            if current_col < Config.CARDS_PER_ROW - 1:
                new_index = (current_page * Config.CARDS_PER_PAGE) + (current_row * Config.CARDS_PER_ROW) + (current_col + 1)
            elif current_page < total_pages - 1:
                new_page = current_page + 1
                new_col = 0  # Leftmost column
                new_index = (new_page * Config.CARDS_PER_PAGE) + (current_row * Config.CARDS_PER_ROW) + new_col
                if new_index < total_items and page_setter:
                    page_setter(new_page)
                    
        return min(new_index, total_items - 1) if new_index < total_items else current_selected
