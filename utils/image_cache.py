import os
import hashlib
import requests
import logging
import time
from typing import Optional
from utils.config import Config
from PIL import Image

logger = logging.getLogger(__name__)

class ImageCache:
    @staticmethod
    def get_cached_image_path(image_url: str) -> str:
        """
        Generate a unique filename for the cached image based on URL
        
        :param image_url: URL of the image to cache
        :return: Path to the cached image file
        """
        # Create cache directory if it doesn't exist
        cache_dir = Config.IMAGES_CACHE_DIR
        os.makedirs(cache_dir, exist_ok=True)
        
        # Generate a unique filename based on URL hash
        url_hash = hashlib.md5(image_url.encode()).hexdigest()
        
        
        cached_filename = f"{url_hash}.png"
        cached_path = os.path.join(cache_dir, cached_filename)
        return cached_path

    @classmethod
    def download_image(cls, image_url: str, force_download: bool = False) -> Optional[str]:
        """
        Download and cache an image from a URL with advanced error handling
        
        :param image_url: URL of the image to download
        :param force_download: Whether to force re-download even if cached
        :return: Path to the cached image file, or None if download fails
        """
        # Validate URL
        if not image_url or not isinstance(image_url, str):
            logger.error(f"Invalid image URL: {image_url}")
            return None

        cached_path = cls.get_cached_image_path(image_url)
        
        # Return cached image if it exists and not forcing download
        if not force_download and os.path.exists(cached_path):
            return cached_path
        
        # Specialized headers for different domains
        headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'image/webp,*/*',
                'Accept-Language': 'en-US,en;q=0.5'
            }

        for attempt in range(Config.IMAGE_DOWNLOAD_MAX_RETRIES):
            try:
                # Download the image with extended timeout and stream mode
                response = requests.get(
                    image_url, 
                    headers=headers,
                    timeout=Config.IMAGE_DOWNLOAD_TIMEOUT,  # (connect timeout, read timeout)
                    stream=True,
                    allow_redirects=True
                )
                
                # Raise an exception for bad status codes
                response.raise_for_status()
                
                # Check content type
                content_type = response.headers.get('content-type', '')
                if not content_type.startswith('image/'):
                    logger.warning(f"Invalid content type for {image_url}: {content_type}")
                    # Continue to next retry or fallback
                    continue
                
                # Save the image
                with open(cached_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                #convert to png
                with Image.open(cached_path) as img:
                    if img.format != 'PNG':
                        img.convert("RGBA").save(cached_path, format='PNG')
                
                # Verify file was saved successfully
                if not os.path.exists(cached_path) or os.path.getsize(cached_path) == 0:
                    logger.warning(f"Failed to save image from {image_url}")
                    continue
                
                logger.info(f"Cached image from {image_url} to {cached_path}")
                return cached_path
            
            except requests.exceptions.ConnectionError as e:
                logger.warning(f"Connection error (Attempt {attempt+1}) for {image_url}: {e}")
            except requests.exceptions.Timeout as e:
                logger.warning(f"Timeout error (Attempt {attempt+1}) for {image_url}: {e}")
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request error (Attempt {attempt+1}) for {image_url}: {e}")
            except PermissionError as e:
                logger.error(f"Permission error saving image: {e}")
                break
            except Exception as e:
                logger.error(f"Unexpected error downloading image {image_url}: {e}")
                break
            
            # Wait before retrying with exponential backoff
            if attempt < Config.IMAGE_DOWNLOAD_MAX_RETRIES - 1:
                time.sleep(Config.IMAGE_DOWNLOAD_RETRY_DELAYS[attempt])
        
        # Fallback to a default image if all attempts fail
        if os.path.exists(Config.DEFAULT_IMAGE_PATH):
            logger.warning(f"Using default image for {image_url}")
            return Config.DEFAULT_IMAGE_PATH
        
        return None