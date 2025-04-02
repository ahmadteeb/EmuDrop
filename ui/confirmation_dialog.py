"""
View class for rendering confirmation dialogs.
"""
import sdl2
from typing import Optional, Dict, Tuple, List
from utils.theme import Theme
from utils.config import Config
from utils.logger import logger
from utils.download_manager import DownloadManager
from .base_view import BaseView

class ConfirmationDialog(BaseView):
    """View class for rendering confirmation dialogs"""
    
    def __init__(self, renderer, font, texture_manager):
        """Initialize the confirmation dialog view"""
        super().__init__(renderer, font, texture_manager)
        
    def render(self, 
               message: str,
               confirmation_selected: bool,
               button_texts: Tuple[str, str] = ("Yes", "No"),
               button_colors: Optional[Tuple[Tuple[int, int, int, int], Tuple[int, int, int, int]]] = None,
               additional_info: Optional[List[Tuple[str, Tuple[int, int, int, int]]]] = None) -> None:
        """Render the confirmation dialog
        
        Args:
            message: Main message to display in the dialog
            confirmation_selected: Whether the first button is selected
            button_texts: Tuple of (first_button_text, second_button_text) - defaults to ("Yes", "No")
            button_colors: Tuple of (selected_color, unselected_color) for buttons - defaults to theme colors
            additional_info: List of tuples containing (text, color) for additional information lines
        """
        try:
            # Draw semi-transparent overlay with blur effect
            overlay = sdl2.SDL_Rect(0, 0, Config.SCREEN_WIDTH, Config.SCREEN_HEIGHT)
            sdl2.SDL_SetRenderDrawColor(self.renderer, *Theme.OVERLAY_COLOR)
            sdl2.SDL_SetRenderDrawBlendMode(self.renderer, sdl2.SDL_BLENDMODE_BLEND)
            sdl2.SDL_RenderFillRect(self.renderer, overlay)
            
            # Dialog box dimensions
            dialog_x = (Config.SCREEN_WIDTH - Config.DIALOG_WIDTH) // 2
            dialog_y = (Config.SCREEN_HEIGHT - Config.DIALOG_HEIGHT) // 2
            
            # Draw dialog shadow
            shadow_rect = sdl2.SDL_Rect(
                dialog_x + 4,
                dialog_y + 4,
                Config.DIALOG_WIDTH,
                Config.DIALOG_HEIGHT
            )
            sdl2.SDL_SetRenderDrawColor(self.renderer, *Theme.DIALOG_SHADOW)
            sdl2.SDL_RenderFillRect(self.renderer, shadow_rect)
            
            # Draw dialog background with gradient
            dialog_rect = sdl2.SDL_Rect(dialog_x, dialog_y, Config.DIALOG_WIDTH, Config.DIALOG_HEIGHT)
            sdl2.SDL_SetRenderDrawColor(self.renderer, *Theme.DIALOG_BG, 255)
            sdl2.SDL_RenderFillRect(self.renderer, dialog_rect)
            
            # Draw dialog border with rounded corners
            sdl2.SDL_SetRenderDrawColor(self.renderer, *Theme.DIALOG_BORDER, 255)
            sdl2.SDL_RenderDrawRect(self.renderer, dialog_rect)
            
            # Draw main message with improved styling
            self.render_text(
                message,
                Config.SCREEN_WIDTH // 2,
                dialog_y + Config.DIALOG_MESSAGE_MARGIN,
                color=Theme.DIALOG_TITLE,  # Use title color for main message
                center=True
            )
            
            # Draw additional information if provided
            if additional_info:
                for i, (text, color) in enumerate(additional_info):
                    self.render_text(
                        text,
                        Config.SCREEN_WIDTH // 2,
                        dialog_y + Config.DIALOG_MESSAGE_MARGIN + 40 + (i * 40),
                        color=color,
                        center=True
                    )
            
            # Set button colors
            if button_colors is None:
                button_colors = (
                    Theme.CONFIRM_YES_SELECTED if confirmation_selected else Theme.CONFIRM_YES_UNSELECTED,
                    Theme.CONFIRM_NO_UNSELECTED if confirmation_selected else Theme.CONFIRM_NO_SELECTED
                )
            
            # Calculate button positions relative to dialog center
            button_y = dialog_y + Config.DIALOG_BUTTON_Y
            button_spacing = 40  # Space between buttons
            total_buttons_width = (Config.DIALOG_BUTTON_WIDTH * 2) + button_spacing
            start_x = dialog_x + (Config.DIALOG_WIDTH - total_buttons_width) // 2
            
            # Draw first button background
            first_button_rect = sdl2.SDL_Rect(
                start_x,
                button_y - 10,
                Config.DIALOG_BUTTON_WIDTH,
                40
            )
            sdl2.SDL_SetRenderDrawColor(self.renderer, *Theme.BUTTON_BG if confirmation_selected else Theme.BUTTON_DISABLED_BG, 200)
            sdl2.SDL_RenderFillRect(self.renderer, first_button_rect)
            sdl2.SDL_SetRenderDrawColor(self.renderer, *Theme.BUTTON_BORDER, 255)
            sdl2.SDL_RenderDrawRect(self.renderer, first_button_rect)
            
            # Draw second button background
            second_button_rect = sdl2.SDL_Rect(
                start_x + Config.DIALOG_BUTTON_WIDTH + button_spacing,
                button_y - 10,
                Config.DIALOG_BUTTON_WIDTH,
                40
            )
            sdl2.SDL_SetRenderDrawColor(self.renderer, *Theme.BUTTON_BG if not confirmation_selected else Theme.BUTTON_DISABLED_BG, 200)
            sdl2.SDL_RenderFillRect(self.renderer, second_button_rect)
            sdl2.SDL_SetRenderDrawColor(self.renderer, *Theme.BUTTON_BORDER, 255)
            sdl2.SDL_RenderDrawRect(self.renderer, second_button_rect)
            
            # Draw button text
            self.render_text(
                button_texts[0],
                start_x + Config.DIALOG_BUTTON_WIDTH // 2,
                button_y,
                color=Theme.BUTTON_TEXT if confirmation_selected else Theme.TEXT_DISABLED,
                center=True
            )
            
            self.render_text(
                button_texts[1],
                start_x + Config.DIALOG_BUTTON_WIDTH + button_spacing + Config.DIALOG_BUTTON_WIDTH // 2,
                button_y,
                color=Theme.BUTTON_TEXT if not confirmation_selected else Theme.TEXT_DISABLED,
                center=True
            )
            
        except Exception as e:
            logger.error(f"Error rendering confirmation dialog: {e}", exc_info=True)
            raise 