import requests, json
from bs4 import BeautifulSoup

base_url = "https://www.consoleroms.com"

session = requests.session()

def extract_games(page_url):
    print(page_url)
    game_grid_request = session.get(f'{page_url}')
    soup = BeautifulSoup(game_grid_request.text, 'html.parser')
    game_grid = list(set(soup.find_all('div', attrs={'class': "thumbnail-home"})))
    print(f"{len(game_grid)} Games to be extracted")
    games = []
    for game in game_grid:
        game_name = game.find('strong').text.replace('Download', '').replace('Rom', '').replace('ROM', '').strip()
        print(f"Extracting data from {game_name}")
        game_url = game.find('div', attrs={'class': 'imgCon'}).find('a').get('href')
        image_url = game.find('img').get('src')
        if image_url is None:
            image_url = game.find('img').get('data-src')
        game_request = session.get(f"{base_url}{game_url}")
        game_soup = BeautifulSoup(game_request.text, 'html.parser')
        download_request_url = game_soup.find('a', attrs={'id': "btnDownload"}).get('href')
        download_request = session.get(f"{base_url}{download_request_url}")
        download_soup = BeautifulSoup(download_request.text, 'html.parser')
        download_url = download_soup.find('a', attrs={'rel': "nofollow"}).get('href')

        games.append({
            'name': game_name.lstrip().rstrip(),
            'image_url': image_url if image_url.startswith(('https://', 'http://')) else 'default_image.png',
            'game_url': download_url
        })

    return games

def extract_pages(platform_url):
    platform_request = session.get(f"{base_url}{platform_url}")
    soup = BeautifulSoup(platform_request.text, 'html.parser')
    pages = None
    try:
        pages = int(soup.find('ul', attrs={'class': "pagination"}).find_all('li')[-1].find('a').get('href').split('/')[-1])
    except AttributeError:
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
            'source_name': "ConsolesRom",
            'games': extract_pages(cate['page'])
        }
    )
    
    del cate['page']
# Final save for the platform
with open('catalog.json', 'w', encoding="utf-8") as f:
    json.dump(catalog, f, indent=2, ensure_ascii=False)

