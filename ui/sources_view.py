"""
View class for rendering game sources.
"""
import sdl2
from typing import List, Dict
from utils.theme import Theme
from utils.config import Config
from utils.logger import logger
from .base_view import BaseView

class SourcesView(BaseView):
    """View class for rendering game sources"""
    
    def render(self, current_page: int, selected_source: int, sources: List[Dict]) -> None:
        """Render sources in a modern grid layout
        
        Args:
            current_page: Current page number
            selected_source: Index of currently selected source
            sources: List of source dictionaries containing sourceName
        """
        try:
            # Render the title at the top
            self.render_title("Sources")
            
            # Render control guides
            controls = {
                'left': [
                    "grid-controls.png",
                    "select.png",
                    "back.png"
                ],
                'right': [
                    "previous-page.png",
                    "next-page.png"
                ]
            }
            self.render_control_guides(controls)
            
            # Add "All Sources" option at the beginning
            total_sources = len(sources)
                
            # Calculate pagination
            total_pages = (total_sources + Config.CARDS_PER_PAGE - 1) // Config.CARDS_PER_PAGE
            self._render_page_navigation(current_page, total_pages)
            
            if not sources:
                self.render_text(
                        "No sources available",
                        Config.SCREEN_WIDTH // 2,
                        Config.SCREEN_HEIGHT // 2,
                        color=Theme.TEXT_SECONDARY,
                        center=True
                    )
            
            start_idx = current_page * Config.CARDS_PER_PAGE
            end_idx = min(start_idx + Config.CARDS_PER_PAGE, total_sources)
            page_sources = sources[start_idx:end_idx]
            
            # Calculate grid layout
            start_x = (Config.SCREEN_WIDTH - (Config.CARD_WIDTH * Config.CARDS_PER_ROW + 
                     Config.GRID_SPACING * (Config.CARDS_PER_ROW - 1))) // 2
            start_y = int(100 * Config.SCALE_FACTOR)  # Scale the top margin like in platformsView
            
            # Render source cards
            for i, source in enumerate(page_sources):
                row = i // Config.CARDS_PER_ROW
                col = i % Config.CARDS_PER_ROW
                
                x = start_x + col * (Config.CARD_WIDTH + Config.GRID_SPACING)
                y = start_y + row * (Config.CARD_HEIGHT + Config.GRID_SPACING)
                
                is_selected = (start_idx + i) == selected_source
                
                # Draw card background with modern styling
                card_rect = sdl2.SDL_Rect(x, y, Config.CARD_WIDTH, Config.CARD_HEIGHT)
                
                # Draw shadow for selected card
                if is_selected:
                    shadow_offset = 4
                    shadow_rect = sdl2.SDL_Rect(
                        x + shadow_offset,
                        y + shadow_offset,
                        Config.CARD_WIDTH,
                        Config.CARD_HEIGHT
                    )
                    sdl2.SDL_SetRenderDrawBlendMode(self.renderer, sdl2.SDL_BLENDMODE_BLEND)
                    sdl2.SDL_SetRenderDrawColor(self.renderer, 0, 0, 0, 100)
                    sdl2.SDL_RenderFillRect(self.renderer, shadow_rect)
                
                # Draw card background
                if is_selected:
                    sdl2.SDL_SetRenderDrawColor(self.renderer, 60, 60, 60, 255)
                else:
                    sdl2.SDL_SetRenderDrawColor(self.renderer, 40, 40, 40, 255)
                sdl2.SDL_RenderFillRect(self.renderer, card_rect)
                
                # Draw subtle border
                sdl2.SDL_SetRenderDrawColor(self.renderer, 80, 80, 80, 100)
                sdl2.SDL_RenderDrawRect(self.renderer, card_rect)
                
                # Render source name
                self.render_text(
                    source['source_name'],
                    x + Config.CARD_WIDTH // 2,
                    y + Config.CARD_HEIGHT // 2,
                    color=Theme.TEXT_PRIMARY if is_selected else Theme.TEXT_SECONDARY,
                    center=True
                )
            
        except Exception as e:
            logger.error(f"Error rendering sources view: {e}", exc_info=True)