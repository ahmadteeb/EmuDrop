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
    
    def __init__(self, renderer, font=None):
        """Initialize the keyboard view with layout"""
        super().__init__(renderer, font)
        self.keyboard_layout = [
            ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '@'],
            ['Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P', '#'],
            ['A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L', '"', '/'],
            ['Z', 'X', 'C', 'V', 'B', 'N', 'M', '-', '_', '?', '!'],
            ['Clear', 'Space', 'Return', '<']
        ]
        self.cursor_blink_rate = 530  # Blink rate in milliseconds
        
    def render(self, selected_key: int, search_text: str) -> None:
        """Render the on-screen keyboard and search box"""
        try:
            # Semi-transparent overlay
            overlay = sdl2.SDL_Rect(0, 0, Config.SCREEN_WIDTH, Config.SCREEN_HEIGHT)
            sdl2.SDL_SetRenderDrawBlendMode(self.renderer, sdl2.SDL_BLENDMODE_BLEND)
            sdl2.SDL_SetRenderDrawColor(self.renderer, *Theme.OVERLAY_COLOR)
            sdl2.SDL_RenderFillRect(self.renderer, overlay)

            # Create keyboard panel with scaled dimensions
            panel_padding = int(20 * Config.SCALE_FACTOR)
            panel_height = int(300 * Config.SCALE_FACTOR)
            panel_y = Config.SCREEN_HEIGHT - panel_height - panel_padding
            panel_width = min(int(800 * Config.SCALE_FACTOR), Config.SCREEN_WIDTH - (panel_padding * 2))
            panel_x = (Config.SCREEN_WIDTH - panel_width) // 2
            
            panel_rect = sdl2.SDL_Rect(
                panel_x,
                panel_y,
                panel_width,
                panel_height
            )

            # Draw panel background with shadow
            shadow_offset = int(4 * Config.SCALE_FACTOR)
            shadow_rect = sdl2.SDL_Rect(
                panel_rect.x + shadow_offset,
                panel_rect.y + shadow_offset,
                panel_rect.w,
                panel_rect.h
            )
            sdl2.SDL_SetRenderDrawColor(self.renderer, *Theme.SHADOW_COLOR)
            sdl2.SDL_RenderFillRect(self.renderer, shadow_rect)

            sdl2.SDL_SetRenderDrawColor(self.renderer, 30, 30, 30, 255)
            sdl2.SDL_RenderFillRect(self.renderer, panel_rect)
            
            sdl2.SDL_SetRenderDrawColor(self.renderer, 50, 50, 50, 255)
            sdl2.SDL_RenderDrawRect(self.renderer, panel_rect)

            # Render search box with scaled dimensions
            search_box_height = int(40 * Config.SCALE_FACTOR)
            search_box_y = panel_y + int(20 * Config.SCALE_FACTOR)
            search_box_padding = int(20 * Config.SCALE_FACTOR)
            
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

            # Render search text or placeholder with scaled dimensions
            text_padding = int(10 * Config.SCALE_FACTOR)
            text_y = search_box_y + (search_box_height - int(24 * Config.SCALE_FACTOR)) // 2
            text_x = panel_x + search_box_padding + text_padding
            
            if search_text:
                # Get text dimensions for cursor positioning
                text_surface = sdl2.sdlttf.TTF_RenderText_Solid(
                    self.font,
                    search_text.encode(),
                    sdl2.SDL_Color(230, 230, 230)
                )
                text_width = text_surface.contents.w
                sdl2.SDL_FreeSurface(text_surface)
                
                # Render the search text
                self.render_text(
                    search_text,
                    text_x,
                    text_y,
                    color=(230, 230, 230),
                    center=False
                )
                
                # Draw blinking cursor with scaled dimensions
                current_time = sdl2.SDL_GetTicks()
                if (current_time // self.cursor_blink_rate) % 2 == 0:
                    cursor_x = text_x + text_width + int(2 * Config.SCALE_FACTOR)
                    cursor_height = int(20 * Config.SCALE_FACTOR)
                    cursor_y = text_y + int(2 * Config.SCALE_FACTOR)
                    
                    # Draw cursor line
                    sdl2.SDL_SetRenderDrawColor(self.renderer, 230, 230, 230, 255)
                    sdl2.SDL_RenderDrawLine(
                        self.renderer,
                        cursor_x,
                        cursor_y,
                        cursor_x,
                        cursor_y + cursor_height
                    )
            else:
                self.render_text(
                    "Type to search games...",
                    text_x,
                    text_y,
                    color=(120, 120, 120),
                    center=False
                )

            # Keyboard layout with scaled dimensions
            keyboard_y = search_box_y + search_box_height + int(20 * Config.SCALE_FACTOR)
            keyboard_width = panel_width - (search_box_padding * 2)
            key_height = int(36 * Config.SCALE_FACTOR)
            key_spacing = int(6 * Config.SCALE_FACTOR)

            # Calculate key sizes based on available width
            standard_key_width = int((keyboard_width - (10 * key_spacing)) / 11)  # Based on regular rows with 11 keys
            
            # Calculate total width of regular rows (this is our target width)
            regular_row_width = (standard_key_width * 11) + (10 * key_spacing)
            
            # Calculate special key widths
            clear_width = (standard_key_width * 2) + key_spacing  # Exactly 2 keys + 1 spacing
            backspace_width = (standard_key_width * 2) + key_spacing  # Exactly 2 keys + 1 spacing
            
            # Remaining width split evenly between SPACE and RETURN
            remaining_width = regular_row_width - clear_width - backspace_width - (3 * key_spacing)
            space_width = remaining_width // 2
            return_width = remaining_width - space_width  # Give any odd pixel to RETURN

            current_key_index = 0

            for row_index, row in enumerate(self.keyboard_layout):
                # Calculate row width
                row_width = 0
                for key in row:
                    if key == 'Space':
                        row_width += space_width + key_spacing
                    elif key == 'Clear':
                        row_width += clear_width + key_spacing
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
                    elif key == 'Clear':
                        current_key_width = clear_width
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
                        int(keyboard_y + (key_height + key_spacing) * row_index + (key_height - int(24 * Config.SCALE_FACTOR)) // 2),
                        color=text_color,
                        center=True
                    )

                    current_x += current_key_width + key_spacing
                    current_key_index += 1

        except Exception as e:
            logger.error(f"Error rendering keyboard: {e}", exc_info=True)
            
    def get_key_index(self, row_index: int, position: int) -> int:
        """Get the absolute key index from row and position."""
        total = 0
        for i in range(row_index):
            total += len(self.keyboard_layout[i])
        return total + position
        
    def get_keyboard_position(self, selected_key: int) -> Tuple[int, int]:
        """Get the row and position for a key index."""
        current_index = 0
        for row_index, row in enumerate(self.keyboard_layout):
            row_length = len(row)
            if current_index + row_length > selected_key:
                return row_index, selected_key - current_index
            current_index += row_length
        return len(self.keyboard_layout) - 1, len(self.keyboard_layout[-1]) - 1 