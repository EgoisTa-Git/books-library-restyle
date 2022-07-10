import argparse
import os

import requests
from bs4 import BeautifulSoup
from pathvalidate import sanitize_filename
from urllib.parse import urljoin

BOOK_DIR = 'books'
IMAGE_DIR = 'images'


def parse_book_page(response):
    data = {}
    soup = BeautifulSoup(response.text, 'lxml')
    attributes = soup.find('div', id="content").find('h1').text
    title, author = attributes.split('::')
    data['title'] = sanitize_filename(title.strip())
    data['author'] = author.strip()
    image = soup.find('div', class_="bookimage").find('img')
    data['image_url'] = urljoin(response.url, image['src'])
    comments_block = soup.find_all('div', class_='texts')
    comments = []
    for comment in comments_block:
        comments.append(comment.find('span', class_='black').text)
    data['comments'] = comments
    genres = []
    genres_block = soup.find('span', class_="d_book").find_all('a')
    for genre in genres_block:
        genres.append(genre.text)
    data['genres'] = genres
    return data


def get_book(book_id):
    url = f'https://tululu.org/txt.php?id={book_id}'
    response = requests.get(url, allow_redirects=False)
    response.raise_for_status()
    return response


def check_for_redirect(response):
    if 300 <= response.status_code < 400:
        raise requests.HTTPError


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
        try:
            book = get_book(id_)
            check_for_redirect(book)
        except requests.HTTPError:
            continue
        book_page_url = f'https://tululu.org/b{id_}/'
        book_page_response = requests.get(book_page_url)
        book_data = parse_book_page(book_page_response)
        book_title = book_data['title']
        book_author = book_data['author']
        book_image_url = book_data['image_url']
        book_comments = book_data['comments']
        book_genres = book_data['genres']
        book_image_name = os.path.basename(book_image_url)
        with open(
                os.path.join(
                    BOOK_DIR,
                    f'{book_title} ({id_}).txt'),
                'w',
        ) as file:
            file.write(book.text)
        with open(os.path.join(IMAGE_DIR, f'{book_image_name}'), 'wb') as file:
            book_image_response = requests.get(book_image_url)
            book_image_response.raise_for_status()
            file.write(book_image_response.content)
