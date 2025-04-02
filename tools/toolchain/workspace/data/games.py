import json
import os
import logging
import math
from typing import List, Dict, Optional
from utils.config import Config
from data.categories import CategoryManager

logger = logging.getLogger(__name__)

class GameManager:
    """Manages game data for different categories"""
    _games_data = None

    @classmethod
    def _load_games_data(cls, category_id):
        """Load games data from the JSON file"""
        category_manager = CategoryManager()
        games = category_manager.get_category_by_id(category_id)
        return games

    @classmethod
    def get_games_by_category(cls, category_id: str) -> List[Dict[str, str]]:
        """Retrieve games for a specific category ID"""
        games = cls._load_games_data(category_id).get('games', [])
        if not games:
            return games
        else:
            return sorted(games, key=lambda game: game['name'])

    @classmethod
    def get_total_games_in_category(cls, category_id: str) -> int:
        """Get total number of games in a specific category"""
        return len(cls.get_games_by_category(category_id))

    @classmethod
    def get_games_for_page(cls, category_id: str, page: int, games_per_page: int = None) -> List[Dict[str, str]]:
        """Get games for a specific page within a category"""
        category_games = cls.get_games_by_category(category_id)
        
        # Use provided games_per_page or default from config
        games_per_page = games_per_page or Config.GAMES_PER_PAGE
        
        start_index = page * games_per_page
        end_index = start_index + games_per_page
        
        return category_games[start_index:end_index]

    @classmethod
    def get_total_game_pages(cls, category_id: str, games_per_page: int = None) -> int:
        """Calculate total pages for a category"""
        # Use provided games_per_page or default from config
        games_per_page = games_per_page or Config.GAMES_PER_PAGE
        total_games = cls.get_total_games_in_category(category_id)
        return math.ceil(total_games / games_per_page)

    @classmethod
    def get_game(cls, category_id: str, game_index: int) -> Optional[Dict[str, str]]:
        """Get a specific game by category and index"""
        games = cls.get_games_by_category(category_id)
        if 0 <= game_index < len(games):
            return games[game_index]
        return None 