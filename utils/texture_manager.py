import os
import sdl2
import sdl2.sdlimage
import logging
import threading
from typing import Dict, Optional
from utils.logger import logger
from utils.config import Config
from utils.image_cache import ImageCache

logger = logging.getLogger(__name__)

class TextureManager:
    """Manages SDL textures for the application"""

    def __init__(self, renderer):
        """
        Initialize texture manager
        
        :param renderer: SDL renderer
        """
        self.renderer = renderer
        self.textures: Dict[str, sdl2.SDL_Texture] = {}
        self.texture_last_used = {}  # Track when each texture was last used
        self.max_textures = 20  # Maximum number of textures to keep in memory for low-power devices
        self.current_loading_texture = None  # Track the currently loading texture
        self.download_thread = None  # Thread for downloading images
        self.cached_image_path = None  # Path to the most recently downloaded image

    def get_texture(self, image_path_or_url: str) -> Optional[sdl2.SDL_Texture]:
        """
        Get SDL texture for an image, supporting local paths and URLs
        
        :param image_path_or_url: Path or URL of the image
        :return: SDL texture or None if loading fails
        """
        # If image_path_or_url is None, use default image
        if image_path_or_url is None:
            return self._load_texture_from_path(Config.DEFAULT_IMAGE_PATH, "default_image")
            
        # Update last used timestamp for cache management
        current_time = sdl2.SDL_GetTicks()
        
        # Check if texture is already loaded
        if image_path_or_url in self.textures:
            self.texture_last_used[image_path_or_url] = current_time
            return self.textures[image_path_or_url]

        # Check if we need to free up some textures
        if len(self.textures) >= self.max_textures:
            self._free_least_used_textures(1)  # Free at least one texture
        
        # Handle URL images
        if image_path_or_url.startswith(('http://', 'https://')):
            # If this is the URL we're currently loading and we have a cached path
            if image_path_or_url == self.current_loading_texture and self.cached_image_path:
                # Load the texture from the cached path
                texture = self._load_texture_from_path(self.cached_image_path, image_path_or_url)
                if texture:
                    self.current_loading_texture = None
                    self.cached_image_path = None
                    return texture
                return None
            
            # If no download is in progress, start one
            if self.download_thread is None or not self.download_thread.is_alive():
                self.current_loading_texture = image_path_or_url
                self.cached_image_path = None
                self.download_thread = threading.Thread(
                    target=self._download_image,
                    args=(image_path_or_url,),
                    daemon=True
                )
                self.download_thread.start()
            return None
        
        else:
            # Load local textures
            image_path = os.path.join(Config.IMAGES_CONSOLES_DIR, image_path_or_url)
            return self._load_texture_from_path(image_path, image_path_or_url)

    def _download_image(self, image_url: str):
        """Download image in a separate thread"""
        try:
            cached_path = ImageCache.download_image(image_url)
            if cached_path:
                # Store the cached path - texture will be loaded on next get_texture call
                self.cached_image_path = cached_path
            else:
                # If download failed, reset states
                self.current_loading_texture = None
                self.cached_image_path = None
        except Exception as e:
            logger.error(f"Error downloading image from URL {image_url}: {str(e)}")
            self.current_loading_texture = None
            self.cached_image_path = None

    def _load_texture_from_path(self, image_path: str, key: str) -> Optional[sdl2.SDL_Texture]:
        """Load a texture from a local file path"""
        try:
            surface = sdl2.sdlimage.IMG_Load(image_path.encode('utf-8'))
            if not surface:
                logger.error(f"Failed to load image surface: {image_path}. SDL_image error: {sdl2.sdlimage.IMG_GetError().decode('utf-8')}")
                return None

            texture = sdl2.SDL_CreateTextureFromSurface(self.renderer, surface)
            sdl2.SDL_FreeSurface(surface)

            if not texture:
                logger.error(f"Failed to create texture from image: {image_path}")
                return None

            # Store texture
            self.textures[key] = texture
            self.texture_last_used[key] = sdl2.SDL_GetTicks()
            return texture

        except Exception as e:
            logger.error(f"Texture loading error for {image_path}: {e}")
            return None

    def _free_least_used_textures(self, count=1):
        """
        Free the least recently used textures
        
        :param count: Number of textures to free
        """
        if not self.textures:
            return
        
        # Sort textures by last used time
        sorted_textures = sorted(
            self.texture_last_used.items(), 
            key=lambda x: x[1]
        )
        
        # Free the oldest textures
        for i in range(min(count, len(sorted_textures))):
            texture_path = sorted_textures[i][0]
            if texture_path in self.textures:
                sdl2.SDL_DestroyTexture(self.textures[texture_path])
                del self.textures[texture_path]
                del self.texture_last_used[texture_path]
                logger.debug(f"Freed texture: {texture_path}")

    def cleanup(self):
        """Clean up all loaded textures"""
        try:
            # Wait for any ongoing download to complete
            if self.download_thread and self.download_thread.is_alive():
                self.download_thread.join(timeout=2.0)
            
            # Destroy all textures
            for texture in list(self.textures.values()):  # Create a copy of values to iterate
                if texture:
                    try:
                        sdl2.SDL_DestroyTexture(texture)
                    except Exception as e:
                        logger.error(f"Error destroying texture: {str(e)}")
            
            # Clear all tracking collections
            self.textures.clear()
            self.texture_last_used.clear()
            self.current_loading_texture = None
            self.cached_image_path = None
            
            logger.info("TextureManager cleanup completed successfully")
            
        except Exception as e:
            logger.error(f"Error during TextureManager cleanup: {str(e)}")
            raise 