import argparse
import json
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
    attributes_selector = '.tabs .ow_px_td h1'
    attributes = soup.select_one(attributes_selector).text
    title, author = attributes.split('::')
    image_selector = '.tabs .ow_px_td .d_book .bookimage img'
    image = soup.select_one(image_selector)
    comment_selector = '.tabs .ow_px_td .texts .black'
    comments_block = soup.select(comment_selector)
    comments = [comment.text for comment in comments_block]
    genres_selector = '.tabs .ow_px_td span.d_book a'
    genres_block = soup.select(genres_selector)
    genres = [genre.text for genre in genres_block]
    properties = {
        'title': sanitize_filename(title.strip()),
        'author': author.strip(),
        'image_url': image['src'],
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


def download_image(url, directory):
    image_response = requests.get(url)
    image_response.raise_for_status()
    image_name = os.path.basename(url)
    image_path = os.path.join(directory, f'{image_name}')
    with open(image_path, 'wb') as file:
        file.write(image_response.content)


def get_urls_from_page(response):
    urls = []
    soup = BeautifulSoup(response.text, 'lxml')
    url_selector = '.tabs .ow_px_td .d_book .bookimage a'
    urls_tags = soup.select(url_selector)
    for tag in urls_tags:
        short_url = tag['href']
        url = urljoin(response.url, short_url)
        urls.append(url)
    return urls


def get_last_page(url):
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'lxml')
    selector = '.tabs .ow_px_td .center .npage'
    page_number = soup.select(selector)[-1].text
    return int(page_number)


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
        help='Остановить скачивание на странице №... (включительно)',
    )
    args = parser.parse_args()
    return args.start, args.end


if __name__ == '__main__':
    os.makedirs(BOOK_DIR, exist_ok=True)
    os.makedirs(IMAGE_DIR, exist_ok=True)
    category_url = 'https://tululu.org/l55/'
    book_url = 'https://tululu.org/txt.php'
    books_properties = {}
    start_page, end_page = parse_arguments()
    if not end_page:
        end_page = get_last_page(category_url)
    for page in range(start_page, end_page+1):
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
                    image_url = urljoin(
                        book_page_response.url,
                        book_properties['image_url'],
                    )
                    download_image(image_url, IMAGE_DIR)
                    book_properties['image_url'] = book_properties[
                        'image_url'].replace('shots', IMAGE_DIR)
                    books_properties[id_] = book_properties
                    connection = True
                except requests.HTTPError:
                    print('Errors on the client or server side')
                    break
                except requests.ConnectionError:
                    print('Connection error occurs! Trying to get book...')
                    sleep(1)
                except requests.TooManyRedirects:
                    print(f'There isn`t book with ID {id_}. Redirect detected')
                    break
    with open('books.json', 'w', encoding='utf8') as json_file:
        json.dump(
            books_properties,
            json_file,
            ensure_ascii=False,
        )
