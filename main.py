import argparse
import os

import requests
from bs4 import BeautifulSoup
from pathvalidate import sanitize_filename
from urllib.parse import urljoin

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


def download_book(response, directory, title, book_id):
    with open(
            os.path.join(
                directory,
                f'{title} {book_id}.txt'),
            'w',
    ) as file:
        file.write(response.text)


def download_image(response, directory, image_name):
    with open(os.path.join(directory, f'{image_name}'), 'wb') as file:
        file.write(response.content)


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Парсер онлайн-библиотеки'
    )
    parser.add_argument(
        '--start_id',
        default=1,
        type=int,
        help='Начать скачивать с №...',
    )
    parser.add_argument(
        '--end_id',
        type=int,
        help='Остановить скачивание на №...',
    )
    args = parser.parse_args()
    start = args.start_id
    end = args.end_id if args.end_id else args.start_id + 1
    return start, end


if __name__ == '__main__':
    os.makedirs(BOOK_DIR, exist_ok=True)
    os.makedirs(IMAGE_DIR, exist_ok=True)
    start_id, end_id = parse_arguments()
    for id_ in range(start_id, end_id):
        payload = {
            'id': id_
        }
        book_url = f'https://tululu.org/txt.php'
        book_response = requests.get(
            book_url,
            params=payload,
            allow_redirects=False,
        )
        try:
            book_response.raise_for_status()
        except requests.HTTPError:
            print('Errors on the client or server side')
            continue
        except requests.ConnectionError:
            print('Connection error occurs! Trying next book...')
            continue
        try:
            check_for_redirect(book_response)
        except requests.TooManyRedirects:
            print(f'There isn`t book with ID {id_}. Redirect detected!')
            continue
        book_page_url = f'https://tululu.org/b{id_}/'
        book_page_response = requests.get(book_page_url)
        try:
            book_page_response.raise_for_status()
        except requests.HTTPError:
            print('Errors on the client or server side')
            continue
        except requests.ConnectionError:
            print('Connection error occurs! Trying next book...')
            continue
        try:
            check_for_redirect(book_page_response)
        except requests.TooManyRedirects:
            print(f'There isn`t page for book with ID {id_}. Redirect '
                  f'detected!')
            continue
        book_properties = parse_book_page(book_page_response)
        book_title = book_properties['title']
        book_author = book_properties['author']
        book_image_url = book_properties['image_url']
        book_comments = book_properties['comments']
        book_genres = book_properties['genres']
        book_image_name = os.path.basename(book_image_url)
        download_book(book_response, BOOK_DIR, book_title, id_)
        book_image_response = requests.get(book_image_url)
        book_image_response.raise_for_status()
        download_image(book_image_response, IMAGE_DIR, book_image_name)
