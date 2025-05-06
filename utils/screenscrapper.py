import requests
import urllib3
import hashlib
import base64
import os
import shutil
import re
from utils.config import Config
from utils.image_cache import ImageCache
from utils.logger import logger

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class ScreenScraper:
    def __init__(self):
        # API credentials
        self.media_type = os.environ['SCRAPER_API_MEDIA_TYPE']
        self.softname = os.environ['SCRAPER_API_SOFTNAME']
        self.u = self._decode_base(os.environ['SCRAPER_ENCODED_API_USERNAME'])
        self.p = self._decode_base(os.environ['SCRAPER_ENCODED_API_PASSWORD'])
        self.user_ss = os.environ.get('SCRAPER_API_USERSSID', '')
        self.pass_ss = os.environ.get('SCRAPER_API_SSPASS', '')
        
        # Setup session with SSL verification disabled
        self.session = requests.Session()
        self.session.verify = False
        
    def _decode_base(self, encoded_str: str) -> str:
            """Decode base32 then base64 string"""
            return base64.b64decode(base64.b32decode(encoded_str)).decode()
    
    def _compute_md5(self, file_path):
        md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                md5.update(chunk)
        return md5.hexdigest()
    
    def _trim_file_name(self, file_name_no_ext):
        # Clean up name
        trimed_file_name = file_name_no_ext
        for remove in ['nkit', '!', '&', 'Disc ', 'Rev ', 'Rom']:
            trimed_file_name = trimed_file_name.replace(remove, '')
        
        # Remove content in parentheses and brackets
        trimed_file_name = re.sub(r'\([^)]*\)', '', trimed_file_name)
        trimed_file_name = re.sub(r'\[[^\]]*\]', '', trimed_file_name)
        trimed_file_name = trimed_file_name.replace(' - ', '%20').replace('-', '%20').replace(' ', '%20')
        return trimed_file_name
    
    def _get_system_id(self, system: str) -> str:
            """Get ScreenScraper system ID"""
            system_ids = {
                "ADVMAME":            "75",    # Mame
                "AMIGA":              "64",    # Commodore Amiga
                "AMIGACD":            "134",   # Commodore Amiga CD
                "AMIGACDTV":          "129",   # Commodore Amiga CD
                "ARCADE":             "75",    # Mame
                "ARDUBOY":            "263",   # Arduboy
                "ATARI2600":          "26",    # Atari 2600
                "ATARIST":            "42",    # Atari ST
                "ATOMISWAVE":         "53",    # Atari ST
                "COLECO":             "183",   # Coleco
                "COLSGM":             "183",   # Coleco
                "C64":                "66",    # Commodore 64
                "CPC":                "65",    # Amstrad CPC
                "CPET":               "240",   # Commodore PET
                "CPLUS4":             "99",    # Commodore Plus 4
                "CPS1":               "6",     # Capcom Play System
                "CPS2":               "7",     # Capcom Play System 2
                "CPS3":               "8",     # Capcom Play System 3
                "DAPHNE":             "49",    # Daphne
                "DC":                 "23",    # dreamcast
                "DOS":                "135",   # DOS
                "EASYRPG":            "231",   # EasyRPG
                "EBK":                "93",    # EBK
                "ATARI800":           "43",    # Atari 800
                "CHANNELF":           "80",    # Fairchild Channel F
                "FBA2012":            "75",    # FBA2012
                "FBALPHA":            "75",    # FBAlpha
                "FC":                 "3",     # NES (Famicom)
                "FDS":                "106",   # Famicom Disk System
                "ATARI5200":          "40",    # Atari 5200
                "GB":                 "9",     # Game Boy
                "GBA":                "12",    # Game Boy Advance
                "GBC":                "10",    # Game Boy Color
                "GG":                 "21",    # Sega Game Gear
                "GW":                 "52",    # Nintendo Game & Watch
                "INTELLIVISION":      "115",   # Intellivision
                "JAGUAR":             "27",    # Atari Jaguar
                "LOWRESNX":           "244",   # LowRes NX
                "LUTRO":              "206",   # Lutro
                "LYNX":               "28",    # Atari Lynx
                "MAME":               "75",    # Mame 2000
                "MAME2003PLUS":       "75",    # Mame 2003
                "MAME2010":           "75",    # Mame 2003
                "MBA":                "75",    # MBA
                "MD":                 "1",     # Sega Genesis (Mega Drive)
                "MDMSU":              "1",     # Sega Genesis (Mega Drive) Hacks
                "MEGADUCK":           "90",    # Megaduck
                "MS":                 "2",     # Sega Master System
                "MSX":                "113",   # MSX
                "MSX2":               "116",   # MSX
                "N64":                "14",    # Nintendo 64
                "N64DD":              "122",   # Nintendo 64DD
                "NAOMI":              "56",    # Sega Naomi
                "NDS":                "15",    # NDS
                "NEOCD":              "70",    # Neo Geo CD
                "NEOGEO":             "142",   # Neo Geo AES
                "NGP":                "25",    # Neo Geo Pocket
                "NGC":                "82",    # Neo-geo Pocket Color
                "ODYSSEY":            "104",   # Videopac / Magnavox Odyssey 2
                "OPENBOR":            "214",   # OpenBOR
                "PALMOS":             "219",   # Palm
                "PANASONIC":          "29",    # 3DO
                "PCE":                "31",    # NEC TurboGrafx-16 / PC Engine
                "PCECD":              "114",   # NEC TurboGrafx-CD
                "PC88":               "221",   # NEC PC-8000 & PC-8800 series / NEC PC-8801
                "PCFX":               "72",    # NEC PC-FX
                "PC98":               "208",   # NEC PC-98 / NEC PC-9801
                "PICO":               "234",   # PICO
                "POKEMINI":           "211",   # PokeMini
                "PORTS":              "137",   # PC Win9X
                "PS":                 "57",    # Sony Playstation
                "PSP":                "61",    # Sony PSP
                "PSPMINIS":           "172",   # Sony PSP Minis
                "SATURN":             "22",    # Sony PSP Minis
                "SATELLAVIEW":        "107",   # Satellaview
                "SCUMMVM":            "123",   # ScummVM
                "SEGACD":             "20",    # Sega CD
                "SG1000":             "109",   # Sega SG-1000
                "ATARI7800":          "41",    # Atari 7800
                "SFC":                "4",     # Super Nintendo (SNES)
                "SFCMSU":             "4",     # Super Nintendo (SNES) hacks
                "SGB":                "127",   # Super Game Boy
                "SFX":                "105",   # NEC PC Engine SuperGrafx
                "SUFAMI":             "108",   # Sufami Turbo
                "WS":                 "207",   # Watara Supervision
                "WSC":                "207",   # Watara Supervision
                "SEGA32X":            "19",    # Sega 32X
                "SFX":                "19",    # Sega 32X
                "THOMSON":            "141",   # Thomson
                "TIC":                "222",   # TIC-80
                "UZEBOX":             "216",   # Uzebox
                "VB":                 "11",    # Virtual Boy
                "VECTREX":            "102",   # Vectrex
                "VIC20":              "73",    # Commodore VIC-20
                "VIDEOPAC":           "104",   # Videopac
                "VMU":                "23",    # Dreamcast VMU (useless)
                "WS":                 "45",    # Bandai WonderSwan & Color
                "X68000":             "79",    # Sharp X68000
                "X1":                 "220",   # Sharp X1
                "ZXEIGHTYONE":        "77",    # Sinclair ZX-81
                "ZXS":                "76"    # Sinclair ZX Spectrum
            }
            return system_ids.get(system, '')
    
    def _extract_media_url(self, data):
        if 'response' in data and 'jeu' in data['response']:
                medias = data['response']['jeu']['medias']
                media_url = None
                for media in medias:
                    if media['type'] == self.media_type:
                        media_url = f"{media['url']}&maxwidth=400&maxheight=580"
                        break
                return media_url
    
    def _scrape_using_file_hash(self, file_path, system):
        url = "https://www.screenscraper.fr/api2/jeuInfos.php"
        params = {
            "md5": self._compute_md5(file_path),
            "devid": self.u[:-1],              # Dev ID, use 1 for testing or register your own
            "devpassword": self.p[2:],
            "softname": self.softname,     # Name of your app/tool
            "ssid": self.user_ss,
            "sspassword": self.pass_ss,
            "output": "json",
            "systemeid": self._get_system_id(system),
            "romtype":"rom"
        }
        
        response = self.session.get(url, params=params)
        if response.ok:
            data = response.json()
            return self._extract_media_url(data)
    
    def _scrape_using_file_name(self, trimed_file_name, system):
        url = "https://www.screenscraper.fr/api2/jeuInfos.php"
        params = {
            "romnom": f"{trimed_file_name}.zip",
            "devid": self.u[:-1],              # Dev ID, use 1 for testing or register your own
            "devpassword": self.p[2:],
            "softname": self.softname,     # Name of your app/tool
            "ssid": self.user_ss,
            "sspassword": self.pass_ss,
            "output": "json",
            "systemeid": self._get_system_id(system),
            "romtype":"rom"
        }

        response = self.session.get(url, params=params)
        if response.ok:
            data = response.json()
            return self._extract_media_url(data)

    
    def scrape_rom(self, image_url, file_name, system):
        file_name_no_ext, _ = os.path.splitext(file_name)
        image_name = f"{file_name_no_ext}.png"
        target_image = os.path.join(os.environ['IMGS_DIR'], system, image_name)
        
        os.makedirs(os.path.dirname(target_image), exist_ok=True)
        
        if os.path.exists(target_image):
            return "Already scraped"
        
        try:
            logger.info("Trying to scrape by hashing the file")
            file_path = os.path.join(os.environ['ROMS_DIR'], system, file_name)
            media_url = self._scrape_using_file_hash(file_path, system)
            
            if not media_url:
                logger.info("Trying to scrape using file name")
                trimed_file_name = self._trim_file_name(file_name_no_ext)
                media_url = self._scrape_using_file_name(trimed_file_name, system)
            
            if not media_url:
                raise
            
            image_response = self.session.get(media_url)
            if not image_response.ok:
                raise
            
            with open(target_image, 'wb') as f:
                f.write(image_response.content)    
            
            return "Successfully scraped from scrapper"
        
        except Exception as e:
            logger.warning(f"Somthing went wrong while scraping from scrapper: {e}")
            image_path = ImageCache.download_image(image_url)
            shutil.copy(image_path, target_image)
            return "Successfully scraped from cache"