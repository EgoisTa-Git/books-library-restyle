import os

import requests
from bs4 import BeautifulSoup
from pathvalidate import sanitize_filename

BASEDIR = 'books'


def get_book_attributes(book_id):
    url = f'https://tululu.org/b{book_id}/'
    book_page_response = requests.get(url)
    soup = BeautifulSoup(book_page_response.text, 'lxml')
    book_attributes = soup.find('div', id="content").find('h1').text
    book_title, book_author = book_attributes.split('::')
    book_title = sanitize_filename(book_title.strip())
    book_author = book_author.strip()
    return book_title, book_author


def get_book(book_id):
    url = f'https://tululu.org/txt.php?id={book_id}'
    response = requests.get(url, allow_redirects=False)
    response.raise_for_status()
    return response


def check_for_redirect(response):
    if 300 <= response.status_code < 400:
        raise requests.HTTPError


if __name__ == '__main__':
    os.makedirs(BASEDIR, exist_ok=True)
    for id_ in range(1, 11):
        try:
            book = get_book(id_)
            check_for_redirect(book)
            title, author = get_book_attributes(id_)
        except requests.HTTPError:
            continue
        with open(os.path.join(BASEDIR, f'{title} ({id_}).txt'), 'w') as file:
            file.write(book.text)
