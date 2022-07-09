import os

import requests
from bs4 import BeautifulSoup
from pathvalidate import sanitize_filename
from urllib.parse import urljoin

BOOK_DIR = 'books'
IMAGE_DIR = 'images'


def get_book_attributes(book_id):
    url = f'https://tululu.org/b{book_id}/'
    book_page_response = requests.get(url)
    soup = BeautifulSoup(book_page_response.text, 'lxml')
    book_attributes = soup.find('div', id="content").find('h1').text
    book_title, book_author = book_attributes.split('::')
    book_title = sanitize_filename(book_title.strip())
    book_author = book_author.strip()
    book_image = soup.find('div', class_="bookimage").find('img')
    book_image_url = urljoin(book_page_response.url, book_image['src'])
    return book_title, book_author, book_image_url


def get_book(book_id):
    url = f'https://tululu.org/txt.php?id={book_id}'
    response = requests.get(url, allow_redirects=False)
    response.raise_for_status()
    return response


def get_book_image(url):
    response = requests.get(url)
    response.raise_for_status()
    return response.content


def check_for_redirect(response):
    if 300 <= response.status_code < 400:
        raise requests.HTTPError


if __name__ == '__main__':
    os.makedirs(BOOK_DIR, exist_ok=True)
    os.makedirs(IMAGE_DIR, exist_ok=True)
    for id_ in range(1, 11):
        try:
            book = get_book(id_)
            check_for_redirect(book)
            title, author, image_url = get_book_attributes(id_)
            image_name = os.path.basename(image_url)
        except requests.HTTPError:
            continue
        with open(os.path.join(BOOK_DIR, f'{title} ({id_}).txt'), 'w') as file:
            file.write(book.text)
        with open(os.path.join(IMAGE_DIR, f'{image_name}'), 'wb') as file:
            file.write(get_book_image(image_url))
