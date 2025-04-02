import os
import requests
import hashlib
from typing import Tuple
import base64
import re
import urllib3
from utils.config import Config

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class ScreenScraper:
    def __init__(self):
        # Base paths
        self.media_type = 'box-2D'  # default value
        self.user_ss = ''
        self.pass_ss = ''
        
        # API credentials
        self.u = self._decode_base("KUZE433CLBLHSZCIOB2AU===")
        self.p = self._decode_base("KZEFMTCTIRBHMWJQN55GKSCRGFKGOPJ5BI======")
        
        # Setup session with SSL verification disabled
        self.session = requests.Session()
        self.session.verify = False

    def _decode_base(self, encoded_str: str) -> str:
        """Decode base32 then base64 string"""
        return base64.b64decode(base64.b32decode(encoded_str)).decode()

    def _get_system_id(self, system: str) -> str:
        """Get ScreenScraper system ID"""
        system_ids = {
            'ADVMAME': '75',    # Mame
            'AMIGA': '64',      # Commodore Amiga
            'AMIGACD': '134',   # Commodore Amiga CD
            'ARCADE': '75',     # Mame
            'FC': '3',          # NES (Famicom)
            'GB': '9',          # Game Boy
            'GBA': '12',        # Game Boy Advance
            'GBC': '10',        # Game Boy Color
            'MD': '1',          # Sega Genesis
            'N64': '14',        # Nintendo 64
            'NDS': '15',        # Nintendo DS
            'PS': '57',         # PlayStation
            'PSP': '61',        # Added PSP
            'SFC': '4',         # Super Nintendo
        }
        return system_ids.get(system, '')

    def scrape_rom(self, rom_name: str, system: str) -> Tuple[bool, str]:
        """
        Scrape a single ROM file
        Args:
            rom_name: ROM filename
            system: System identifier (e.g., 'SFC', 'PS', etc.)
        Returns:
            Tuple[bool, str]: (success, message)
        """
        rom_name_no_ext = os.path.splitext(rom_name)[0]
        img_name = f"{rom_name_no_ext}.png"
        
        # Check if already scraped
        target_image = os.path.join(Config.IMGS_DIR, system, img_name)
        if os.path.exists(target_image):
            return True, "Already scraped"

        # Clean up name
        rom_name_trimmed = rom_name_no_ext
        for remove in ['nkit', '!', '&', 'Disc ', 'Rev ']:
            rom_name_trimmed = rom_name_trimmed.replace(remove, '')
        
        # Remove content in parentheses and brackets
        rom_name_trimmed = re.sub(r'\([^)]*\)', '', rom_name_trimmed)
        rom_name_trimmed = re.sub(r'\[[^\]]*\]', '', rom_name_trimmed)
        rom_name_trimmed = rom_name_trimmed.replace(' - ', '%20').replace('-', '%20').replace(' ', '%20')

        # Get ROM size
        try:
            rom_size = os.path.getsize(os.path.join(Config.ROMS_DIR, system, rom_name))
        except Exception:
            return False, "Could not get ROM size"

        # Try name-based search first
        system_id = self._get_system_id(system)
        url = (
            f"https://www.screenscraper.fr/api2/jeuInfos.php?"
            f"devid={self.u[:-1]}&devpassword={self.p[2:]}"
            f"&softname=crossmix&output=json"
            f"&ssid={self.user_ss}&sspassword={self.pass_ss}"
            f"&sha1=&systemeid={system_id}&romtype=rom"
            f"&romnom={rom_name_trimmed}.zip&romtaille={rom_size}"
        )

        try:
            response = self.session.get(url)  # Using session instead of direct requests
            if not response.ok:
                return False, "API request failed"
            
            data = response.json()
            if 'error' in data:
                # If name search fails, try SHA1
                if rom_size <= 52428800:  # 50MB limit
                    sha1 = hashlib.sha1()
                    with open(os.path.join('Roms', system, rom_name), 'rb') as f:
                        for chunk in iter(lambda: f.read(4096), b''):
                            sha1.update(chunk)
                    
                    url = (
                        f"https://www.screenscraper.fr/api2/jeuInfos.php?"
                        f"devid={self.u[:-1]}&devpassword={self.p[2:]}"
                        f"&softname=crossmix&output=json"
                        f"&ssid={self.user_ss}&sspassword={self.pass_ss}"
                        f"&sha1={sha1.hexdigest()}&systemeid=&romtype=rom"
                        f"&romnom={rom_name_trimmed}.zip&romtaille={rom_size}"
                    )
                    
                    response = self.session.get(url)  # Using session instead of direct requests
                    if not response.ok:
                        return False, "SHA1 search failed"
                    data = response.json()
                    if 'error' in data:
                        return False, "Game not found"
                else:
                    return False, "ROM too large for checksum"

            # Get media URL
            if 'response' not in data or 'jeu' not in data['response']:
                return False, "Invalid API response"

            medias = data['response']['jeu']['medias']
            media_url = None
            for media in medias:
                if media['type'] == self.media_type:
                    media_url = media['url']
                    break

            if not media_url:
                return False, "No media found"

            # Download image
            media_url = f"{media_url}&maxwidth=400&maxheight=580"
            os.makedirs(os.path.dirname(target_image), exist_ok=True)
            
            img_response = self.session.get(media_url)  # Using session instead of direct requests
            if not img_response.ok:
                return False, "Image download failed"

            with open(target_image, 'wb') as f:
                f.write(img_response.content)

            return True, "Successfully scraped"

        except Exception as e:
            return False, f"Error: {str(e)}"