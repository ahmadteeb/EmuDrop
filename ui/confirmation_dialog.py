"""
View class for rendering confirmation dialogs.
"""
import sdl2
from typing import Optional, Tuple, List, Dict
from utils.theme import Theme
from utils.config import Config
from utils.logger import logger
from .base_view import BaseView
import time

class ConfirmationDialog(BaseView):
    """View class for rendering confirmation dialogs"""
    
    def __init__(self, renderer, font=None):
        """Initialize the confirmation dialog view"""
        super().__init__(renderer, font)
        self.marquee_states = {}  # Store marquee state for text
        self.marquee_speed = int(50 * Config.SCALE_FACTOR)  # Scale the marquee speed
        self.marquee_pause = 2.0  # Seconds to pause at each end
        
    def _get_marquee_state(self, text_id: str, text_width: int, container_width: int) -> Dict:
        """Get or initialize marquee state for text"""
        if text_id not in self.marquee_states:
            self.marquee_states[text_id] = {
                'offset': 0,
                'direction': 1,
                'pause_time': 0,
                'last_update': time.time()
            }
        
        state = self.marquee_states[text_id]
        current_time = time.time()
        delta_time = current_time - state['last_update']
        state['last_update'] = current_time
        
        # If text fits, don't animate
        if text_width <= container_width:
            state['offset'] = 0
            return state
            
        # Handle pausing at ends
        if state['pause_time'] > 0:
            state['pause_time'] -= delta_time
            return state
            
        # Calculate maximum offset to ensure text stays within container
        max_offset = text_width - container_width
        
        # Update position
        state['offset'] += self.marquee_speed * delta_time * state['direction']
        
        # Clamp offset to valid range
        state['offset'] = max(0, min(state['offset'], max_offset))
        
        # Handle direction changes
        if state['offset'] >= max_offset:
            state['direction'] = -1
            state['pause_time'] = self.marquee_pause
        elif state['offset'] <= 0:
            state['direction'] = 1
            state['pause_time'] = self.marquee_pause
            
        return state
        
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
            
            # Draw dialog shadow with scaled offset
            shadow_offset = int(4 * Config.SCALE_FACTOR)
            shadow_rect = sdl2.SDL_Rect(
                dialog_x + shadow_offset,
                dialog_y + shadow_offset,
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
            
            # Calculate maximum width for text
            max_message_width = Config.DIALOG_WIDTH - (Config.DIALOG_PADDING * 2)
            
            # Create text surface to get dimensions
            text_color = sdl2.SDL_Color(*Theme.DIALOG_TITLE)
            text_surface = sdl2.sdlttf.TTF_RenderText_Blended(
                self.font,
                message.encode('utf-8'),
                text_color
            )
            
            if text_surface:
                text_width = text_surface.contents.w
                text_height = text_surface.contents.h
                
                # Create texture from surface
                texture = sdl2.SDL_CreateTextureFromSurface(self.renderer, text_surface)
                sdl2.SDL_FreeSurface(text_surface)
                
                if texture:
                    if text_width > max_message_width:
                        # Get marquee state for text that needs scrolling
                        state = self._get_marquee_state('message', text_width, max_message_width)
                        
                        # Calculate the visible portion
                        visible_width = min(max_message_width, text_width - int(state['offset']))
                        
                        # Setup source rectangle (the portion of text to show)
                        src_rect = sdl2.SDL_Rect(
                            int(state['offset']),  # Start from offset
                            0,
                            visible_width,  # Show only what fits
                            text_height
                        )
                        
                        # Setup destination rectangle (where to render)
                        dst_rect = sdl2.SDL_Rect(
                            dialog_x + Config.DIALOG_PADDING,
                            dialog_y + Config.DIALOG_MESSAGE_MARGIN,
                            visible_width,
                            text_height
                        )
                        
                        # Render the clipped portion
                        sdl2.SDL_RenderCopy(self.renderer, texture, src_rect, dst_rect)
                    else:
                        # Text fits, render normally centered
                        dst_rect = sdl2.SDL_Rect(
                            dialog_x + (Config.DIALOG_WIDTH - text_width) // 2,
                            dialog_y + Config.DIALOG_MESSAGE_MARGIN,
                            text_width,
                            text_height
                        )
                        sdl2.SDL_RenderCopy(self.renderer, texture, None, dst_rect)
                    
                    sdl2.SDL_DestroyTexture(texture)
            
            # Draw additional information if provided
            if additional_info:
                line_spacing = int(40 * Config.SCALE_FACTOR)
                for i, (text, color) in enumerate(additional_info):
                    text_surface = sdl2.sdlttf.TTF_RenderText_Blended(
                        self.font,
                        text.encode('utf-8'),
                        sdl2.SDL_Color(*color)
                    )
                    
                    if text_surface:
                        text_width = text_surface.contents.w
                        text_height = text_surface.contents.h
                        
                        texture = sdl2.SDL_CreateTextureFromSurface(self.renderer, text_surface)
                        sdl2.SDL_FreeSurface(text_surface)
                        
                        if texture:
                            if text_width > max_message_width:
                                # Get marquee state for additional text
                                state = self._get_marquee_state(f'additional_{i}', text_width, max_message_width)
                                
                                # Calculate the visible portion
                                visible_width = min(max_message_width, text_width - int(state['offset']))
                                
                                src_rect = sdl2.SDL_Rect(
                                    int(state['offset']),
                                    0,
                                    visible_width,
                                    text_height
                                )
                                
                                dst_rect = sdl2.SDL_Rect(
                                    dialog_x + Config.DIALOG_PADDING,
                                    dialog_y + Config.DIALOG_MESSAGE_MARGIN + line_spacing + (i * line_spacing),
                                    visible_width,
                                    text_height
                                )
                                
                                sdl2.SDL_RenderCopy(self.renderer, texture, src_rect, dst_rect)
                            else:
                                # Text fits, render normally centered
                                dst_rect = sdl2.SDL_Rect(
                                    dialog_x + (Config.DIALOG_WIDTH - text_width) // 2,
                                    dialog_y + Config.DIALOG_MESSAGE_MARGIN + line_spacing + (i * line_spacing),
                                    text_width,
                                    text_height
                                )
                                sdl2.SDL_RenderCopy(self.renderer, texture, None, dst_rect)
                            
                            sdl2.SDL_DestroyTexture(texture)
            
            # Set button colors
            if button_colors is None:
                button_colors = (
                    Theme.CONFIRM_YES_SELECTED if confirmation_selected else Theme.CONFIRM_YES_UNSELECTED,
                    Theme.CONFIRM_NO_UNSELECTED if confirmation_selected else Theme.CONFIRM_NO_SELECTED
                )
            
            # Calculate button positions relative to dialog center with scaled dimensions
            button_y = dialog_y + Config.DIALOG_BUTTON_Y
            button_spacing = int(40 * Config.SCALE_FACTOR)  # Scale space between buttons
            button_height = int(40 * Config.SCALE_FACTOR)  # Scale button height
            button_y_offset = int(10 * Config.SCALE_FACTOR)  # Scale vertical offset
            total_buttons_width = (Config.DIALOG_BUTTON_WIDTH * 2) + button_spacing
            start_x = dialog_x + (Config.DIALOG_WIDTH - total_buttons_width) // 2
            
            # Draw first button background
            first_button_rect = sdl2.SDL_Rect(
                start_x,
                button_y - button_y_offset,
                Config.DIALOG_BUTTON_WIDTH,
                button_height
            )
            sdl2.SDL_SetRenderDrawColor(self.renderer, *Theme.BUTTON_BG if confirmation_selected else Theme.BUTTON_DISABLED_BG, 200)
            sdl2.SDL_RenderFillRect(self.renderer, first_button_rect)
            sdl2.SDL_SetRenderDrawColor(self.renderer, *Theme.BUTTON_BORDER, 255)
            sdl2.SDL_RenderDrawRect(self.renderer, first_button_rect)
            
            # Draw second button background
            second_button_rect = sdl2.SDL_Rect(
                start_x + Config.DIALOG_BUTTON_WIDTH + button_spacing,
                button_y - button_y_offset,
                Config.DIALOG_BUTTON_WIDTH,
                button_height
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