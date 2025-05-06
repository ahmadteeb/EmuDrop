"""
Games view class that handles rendering the games list for a platform.
"""
from typing import Dict, Optional
import sdl2
import time
from utils.theme import Theme
from utils.config import Config
from utils.logger import logger
from .base_view import BaseView

class GamesView(BaseView):
    """View class for displaying games in a platform"""
    
    def __init__(self, renderer, font=None):
        super().__init__(renderer, font)
        self.marquee_states = {}  # Store marquee state for each game
        self.marquee_speed = int(50 * Config.SCALE_FACTOR)  # Scale the marquee speed
        self.marquee_pause = 2.0  # Seconds to pause at each end
        self.marquee_spacing = int(50 * Config.SCALE_FACTOR)  # Scale the spacing
        
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
            
        # Calculate maximum scroll offset
        max_scroll = text_width - container_width
        
        # Update scroll position
        scroll_amount = self.marquee_speed * delta_time
        if state['direction'] > 0:
            state['offset'] = min(state['offset'] + scroll_amount, max_scroll)
            if state['offset'] >= max_scroll:
                state['direction'] = -1
                state['pause_time'] = self.marquee_pause
        else:
            state['offset'] = max(state['offset'] - scroll_amount, 0)
            if state['offset'] <= 0:
                state['direction'] = 1
                state['pause_time'] = self.marquee_pause
        
        return state
    
    def _render_game_placeholder(self, x: int, y: int, is_loading: bool = False) -> None:
        """Render a placeholder for game images"""
        try:
            # Draw placeholder background
            rect = sdl2.SDL_Rect(x, y, Config.GAME_LIST_IMAGE_SIZE, Config.GAME_LIST_IMAGE_SIZE)
            sdl2.SDL_SetRenderDrawColor(self.renderer, 30, 30, 30, 255)
            sdl2.SDL_RenderFillRect(self.renderer, rect)
            
            if is_loading:
                # Draw "Loading..." text in the center of the placeholder
                self.render_text(
                    "Loading...",
                    x + Config.GAME_LIST_IMAGE_SIZE // 2,
                    y + Config.GAME_LIST_IMAGE_SIZE // 2,
                    color=(200, 200, 200),  # Light gray color
                    center=True
                )
            
        except Exception as e:
            logger.error(f"Error rendering game placeholder: {e}", exc_info=True)
            
    def render(self,
               current_page: int, total_games: int,
               selected_game: int, show_image: bool = False,
               isSearched: bool = False, games: list = None,
               active_downloads_count: int = None) -> None:
        
        """Render the games view
        
        Args:
            current_page: Current page number
            selected_game: Index of the currently selected game
            show_image: Whether to show the game image
            isSearched: Whether this is a search result view
            games: List of games to display
            active_downloads_count: Number of active downloads
        """
        try:
            # Render the title at the top
            self.render_title("Games")

            if active_downloads_count:
                self._render_active_download_count(active_downloads_count)    

             # Render control guides
            controls = {
                'left': [
                    "list-controls.png",
                    "select.png",
                    "back.png",
                    "search.png",
                    "downloads.png",
                ],
                'right': [
                    "sources.png",
                    "previous-page.png",
                    "next-page.png"
                ]
            }
            self.render_control_guides(controls)
            
            total_pages = (total_games + Config.GAMES_PER_PAGE - 1) // Config.GAMES_PER_PAGE
            # Get selected game data
            if games:
                if 0 <= selected_game < len(games):
                    selected_game_data = games[selected_game]
                else:
                    selected_game_data = None
                search_text_result = None
                if isSearched:
                    search_text_result = f"Search Results: {total_games} found."
                self._render_page_navigation(current_page, total_pages, search_text_result)
            else:
                # Show "No games found" message
                self.render_text(
                    "No games found",
                    Config.SCREEN_WIDTH // 2,
                    Config.SCREEN_HEIGHT // 2 - int(30 * Config.SCALE_FACTOR),
                    color=(200, 200, 200),
                    center=True
                )
                return
            
            # Calculate starting positions
            list_start_x = int((Config.SCREEN_WIDTH - (Config.GAME_LIST_WIDTH + Config.GAME_LIST_IMAGE_SIZE + Config.GAME_LIST_SPACING_BETWEEN)) // 2)
            image_start_x = list_start_x + Config.GAME_LIST_WIDTH + Config.GAME_LIST_SPACING_BETWEEN
            
            # Calculate list area height based on actual number of games
            max_list_height = (Config.GAME_LIST_ITEM_HEIGHT + Config.GAME_LIST_SPACING) * Config.GAMES_PER_PAGE - Config.GAME_LIST_SPACING
            actual_list_height = (Config.GAME_LIST_ITEM_HEIGHT + Config.GAME_LIST_SPACING) * Config.GAMES_PER_PAGE - Config.GAME_LIST_SPACING
            
            # Calculate vertical positions to center both the list and image
            list_start_y = Config.GAME_LIST_START_Y + (max_list_height - actual_list_height) // 2
            image_start_y = Config.GAME_LIST_START_Y + (max_list_height - Config.GAME_LIST_IMAGE_SIZE) // 2
            
            # Render featured game section (large image and details)
            if selected_game_data:
                # Scale padding and shadow offset
                padding = int(Config.GAME_LIST_CARD_PADDING * Config.SCALE_FACTOR)
                shadow_offset = int(4 * Config.SCALE_FACTOR)
                
                # Render featured game card background
                featured_rect = sdl2.SDL_Rect(
                    image_start_x - padding,
                    image_start_y - padding,
                    Config.GAME_LIST_IMAGE_SIZE + padding * 2,
                    Config.GAME_LIST_IMAGE_SIZE + padding * 2
                )
                
                # Draw card shadow
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
                
                # Render game platform and source name above the image
                name_y = image_start_y - int(120 * Config.SCALE_FACTOR)  # Position above image
                self.render_text(
                    f"Platform: {selected_game_data['platform_name']}",
                    image_start_x,
                    name_y,
                    color=Theme.TEXT_PRIMARY,
                    center=False
                )
                
                name_y = image_start_y - int(80 * Config.SCALE_FACTOR)  # Position above image
                self.render_text(
                    f"Source: {selected_game_data['source_name']}",
                    image_start_x,
                    name_y,
                    color=Theme.TEXT_PRIMARY,
                    center=False
                )
                
                # Only render the game image if the hold timer has elapsed
                if show_image and 'image_url' in selected_game_data and selected_game_data['image_url']:
                    texture = self.get_texture(selected_game_data['image_url'])
                    if texture:
                        image_rect = sdl2.SDL_Rect(
                            image_start_x,
                            image_start_y,
                            Config.GAME_LIST_IMAGE_SIZE,
                            Config.GAME_LIST_IMAGE_SIZE
                        )
                        sdl2.SDL_RenderCopy(self.renderer, texture, None, image_rect)
                    else:
                        # Show loading indicator while texture is being loaded
                        self._render_game_placeholder(image_start_x, image_start_y, is_loading=True)
                else:
                    # Show loading indicator or placeholder while waiting
                    self._render_game_placeholder(image_start_x, image_start_y)
                    
                    # Show "Hold to view image" text if not loaded yet
                    if not show_image:
                        # Display hold message underneath the image with scaled position
                        self.render_text(
                            "Hold to view image",
                            image_start_x + Config.GAME_LIST_IMAGE_SIZE // 2,
                            image_start_y + Config.GAME_LIST_IMAGE_SIZE // 2,
                            color=Theme.TEXT_SECONDARY,
                            center=True
                        )
            
            # Render game list with modern styling
            for i, game in enumerate(games):
                y = list_start_y + (Config.GAME_LIST_ITEM_HEIGHT + Config.GAME_LIST_SPACING) * i
                is_selected = i == selected_game
                
                # Calculate item position with padding
                item_x = list_start_x
                item_y = y
                
                # Draw item shadow for selected item
                if is_selected:
                    shadow_offset = int(4 * Config.SCALE_FACTOR)
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
                
                # Render game name with scaled padding
                name_x = item_x + int(20 * Config.SCALE_FACTOR)
                name_y = item_y + (Config.GAME_LIST_ITEM_HEIGHT - int(30 * Config.SCALE_FACTOR)) // 2
                
                # Get container width with scaled padding
                container_width = Config.GAME_LIST_WIDTH - int(40 * Config.SCALE_FACTOR)
                
                # Create text surface to get dimensions
                text_color = Theme.TEXT_PRIMARY if is_selected else Theme.TEXT_SECONDARY
                texture = None
                ellipsis_texture = None
                
                try:
                    texture, text_width, text_height = self.create_text_texture(game['name'], text_color)
                    
                    if not texture:
                        continue
                        
                    if text_width > container_width:
                        if is_selected:
                            # Handle scrolling for selected items
                            state = self._get_marquee_state(game['id'], text_width, container_width, is_selected)
                            
                            # Calculate the visible portion
                            visible_width = min(container_width - int(20 * Config.SCALE_FACTOR), text_width - int(state['offset']))
                            
                            # Setup source rectangle (the portion of text to show)
                            src_rect = sdl2.SDL_Rect(
                                int(state['offset']),  # Start from offset
                                0,
                                visible_width,  # Show only what fits
                                text_height
                            )
                            
                            # Setup destination rectangle (where to render)
                            dst_rect = sdl2.SDL_Rect(
                                name_x,
                                name_y,
                                visible_width,  # Match the visible width
                                text_height
                            )
                            
                            # Render the clipped portion
                            sdl2.SDL_RenderCopy(self.renderer, texture, src_rect, dst_rect)
                            
                            # Add ellipsis if not at end of scroll
                            if state['offset'] < (text_width - container_width):
                                try:
                                    ellipsis_texture, ellipsis_width, _ = self.create_text_texture("...", text_color)
                                    if ellipsis_texture:
                                        ellipsis_rect = sdl2.SDL_Rect(
                                            name_x + visible_width,  # Place after visible text
                                            name_y,
                                            ellipsis_width,
                                            text_height
                                        )
                                        sdl2.SDL_RenderCopy(self.renderer, ellipsis_texture, None, ellipsis_rect)
                                finally:
                                    if ellipsis_texture:
                                        sdl2.SDL_DestroyTexture(ellipsis_texture)
                        else:
                            # For non-selected items, clip text and add ellipsis
                            try:
                                # Calculate space needed for ellipsis
                                ellipsis_texture, ellipsis_width, _ = self.create_text_texture("...", text_color)
                                if ellipsis_texture:
                                    # Adjust visible width to accommodate ellipsis
                                    visible_width = container_width - ellipsis_width
                                    
                                    # Render clipped text
                                    src_rect = sdl2.SDL_Rect(0, 0, visible_width, text_height)
                                    dst_rect = sdl2.SDL_Rect(name_x, name_y, visible_width, text_height)
                                    sdl2.SDL_RenderCopy(self.renderer, texture, src_rect, dst_rect)
                                    
                                    # Render ellipsis
                                    ellipsis_rect = sdl2.SDL_Rect(
                                        name_x + visible_width,
                                        name_y,
                                        ellipsis_width,
                                        text_height
                                    )
                                    sdl2.SDL_RenderCopy(self.renderer, ellipsis_texture, None, ellipsis_rect)
                            finally:
                                if ellipsis_texture:
                                    sdl2.SDL_DestroyTexture(ellipsis_texture)
                    else:
                        # Text fits, render it completely
                        dst_rect = sdl2.SDL_Rect(name_x, name_y, text_width, text_height)
                        sdl2.SDL_RenderCopy(self.renderer, texture, None, dst_rect)
                finally:
                    if texture:
                        sdl2.SDL_DestroyTexture(texture)

        except Exception as e:
            logger.error(f"Error rendering games view: {e}", exc_info=True)