import sdl2
import sdl2.sdlttf
import time
import math
from ui.base_view import BaseView
from utils.config import Config
from utils.logger import logger
from utils.theme import Theme

class LoadingScreen(BaseView):
    """Manages the loading screen rendering"""

    def __init__(self, renderer, width, height, shared_font=None):
        """
        Initialize the loading screen
        
        :param renderer: SDL renderer
        :param width: Screen width
        :param height: Screen height
        :param shared_font: Optional shared font instance
        """
        super().__init__(renderer, shared_font)
        self.width = width
        self.height = height
        if not self.font:
            self._load_font()
        self.last_time = time.time()
        self.animation_angle = 0

    def _load_font(self):
        """Load the font with the correct scaled size"""
        font_path = Config.get_font_path()
        if font_path:
            try:
                # Use a larger font size for the loading screen
                font_size = int(36 * Config.SCALE_FACTOR)
                self.font = sdl2.sdlttf.TTF_OpenFont(font_path.encode('utf-8'), font_size)
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
            
            # Calculate scaled dimensions and positions
            center_x = self.width // 2
            center_y = self.height // 2
            
            # Scale the vertical spacing
            vertical_spacing = int(50 * Config.SCALE_FACTOR)
            
            # Draw animated loading circle
            self._render_loading_circle(center_x, center_y - vertical_spacing)
            
            # Draw progress bar with scaled dimensions
            bar_width = int(400 * Config.SCALE_FACTOR)
            bar_height = int(6 * Config.SCALE_FACTOR)
            self._render_progress_bar(
                center_x - bar_width // 2,
                center_y + vertical_spacing,
                bar_width,
                bar_height,
                progress
            )
            
            # Draw loading message
            self._render_text(status_text, center_x, center_y + vertical_spacing * 2)
            
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
        # Scale the radius and line thickness
        radius = int(30 * Config.SCALE_FACTOR)
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
            
            # Draw segment with scaled line thickness
            sdl2.SDL_SetRenderDrawColor(self.renderer, *Theme.LOADING_SPINNER, opacity)
            self._draw_thick_line(int(x1), int(y1), int(x2), int(y2), int(2 * Config.SCALE_FACTOR))
    
    def _draw_thick_line(self, x1, y1, x2, y2, thickness):
        """Draw a line with specified thickness"""
        angle = math.atan2(y2 - y1, x2 - x1)
        dx = thickness * math.sin(angle) / 2
        dy = thickness * math.cos(angle) / 2
        
        points = [
            (x1 + dx, y1 - dy),
            (x1 - dx, y1 + dy),
            (x2 - dx, y2 + dy),
            (x2 + dx, y2 - dy)
        ]
        
        # Convert points to SDL_Point array
        sdl_points = (sdl2.SDL_Point * 5)(
            sdl2.SDL_Point(int(points[0][0]), int(points[0][1])),
            sdl2.SDL_Point(int(points[1][0]), int(points[1][1])),
            sdl2.SDL_Point(int(points[2][0]), int(points[2][1])),
            sdl2.SDL_Point(int(points[3][0]), int(points[3][1])),
            sdl2.SDL_Point(int(points[0][0]), int(points[0][1]))  # Close the polygon
        )
        
        sdl2.SDL_RenderDrawLines(self.renderer, sdl_points, 5)
    
    def _render_progress_bar(self, x, y, width, height, progress):
        """Render a modern progress bar"""
        # Scale the padding and glow size
        padding = int(2 * Config.SCALE_FACTOR)
        glow_size = int(2 * Config.SCALE_FACTOR)
        
        # Draw background
        bg_rect = sdl2.SDL_Rect(x - padding, y - padding, width + padding * 2, height + padding * 2)
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
            glow_rect = sdl2.SDL_Rect(x, y - glow_size, progress_width, height + glow_size * 2)
            sdl2.SDL_RenderFillRect(self.renderer, glow_rect)
    
    def _render_text(self, text, x, y):
        """Render text with a subtle glow effect"""
        texture, width, height = self.create_text_texture(text, Theme.TEXT_PRIMARY)
        if texture:
            # Draw text
            dst_rect = sdl2.SDL_Rect(
                x - width // 2,
                y - height // 2,
                width,
                height
            )
            sdl2.SDL_RenderCopy(self.renderer, texture, None, dst_rect)
            sdl2.SDL_DestroyTexture(texture)