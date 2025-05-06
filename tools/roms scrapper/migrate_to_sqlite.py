import json
import sqlite3
from pathlib import Path
import argparse

def create_tables(cursor):
    # Create platforms table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS platforms (
        id TEXT PRIMARY KEY UNIQUE,
        name TEXT NOT NULL,
        image TEXT,
        isExtractable BOOLEAN,
        canBeRenamed BOOLEAN
    )
    ''')

    # Create sources table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS sources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_name TEXT UNIQUE NOT NULL
    )
    ''')

    # Create games table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS games (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        platform_id TEXT,
        source_id INTEGER,
        name TEXT NOT NULL,
        image_url TEXT,
        game_url TEXT UNIQUE,
        attributes TEXT,
        FOREIGN KEY (platform_id) REFERENCES platforms (id),
        FOREIGN KEY (source_id) REFERENCES sources (id)
    )
    ''')
    
# To improve the search
def build_virtual_table_for_game_search(cursor):
    cursor.execute("DROP TABLE IF EXISTS games_fts")
    cursor.execute("CREATE VIRTUAL TABLE games_fts USING fts5(id, name)")
    cursor.execute("INSERT INTO games_fts(id, name) SELECT id, name FROM games;")
    

def get_or_build_source_id(cursor, source_name):
    # Try to get existing source ID
    cursor.execute('SELECT id FROM sources WHERE source_name = ?', (source_name,))
    result = cursor.fetchone()
    
    if result:
        return result[0]
    
    # If not exists, insert new source
    cursor.execute('INSERT INTO sources (source_name) VALUES (?)', (source_name,))
    return cursor.lastrowid

def migrate_platforms(cursor, platforms_data):
    # Insert platforms
    for platform in platforms_data:
        cursor.execute('''
        INSERT OR IGNORE INTO platforms (id, name, image, isExtractable, canBeRenamed)
        VALUES (?, ?, ?, ?, ?)
        ''', (platform['id'], platform['name'], platform['image'], 
              platform.get('isExtractable', False), platform.get('canBeRenamed', False)))

def migrate_games(cursor, json_data):
    # Process sources and games for each platform
    for platform in json_data:
        for source in platform.get('sources', []):
            # Get or create source ID
            source_id = get_or_build_source_id(cursor, source['source_name'])

            # Insert games
            for game in source.get('games', []):
                attributes = json.dumps(game['attributes']) if game.get('attributes', None) else ''
                try:
                    cursor.execute('''
                    INSERT OR IGNORE INTO games (platform_id, source_id, name, image_url, game_url, attributes)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ''', (platform['id'], source_id, game['name'], game['image_url'], game['game_url'], attributes))
                except sqlite3.IntegrityError as e:
                    print(f"Error inserting game {game['name']}: {e}")

def is_database_empty(cursor):
    # Check if platforms table is empty
    cursor.execute('SELECT COUNT(*) FROM platforms')
    return cursor.fetchone()[0] == 0

def parse_arguments():
    parser = argparse.ArgumentParser(description='Migrate games catalog from JSON to SQLite database')
    parser.add_argument('--input', '-i', type=str, default='catalog.json',
                      help='Input JSON file path (default: catalog.json)')
    parser.add_argument('--platforms', '-p', type=str, default='platforms.json',
                      help='Platforms JSON file path (default: platforms.json)')
    parser.add_argument('--output', '-o', type=str, default='games_catalog.db',
                      help='Output SQLite database file path (default: games_catalog.db)')
    parser.add_argument('--overwrite', '-w', action='store_true',
                      help='Overwrite existing database instead of appending to it')
    return parser.parse_args()

def main():
    args = parse_arguments()
    
    # Convert paths to Path objects
    input_path = Path(args.input)
    platforms_path = Path(args.platforms)
    db_path = Path(args.output)
    
    # Check if input files exist
    if not input_path.exists():
        print(f"Error: Input file '{input_path}' does not exist!")
        return
    
    if not platforms_path.exists():
        print(f"Error: Platforms file '{platforms_path}' does not exist!")
        return
    
    # Check if we should overwrite existing database
    if db_path.exists() and args.overwrite:
        print(f"Warning: Database '{db_path}' will be overwritten!")
        if input("Continue? (y/N): ").lower() != 'y':
            print("Operation cancelled.")
            return
        db_path.unlink()
    
    # Read JSON files
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            catalog_data = json.load(f)
            
        with open(platforms_path, 'r', encoding='utf-8') as f:
            platforms_data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON file: {e}")
        return
    except Exception as e:
        print(f"Error reading input file: {e}")
        return

    # Connect to SQLite database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Create tables
        create_tables(cursor)
        
        # Check if database is empty (new database)
        is_new_database = is_database_empty(cursor)
        
        if is_new_database:
            # Migrate platforms only for new database
            migrate_platforms(cursor, platforms_data)
            print("Platforms migrated successfully!")
        else:
            print("Using existing platforms in database")
        
        # Always migrate games
        migrate_games(cursor, catalog_data)
        print("Games migrated successfully!")
        
        # Build search index
        build_virtual_table_for_game_search(cursor)
        
        # Commit changes
        conn.commit()
        print(f"Migration completed successfully! Database saved to {db_path}")
        
        # Print some statistics
        cursor.execute('SELECT COUNT(*) FROM platforms')
        platforms_count = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM sources')
        sources_count = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM games')
        games_count = cursor.fetchone()[0]
        
        print(f"\nStatistics:")
        print(f"Platforms: {platforms_count}")
        print(f"Sources: {sources_count}")
        print(f"Games: {games_count}")

    except Exception as e:
        print(f"An error occurred: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    main() 