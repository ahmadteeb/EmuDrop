"""
View class for rendering download status and progress indicators.
"""
import sdl2
import time
from typing import Dict, Optional
from utils.theme import Theme
from utils.config import Config
from utils.logger import logger
from utils.download_manager import DownloadManager
from .base_view import BaseView

class DownloadView(BaseView):
    """View class for rendering download status and progress indicators"""
    
    def __init__(self, renderer, font, texture_manager):
        """Initialize the download view"""
        super().__init__(renderer, font, texture_manager)
        
    def render(self, active_downloads: Dict[str, Dict], showing_confirmation: bool = False, selected_download: Optional[str] = None) -> None:
        """Render the download status page
        
        Args:
            active_downloads: Dictionary of active downloads with game names as keys and download info as values
            showing_confirmation: Whether a confirmation dialog is being shown
            selected_download: Name of the currently selected download, if any
        """
        try:
            # Render the title at the top
            self.render_title("Downloads")

            if not active_downloads:
                self._render_no_downloads_message()
                return

            # Calculate layout with improved margins
            start_y = 100  # Reduced top margin for more content space
            item_height = 110  # Increased height for better spacing
            spacing = 15  # Reduced spacing between items
            progress_bar_height = 16  # Slightly smaller progress bar
            side_padding = 30  # Consistent side padding
            inner_padding = 20  # Padding inside the card
            
            # Render each download
            y_offset = start_y
            completed_downloads = []
            
            for game_name, download_info in list(active_downloads.items()):
                # Skip if no manager
                if 'manager' not in download_info:
                    continue

                # Create status dict from download info
                status = {
                    'progress': download_info.get('progress', 0),
                    'is_downloading': download_info.get('status') == 'downloading',
                    'is_scrapping': download_info.get('status') == 'scrapping',
                    'is_extracting': download_info.get('status') == 'extracting',
                    'download_speed': download_info.get('speed', 0),
                    'current_size': download_info.get('current_size', 0),
                    'total_size': download_info.get('total_size', 0),
                    'eta': download_info['eta']
                }
                
                # Only remove completed downloads that are not extracting
                if status['progress'] >= 100 and not status['is_extracting'] and not status['is_downloading'] and not status['is_scrapping']:
                    completed_downloads.append(game_name)
                    continue
                
                # Calculate card dimensions
                card_width = Config.SCREEN_WIDTH - (side_padding * 2)
                
                # Draw item background with selection highlight if selected
                item_rect = sdl2.SDL_Rect(
                    side_padding, 
                    y_offset, 
                    card_width, 
                    item_height
                )
                if game_name == selected_download:
                    # Draw selection highlight
                    sdl2.SDL_SetRenderDrawColor(self.renderer, *Theme.SELECTION_BG, 255)
                else:
                    sdl2.SDL_SetRenderDrawColor(self.renderer, *Theme.CARD_BG, 255)
                sdl2.SDL_RenderFillRect(self.renderer, item_rect)
                
                # Draw item border
                sdl2.SDL_SetRenderDrawColor(self.renderer, *Theme.CARD_BORDER, 255)
                sdl2.SDL_RenderDrawRect(self.renderer, item_rect)
                
                # Render game name and status
                self._render_game_status(game_name, status, y_offset)
                
                # Render progress bar only if downloading and not extracting
                if status['is_downloading'] and not status['is_extracting'] and not status['is_scrapping']:
                    progress_bar_width = card_width - (inner_padding * 2)
                    self._render_progress_bar(
                        status['progress'],
                        y_offset + item_height - progress_bar_height - 15,  # Bottom padding
                        side_padding + inner_padding,  # X position with padding
                        progress_bar_width,
                        progress_bar_height
                    )
                
                y_offset += item_height + spacing
            
            # Remove completed downloads after iteration
            for game_name in completed_downloads:
                del active_downloads[game_name]

            # Update control guides based on whether there are downloads and selection
            controls = {
                'left': [
                    "back.png",
                    "select.png"  # Only show A button if a download is selected
                ],
                'right': []
            }
            self.render_control_guides(controls)
        except Exception as e:
            logger.error(f"Download status rendering error: {e}", exc_info=True)

    def _render_no_downloads_message(self):
        """Render message when no downloads are active"""
        self.render_text(
            "No active downloads",
            Config.SCREEN_WIDTH // 2,
            Config.SCREEN_HEIGHT // 2 - 20,
            color=Theme.TEXT_SECONDARY,
            center=True
        )
        
        self.render_text(
            "Press B to go back",
            Config.SCREEN_WIDTH // 2,
            Config.SCREEN_HEIGHT // 2 + 20,
            color=Theme.TEXT_DISABLED,
            center=True
        )

    def _render_game_status(self, game_name: str, status: Dict, y_offset: int):
        """Render status for a single game
        
        Args:
            game_name: Name of the game being downloaded
            status: Dictionary containing download status information
            y_offset: Vertical position to render at
        """
        text_padding = 40  # Left padding for text
        
        # Game name with shadow effect
        self.render_text(
            game_name,
            text_padding,
            y_offset + 15,  # Top padding
            color=Theme.TEXT_PRIMARY
        )
        
        # Status section - check extraction first, then download
        if status.get('is_extracting', False):
            self._render_text_progress("Extracting", "Please wait while files are being extracted", y_offset)
        elif status.get('is_scrapping', False):
            self._render_text_progress("Scrapping", "Please wait while cover imgae is being scrapped", y_offset)
        elif status.get('is_downloading', False):
            self._render_download_progress(status, y_offset)

    def _render_download_progress(self, status: Dict, y_offset: int):
        """Render download progress section
        
        Args:
            status: Dictionary containing download status information
            y_offset: Vertical position to render at
        """
        text_start_x = 40  # Left padding for text
        text_y = y_offset + 45  # Vertical position for status text
        
        # Progress percentage with safe float conversion
        try:
            progress = float(status.get('progress', 0))
        except (ValueError, TypeError):
            progress = 0
            
        progress_text = f"{progress:.1f}%"
        self.render_text(
            progress_text,
            text_start_x,
            text_y,
            color=Theme.PROGRESS_BAR_TEXT
        )
        
        # Download speed with safe fallbacks
        speed = status.get('download_speed', 0)
        speed_text = f"Speed: {DownloadManager.format_size(speed)}/s" if speed else "Speed: calculating..."
        eta_text = f"ETA: {self.format_eta(status['eta'])}"
        # Size information
        current_size = status.get('current_size', 0)
        total_size = status.get('total_size', 0)
        size_text = f"{DownloadManager.format_size(current_size)} / {DownloadManager.format_size(total_size)}"
        
        # Render speed (centered)
        self.render_text(
            speed_text,
            text_start_x + 180,  # Positioned after progress
            text_y,
            color=Theme.TEXT_SECONDARY
        )
        
        # Render size info (right-aligned)
        self.render_text(
            size_text,
            text_start_x + 450,  # Further right for size info
            text_y,
            color=Theme.TEXT_SECONDARY
        )
        
        self.render_text(
            eta_text,
            text_start_x + 700,
            text_y,
            color=Theme.TEXT_SECONDARY
        )

    def _render_progress_bar(self, progress: float, y: int, x: int, width: int, height: int):
        """Render a progress bar with improved visuals
        
        Args:
            progress: Progress percentage (0-100)
            y: Y position
            x: X position
            width: Total width of the progress bar
            height: Height of the progress bar
        """
        try:
            # Ensure progress is a valid float between 0-100
            progress = min(100, max(0, float(progress)))
        except (ValueError, TypeError):
            progress = 0
        
        # Background
        bg_rect = sdl2.SDL_Rect(x, y, width, height)
        sdl2.SDL_SetRenderDrawColor(self.renderer, *Theme.PROGRESS_BAR_BG, 255)
        sdl2.SDL_RenderFillRect(self.renderer, bg_rect)
        
        # Progress fill
        if progress > 0:
            fill_width = int((progress / 100.0) * width)
            if fill_width > 0:
                fill_rect = sdl2.SDL_Rect(x, y, fill_width, height)
                sdl2.SDL_SetRenderDrawColor(self.renderer, *Theme.PROGRESS_BAR_FILL, 255)
                sdl2.SDL_RenderFillRect(self.renderer, fill_rect)
        
        # Border
        border_rect = sdl2.SDL_Rect(x, y, width, height)
        sdl2.SDL_SetRenderDrawColor(self.renderer, *Theme.PROGRESS_BAR_BORDER, 255)
        sdl2.SDL_RenderDrawRect(self.renderer, border_rect)

    def _render_text_progress(self, title, text, y_offset: int):
        """Render extraction progress section
        
        Args:
            y_offset: Vertical position to render at
        """
        # Extracting text with animated dots
        current_time = sdl2.SDL_GetTicks() // 400  # Slightly faster animation
        dots = "." * ((current_time % 4) + 1)  # 1 to 4 dots
        spaces = " " * (4 - len(dots))  # Add spaces to keep text position stable
        
        # Render extracting text with fixed width for dots
        self.render_text(
            f"{title}{dots}{spaces}",
            40,  # Left padding
            y_offset + 45,  # Vertical position
            color=Theme.TEXT_ACCENT  # Use accent color for visibility
        )
        
        # Add a small status message
        self.render_text(
            text,
            250,  # Position after "Extracting" text
            y_offset + 45,
            color=Theme.TEXT_SECONDARY
        )
        
    def format_eta(self, seconds):
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{int(hours):02}:{int(minutes):02}:{int(secs):02}"