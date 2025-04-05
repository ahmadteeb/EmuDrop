"""
Base view class that provides common functionality for all views.
"""
from typing import Optional, Dict, List
import sdl2
import math
import time
import os
import ctypes
from utils.theme import Theme
from utils.config import Config
from utils.logger import logger
from typing import Tuple

class BaseView:
    """Base class for all views in the application"""
    
    def __init__(self, renderer, font, texture_manager):
        """Initialize the base view with common components"""
        self.renderer = renderer
        self.font = font
        self.texture_manager = texture_manager
        
    def render_title(self, title: str) -> None:
        """Render a title at the top of the view
        
        Args:
            title: The title text to render
        """
        self.render_text(
            title,
            Config.SCREEN_WIDTH // 2,
            40,  # Position from top
            color=Theme.TEXT_PRIMARY,
            center=True
        )
        
    def render_background(self, simplified=False) -> None:
        """Render a modern gradient background with subtle animation
        
        Args:
            simplified: Use simplified rendering for low-power devices
        """
        try:
            if simplified:
                # Simple solid background for low-power devices
                sdl2.SDL_SetRenderDrawColor(self.renderer, *Theme.BG_DARK, 255)
                bg_rect = sdl2.SDL_Rect(0, 0, Config.SCREEN_WIDTH, Config.SCREEN_HEIGHT)
                sdl2.SDL_RenderFillRect(self.renderer, bg_rect)
                return
                
            current_time = time.time()
            animation = (math.sin(current_time) + 1) * 0.5  # 0 to 1 animation
            
            # Create gradient from dark to darker
            for y in range(Config.SCREEN_HEIGHT):
                # Calculate base gradient colors
                progress = y / Config.SCREEN_HEIGHT
                base_r = int(Theme.BG_DARKER[0] + (Theme.BG_DARK[0] - Theme.BG_DARKER[0]) * progress)
                base_g = int(Theme.BG_DARKER[1] + (Theme.BG_DARK[1] - Theme.BG_DARKER[1]) * progress)
                base_b = int(Theme.BG_DARKER[2] + (Theme.BG_DARK[2] - Theme.BG_DARKER[2]) * progress)
                
                # Add subtle animation
                r = int(base_r + animation * 10)
                g = int(base_g + animation * 10)
                b = int(base_b + animation * 10)
                
                # Draw gradient line
                sdl2.SDL_SetRenderDrawColor(self.renderer, r, g, b, 255)
                line = sdl2.SDL_Rect(0, y, Config.SCREEN_WIDTH, 1)
                sdl2.SDL_RenderFillRect(self.renderer, line)

        except Exception as e:
            logger.error(f"Error rendering background: {e}", exc_info=True)
            
    def render_card(self, x: int, y: int, width: int, height: int, 
                   selected: bool = False, hovered: bool = False) -> None:
        """Render a modern card with shadow and hover effects"""
        try:
            # Draw shadow
            shadow_offset = 4
            shadow_rect = sdl2.SDL_Rect(x + shadow_offset, y + shadow_offset, width, height)
            sdl2.SDL_SetRenderDrawBlendMode(self.renderer, sdl2.SDL_BLENDMODE_BLEND)
            sdl2.SDL_SetRenderDrawColor(self.renderer, *Theme.SHADOW_COLOR)
            sdl2.SDL_RenderFillRect(self.renderer, shadow_rect)
            
            # Draw card background
            bg_color = Theme.CARD_SELECTED if selected else Theme.CARD_BG
            if hovered:
                bg_color = Theme.get_hover_color(bg_color)
            
            card_rect = sdl2.SDL_Rect(x, y, width, height)
            sdl2.SDL_SetRenderDrawColor(self.renderer, *bg_color, 255)
            sdl2.SDL_RenderFillRect(self.renderer, card_rect)
            
            # Draw border
            sdl2.SDL_SetRenderDrawColor(self.renderer, *Theme.CARD_BORDER, 255)
            sdl2.SDL_RenderDrawRect(self.renderer, card_rect)
            
            # Draw glow effect for selected cards
            if selected:
                sdl2.SDL_SetRenderDrawBlendMode(self.renderer, sdl2.SDL_BLENDMODE_BLEND)
                sdl2.SDL_SetRenderDrawColor(self.renderer, *Theme.GLOW_COLOR)
                glow_rect = sdl2.SDL_Rect(x - 2, y - 2, width + 4, height + 4)
                sdl2.SDL_RenderFillRect(self.renderer, glow_rect)

        except Exception as e:
            logger.error(f"Error rendering card: {e}", exc_info=True)
            
    def render_text(self, text: str, x: int, y: int, 
                   color: tuple = Theme.TEXT_PRIMARY, 
                   center: bool = False) -> None:
        """Render text at the specified position"""
        try:
            # Create SDL_Color instance from the color tuple
            text_color = sdl2.SDL_Color(*color)
            
            # Create text surface with the SDL_Color
            surface = sdl2.sdlttf.TTF_RenderText_Solid(self.font, text.encode(), text_color)
            if surface:
                texture = sdl2.SDL_CreateTextureFromSurface(self.renderer, surface)
                if texture:
                    width = surface.contents.w
                    height = surface.contents.h
                    if center:
                        x -= width // 2
                    rect = sdl2.SDL_Rect(x, y, width, height)
                    sdl2.SDL_RenderCopy(self.renderer, texture, None, rect)
                    sdl2.SDL_DestroyTexture(texture)
                sdl2.SDL_FreeSurface(surface)
        except Exception as e:
            logger.error(f"Error rendering text: {e}", exc_info=True)
            
    def _render_page_navigation(self, current_page: int, total_pages: int) -> None:
        """Render page navigation controls"""
        if total_pages > 1:
            page_text = f"Page {current_page + 1} of {total_pages}"
            self.render_text(
                page_text,
                Config.SCREEN_WIDTH // 2,
                Config.SCREEN_HEIGHT - 40,
                color=Theme.TEXT_SECONDARY,
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

    def _render_control_image(self, texture, x: int, y: int) -> None:
        """Render a single control image at the specified position"""
        if not texture:
            return
            
        width, height = self._get_texture_dimensions(texture)
        render_width, render_height, y_offset = self._calculate_render_dimensions(width, height)
        
        rect = sdl2.SDL_Rect(
            x,
            y + y_offset,
            render_width,
            render_height
        )
        sdl2.SDL_RenderCopy(self.renderer, texture, None, rect)

    def render_control_guides(self, controls: Dict[str, List[str]]) -> None:
        """Render control guides at the bottom of the screen
        
        Args:
            controls: Dictionary with 'left' and 'right' keys containing lists of control image names
        """
        try:
            # Calculate base positions
            bottom_y = Config.SCREEN_HEIGHT - Config.CONTROL_BOTTOM_MARGIN
            left_x = Config.CONTROL_MARGIN
            right_x = Config.SCREEN_WIDTH - Config.CONTROL_MARGIN - Config.CONTROL_SIZE * 2
            
            # Render left controls
            for i, image_name in enumerate(controls.get('left', [])):
                texture = self.texture_manager.get_texture(
                    os.path.join(Config.IMAGES_CONTROLS_DIR, image_name)
                )
                x = left_x + (Config.CONTROL_SPACING * i)
                self._render_control_image(texture, x, bottom_y)
            
            # Render right controls
            for i, image_name in enumerate(controls.get('right', [])):
                texture = self.texture_manager.get_texture(
                    os.path.join(Config.IMAGES_CONTROLS_DIR, image_name)
                )
                x = right_x + (Config.CONTROL_SPACING * i)
                self._render_control_image(texture, x, bottom_y)
        except Exception as e:
            logger.error(f"Error rendering control guides: {e}", exc_info=True)