import sqlite3
import os
from utils.config import Config
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self) -> None:
        """Initialize database connection"""
        try:
            self.connection = sqlite3.connect(os.path.join(Config.ASSETS_DIR, 'catalog.db'))
            self.connection.row_factory = sqlite3.Row
            self.cursor = self.connection.cursor()
            self.cursor.execute('PRAGMA journal_mode = OFF')
            self.cursor.execute('PRAGMA synchronous = OFF')
            self.cursor.execute('PRAGMA temp_store = MEMORY')
            self.cursor.execute('PRAGMA cache_size = 10000')  # Use 2MB of cache
            
            logger.info("Database connection initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database connection: {e}", exc_info=True)
            raise
    
    def close(self):
        """Close database connection"""
        if hasattr(self, 'connection'):
            try:
                if hasattr(self, 'cursor'):
                    self.cursor.close()
                self.connection.close()
                logger.info("Database connection closed successfully")
            except Exception as e:
                logger.error(f"Error closing database connection: {e}", exc_info=True)

    def get_platforms(self):
        """Get all game platforms"""
        try:
            logger.debug("Fetching all platforms")
            query = """SELECT *
                        FROM platforms p
                        WHERE EXISTS (
                            SELECT 1
                            FROM games g
                            WHERE g.platform_id = p.id
                        )
                            ORDER BY name
                        ;"""
                
            platforms = [{'id': "ALL", 'name': "All Platforms", 'image': "all.png"}]
            self.cursor.execute(query)
            platforms += [dict(row) for row in self.cursor.fetchall()]          
            logger.info(f"Retrieved {len(platforms)} platforms")
            return platforms
        except Exception as e:
            logger.error(f"Error fetching platforms: {e}", exc_info=True)
            return []
    
    def get_games(self, platform_id, source_id=None, search_text=None, limit=None, offset=None):
        """Get games filtered by platform, source, and search text (optimized)"""
        try:
            logger.debug(f"Fetching games for platform_id={platform_id}, source_id={source_id}, search_text='{search_text}'")
            
            # Build WHERE conditions
            conditions = []
            params = []
            
            if platform_id != "ALL":
                conditions.append("g.platform_id = ?")
                params.append(platform_id)
            if source_id:
                conditions.append("g.source_id = ?")
                params.append(source_id)
            if search_text:
                conditions.append("games_fts MATCH ?")
                params.append(f"{search_text}*")
            
            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
            
            # 1. First: get total count (FAST)
            count_query = f'''
                SELECT COUNT(*) FROM games_fts
                JOIN games g ON g.id = games_fts.id
                {where_clause}
            '''
            self.cursor.execute(count_query, params)
            total_games = self.cursor.fetchone()[0]
            
            # 2. Then: fetch data with LIMIT and OFFSET
            data_query = f'''
                SELECT g.*, 
                    s.source_name,
                    p.name as platform_name,
                    p.isExtractable,
                    p.canBeRenamed
                FROM games_fts
                JOIN games g ON g.id = games_fts.id
                JOIN platforms p ON g.platform_id = p.id
                JOIN sources s ON g.source_id = s.id
                {where_clause}
                ORDER BY g.name
            '''
            if limit is not None:
                data_query += f" LIMIT {limit}"
            if offset is not None:
                data_query += f" OFFSET {offset}"
            
            self.cursor.execute(data_query, params)
            games = [dict(row) for row in self.cursor.fetchall()]
            
            logger.info(f"Retrieved {len(games)} games matching criteria platform {platform_id if platform_id else 'All'} offset {offset} search {search_text}")
            return total_games, games

        except Exception as e:
            logger.error(f"Error fetching games: {e}", exc_info=True)
            return 0, []
    
    def get_sources(self, platform_id):
        """Get sources for a platform"""
        try:
            logger.debug(f"Fetching sources for platform_id={platform_id}")
            query = f'SELECT * FROM sources'
            self.cursor.execute(query)
            fetched_sources = [dict(row) for row in self.cursor.fetchall()]
            sources = [{'id': 0, 'source_name': 'All Sources'}]
            
            if platform_id == 'ALL':
                return sources + fetched_sources
            
            for source in fetched_sources:
                query = f'SELECT COUNT(id) as count FROM games WHERE platform_id="{platform_id}" AND source_id="{source["id"]}"'
                self.cursor.execute(query)
                count = self.cursor.fetchone()['count']
                if count:
                    sources.append(source)
            logger.info(f"Retrieved {len(sources)} sources for platform")
            return sources
        except Exception as e:
            logger.error(f"Error fetching sources: {e}", exc_info=True)
            return []