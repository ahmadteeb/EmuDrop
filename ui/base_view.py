"""
Base view class that provides common functionality for all views.
"""
from typing import Dict, List, Optional, Tuple
import sdl2
import math
import time
import os
import ctypes
from utils.theme import Theme
from utils.config import Config
from utils.logger import logger

class BaseView:
    """Base class for all views in the application"""
    
    def __init__(self, renderer, font=None):
        """Initialize the base view with common components"""
        self.renderer = renderer
        self.font = font if font else self._load_font()
        self.texture_manager = None
        
    def set_texture_manager(self, texture_manager):
        """Set the texture manager instance"""
        self.texture_manager = texture_manager
    
    def get_texture(self, image_path: str) -> Optional[sdl2.SDL_Texture]:
        """Get a texture using the texture manager"""
        if self.texture_manager:
            return self.texture_manager.get_texture(image_path)
        return None
    
    def _load_font(self):
        """Load the font with the correct scaled size"""
        font_path = Config.get_font_path()
        if font_path:
            try:
                font = sdl2.sdlttf.TTF_OpenFont(font_path.encode('utf-8'), Config.FONT_SIZE)
                if font:
                    logger.info(f"Font loaded successfully: {font_path}")
                    return font
            except Exception as e:
                logger.error(f"Failed to load font: {e}")
        return None
        
    def render_title(self, title: str) -> None:
        """Render a title at the top of the view"""
        self.render_text(
            title,
            Config.SCREEN_WIDTH // 2,
            int(40 * Config.SCALE_FACTOR),  # Scale the position
            color=Theme.TEXT_PRIMARY,
            center=True
        )
        
    def render_background(self, simplified=False) -> None:
        """Render a modern gradient background with subtle animation"""
        try:
            if simplified:
                sdl2.SDL_SetRenderDrawColor(self.renderer, *Theme.BG_DARK, 255)
                bg_rect = sdl2.SDL_Rect(0, 0, Config.SCREEN_WIDTH, Config.SCREEN_HEIGHT)
                sdl2.SDL_RenderFillRect(self.renderer, bg_rect)
                return
                
            current_time = time.time()
            animation = (math.sin(current_time) + 1) * 0.5
            
            for y in range(Config.SCREEN_HEIGHT):
                progress = y / Config.SCREEN_HEIGHT
                base_r = int(Theme.BG_DARKER[0] + (Theme.BG_DARK[0] - Theme.BG_DARKER[0]) * progress)
                base_g = int(Theme.BG_DARKER[1] + (Theme.BG_DARK[1] - Theme.BG_DARKER[1]) * progress)
                base_b = int(Theme.BG_DARKER[2] + (Theme.BG_DARK[2] - Theme.BG_DARKER[2]) * progress)
                
                r = int(base_r + animation * 10)
                g = int(base_g + animation * 10)
                b = int(base_b + animation * 10)
                
                sdl2.SDL_SetRenderDrawColor(self.renderer, r, g, b, 255)
                line = sdl2.SDL_Rect(0, y, Config.SCREEN_WIDTH, 1)
                sdl2.SDL_RenderFillRect(self.renderer, line)

        except Exception as e:
            logger.error(f"Error rendering background: {e}", exc_info=True)
            
    def render_card(self, x: int, y: int, width: int, height: int, 
                   selected: bool = False, hovered: bool = False) -> None:
        """Render a modern card with shadow and hover effects"""
        try:
            # Scale shadow offset
            shadow_offset = int(4 * Config.SCALE_FACTOR)
            
            # Draw shadow
            shadow_rect = sdl2.SDL_Rect(
                int(x + shadow_offset),
                int(y + shadow_offset),
                int(width),
                int(height)
            )
            sdl2.SDL_SetRenderDrawBlendMode(self.renderer, sdl2.SDL_BLENDMODE_BLEND)
            sdl2.SDL_SetRenderDrawColor(self.renderer, *Theme.SHADOW_COLOR)
            sdl2.SDL_RenderFillRect(self.renderer, shadow_rect)
            
            # Draw card background
            bg_color = Theme.CARD_SELECTED if selected else Theme.CARD_BG
            if hovered:
                bg_color = Theme.get_hover_color(bg_color)
            
            card_rect = sdl2.SDL_Rect(int(x), int(y), int(width), int(height))
            sdl2.SDL_SetRenderDrawColor(self.renderer, *bg_color, 255)
            sdl2.SDL_RenderFillRect(self.renderer, card_rect)
            
            # Draw border
            sdl2.SDL_SetRenderDrawColor(self.renderer, *Theme.CARD_BORDER, 255)
            sdl2.SDL_RenderDrawRect(self.renderer, card_rect)
            
            # Draw glow effect for selected cards
            if selected:
                glow_size = int(2 * Config.SCALE_FACTOR)
                sdl2.SDL_SetRenderDrawBlendMode(self.renderer, sdl2.SDL_BLENDMODE_BLEND)
                sdl2.SDL_SetRenderDrawColor(self.renderer, *Theme.GLOW_COLOR)
                glow_rect = sdl2.SDL_Rect(
                    int(x - glow_size),
                    int(y - glow_size),
                    int(width + glow_size * 2),
                    int(height + glow_size * 2)
                )
                sdl2.SDL_RenderFillRect(self.renderer, glow_rect)

        except Exception as e:
            logger.error(f"Error rendering card: {e}", exc_info=True)
            
    def create_text_texture(self, text: str, color: tuple = Theme.TEXT_PRIMARY) -> Tuple[Optional[sdl2.SDL_Texture], int, int]:
        """Create a texture from text using the texture manager"""
        try:
            text_color = sdl2.SDL_Color(*color)
            surface = sdl2.sdlttf.TTF_RenderText_Blended(self.font, text.encode(), text_color)
            if surface and self.texture_manager:
                texture = sdl2.SDL_CreateTextureFromSurface(self.renderer, surface)
                width = surface.contents.w
                height = surface.contents.h
                sdl2.SDL_FreeSurface(surface)
                return texture, width, height
        except Exception as e:
            logger.error(f"Error creating text texture: {e}", exc_info=True)
        return None, 0, 0

    def render_text(self, text: str, x: int, y: int, 
                   color: tuple = Theme.TEXT_PRIMARY, 
                   center: bool = False) -> None:
        """Render text at the specified position"""
        try:
            texture, width, height = self.create_text_texture(text, color)
            if texture:
                if center:
                    x -= width // 2
                rect = sdl2.SDL_Rect(int(x), int(y), width, height)
                sdl2.SDL_RenderCopy(self.renderer, texture, None, rect)
                sdl2.SDL_DestroyTexture(texture)
        except Exception as e:
            logger.error(f"Error rendering text: {e}", exc_info=True)
            
    def _render_page_navigation(self, current_page: int, total_pages: int, search_text_result: int=None) -> None:
        """Render page navigation controls"""
        page_text = f"Page {current_page + 1} of {total_pages}"
        self.render_text(
            page_text,
            Config.SCREEN_WIDTH // 2,
            Config.SCREEN_HEIGHT - int(40 * Config.SCALE_FACTOR),
            color=Theme.TEXT_SECONDARY,
            center=True
        )
        if search_text_result:
            self.render_text(
                search_text_result,
                Config.SCREEN_WIDTH // 2,
                Config.SCREEN_HEIGHT - int(70 * Config.SCALE_FACTOR),
                color=Theme.TEXT_ACCENT,
                center=True
            )

    def _get_texture_dimensions(self, texture) -> Tuple[int, int]:
        """Get the width and height of a texture"""
        w = ctypes.c_int()
        h = ctypes.c_int()
        sdl2.SDL_QueryTexture(texture, None, None, ctypes.byref(w), ctypes.byref(h))
        return w.value, h.value

    def _calculate_render_dimensions(self, width: int, height: int) -> Tuple[int, int, int]:
        """Calculate render dimensions and vertical offset while maintaining aspect ratio"""
        aspect_ratio = width / height
        if aspect_ratio > 1:  # Wider than tall
            render_width = Config.CONTROL_SIZE
            render_height = int(Config.CONTROL_SIZE / aspect_ratio)
            y_offset = (Config.CONTROL_SIZE - render_height) // 2
        else:  # Taller than wide
            render_height = Config.CONTROL_SIZE
            render_width = int(Config.CONTROL_SIZE * aspect_ratio)
            y_offset = 0
        return render_width, render_height, y_offset

    def _render_control_image(self, image_name: str, x: int, y: int) -> None:
        """Render a single control image at the specified position"""
        try:
            image_path = os.path.join(Config.IMAGES_CONTROLS_DIR, image_name)
            texture = self.get_texture(image_path)
            if texture:
                width, height = self._get_texture_dimensions(texture)
                render_width, render_height, y_offset = self._calculate_render_dimensions(width, height)
                
                rect = sdl2.SDL_Rect(
                    int(x),
                    int(y + y_offset),
                    render_width,
                    render_height
                )
                sdl2.SDL_RenderCopy(self.renderer, texture, None, rect)
        except Exception as e:
            logger.error(f"Error rendering control image: {e}", exc_info=True)
            
    def render_control_guides(self, controls: Dict[str, List[str]]) -> None:
        """Render control guides at the bottom of the screen"""
        try:
            # Calculate scaled positions
            bottom_y = Config.SCREEN_HEIGHT - Config.CONTROL_BOTTOM_MARGIN
            left_x = Config.CONTROL_MARGIN
            right_x = Config.SCREEN_WIDTH - Config.CONTROL_MARGIN
            
            # Render left controls
            for i, image_name in enumerate(controls.get('left', [])):
                x = left_x + (Config.CONTROL_SPACING * i)
                self._render_control_image(image_name, x, bottom_y)
            
            # Render right controls from right to left
            for i, image_name in enumerate(reversed(controls.get('right', []))):
                x = right_x - (Config.CONTROL_SPACING * i) - Config.CONTROL_SIZE
                self._render_control_image(image_name, x, bottom_y)
                
        except Exception as e:
            logger.error(f"Error rendering control guides: {e}", exc_info=True)
            
    def _render_active_download_count(self, count):
        """Render the active download count"""
        download_text = f"Active Downloads: {count}"
        text_surface = sdl2.sdlttf.TTF_RenderText_Blended(
            self.font,
            download_text.encode('utf-8'),
            sdl2.SDL_Color(*Theme.TEXT_HIGHLIGHT)
        )
        text_width = text_surface.contents.w
        sdl2.SDL_FreeSurface(text_surface)
        
        x_pos = Config.SCREEN_WIDTH - text_width - int(20 * Config.SCALE_FACTOR)
        self.render_text(
            download_text,
            x_pos,
            int(20 * Config.SCALE_FACTOR),
            color=Theme.TEXT_HIGHLIGHT,
            center=False
        )