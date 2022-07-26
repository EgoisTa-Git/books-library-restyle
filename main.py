import argparse
import os
from time import sleep

import requests
from bs4 import BeautifulSoup
from pathvalidate import sanitize_filename
from urllib.parse import urljoin, urlparse

BOOK_DIR = 'books'
IMAGE_DIR = 'images'


def parse_book_page(response):
    soup = BeautifulSoup(response.text, 'lxml')
    attributes = soup.find('div', id="content").find('h1').text
    title, author = attributes.split('::')
    image = soup.find('div', class_="bookimage").find('img')
    comments_block = soup.find_all('div', class_='texts')
    comments = [
        comment.find('span', class_='black').text for comment in comments_block
    ]
    genres_block = soup.find('span', class_="d_book").find_all('a')
    genres = [genre.text for genre in genres_block]
    properties = {
        'title': sanitize_filename(title.strip()),
        'author': author.strip(),
        'image_url': urljoin(response.url, image['src']),
        'comments': comments,
        'genres': genres,
    }
    return properties


def check_for_redirect(response):
    if 300 <= response.status_code < 400:
        raise requests.TooManyRedirects


def download_book(url, book_id, directory, title):
    payload = {
        'id': book_id
    }
    response = requests.get(url, params=payload, allow_redirects=False)
    response.raise_for_status()
    check_for_redirect(response)
    file_path = os.path.join(directory, f'{title} {book_id}.txt')
    with open(file_path, 'w',) as file:
        file.write(response.text)


def download_image(image_url, directory):
    image_response = requests.get(image_url)
    image_response.raise_for_status()
    image_name = os.path.basename(image_url)
    image_path = os.path.join(directory, f'{image_name}')
    with open(image_path, 'wb') as file:
        file.write(image_response.content)


def get_urls_from_page(response):
    urls = []
    soup = BeautifulSoup(response.text, 'lxml')
    book_tags = soup.find_all('table', class_='d_book')
    for tag in book_tags:
        short_url = tag.find('div', class_='bookimage').find('a')['href']
        url = urljoin(response.url, short_url)
        urls.append(url)
    return urls


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Парсер онлайн-библиотеки'
    )
    parser.add_argument(
        '--start',
        default=1,
        type=int,
        help='Начать скачивать со страницы №...',
    )
    parser.add_argument(
        '--end',
        type=int,
        help='Остановить скачивание на странице №...',
    )
    args = parser.parse_args()
    start = args.start
    end = args.end if args.end else args.start + 1
    return start, end


if __name__ == '__main__':
    os.makedirs(BOOK_DIR, exist_ok=True)
    os.makedirs(IMAGE_DIR, exist_ok=True)
    category_url = 'https://tululu.org/l55/'
    book_url = 'https://tululu.org/txt.php'
    start_page, end_page = parse_arguments()
    for page in range(start_page, end_page):
        page_url = urljoin(category_url, str(page))
        print(f'Parsing {page_url}')
        book_response = requests.get(page_url)
        book_response.raise_for_status()
        book_page_urls = get_urls_from_page(book_response)
        for book_page_url in book_page_urls:
            id_ = urlparse(book_page_url).path.strip('/')[1:]
            connection = False
            while not connection:
                try:
                    print(f'Downloading book # {id_}...')
                    book_page_response = requests.get(
                        book_page_url,
                        allow_redirects=False,
                    )
                    book_page_response.raise_for_status()
                    check_for_redirect(book_page_response)
                    book_properties = parse_book_page(book_page_response)
                    download_book(
                        book_url,
                        id_,
                        BOOK_DIR,
                        book_properties['title'],
                    )
                    download_image(book_properties['image_url'], IMAGE_DIR)
                    connection = True
                except requests.HTTPError:
                    print('Errors on the client or server side')
                    break
                except requests.ConnectionError:
                    print('Connection error occurs! Trying to get book...')
                    sleep(5)
                except requests.TooManyRedirects:
                    print(f'There isn`t book with ID {id_}. Redirect detected')
                    break
