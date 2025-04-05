"""
View class for rendering game categories.
"""
import os
from typing import List, Dict
import sdl2
from utils.theme import Theme
from utils.config import Config
from utils.logger import logger
from data.categories import CategoryManager
from .base_view import BaseView

class CategoriesView(BaseView):
    """View class for rendering game categories"""
    
    def render(self, current_page: int, selected_category: int) -> None:
        """Render categories in a modern grid layout with console images"""
        try:
            # Render the title at the top
            self.render_title("Categories")

            # Get categories for current page
            categories = CategoryManager.get_categories()
            total_categories = len(categories)
            if total_categories == 0:
                self.render_text(
                    "No categories available",
                    Config.SCREEN_WIDTH // 2,
                    Config.SCREEN_HEIGHT // 2,
                    color=Theme.TEXT_SECONDARY,
                    center=True
                )
                return
                
            # Calculate pagination
            total_pages = (total_categories + Config.CARDS_PER_PAGE - 1) // Config.CARDS_PER_PAGE
            start_idx = current_page * Config.CARDS_PER_PAGE
            end_idx = min(start_idx + Config.CARDS_PER_PAGE, total_categories)
            page_categories = categories[start_idx:end_idx]
            
            # Calculate grid layout
            start_x = (Config.SCREEN_WIDTH - (Config.CARD_WIDTH * Config.CARDS_PER_ROW + 
                     Config.GRID_SPACING * (Config.CARDS_PER_ROW - 1))) // 2
            start_y = 100
            
            # Render category cards
            for i, category in enumerate(page_categories):
                # Calculate grid position
                row = i // Config.CARDS_PER_ROW
                col = i % Config.CARDS_PER_ROW
                
                x = int(start_x + (Config.CARD_WIDTH + Config.GRID_SPACING) * col)
                y = int(start_y + (Config.CARD_HEIGHT + Config.GRID_SPACING) * row)
                
                is_selected = (i + current_page * Config.CARDS_PER_PAGE) == selected_category
                self.render_card(x, y, Config.CARD_WIDTH, Config.CARD_HEIGHT, selected=is_selected)
                
                # Load and render console image
                image_path = os.path.join(Config.IMAGES_CONSOLES_DIR, f"{category['id']}.png")
                self._render_console_image(image_path, x, y, Config.CARD_WIDTH, Config.CARD_IMAGE_HEIGHT)
                
                # Render category name
                self.render_text(
                    category['name'],
                    x + Config.CARD_WIDTH // 2,
                    y + Config.CARD_HEIGHT - 30,
                    color=Theme.TEXT_PRIMARY if is_selected else Theme.TEXT_SECONDARY,
                    center=True
                )
            
            # Render page navigation
            self._render_page_navigation(current_page, total_pages)
            
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
            
        except Exception as e:
            logger.error(f"Error rendering categories: {e}", exc_info=True)
            
    def _render_console_image(self, image_path: str, x: int, y: int, width: int, height: int) -> None:
        """Render a console image within a card"""
        try:
            texture = self.texture_manager.get_texture(image_path)
            if texture:
                # Calculate image dimensions to maintain aspect ratio
                img_width = width - 20  # Padding
                img_height = height - 20
                
                # Center the image
                img_x = x + (width - img_width) // 2
                img_y = y + (height - img_height) // 2
                
                rect = sdl2.SDL_Rect(img_x, img_y, img_width, img_height)
                sdl2.SDL_RenderCopy(self.renderer, texture, None, rect)
        except Exception as e:
            logger.error(f"Error rendering console image: {e}", exc_info=True) 