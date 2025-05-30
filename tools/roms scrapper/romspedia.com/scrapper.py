import requests, json
from bs4 import BeautifulSoup

base_url = "https://www.romspedia.com"

session = requests.session()

def extract_games(page_url):
    game_grid_request = session.get(f'{page_url}')
    soup = BeautifulSoup(game_grid_request.text, 'html.parser')
    game_grid = soup.find_all('div', attrs={'class': "single-rom"})
    print(f"{len(game_grid)} Games to be extracted")
    games = []
    for game in game_grid:
        try:
            game_name = game.find('div', attrs={'class': "roms-ftr"}).find('a').find('h2').text.strip()
            print(f"Extracting data from {game_name}")
            game_url = game.find('div', attrs={'class': "roms-img"}).find('a').get('href') + "/download?speed=fast"
            image_url = game.find('div', attrs={'class': "roms-img"}).find('a').find('img').get('data-src')
            if image_url is None:
                image_url = game.find('div', attrs={'class': "roms-img"}).find('a').find('img').get('src')
            game_request = session.get(f"{base_url}{game_url}")
            game_soup = BeautifulSoup(game_request.text, 'html.parser')
            download_url = game_soup.find('a', string="click here").get('href')
            games.append({
            'name': game_name.lstrip().rstrip(),
            'image_url': image_url if image_url.startswith(('https://', 'https://')) else None,
            'game_url': f"{download_url}",
        })
        except AttributeError:
            pass
        
    return games

def extract_pages(platform_url):
    platform_request = session.get(f"{base_url}{platform_url}")
    soup = BeautifulSoup(platform_request.text, 'html.parser')
    pages = None
    try:
        pages = int(soup.find_all('li', attrs={'class': 'page-item'})[-1].find('a').get('href').split('/')[-1])
    except IndexError:
        pages = 1
    except ValueError:
        pages = 1
        
    print(f"Extracting games from {platform_url}")
    print(f"{pages} Pages to be extracted")
    games = []
    for index in range(1, pages+1):
        print(f"Page: {index}")
        page_url = f"{base_url}{platform_url}page/{index}"
        page_games = extract_games(page_url)
        games += page_games
    return list({d["name"]: d for d in reversed(games)}.values())[::-1]


with open('consoles.json', 'r') as f:
    catalog = json.loads(f.read())

for cate in catalog:
    print(cate)
    cate['sources'] = []
    # Extract and save games for the platform
    cate['sources'].append(
        {
            'source_name': "RomSpedia",
            'games': extract_pages(cate['page'])
        }
    )
    
    
    del cate['page']
    
# Final save for the platform
with open('catalog.json', 'w', encoding="utf-8") as f:
    json.dump(catalog, f, indent=2, ensure_ascii=False)