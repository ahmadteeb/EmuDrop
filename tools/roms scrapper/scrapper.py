import requests, json
from bs4 import BeautifulSoup

base_url = "https://www.consoleroms.com"

session = requests.session()

def extract_games(page_url):
    print(page_url)
    game_grid_request = session.get(f'{page_url}')
    soup = BeautifulSoup(game_grid_request.text, 'html.parser')
    game_grid = soup.find_all('div', attrs={'class': "thumbnail-home"})
    print(f"{len(game_grid)} Games to be extracted")
    games = []
    for game in game_grid:
        game_name = game.find('strong').text
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
            'image_url': image_url,
            'game_url': download_url
        })

    return games

def extract_pages(category_url):
    category_request = session.get(f"{base_url}{category_url}")
    soup = BeautifulSoup(category_request.text, 'html.parser')
    pages = None
    try:
        pages = int(soup.find('ul', attrs={'class': "pagination"}).find_all('li')[-1].find('a').get('href').split('/')[-1])
    except AttributeError:
        pages = 1
    print(f"Extracting games from {category_url}")
    print(f"{pages} Pages to be extracted")
    games = []
    for index in range(1, pages+1):
        print(f"Page: {index}")
        page_url = f"{base_url}{category_url}page/{index}"
        page_games = extract_games(page_url)
        games += page_games
        
        # Update catalog after each page
        for cate in catalog:
            if cate.get('page', None) == category_url:
                cate_index = catalog.index(cate)
                catalog[cate_index]['games'] = games
                
                # Save catalog after each page
                with open('catalog.json', 'w') as f:
                    json.dump(catalog, f, indent=2)
                break
    return games


with open('consoles.json', 'r') as f:
    catalog = json.loads(f.read())

for cate in catalog:
    print(cate)
    # Extract and save games for the category
    cate['games'] = extract_pages(cate['page'])
    
    del cate['page']
    # Final save for the category
    with open('catalog.json', 'w') as f:
        json.dump(catalog, f, indent=2)

# Optional: final save with indentation for readability
with open('catalog.json', 'w') as f:
    json.dump(catalog, f, indent=2)