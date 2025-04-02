"""
View class for rendering the on-screen keyboard for search functionality.
"""
from typing import Tuple
import sdl2
from utils.theme import Theme
from utils.config import Config
from utils.logger import logger
from .base_view import BaseView

class KeyboardView(BaseView):
    """View class for rendering the on-screen keyboard"""
    
    def __init__(self, renderer, font, texture_manager):
        """Initialize the keyboard view with layout"""
        super().__init__(renderer, font, texture_manager)
        self.keyboard_layout = [
            ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '<'],
            ['Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P'],
            ['A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L'],
            ['Z', 'X', 'C', 'V', 'B', 'N', 'M'],
            ['Space', 'Return']
        ]
        
    def render(self, selected_key: int, search_text: str) -> None:
        """Render the on-screen keyboard and search box
        
        Args:
            selected_key: Index of the currently selected key
            search_text: Current search text
        """
        try:
            # Semi-transparent overlay
            overlay = sdl2.SDL_Rect(0, 0, Config.SCREEN_WIDTH, Config.SCREEN_HEIGHT)
            sdl2.SDL_SetRenderDrawBlendMode(self.renderer, sdl2.SDL_BLENDMODE_BLEND)
            sdl2.SDL_SetRenderDrawColor(self.renderer, *Theme.OVERLAY_COLOR)
            sdl2.SDL_RenderFillRect(self.renderer, overlay)

            # Create keyboard panel with adjusted size
            panel_padding = 20
            panel_height = 300
            panel_y = Config.SCREEN_HEIGHT - panel_height - panel_padding
            panel_width = min(800, Config.SCREEN_WIDTH - (panel_padding * 2))
            panel_x = (Config.SCREEN_WIDTH - panel_width) // 2
            
            panel_rect = sdl2.SDL_Rect(
                panel_x,
                panel_y,
                panel_width,
                panel_height
            )

            # Draw panel background with shadow
            shadow_rect = sdl2.SDL_Rect(
                panel_rect.x + 4,
                panel_rect.y + 4,
                panel_rect.w,
                panel_rect.h
            )
            sdl2.SDL_SetRenderDrawColor(self.renderer, *Theme.SHADOW_COLOR)
            sdl2.SDL_RenderFillRect(self.renderer, shadow_rect)

            sdl2.SDL_SetRenderDrawColor(self.renderer, 30, 30, 30, 255)
            sdl2.SDL_RenderFillRect(self.renderer, panel_rect)
            
            sdl2.SDL_SetRenderDrawColor(self.renderer, 50, 50, 50, 255)
            sdl2.SDL_RenderDrawRect(self.renderer, panel_rect)

            # Render search box with modern design
            search_box_height = 40
            search_box_y = panel_y + 20
            search_box_padding = 20
            
            # Draw search box background
            search_box_rect = sdl2.SDL_Rect(
                panel_x + search_box_padding,
                search_box_y,
                panel_width - (search_box_padding * 2),
                search_box_height
            )
            sdl2.SDL_SetRenderDrawColor(self.renderer, *Theme.INPUT_BG, 255)
            sdl2.SDL_RenderFillRect(self.renderer, search_box_rect)
            
            # Draw search box border with glow effect
            glow_color = Theme.GLOW_COLOR if search_text else (*Theme.INPUT_BORDER, 255)
            sdl2.SDL_SetRenderDrawColor(self.renderer, *glow_color)
            sdl2.SDL_RenderDrawRect(self.renderer, search_box_rect)

            # Render search text or placeholder
            text_y = search_box_y + (search_box_height - 24) // 2
            if search_text:
                self.render_text(
                    search_text,
                    panel_x + search_box_padding + 10,
                    text_y,
                    color=(230, 230, 230),
                    center=False
                )
            else:
                self.render_text(
                    "Type to search games...",
                    panel_x + search_box_padding + 10,
                    text_y,
                    color=(120, 120, 120),
                    center=False
                )

            # Keyboard layout with improved styling
            keyboard_y = search_box_y + search_box_height + 20
            keyboard_width = panel_width - (search_box_padding * 2)
            key_height = 36
            key_spacing = 6

            # Calculate key sizes based on available width
            standard_key_width = int((keyboard_width - (11 * key_spacing)) / 12)  # Based on longest row (11 keys)
            backspace_width = int(standard_key_width * 1.5)
            space_width = int(keyboard_width * 0.6)  # 60% of keyboard width
            return_width = keyboard_width - space_width - key_spacing  # Remaining width

            current_key_index = 0

            for row_index, row in enumerate(self.keyboard_layout):
                # Calculate row width
                row_width = 0
                for key in row:
                    if key == 'Space':
                        row_width += space_width + key_spacing
                    elif key == 'Return':
                        row_width += return_width + key_spacing
                    elif key == '<':
                        row_width += backspace_width + key_spacing
                    else:
                        row_width += standard_key_width + key_spacing
                row_width -= key_spacing

                # Center the row
                current_x = panel_x + (panel_width - row_width) // 2

                for key in row:
                    # Calculate key width
                    if key == 'Space':
                        current_key_width = space_width
                    elif key == 'Return':
                        current_key_width = return_width
                    elif key == '<':
                        current_key_width = backspace_width
                    else:
                        current_key_width = standard_key_width

                    # Create key rectangle
                    key_rect = sdl2.SDL_Rect(
                        int(current_x),
                        int(keyboard_y + (key_height + key_spacing) * row_index),
                        int(current_key_width),
                        key_height
                    )

                    # Draw key background
                    is_selected = current_key_index == selected_key
                    if is_selected:
                        sdl2.SDL_SetRenderDrawColor(self.renderer, *Theme.KEYBOARD_KEY_SELECTED, 255)
                    else:
                        if key in ['Space', 'Return', '<']:
                            sdl2.SDL_SetRenderDrawColor(self.renderer, 45, 45, 45, 255)
                        else:
                            sdl2.SDL_SetRenderDrawColor(self.renderer, 40, 40, 40, 255)
                    sdl2.SDL_RenderFillRect(self.renderer, key_rect)

                    # Draw key border
                    if is_selected:
                        border_color = (*Theme.KEYBOARD_KEY_SELECTED, 255)
                    else:
                        border_color = (70, 70, 70, 255) if key in ['Space', 'Return', '<'] else (60, 60, 60, 255)
                    sdl2.SDL_SetRenderDrawColor(self.renderer, *border_color)
                    sdl2.SDL_RenderDrawRect(self.renderer, key_rect)

                    # Render key text
                    text_color = Theme.KEYBOARD_KEY_TEXT_SELECTED if is_selected else Theme.KEYBOARD_KEY_TEXT
                    
                    display_text = key.upper()

                    self.render_text(
                        display_text,
                        int(current_x + current_key_width // 2),
                        int(keyboard_y + (key_height + key_spacing) * row_index + (key_height - 24) // 2),
                        color=text_color,
                        center=True
                    )

                    current_x += current_key_width + key_spacing
                    current_key_index += 1

        except Exception as e:
            logger.error(f"Error rendering keyboard: {e}", exc_info=True)
            
    def get_keyboard_position(self, selected_key: int) -> Tuple[int, int]:
        """Get the current row and position within row for keyboard navigation
        
        Args:
            selected_key: Index of the currently selected key
            
        Returns:
            Tuple[int, int]: (row_index, position_in_row)
        """
        current_index = 0
        for row_index, row in enumerate(self.keyboard_layout):
            row_length = len(row)
            if current_index + row_length > selected_key:
                return row_index, selected_key - current_index
            current_index += row_length
        return len(self.keyboard_layout) - 1, 0 