import os
import shutil
from requests import Session
import threading
import time
import json
from dataclasses import dataclass, fields
from utils.config import Config
from utils.logger import logger
from utils.screenscrapper import ScreenScraper
from utils.games_extractor_converter import GamesExtractorConverter

@dataclass
class GameProp:
    platform_id: str
    name: str
    game_url: str
    image_url: str
    isExtractable: bool
    canBeRenamed: bool
    source_name: str
    attributes: str

class DownloadManager:
    """Manages game downloads with progress tracking and cancellation support"""

    # Class variable to track all download managers
    _all_managers = []
    
    def __init__(self, game: dict):
        """
        Initialize download manager for a specific game
        
        :param game_name: Name of the game to download
        :param game_url: URL to request download link
        """
        
        game_fields = {f.name for f in fields(GameProp)}
        filtered_data = {k: v for k, v in game.items() if k in game_fields}
        self.game_prop = GameProp(**filtered_data)
        
        for ch in ['<', '>', ':', '"', '/', '\\', '|', '?', '*']:
            self.game_prop.name = self.game_prop.name.replace(ch, '')
        
        self.download_path = os.path.join(Config.DOWNLOAD_DIR, self.game_prop.name)
        
        # Download state as JSON
        self.status = {
            "state": "queued",  # queued, downloading, processing, scraping, completed, error, cancelled
            "progress": 0,
            "total_size": 0,
            "current_size": 0,
            "download_speed": 0,
            "queue_position": 0,
            "current_operation": "",
            "error_message": "",
            "is_paused": False
        }
        
        # Control events
        self.cancel_download = threading.Event()
        self.pause_download = threading.Event()
        
        # Thread references
        self.download_url = None
        self.session = Session()
        self.download_thread = None
        self.size_check_thread = None
        self.size_check_complete = threading.Event()
        self.size_check_error = None
        self.gameExtractorConverter = None
        
    
    
    def add_manager(self):
        DownloadManager._all_managers.append(self)
        self._update_queue_positions()
        
    def _update_queue_positions(self):
        """Update queue positions for all queued downloads"""
        queued_managers = [m for m in DownloadManager._all_managers if m.status["state"] == "queued"]
        for i, manager in enumerate(queued_managers):
            manager.status["queue_position"] = i + 1

    def _get_download_url(self):
        if self.download_url:
            return self.download_url
        
        
        self.filename = self.get_file_name_from_url(self.game_prop.game_url)
        return self.game_prop.game_url
    
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

    def start_download(self):
        """
        Start downloading the game
        
        :return: True if download started, False otherwise
        """
        # Prevent multiple simultaneous downloads
        if self.status["state"] == "downloading":
            logger.warning("Download already in progress")
            return False
        
        # Get download URL
        download_url = self._get_download_url()
        if not download_url:
            logger.error("Could not retrieve download URL")
            self.status["state"] = "error"
            self.status["error_message"] = "Could not retrieve download URL"
            return False
        
        # Reset download state
        self.status.update({
            "state": "downloading",
            "progress": 0,
            "current_size": 0,
            "queue_position": 0,
            "error_message": "",
            "is_paused": False
        })
        
        self.cancel_download.clear()
        
        # Update queue positions for remaining queued downloads
        self._update_queue_positions()
        
        if os.path.exists(self.download_path):
            shutil.rmtree(self.download_path)
            
        os.makedirs(self.download_path)

        # Start download in a separate thread
        self.download_thread = threading.Thread(
            target=self._download_worker, 
            args=(download_url, )
        )
        self.download_thread.start()
        
        return True

    def pause(self):
        """Pause the ongoing download"""
        if self.status["state"] == "downloading":
            self.pause_download.set()
            self.status["is_paused"] = True
            logger.info(f"Download paused: {self.game_prop.name}")

    def resume(self):
        """Resume the paused download"""
        if self.status["state"] == "downloading" and self.status["is_paused"]:
            self.pause_download.clear()
            self.status["is_paused"] = False
            logger.info(f"Download resumed: {self.game_prop.name}")

    def _download_worker(self, download_url):
        """
        Background worker to download the game file
        
        :param download_url: URL to download from
        """
        try:
            with self.session.get(download_url, stream=True, timeout=30) as response:
                response.raise_for_status()
                
                # Get total file size
                self.status["total_size"] = int(response.headers.get('content-length', 0))
                    
                with open(os.path.join(self.download_path, self.filename), 'wb') as file:
                    start_time = time.time()
                    downloaded = 0
                    
                    for chunk in response.iter_content(chunk_size=8192):
                        # Check for cancellation
                        if self.cancel_download.is_set():
                            logger.info("Download cancelled")
                            break
                        
                        # Check for pause
                        if self.pause_download.is_set():
                            while self.pause_download.is_set() and not self.cancel_download.is_set():
                                time.sleep(0.1)  # Sleep while paused
                            if self.cancel_download.is_set():
                                break
                        
                        if chunk:
                            file.write(chunk)
                            downloaded += len(chunk)
                            
                            # Calculate progress and speed
                            elapsed_time = time.time() - start_time
                            self.status["current_size"] = downloaded
                            self.status["progress"] = (downloaded / self.status["total_size"] * 100) if self.status["total_size"] > 0 else 0
                            
                            # Update download speed every second
                            if elapsed_time > 0:
                                self.status["download_speed"] = downloaded / elapsed_time
            
            # Process the downloaded file if not cancelled
            if not self.cancel_download.is_set():
                self.status["progress"] = 100
                self.status["state"] = "processing"
                
                self.gameExtractorConverter = GamesExtractorConverter(self.status, self.game_prop, self.download_path)
                game_names_to_scrape = self.gameExtractorConverter.move_game()
                logger.info(f"{self.game_prop.name} has been moved successfully")
                
                # Update status for scraping
                self.status["state"] = "scraping"
                self.status["current_operation"] = "Scraping Cover Images"
                
                scrapper = ScreenScraper()
                for name in game_names_to_scrape:
                    message = scrapper.scrape_rom(self.game_prop.image_url, name, self.game_prop.platform_id)
                    logger.info(message)
                
                # Mark as completed
                self.status["state"] = "completed"
                self.status["current_operation"] = ""

        except Exception as e:
            logger.error(f"Download failed: {e}")
            self.status["state"] = "error"
            self.status["error_message"] = str(e)
        
        finally:
            shutil.rmtree(self.download_path)
        
        
    def cancel(self):
        """Cancel the ongoing download"""
        self.status['state'] = "cancelling"
        if self.gameExtractorConverter is not None and self.gameExtractorConverter.process is not None:
            self.gameExtractorConverter.process.terminate()
            self.gameExtractorConverter.process.wait()
        
        if self.download_thread:
            self.cancel_download.set()
            if self.download_thread:
                self.download_thread.join()
        
        # Remove partial download file if exists
        if self.status["state"] != "queued" and os.path.exists(self.download_path):
            shutil.rmtree(self.download_path)

        # Remove from the list of all managers
        if self in DownloadManager._all_managers:
            DownloadManager._all_managers.remove(self)
                
        # Update queue positions for remaining downloads
        self._update_queue_positions()

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

    @staticmethod
    def get_disk_space():
        """
        Get disk space information for the given path
        
        :param path: Path to check disk space
        :return: Tuple of (total_space, free_space) in bytes
        """
        try:
            if os.name == 'nt':  # Windows
                import ctypes
                free_bytes = ctypes.c_ulonglong(0)
                total_bytes = ctypes.c_ulonglong(0)
                ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                    ctypes.c_wchar_p(os.path.dirname(Config.DOWNLOAD_DIR)),
                    None,
                    ctypes.pointer(total_bytes),
                    ctypes.pointer(free_bytes)
                )
                return total_bytes.value, free_bytes.value
            else:  # Unix/Linux/macOS
                st = os.statvfs(os.path.dirname(Config.DOWNLOAD_DIR))
                total = st.f_blocks * st.f_frsize
                free = st.f_bavail * st.f_frsize
                return total, free
        except Exception as e:
            logger.error(f"Error getting disk space: {e}")
            return 0, 0

    def get_game_size_async(self):
        """
        Start asynchronous game size check
        """
        if self.size_check_thread and self.size_check_thread.is_alive():
            return
            
        self.size_check_complete.clear()
        self.size_check_error = None
        self.size_check_thread = threading.Thread(target=self._size_check_worker)
        self.size_check_thread.daemon = True
        self.size_check_thread.start()

    def _size_check_worker(self):
        """Background worker for checking game size"""
        try:
            download_url = self._get_download_url()
            if not download_url:
                self.size_check_error = "Could not get download URL"
                return
            
            # Make a HEAD request to get content length
            response = self.session.head(download_url, timeout=10, allow_redirects=True)
            if response.status_code == 200:
                self.status["total_size"] = int(response.headers.get('content-length', 0))
            else:
                self.size_check_error = f"HTTP error: {response.status_code}"
        except Exception as e:
            logger.error(f"Error getting game size: {e}")
            self.size_check_error = str(e)
        finally:
            self.size_check_complete.set()

    def wait_for_size(self, timeout=None):
        """
        Wait for size check to complete
        
        :param timeout: Maximum time to wait in seconds
        :return: True if size check completed successfully, False otherwise
        """
        if not self.size_check_thread:
            return False
            
        self.size_check_complete.wait(timeout)
        return not bool(self.size_check_error)
    
    @classmethod
    def get_active_download_count(cls):
        """
        Get the number of active downloads
        
        :return: Number of active downloads
        """
        return sum(1 for m in cls._all_managers if m.status["state"] in ["downloading", "processing", "scraping"])
