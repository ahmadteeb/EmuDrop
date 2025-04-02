import os
import requests
import threading
import time
import patoolib, zipfile, py7zr
from utils.config import Config
from utils.logger import logger
from utils.screenscrapper import ScreenScraper

class DownloadManager:
    """Manages game downloads with progress tracking and cancellation support"""

    def __init__(self, id, game_name, game_url):
        """
        Initialize download manager for a specific game
        
        :param game_name: Name of the game to download
        :param game_url: URL to request download link
        """
        self.id = id
        self.game_name = game_name
        self.game_url = game_url
        
        # Download state
        self.download_thread = None
        self.is_downloading = False
        self.download_progress = 0
        self.total_size = 0
        self.current_size = 0
        self.download_speed = 0
        self.cancel_download = threading.Event()
        
        # Extraction state
        self.is_extracting = False
        
        # Ensure download directory exists
        os.makedirs(Config.DOWNLOAD_DIR, exist_ok=True)

    def _get_download_url(self):
        '''
            This function if the downloading link need request
        '''
        return self.game_url
    
    def get_file_name_from_url(self, text):
        # Dictionary of URL-encoded characters
        decode_map = {
            "%20": " ", "%21": "!", "%22": '"', "%23": "#", "%24": "$", "%25": "%", "%26": "&",
            "%27": "'", "%28": "(", "%29": ")", "%2A": "*", "%2B": "+", "%2C": ",", "%2D": "-",
            "%2E": ".", "%2F": "/", "%3A": ":", "%3B": ";", "%3C": "<", "%3D": "=", "%3E": ">",
            "%3F": "?", "%40": "@", "%5B": "[", "%5C": "\\", "%5D": "]", "%5E": "^", "%5F": "_",
            "%60": "`", "%7B": "{", "%7C": "|", "%7D": "}", "%7E": "~"
        }
        # Replace each encoded character with its actual character

        for encoded, decoded in decode_map.items():
            text = text.replace(encoded, decoded)
        
        file_name = text.split('/')[-1]
        return file_name

    def delete_folder(self, folder):
        """Recursively delete a folder and all its contents.
        
        Args:
            folder (str): Path to the folder to delete
        """
        try:
            for file in os.listdir(folder):
                file_path = os.path.join(folder, file)
                if os.path.isdir(file_path):
                    self.delete_folder(file_path)
                else:
                    os.remove(file_path)
            os.rmdir(folder)
        except Exception as e:
            logger.error(f"Error deleting folder {folder}: {e}")
            raise
        
    def extractor(self, file, extract_to):
        """Extract archive file.
        
        Args:
            file (str): Path to the archive file
            extract_to (str): Directory to extract files to
            
        Raises:
            ValueError: If file extension is not supported
        """
        try:
            if not os.path.exists(file):
                raise FileNotFoundError(f"Archive file not found: {file}")
                
            if not os.path.exists(extract_to):
                os.makedirs(extract_to)
                
            if file.endswith(".zip"):
                self._extract_zip(file, extract_to)
            elif file.endswith(".7z"):
                self._extract_7z(file, extract_to)
            elif file.endswith(".rar"):
                self._extract_rar(file, extract_to)
            else:
                raise ValueError(f"Unsupported archive format: {file}")
                
            # Clean up the archive file after successful extraction
            os.remove(file)
            
        except Exception as e:
            logger.error(f"Extraction error for {file}: {e}")
            raise
            
    def _extract_rar(self, file, extract_to):
        """Extract RAR archive.
        
        Args:
            file (str): Path to the RAR file
            extract_to (str): Directory to extract files to
        """
        patoolib.extract_archive(file, outdir=extract_to)
        
    def _extract_zip(self, file, extract_to):
        """Extract ZIP archive.
        
        Args:
            file (str): Path to the ZIP file
            extract_to (str): Directory to extract files to
        """
        with zipfile.ZipFile(file, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
                
    def _extract_7z(self, file, extract_to):
        """Extract 7Z archive.
        
        Args:
            file (str): Path to the 7Z file
            extract_to (str): Directory to extract files to
        """
        with py7zr.SevenZipFile(file, 'r') as sevenz_ref:
            sevenz_ref.extractall(extract_to)
    
    def move_and_extract_game(self, folder):
        """Move and extract game files to the ROMs directory"""
        try:
            self.is_extracting = True
            
            # Create ROM directory
            rom_path = os.path.join(Config.ROMS_DIR, self.id) # for development only
            os.makedirs(rom_path, exist_ok=True)
            
            # Handle nested folders
            if os.path.exists(folder):
                files = os.listdir(folder)
                if files and os.path.isdir(os.path.join(folder, files[0])):
                    folder = os.path.join(folder, files[0])
            
            # Check for archive files
            archive_files = [f for f in os.listdir(folder) 
                           if any(ext in f.lower() for ext in ['.zip', '.rar', '.7z'])]
            
            if archive_files:
                # Extract archive
                tmp_path = os.path.join(folder, 'tmp')
                os.makedirs(tmp_path, exist_ok=True)
                self.extractor(os.path.join(folder, archive_files[0]), tmp_path)
                self.move_and_extract_game(tmp_path)
            else:
                # Move files
                for file in os.listdir(folder):
                    if '.nfo' not in file:
                        name, ext = os.path.splitext(file)
                        new_name = self.game_name + ext
                        os.rename(os.path.join(folder, file), os.path.join(rom_path, new_name))
                        scrapper = ScreenScraper()
                        success, message = scrapper.scrape_rom(new_name, self.id)
                        if success:
                            logger.info(message)
                        else:
                            logger.error(message)
                        
            self.delete_folder(folder)
            self.is_extracting = False
            return True
            
        except Exception as e:
            logger.error(f"Error moving and extracting game: {e}")
            self.is_extracting = False
            return False

    def start_download(self):
        """
        Start downloading the game
        
        :return: True if download started, False otherwise
        """
        # Prevent multiple simultaneous downloads
        if self.is_downloading:
            logger.warning("Download already in progress")
            return False
        
        # Get download URL
        download_url = self._get_download_url()
        if not download_url:
            logger.error("Could not retrieve download URL")
            return False
        
        # Reset download state
        self.is_downloading = True
        self.download_progress = 0
        self.current_size = 0
        self.cancel_download.clear()
        
        # Prepare download file path
        self.filename = self.get_file_name_from_url(download_url)
        self.download_path = os.path.join(Config.DOWNLOAD_DIR, self.filename)
        if os.path.exists(self.download_path):
            os.remove(self.download_path)

        # Start download in a separate thread
        self.download_thread = threading.Thread(
            target=self._download_worker, 
            args=(download_url, )
        )
        self.download_thread.start()
        
        return True

    def _download_worker(self, download_url):
        """
        Background worker to download the game file
        
        :param download_url: URL to download from
        """
        try:
            with requests.get(download_url, stream=True, timeout=30) as response:
                response.raise_for_status()
                
                # Get total file size
                self.total_size = int(response.headers.get('content-length', 0))
                
                # Open file for writing
                with open(self.download_path, 'wb') as file:
                    start_time = time.time()
                    downloaded = 0
                    
                    for chunk in response.iter_content(chunk_size=8192):
                        # Check for cancellation
                        if self.cancel_download.is_set():
                            logger.info("Download cancelled")
                            break
                        
                        if chunk:
                            file.write(chunk)
                            downloaded += len(chunk)
                            
                            # Calculate progress and speed
                            elapsed_time = time.time() - start_time
                            self.current_size = downloaded
                            self.download_progress = (downloaded / self.total_size * 100) if self.total_size > 0 else 0
                            
                            # Update download speed every second
                            if elapsed_time > 0:
                                self.download_speed = downloaded / elapsed_time
            
            # Mark download as complete if not cancelled
            if not self.cancel_download.is_set():
                self.download_progress = 100
                logger.info(f"Download complete: {self.game_name}")
                os.makedirs(os.path.join(Config.DOWNLOAD_DIR, self.game_name), exist_ok=True)
                os.rename(self.download_path, os.path.join(Config.DOWNLOAD_DIR, self.game_name, self.filename))
                self.move_and_extract_game(os.path.join(Config.DOWNLOAD_DIR, self.game_name))
            
        except Exception as e:
            logger.error(f"Download failed: {e}")
            self.download_progress = -1  # Indicate error
        finally:
            self.is_downloading = False

    def cancel(self):
        """
        Cancel the ongoing download
        """
        if self.is_downloading:
            self.cancel_download.set()
            if self.download_thread:
                self.download_thread.join()
            
            # Remove partial download file if exists
            if os.path.exists(self.download_path):
                os.remove(self.download_path)

    def get_status(self):
        """
        Get current download status
        
        :return: Dictionary with download status details
        """
        return {
            'is_downloading': self.is_downloading,
            'is_extracting': self.is_extracting,
            'progress': round(self.download_progress, 2),
            'total_size': self.total_size,
            'current_size': self.current_size,
            'download_speed': self.download_speed,
            'game_name': self.game_name
        }

    @staticmethod
    def format_size(size_bytes):
        """
        Convert bytes to human-readable format
        
        :param size_bytes: Size in bytes
        :return: Formatted size string
        """
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"

    def get_game_size(self):
        """
        Pre-fetch the game size without starting the download
        
        :return: Size in bytes, or 0 if size cannot be determined
        """
        try:
            download_url = self._get_download_url()
            if not download_url:
                return 0
            
            # Make a HEAD request to get content length
            response = requests.head(download_url, timeout=10, allow_redirects=True)
            if response.status_code == 200:
                size = int(response.headers.get('content-length', 0))
                self.total_size = size  # Store for later use
                return size
            return 0
        except Exception as e:
            logger.error(f"Error getting game size: {e}")
            return 0 