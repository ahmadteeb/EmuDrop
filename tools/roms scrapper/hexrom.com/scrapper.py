import requests, json
from bs4 import BeautifulSoup

base_url = "https://www.hexrom.com"

session = requests.session()

def extract_games(page_url):
    print(page_url)
    game_grid_request = session.get(f'{page_url}')
    soup = BeautifulSoup(game_grid_request.text, 'html.parser')
    game_grid = list(set(soup.find_all('div', attrs={'class': "custom-card"})))
    print(f"{len(game_grid)} Games to be extracted")
    games = []
    for game in game_grid:
        try:
            game_name = game.find('h2').text.replace('Download', '').replace('Rom', '').replace('ROM', '').strip()
            print(f"Extracting data from {game_name}")
            game_url = game.find('a').get('href') + "download"
            image_url = game.find('img').get('data-src')
            
            if image_url == "https://hexrom.com/images/icon/n/nocover.jpg" or image_url.startswith(('https://', 'http://')):
                image_url = None
            
            game_request = session.get(game_url)
            game_soup = BeautifulSoup(game_request.text, 'html.parser')
        
            download_url = game_soup.find('a', attrs={'class': "dlbi"}).get('href')
            games.append({
            'name': game_name.lstrip().rstrip(),
            'image_url': image_url,
            'game_url': download_url
        })
        except AttributeError:
            pass
        
    return games

def extract_pages(platform_url):
    platform_request = session.get(f"{base_url}{platform_url}")
    soup = BeautifulSoup(platform_request.text, 'html.parser')
    pages = None
    try:
        page_request = session.get(f"{base_url}{platform_url}/page/2")
        page_soup = BeautifulSoup(page_request.text, 'html.parser')
        h1 = page_soup.find('h1', string=lambda text: text and 'download rom' in text.lower()).text
        pages = int(h1.split(' | ')[1].split(' of ')[-1])
    except:
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
            'source_name': "HexRom",
            'games': extract_pages(cate['page'])
        }
    )
    
    
    del cate['page']

# Final save for the platform
with open('catalog.json', 'w', encoding="utf-8") as f:
    json.dump(catalog, f, indent=2, ensure_ascii=False)