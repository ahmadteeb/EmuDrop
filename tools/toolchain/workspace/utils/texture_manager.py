import os
import random
import sdl2
import sdl2.sdlimage
import logging
from typing import Dict, Optional
from utils.logger import logger
from PIL import Image, ImageDraw # type: ignore
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

    def get_texture(self, image_path_or_url: str) -> Optional[sdl2.SDL_Texture]:
        """
        Get SDL texture for an image, supporting local paths and URLs
        
        :param image_path_or_url: Path or URL of the image
        :return: SDL texture or None if loading fails
        """
        # Update last used timestamp for cache management
        current_time = sdl2.SDL_GetTicks()
        
        # Check if texture is already loaded
        if image_path_or_url in self.textures:
            self.texture_last_used[image_path_or_url] = current_time
            return self.textures[image_path_or_url]

        # Check if we need to free up some textures
        if len(self.textures) >= self.max_textures:
            self._free_least_used_textures(1)  # Free at least one texture

        # Determine if it's a URL or local path
        if image_path_or_url.startswith(('http://', 'https://')):
            # Download and cache URL image
            cached_image_path = ImageCache.download_image(image_path_or_url)
            if not cached_image_path:
                logger.error(f"Failed to download image: {image_path_or_url}")
                return None
            image_path = cached_image_path
        else:
            # Use local path
            image_path = os.path.join(Config.IMAGES_CONSOLES_DIR, image_path_or_url)

        # Load texture
        try:
            surface = sdl2.sdlimage.IMG_Load(image_path.encode('utf-8'))
            if not surface:
                logger.error(f"Failed to load image surface: {image_path}")
                return None

            texture = sdl2.SDL_CreateTextureFromSurface(self.renderer, surface)
            sdl2.SDL_FreeSurface(surface)

            if not texture:
                logger.error(f"Failed to create texture from image: {image_path}")
                return None

            # Store texture
            self.textures[image_path_or_url] = texture
            return texture

        except Exception as e:
            logger.error(f"Texture loading error for {image_path}: {e}")
            return None

    def cleanup(self):
        """Clean up all loaded textures"""
        for texture in self.textures.values():
            sdl2.SDL_DestroyTexture(texture)
        self.textures.clear()

        # Optional: Clear old image cache
        ImageCache.clear_old_cache()

    def _get_placeholder_texture(self, image_path: str) -> Optional[sdl2.SDL_Texture]:
        """
        Create a placeholder texture for missing images
        
        :param image_path: Path where placeholder image will be saved
        :return: SDL texture of the placeholder
        """
        # Check placeholder cache
        if image_path in self.placeholder_cache:
            return self.placeholder_cache[image_path]
        
        try:
            # Create a new image with a random background color
            img = Image.new('RGB', (200, 300), 
                            color=(random.randint(50, 200), 
                                   random.randint(50, 200), 
                                   random.randint(50, 200)))
            
            # Draw text on the image
            draw = ImageDraw.Draw(img)
            draw.text((10, 10), os.path.splitext(os.path.basename(image_path))[0], 
                      fill=(255, 255, 255))
            
            # Save the image
            img.save(image_path)
            
            # Load the placeholder image as a texture
            surface = sdl2.sdlimage.IMG_Load(image_path.encode('utf-8'))
            texture = sdl2.SDL_CreateTextureFromSurface(self.renderer, surface)
            sdl2.SDL_FreeSurface(surface)
            
            if texture:
                self.placeholder_cache[image_path] = texture
                return texture
        except Exception as e:
            logger.error(f"Placeholder texture error: {e}")
        
        return None 

    def create_texture_from_pil_image(self, pil_image):
        """
        Create an SDL texture from a PIL Image
        
        :param pil_image: PIL Image object
        :return: SDL texture or None if conversion fails
        """
        try:
            # Ensure image is in RGBA mode
            if pil_image.mode != 'RGBA':
                pil_image = pil_image.convert('RGBA')
            
            # Get image dimensions
            width, height = pil_image.size
            
            # Convert PIL image to bytes
            image_data = pil_image.tobytes()
            
            # Create SDL surface
            surface = sdl2.SDL_CreateRGBSurfaceFrom(
                image_data,
                width, 
                height, 
                32,  # bits per pixel
                width * 4,  # pitch (bytes per row)
                0x000000FF,  # R mask
                0x0000FF00,  # G mask
                0x00FF0000,  # B mask
                0xFF000000   # A mask
            )
            
            if not surface:
                logger.error(f"Failed to create SDL surface from PIL image")
                return None
            
            # Create texture from surface
            texture = sdl2.SDL_CreateTextureFromSurface(self.renderer, surface)
            
            # Free the surface
            sdl2.SDL_FreeSurface(surface)
            
            if not texture:
                logger.error(f"Failed to create texture from SDL surface")
                return None
            
            return texture
        
        except Exception as e:
            logger.error(f"Error creating texture from PIL image: {e}")
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