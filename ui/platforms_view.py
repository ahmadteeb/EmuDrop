"""
View class for rendering game platforms.
"""
import os
from typing import List, Dict
import sdl2
from utils.theme import Theme
from utils.config import Config
from utils.logger import logger
from .base_view import BaseView

class platformsView(BaseView):
    """View class for rendering game platforms"""
    
    def __init__(self, renderer, font=None):
        """Initialize the platforms view"""
        super().__init__(renderer, font)
    
    def render(self, current_page: int, selected_platform: int, platforms: List[Dict], active_downloads_count: Dict = None) -> None:
        """Render platforms in a modern grid layout with console images"""
        try:
            # Render the title at the top
            self.render_title("Platforms")

            # Show active downloads count in the corner
            if active_downloads_count:
                self._render_active_download_count(active_downloads_count)

            # Render control guides
            controls = {
                'left': [
                    "grid-controls.png",
                    "select.png",
                    "back.png",
                    "downloads.png"
                ],
                'right': [
                    "previous-page.png",
                    "next-page.png"
                ]
            }
            self.render_control_guides(controls)
            
            # Get platforms for current page
            total_platforms = len(platforms)
            if total_platforms == 0:
                self.render_text(
                    "No platforms available",
                    Config.SCREEN_WIDTH // 2,
                    Config.SCREEN_HEIGHT // 2,
                    color=Theme.TEXT_SECONDARY,
                    center=True
                )
                return
                
            # Calculate pagination
            total_pages = (total_platforms + Config.CARDS_PER_PAGE - 1) // Config.CARDS_PER_PAGE
            start_idx = current_page * Config.CARDS_PER_PAGE
            end_idx = min(start_idx + Config.CARDS_PER_PAGE, total_platforms)
            page_platforms = platforms[start_idx:end_idx]
            
            # Calculate grid layout with scaled dimensions
            grid_width = (Config.CARD_WIDTH * Config.CARDS_PER_ROW + 
                        Config.GRID_SPACING * (Config.CARDS_PER_ROW - 1))
            start_x = (Config.SCREEN_WIDTH - grid_width) // 2
            start_y = int(100 * Config.SCALE_FACTOR)  # Scale the top margin
            
            # Render platform cards
            for i, platform in enumerate(page_platforms):
                # Calculate grid position
                row = i // Config.CARDS_PER_ROW
                col = i % Config.CARDS_PER_ROW
                
                x = int(start_x + (Config.CARD_WIDTH + Config.GRID_SPACING) * col)
                y = int(start_y + (Config.CARD_HEIGHT + Config.GRID_SPACING) * row)
                
                is_selected = (i + current_page * Config.CARDS_PER_PAGE) == selected_platform
                self.render_card(x, y, Config.CARD_WIDTH, Config.CARD_HEIGHT, selected=is_selected)
                
                # Load and render console image
                image_path = os.path.join(Config.IMAGES_CONSOLES_DIR, platform['image'])
                self._render_console_image(image_path, x, y, Config.CARD_WIDTH, Config.CARD_IMAGE_HEIGHT)
                
                # Render platform name with scaled vertical position
                text_y_offset = int(30 * Config.SCALE_FACTOR)
                self.render_text(
                    platform['name'],
                    x + Config.CARD_WIDTH // 2,
                    y + Config.CARD_HEIGHT - text_y_offset,
                    color=Theme.TEXT_PRIMARY if is_selected else Theme.TEXT_SECONDARY,
                    center=True
                )
            
            # Render page navigation
            self._render_page_navigation(current_page, total_pages)
            
        except Exception as e:
            logger.error(f"Error rendering platforms: {e}", exc_info=True)            
    def _render_console_image(self, image_path: str, x: int, y: int, width: int, height: int) -> None:
        """Render a console image within a card"""
        try:
            texture = self.get_texture(image_path)
            if texture:
                # Calculate scaled padding
                padding = int(20 * Config.SCALE_FACTOR)
                
                # Calculate image dimensions to maintain aspect ratio
                img_width = width - padding * 2
                img_height = height - padding * 2
                
                # Center the image
                img_x = x + (width - img_width) // 2
                img_y = y + (height - img_height) // 2
                
                rect = sdl2.SDL_Rect(
                    int(img_x),
                    int(img_y),
                    int(img_width),
                    int(img_height)
                )
                sdl2.SDL_RenderCopy(self.renderer, texture, None, rect)
        except Exception as e:
            logger.error(f"Error rendering console image: {e}", exc_info=True)
