import json
import os
import logging
import math
from typing import List, Dict
from utils.config import Config

logger = logging.getLogger(__name__)

class CategoryManager:
    """Manages game categories and their metadata"""
    _categories_data = None

    @classmethod
    def _load_categories_data(cls):
        """Load categories data from the JSON file"""
        try:
            json_path = os.path.join(Config.ASSETS_DIR, 'catalog.json')
            with open(json_path, 'r', encoding='utf-8') as f:
                cls._categories_data = sorted(json.load(f), key=lambda cate: cate['name'])
        except FileNotFoundError:
            logger.error(f"Catalog JSON file not found at {json_path}")
            cls._categories_data = []
        except json.JSONDecodeError:
            logger.error("Error decoding catalog JSON file")
            cls._categories_data = []

    @classmethod
    def get_categories(cls) -> List[Dict[str, str]]:
        """Return a list of game categories"""
        if cls._categories_data is None:
            cls._load_categories_data()
        
        return [
            {
                "id": category['id'], 
                "name": category['name'], 
                "image": category['image'],
                "isExtractable": category['isExtractable']
            } for category in cls._categories_data
        ]

    @classmethod
    def get_category_by_id(cls, category_id: str) -> Dict[str, str]:
        """Get a specific category by its ID"""
        if cls._categories_data is None:
            cls._load_categories_data()
        
        for category in cls._categories_data:
            if category['id'] == category_id:
                return category
        
        return {}

    @classmethod
    def get_total_pages(cls, items_per_page: int = 6) -> int:
        """Calculate total pages for categories"""
        categories = cls.get_categories()
        return math.ceil(len(categories) / items_per_page)

    @classmethod
    def get_categories_for_page(cls, page: int, items_per_page: int = 6) -> List[Dict[str, str]]:
        """Get categories for a specific page"""
        categories = cls.get_categories()
        start_index = page * items_per_page
        end_index = start_index + items_per_page
        return categories[start_index:end_index] 