"""
View class for rendering download status and progress indicators.
"""
import os
from typing import Dict, Optional, Any
import sdl2
from utils.theme import Theme
from utils.config import Config
from utils.logger import logger
from .base_view import BaseView

class DownloadView(BaseView):
    """View class for rendering download status and progress indicators"""
    
    def __init__(self, renderer, font=None):
        """Initialize the download view"""
        super().__init__(renderer, font)
        
    def render(self, active_downloads: Dict[str, Dict], selected_download: Optional[str] = None, scroll_offset: int = 0) -> None:
        """Render the download status page
        
        Args:
            active_downloads: Dictionary of active downloads with game names as keys and download info as values
            selected_download: Name of the currently selected download, if any
            scroll_offset: Number of items to skip from the top when rendering
        """
        try:
            self.render_title("Downloads")

            if not active_downloads:
                self._render_no_downloads_message()
         
            self._render_download_list(active_downloads, selected_download, scroll_offset)
            self._render_controls()

        except Exception as e:
            logger.error(f"Download status rendering error: {e}", exc_info=True)

    def _render_download_list(self, active_downloads: Dict[str, Dict], selected_download: Optional[str], scroll_offset: int) -> None:
        """Render the list of active downloads"""
        y_offset = Config.DOWNLOAD_VIEW_START_Y
        item_height = Config.DOWNLOAD_VIEW_ITEM_HEIGHT
        spacing = Config.DOWNLOAD_VIEW_SPACING
        
        # Process downloads
        completed_downloads = []
        visible_downloads = list(active_downloads.items())[scroll_offset:scroll_offset + Config.VISIBLE_DOWNLOADS]
        
        for game_name, download_info in visible_downloads:
            if 'manager' not in download_info:
                continue
            
            manager = download_info['manager']
            
            if manager.status["state"] == "completed":
                completed_downloads.append(game_name)
                continue
            
            self._render_download_item(game_name, manager, y_offset, selected_download)
            y_offset += item_height + spacing
        
        # Remove completed downloads
        for game_name in completed_downloads:
            del active_downloads[game_name]

        # Render scroll bar if needed
        if len(active_downloads) > Config.VISIBLE_DOWNLOADS:
            self._render_scroll_bar(len(active_downloads), scroll_offset)

    def _render_download_item(self, game_name: str, manager: Any, y_offset: int, selected_download: Optional[str]) -> None:
        """Render a single download item"""
        # Draw background and border
        self._render_item_background(game_name, y_offset, selected_download)
        # Render content
        self._render_game_status(game_name, manager, y_offset)

    def _render_item_background(self, game_name: str, y_offset: int, selected_download: Optional[str]) -> None:
        """Render the background for a download item"""
        card_width = Config.SCREEN_WIDTH - (Config.DOWNLOAD_VIEW_SIDE_PADDING * 2)
        item_rect = sdl2.SDL_Rect(
            Config.DOWNLOAD_VIEW_SIDE_PADDING, 
            y_offset, 
            card_width, 
            Config.DOWNLOAD_VIEW_ITEM_HEIGHT
        )
        
        # Set background color based on selection
        bg_color = Theme.SELECTION_BG if game_name == selected_download else Theme.CARD_BG
        sdl2.SDL_SetRenderDrawColor(self.renderer, *bg_color, 255)
        sdl2.SDL_RenderFillRect(self.renderer, item_rect)
        
        # Draw border
        sdl2.SDL_SetRenderDrawColor(self.renderer, *Theme.CARD_BORDER, 255)
        sdl2.SDL_RenderDrawRect(self.renderer, item_rect)

    def _render_game_status(self, game_name: str, manager: Any, y_offset: int) -> None:
        """Render status for a single game"""
        # Game name
        self.render_text(
            game_name,
            Config.DOWNLOAD_VIEW_TEXT_PADDING,
            y_offset + 15,
            color=Theme.TEXT_PRIMARY
        )
        
        status = manager.status
        
        if status["state"] == "downloading":
            if status["is_paused"]:
                self._render_paused_status(Config.DOWNLOAD_VIEW_TEXT_START_X, y_offset + Config.DOWNLOAD_VIEW_TEXT_Y_OFFSET)
            else:
                self._render_download_progress(manager, y_offset)
            self._render_progress_bar(y_offset, status["progress"])
            
        elif status["state"] == "processing":
            self._render_text_progress(
                "Processing",
                status['current_operation'],
                y_offset
            )
            self._render_progress_bar(y_offset, status["progress"])
        
        elif status["state"] == "scraping":
            self._render_text_progress(
                "Scraping",
                "Please wait while cover image is being scrapped",
                y_offset
            )
            
        elif status["state"] == "cancelling":
            self._render_text_progress(
                "Cancelling",
                "Please wait while files being removed",
                y_offset
            )
            
        elif status["state"] == "queued":
            queue_message = f"Waiting for other downloads to complete (Queue position: {status['queue_position']})"
            self._render_text_progress("Queued", queue_message, y_offset)
            
        elif status["state"] == "error":
            self._render_text_progress(
                "Error",
                status["error_message"],
                y_offset
            )

    def _render_progress_bar(self, y_offset: int, progress: float) -> None:
        """Render a progress bar"""
        card_width = Config.SCREEN_WIDTH - (Config.DOWNLOAD_VIEW_SIDE_PADDING * 2)
        progress_bar_width = card_width - (Config.DOWNLOAD_VIEW_INNER_PADDING * 2)
        progress_bar_height = Config.DOWNLOAD_VIEW_PROGRESS_BAR_HEIGHT
        progress_bar_y = y_offset + Config.DOWNLOAD_VIEW_ITEM_HEIGHT - progress_bar_height - 15
        progress_bar_x = Config.DOWNLOAD_VIEW_SIDE_PADDING + Config.DOWNLOAD_VIEW_INNER_PADDING

        # Ensure progress is valid
        progress = min(100, max(0, progress))
        
        # Draw background
        bg_rect = sdl2.SDL_Rect(progress_bar_x, progress_bar_y, progress_bar_width, progress_bar_height)
        sdl2.SDL_SetRenderDrawColor(self.renderer, *Theme.PROGRESS_BAR_BG, 255)
        sdl2.SDL_RenderFillRect(self.renderer, bg_rect)
        
        # Draw progress
        if progress > 0:
            progress_width = int((progress_bar_width * progress) / 100)
            progress_rect = sdl2.SDL_Rect(progress_bar_x, progress_bar_y, progress_width, progress_bar_height)
            sdl2.SDL_SetRenderDrawColor(self.renderer, *Theme.PROGRESS_BAR_FILL, 255)
            sdl2.SDL_RenderFillRect(self.renderer, progress_rect)
            
        # Draw border
        sdl2.SDL_SetRenderDrawColor(self.renderer, *Theme.PROGRESS_BAR_BORDER, 255)
        sdl2.SDL_RenderDrawRect(self.renderer, bg_rect)

    def _render_download_progress(self, manager: Any, y_offset: int) -> None:
        """Render download progress information"""
        status = manager.status
        
        # Format progress text
        progress_text = f"{status['progress']:.1f}%"
        
        # Format speed
        speed = status["download_speed"]
        if speed > 1024 * 1024:  # MB/s
            speed_text = f"Speed: {speed / (1024 * 1024):.1f} MB/s"
        else:  # KB/s
            speed_text = f"Speed: {speed / 1024:.1f} KB/s"
            
        # Format size
        current = status["current_size"]
        total = status["total_size"]
        size_text = f"Size: {self._format_size(current)} / {self._format_size(total)}"
        
        # Calculate ETA
        if speed > 0:
            remaining_bytes = total - current
            eta_seconds = remaining_bytes / speed
            eta_text = f"ETA: {self._format_time(eta_seconds)}"
        else:
            eta_text = "ETA: Calculating..."
            
        # Render progress information
        text_y = y_offset + Config.DOWNLOAD_VIEW_TEXT_Y_OFFSET
        start_x = Config.DOWNLOAD_VIEW_TEXT_START_X
        spacing = Config.DOWNLOAD_VIEW_TEXT_SPACING
        current_x = start_x + Config.DOWNLOAD_VIEW_TEXT_SPACING
        
        # Calculate total width needed
        total_width = sum(self._get_text_width(text) for text in [progress_text, speed_text, size_text, eta_text])
        total_width += spacing * 3  # Add spacing between items
        
        # Adjust spacing if needed to fit all items
        available_width = Config.SCREEN_WIDTH - (Config.DOWNLOAD_VIEW_SIDE_PADDING * 2) - start_x - Config.DOWNLOAD_VIEW_TEXT_SPACING
        if total_width > available_width:
            spacing = max(20, (available_width - total_width) // 3)  # Minimum spacing of 20 pixels
        
        # Render texts with labels and proper spacing
        for text in [progress_text, speed_text, size_text, eta_text]:
            self.render_text(text, current_x, text_y, color=Theme.TEXT_SECONDARY)
            current_x += self._get_text_width(text) + spacing

    def _render_paused_status(self, x: int, y: int) -> None:
        """Render paused status text"""
        self.render_text(
            "Paused",
            x + Config.DOWNLOAD_VIEW_TEXT_SPACING,
            y,
            color=Theme.TEXT_ACCENT
        )

    def _render_text_progress(self, title: str, message: str, y_offset: int) -> None:
        """Render text-based progress with animation"""
        current_time = sdl2.SDL_GetTicks() // 400
        dots = "." * ((current_time % 4) + 1)
        spaces = " " * (4 - len(dots))
        
        self.render_text(
            f"{title}{dots}{spaces}",
            Config.DOWNLOAD_VIEW_TEXT_START_X,
            y_offset + Config.DOWNLOAD_VIEW_TEXT_Y_OFFSET,
            color=Theme.TEXT_ACCENT
        )
        
        self.render_text(
            message,
            Config.DOWNLOAD_VIEW_TEXT_START_X + 250,
            y_offset + Config.DOWNLOAD_VIEW_TEXT_Y_OFFSET,
            color=Theme.TEXT_SECONDARY
        )

    def _render_no_downloads_message(self) -> None:
        """Render message when no downloads are active"""
        center_x = Config.SCREEN_WIDTH // 2
        center_y = Config.SCREEN_HEIGHT // 2
        
        self.render_text(
            "No active downloads",
            center_x,
            center_y - 20,
            color=Theme.TEXT_SECONDARY,
            center=True
        )

    def _format_size(self, size_bytes: int) -> str:
        """Format size in bytes to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"

    def _format_time(self, seconds: float) -> str:
        """Format time in seconds to human readable format"""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            seconds = int(seconds % 60)
            return f"{minutes}m {seconds}s"
        else:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            return f"{hours}h {minutes}m"

    def _render_controls(self) -> None:
        """Render control guides"""
        controls = {
            'left': ["back.png", "select.png"],
            'right': ["pause-resume.png"]
        }
        self.render_control_guides(controls)

    def _get_text_width(self, text: str) -> int:
        """Get the width of text in pixels"""
        text_surface = sdl2.sdlttf.TTF_RenderText_Blended(
            self.font,
            text.encode('utf-8'),
            sdl2.SDL_Color(255, 255, 255)
        )
        width = text_surface.contents.w
        sdl2.SDL_FreeSurface(text_surface)
        return width

    def _calculate_text_spacing(self, texts: list) -> int:
        """Calculate even spacing between texts to fit in available width"""
        total_text_width = sum(self._get_text_width(text) for text in texts)
        available_width = (
            Config.SCREEN_WIDTH 
            - (Config.DOWNLOAD_VIEW_SIDE_PADDING * 2) 
            - Config.DOWNLOAD_VIEW_TEXT_START_X 
            - Config.DOWNLOAD_VIEW_TEXT_SPACING
        )
        
        if len(texts) > 1:
            spacing = (available_width - total_text_width) // (len(texts) - 1)
            return max(20, min(spacing, 100))  # Keep spacing between 20 and 100 pixels
        return 0

    @staticmethod
    def format_eta(seconds: int) -> str:
        """Format seconds into human readable time"""
        if seconds < 0:
            return "calculating..."
        if seconds < 60:
            return f"{seconds}s"
        if seconds < 3600:
            return f"{seconds // 60}m {seconds % 60}s"
        return f"{seconds // 3600}h {(seconds % 3600) // 60}m"

    @staticmethod
    def format_size(bytes: int) -> str:
        """Format bytes into human readable size"""
        if bytes == 0:
            return "0 B"
        
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        i = 0
        size = float(bytes)
        
        while size >= 1024.0 and i < len(units) - 1:
            size /= 1024.0
            i += 1
            
        return f"{size:.2f} {units[i]}"

    def _render_scroll_bar(self, total_items: int, scroll_offset: int) -> None:
        """Render a scroll bar for the download list"""
        if total_items <= Config.VISIBLE_DOWNLOADS:
            return
            
        # Calculate scroll bar dimensions and position
        scroll_bar_width = 8
        scroll_bar_height = Config.SCREEN_HEIGHT - Config.DOWNLOAD_VIEW_START_Y - 60
        scroll_bar_x = Config.SCREEN_WIDTH - 20
        scroll_bar_y = Config.DOWNLOAD_VIEW_START_Y
        
        # Draw scroll bar background
        bg_rect = sdl2.SDL_Rect(scroll_bar_x, scroll_bar_y, scroll_bar_width, scroll_bar_height)
        sdl2.SDL_SetRenderDrawColor(self.renderer, *Theme.SCROLL_BAR_BG, 255)
        sdl2.SDL_RenderFillRect(self.renderer, bg_rect)
        
        # Calculate and draw scroll handle
        visible_ratio = Config.VISIBLE_DOWNLOADS / total_items
        handle_height = max(40, int(scroll_bar_height * visible_ratio))
        scroll_ratio = scroll_offset / (total_items - Config.VISIBLE_DOWNLOADS)
        handle_y = scroll_bar_y + int((scroll_bar_height - handle_height) * scroll_ratio)
        
        handle_rect = sdl2.SDL_Rect(scroll_bar_x, handle_y, scroll_bar_width, handle_height)
        sdl2.SDL_SetRenderDrawColor(self.renderer, *Theme.SCROLL_BAR_HANDLE, 255)
        sdl2.SDL_RenderFillRect(self.renderer, handle_rect)