"""
View class for rendering alert dialogs.
"""
import sdl2
from typing import Optional, List, Tuple
from utils.theme import Theme
from utils.config import Config
from utils.logger import logger
from .base_view import BaseView

class AlertDialog(BaseView):
    """View class for rendering alert dialogs with a single OK button"""
    
    def __init__(self, renderer, font, texture_manager):
        """Initialize the alert dialog view"""
        super().__init__(renderer, font, texture_manager)
        
    def render(self, 
               message: str,
               additional_info: Optional[List[Tuple[str, Tuple[int, int, int, int]]]] = None) -> None:
        """Render the alert dialog
        
        Args:
            message: Main message to display in the dialog
            additional_info: Optional list of tuples containing (text, color) for additional information lines
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
            
            # Calculate button position
            button_y = dialog_y + Config.DIALOG_BUTTON_Y
            button_width = Config.DIALOG_BUTTON_WIDTH
            button_x = dialog_x + (Config.DIALOG_WIDTH - button_width) // 2
            
            # Draw OK button background with highlight effect
            button_rect = sdl2.SDL_Rect(
                button_x,
                button_y - 10,
                button_width,
                40
            )
            sdl2.SDL_SetRenderDrawColor(self.renderer, *Theme.BUTTON_BG, 200)
            sdl2.SDL_RenderFillRect(self.renderer, button_rect)
            
            # Draw button border
            sdl2.SDL_SetRenderDrawColor(self.renderer, *Theme.BUTTON_BORDER, 255)
            sdl2.SDL_RenderDrawRect(self.renderer, button_rect)
            
            # Draw button text
            self.render_text(
                "OK",
                button_x + button_width // 2,
                button_y,
                color=Theme.BUTTON_TEXT,
                center=True
            )
            
            # Draw control guide
            controls = {
                'right': [
                    "select.png"  # Show A button for OK
                ]
            }
            self.render_control_guides(controls)
            
        except Exception as e:
            logger.error(f"Error rendering alert dialog: {e}", exc_info=True)
            raise 