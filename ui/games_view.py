"""
Games view class that handles rendering the games list for a category.
"""
from typing import List, Dict, Optional
import os
import sdl2
import time
from utils.theme import Theme
from utils.config import Config
from utils.logger import logger
from data.games import GameManager
from .base_view import BaseView

class GamesView(BaseView):
    """View class for displaying games in a category"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.marquee_states = {}  # Store marquee state for each game
        self.marquee_speed = 50  # Pixels per second
        self.marquee_pause = 2.0  # Seconds to pause at each end
        self.marquee_spacing = 50  # Pixels between repetitions
        
    def _get_marquee_state(self, game_id: str, text_width: int, container_width: int, is_selected: bool) -> Dict:
        """Get or initialize marquee state for a game"""
        if game_id not in self.marquee_states:
            self.marquee_states[game_id] = {
                'offset': 0,
                'direction': 1,
                'pause_time': 0,
                'last_update': time.time(),
                'is_selected': False
            }
        
        state = self.marquee_states[game_id]
        current_time = time.time()
        delta_time = current_time - state['last_update']
        state['last_update'] = current_time
        
        # Reset state if selection changed
        if state['is_selected'] != is_selected:
            state['offset'] = 0
            state['direction'] = 1
            state['pause_time'] = 0
            state['is_selected'] = is_selected
        
        # If not selected or text fits, don't animate
        if not is_selected or text_width <= container_width:
            state['offset'] = 0
            return state
            
        # Handle pausing at ends
        if state['pause_time'] > 0:
            state['pause_time'] -= delta_time
            return state
            
        # Calculate total animation distance
        total_distance = text_width + self.marquee_spacing
        
        # Update position
        state['offset'] += self.marquee_speed * delta_time * state['direction']
        
        # Handle direction changes
        if state['offset'] >= total_distance:
            state['direction'] = -1
            state['pause_time'] = self.marquee_pause
        elif state['offset'] <= 0:
            state['direction'] = 1
            state['pause_time'] = self.marquee_pause
            
        return state
    
    def render(self, category_id: str, current_page: int, selected_game: int, 
               show_image: bool = False, games_override: Optional[List[Dict]] = None) -> None:
        """Render the games view
        
        Args:
            category_id: ID of the current category
            current_page: Current page number
            selected_game: Index of the currently selected game
            show_image: Whether to show the game image
            games_override: Optional list of games to display instead of category games
        """
        try:
            # Get games list (either from override or category)
            games = games_override if games_override is not None else GameManager.get_games_by_category(category_id)
            
            if not games:
                # Show "No games found" message
                self.render_text(
                    "No games found",
                    Config.SCREEN_WIDTH // 2,
                    Config.SCREEN_HEIGHT // 2 - 30,
                    color=(200, 200, 200),
                    center=True
                )
                return
                
            # Calculate total pages
            total_pages = (len(games) + Config.GAMES_PER_PAGE - 1) // Config.GAMES_PER_PAGE
            current_page = max(0, min(current_page, total_pages - 1))
            
            # Get games for current page
            start_idx = current_page * Config.GAMES_PER_PAGE
            end_idx = min(start_idx + Config.GAMES_PER_PAGE, len(games))
            page_games = games[start_idx:end_idx]
            
            # Calculate starting positions
            list_start_x = int((Config.SCREEN_WIDTH - (Config.GAME_LIST_WIDTH + Config.GAME_LIST_IMAGE_SIZE + Config.GAME_LIST_SPACING_BETWEEN)) // 2)
            image_start_x = list_start_x + Config.GAME_LIST_WIDTH + Config.GAME_LIST_SPACING_BETWEEN
            
            # Calculate list area height based on actual number of games
            max_list_height = (Config.GAME_LIST_ITEM_HEIGHT + Config.GAME_LIST_SPACING) * Config.GAMES_PER_PAGE - Config.GAME_LIST_SPACING
            actual_list_height = (Config.GAME_LIST_ITEM_HEIGHT + Config.GAME_LIST_SPACING) * len(page_games) - Config.GAME_LIST_SPACING
            
            # Calculate vertical positions to center both the list and image
            list_start_y = Config.GAME_LIST_START_Y + (max_list_height - actual_list_height) // 2
            image_start_y = Config.GAME_LIST_START_Y + (max_list_height - Config.GAME_LIST_IMAGE_SIZE) // 2

            # Get selected game data
            if games and 0 <= selected_game < len(games):
                selected_game_data = games[selected_game]
            else:
                selected_game_data = None

            # Render featured game section (large image and details)
            if selected_game_data:
                # Render featured game card background
                featured_rect = sdl2.SDL_Rect(
                    image_start_x - Config.GAME_LIST_CARD_PADDING,
                    image_start_y - Config.GAME_LIST_CARD_PADDING,
                    Config.GAME_LIST_IMAGE_SIZE + Config.GAME_LIST_CARD_PADDING * 2,
                    Config.GAME_LIST_IMAGE_SIZE + Config.GAME_LIST_CARD_PADDING * 2
                )
                
                # Draw card shadow
                shadow_offset = 4
                shadow_rect = sdl2.SDL_Rect(
                    featured_rect.x + shadow_offset,
                    featured_rect.y + shadow_offset,
                    featured_rect.w,
                    featured_rect.h
                )
                sdl2.SDL_SetRenderDrawBlendMode(self.renderer, sdl2.SDL_BLENDMODE_BLEND)
                sdl2.SDL_SetRenderDrawColor(self.renderer, 0, 0, 0, 100)
                sdl2.SDL_RenderFillRect(self.renderer, shadow_rect)
                
                # Draw card background
                sdl2.SDL_SetRenderDrawColor(self.renderer, 45, 45, 45, 255)
                sdl2.SDL_RenderFillRect(self.renderer, featured_rect)
                
                # Draw card border
                sdl2.SDL_SetRenderDrawColor(self.renderer, 80, 80, 80, 255)
                sdl2.SDL_RenderDrawRect(self.renderer, featured_rect)
                
                # Only render the game image if the hold timer has elapsed
                if show_image and 'image_url' in selected_game_data and selected_game_data['image_url']:
                    texture = self.texture_manager.get_texture(selected_game_data['image_url'])
                    if texture:
                        image_rect = sdl2.SDL_Rect(
                            image_start_x,
                            image_start_y,
                            Config.GAME_LIST_IMAGE_SIZE,
                            Config.GAME_LIST_IMAGE_SIZE
                        )
                        sdl2.SDL_RenderCopy(self.renderer, texture, None, image_rect)
                    else:
                        # Render placeholder if texture loading failed
                        self._render_game_placeholder(image_start_x, image_start_y)
                else:
                    # Show loading indicator or placeholder while waiting
                    self._render_game_placeholder(image_start_x, image_start_y)
                    
                    # Show "Hold to view image" text if not loaded yet
                    if not show_image:
                        # Display hold message underneath the image
                        message_y = image_start_y + Config.GAME_LIST_IMAGE_SIZE + 20
                        self.render_text(
                            "Hold to view image...",
                            image_start_x + Config.GAME_LIST_IMAGE_SIZE // 2,
                            message_y,
                            color=(150, 150, 150),
                            center=True
                        )
            
            # Render game list with modern styling
            for i, game in enumerate(page_games):
                y = list_start_y + (Config.GAME_LIST_ITEM_HEIGHT + Config.GAME_LIST_SPACING) * i
                is_selected = i + current_page * Config.GAMES_PER_PAGE == selected_game
                
                # Calculate item position with padding
                item_x = list_start_x
                item_y = y
                
                # Draw item shadow for selected item
                if is_selected:
                    shadow_offset = 4
                    shadow_rect = sdl2.SDL_Rect(
                        item_x + shadow_offset,
                        item_y + shadow_offset,
                        Config.GAME_LIST_WIDTH,
                        Config.GAME_LIST_ITEM_HEIGHT
                    )
                    sdl2.SDL_SetRenderDrawBlendMode(self.renderer, sdl2.SDL_BLENDMODE_BLEND)
                    sdl2.SDL_SetRenderDrawColor(self.renderer, 0, 0, 0, 100)
                    sdl2.SDL_RenderFillRect(self.renderer, shadow_rect)
                
                # Draw item background with modern gradient
                item_rect = sdl2.SDL_Rect(item_x, item_y, Config.GAME_LIST_WIDTH, Config.GAME_LIST_ITEM_HEIGHT)
                if is_selected:
                    sdl2.SDL_SetRenderDrawColor(self.renderer, 60, 60, 60, 255)
                else:
                    sdl2.SDL_SetRenderDrawColor(self.renderer, 40, 40, 40, 255)
                sdl2.SDL_RenderFillRect(self.renderer, item_rect)
                
                # Draw subtle border
                sdl2.SDL_SetRenderDrawColor(self.renderer, 80, 80, 80, 100)
                sdl2.SDL_RenderDrawRect(self.renderer, item_rect)
                
                # Render game name with padding
                name_x = item_x + 20
                name_y = item_y + (Config.GAME_LIST_ITEM_HEIGHT - 30) // 2
                
                # Get container width
                container_width = Config.GAME_LIST_WIDTH - 40  # Account for padding
                
                # Get full text width
                surface = sdl2.sdlttf.TTF_RenderText_Solid(self.font, game['name'].encode(), sdl2.SDL_Color(*Theme.TEXT_PRIMARY))
                if surface:
                    text_width = surface.contents.w
                    sdl2.SDL_FreeSurface(surface)
                    
                    # Get marquee state
                    game_id = f"{category_id}_{i}"
                    marquee_state = self._get_marquee_state(game_id, text_width, container_width, is_selected)
                    
                    # Create clipping rectangle
                    clip_rect = sdl2.SDL_Rect(
                        item_x,
                        item_y,
                        Config.GAME_LIST_WIDTH,
                        Config.GAME_LIST_ITEM_HEIGHT
                    )
                    sdl2.SDL_RenderSetClipRect(self.renderer, clip_rect)
                    
                    # Render text with marquee offset
                    if text_width > container_width and is_selected:
                        # Convert float offset to integer for SDL2
                        offset_x = int(name_x - marquee_state['offset'])
                        # Render the scrolling text
                        self.render_text(
                            game['name'],
                            offset_x,
                            name_y,
                            color=Theme.TEXT_PRIMARY,
                            center=False
                        )
                        # Render the repeated text with integer offset
                        repeat_offset_x = int(offset_x + text_width + self.marquee_spacing)
                        self.render_text(
                            game['name'],
                            repeat_offset_x,
                            name_y,
                            color=Theme.TEXT_PRIMARY,
                            center=False
                        )
                    else:
                        # Render static text if not selected or fits
                        self.render_text(
                            game['name'],
                            name_x,
                            name_y,
                            color=Theme.TEXT_PRIMARY if is_selected else Theme.TEXT_SECONDARY,
                            center=False
                        )
                    
                    # Reset clipping rectangle
                    sdl2.SDL_RenderSetClipRect(self.renderer, None)
            
            # Render page navigation with modern styling
            if games:
                nav_text = f"Page {current_page + 1} of {total_pages}"
                if games_override is not None:
                    nav_text = f"Search Results: {len(games)} found - " + nav_text
            else:
                nav_text = "No games found"
                
            nav_y = Config.SCREEN_HEIGHT - 40
            
            # Draw navigation text without background
            self.render_text(
                nav_text,
                Config.SCREEN_WIDTH // 2,
                nav_y,
                color=Theme.TEXT_ACCENT,
                center=True
            )

             # Render control guides
            controls = {
                'left': [
                    "list-controls.png",
                    "select.png",
                    "back.png",
                    "search.png",
                ],
                'right': [
                    "previous-page.png",
                    "next-page.png"
                ]
            }
            self.render_control_guides(controls)
            
        except Exception as e:
            logger.error(f"Error rendering games view: {e}", exc_info=True)
            
    def _render_game_placeholder(self, x: int, y: int) -> None:
        """Render a placeholder for the game image"""
        try:
            placeholder_rect = sdl2.SDL_Rect(
                x,
                y,
                Config.GAME_LIST_IMAGE_SIZE,
                Config.GAME_LIST_IMAGE_SIZE
            )
            sdl2.SDL_SetRenderDrawColor(self.renderer, 60, 60, 60, 255)
            sdl2.SDL_RenderFillRect(self.renderer, placeholder_rect)
            sdl2.SDL_SetRenderDrawColor(self.renderer, 80, 80, 80, 255)
            sdl2.SDL_RenderDrawRect(self.renderer, placeholder_rect)
        except Exception as e:
            logger.error(f"Error rendering game placeholder: {e}", exc_info=True) 