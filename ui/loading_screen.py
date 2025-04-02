import sdl2
import sdl2.sdlttf
import ctypes
import time
import math
from utils.config import Config
from utils.logger import logger
from utils.theme import Theme

class LoadingScreen:
    """Manages the loading screen rendering"""

    def __init__(self, renderer, width, height):
        """
        Initialize the loading screen
        
        :param renderer: SDL renderer
        :param width: Screen width
        :param height: Screen height
        """
        self.renderer = renderer
        self.width = width
        self.height = height
        self.font = None
        self._load_font()
        self.last_time = time.time()
        self.animation_angle = 0

    def _load_font(self):
        font_path = Config.get_font_path()
        
        if font_path:
            try:
                self.font = sdl2.sdlttf.TTF_OpenFont(font_path.encode('utf-8'), 36)
                if self.font:
                    logger.info(f"Loading screen font loaded: {font_path}")
                    return
            except Exception as e:
                logger.warning(f"Failed to load font {font_path}: {e}")
        
        logger.error("No font could be loaded for loading screen")

    def render(self, progress: float, status_text: str = "Loading..."):
        """Render a modern loading screen with animations"""
        try:
            # Clear screen with dark background
            sdl2.SDL_SetRenderDrawColor(self.renderer, *Theme.LOADING_BG, 255)
            sdl2.SDL_RenderClear(self.renderer)
            
            # Calculate center position
            center_x = self.width // 2
            center_y = self.height // 2
            
            # Draw animated loading circle
            self._render_loading_circle(center_x, center_y - 50)
            
            # Draw progress bar
            bar_width = 400
            bar_height = 6
            self._render_progress_bar(
                center_x - bar_width // 2,
                center_y + 50,
                bar_width,
                bar_height,
                progress
            )
            
            # Draw loading message
            self._render_text(status_text, center_x, center_y + 100)
            
            # Update animation
            current_time = time.time()
            delta_time = current_time - self.last_time
            self.animation_angle += 360 * delta_time  # Rotate 360 degrees per second
            self.last_time = current_time
            
            # Present the rendered frame
            sdl2.SDL_RenderPresent(self.renderer)

        except Exception as e:
            logger.error(f"Loading screen rendering error: {e}")

    def _render_loading_circle(self, x, y):
        """Render animated loading circle"""
        radius = 30
        segments = 12
        segment_angle = 360 / segments
        
        for i in range(segments):
            angle = math.radians(i * segment_angle + self.animation_angle)
            next_angle = math.radians((i + 1) * segment_angle + self.animation_angle)
            
            # Calculate segment opacity based on position
            opacity = int(255 * (i / segments))
            
            # Calculate segment points
            x1 = x + radius * math.cos(angle)
            y1 = y + radius * math.sin(angle)
            x2 = x + radius * math.cos(next_angle)
            y2 = y + radius * math.sin(next_angle)
            
            # Draw segment
            sdl2.SDL_SetRenderDrawColor(self.renderer, *Theme.LOADING_SPINNER, opacity)
            sdl2.SDL_RenderDrawLine(self.renderer, int(x1), int(y1), int(x2), int(y2))
    
    def _render_progress_bar(self, x, y, width, height, progress):
        """Render a modern progress bar"""
        # Draw background
        bg_rect = sdl2.SDL_Rect(x - 2, y - 2, width + 4, height + 4)
        sdl2.SDL_SetRenderDrawColor(self.renderer, *Theme.LOADING_PROGRESS_BG, 255)
        sdl2.SDL_RenderFillRect(self.renderer, bg_rect)
        
        # Draw progress
        progress_width = int(width * progress)
        if progress_width > 0:
            progress_rect = sdl2.SDL_Rect(x, y, progress_width, height)
            sdl2.SDL_SetRenderDrawColor(self.renderer, *Theme.LOADING_PROGRESS, 255)
            sdl2.SDL_RenderFillRect(self.renderer, progress_rect)
            
            # Draw glow effect
            glow_color = (*Theme.LOADING_PROGRESS, 100)  # Add alpha value
            sdl2.SDL_SetRenderDrawBlendMode(self.renderer, sdl2.SDL_BLENDMODE_BLEND)
            sdl2.SDL_SetRenderDrawColor(self.renderer, *glow_color)
            glow_rect = sdl2.SDL_Rect(x, y - 2, progress_width, height + 4)
            sdl2.SDL_RenderFillRect(self.renderer, glow_rect)
    
    def _render_text(self, text, x, y):
        """Render text with a subtle glow effect"""
        # Create text surface
        text_surface = sdl2.sdlttf.TTF_RenderText_Blended(
            self.font,
            text.encode('utf-8'),
            sdl2.SDL_Color(*Theme.TEXT_PRIMARY, 255)
        )
        
        # Create texture from surface
        text_texture = sdl2.SDL_CreateTextureFromSurface(self.renderer, text_surface)
        
        # Get text dimensions
        text_width = text_surface.contents.w
        text_height = text_surface.contents.h
        
        # Draw text
        dst_rect = sdl2.SDL_Rect(
            x - text_width // 2,
            y - text_height // 2,
            text_width,
            text_height
        )
        sdl2.SDL_RenderCopy(self.renderer, text_texture, None, dst_rect)
        
        # Cleanup
        sdl2.SDL_FreeSurface(text_surface)
        sdl2.SDL_DestroyTexture(text_texture)

    def cleanup(self):
        """Clean up loading screen resources"""
        if self.font:
            sdl2.sdlttf.TTF_CloseFont(self.font)