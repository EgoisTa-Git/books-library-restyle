import argparse
import json
import os
import pathlib
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
    selector = '.tabs .ow_px_td .center .npage:last-of-type'
    page_number = soup.select_one(selector).text
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
        help='Остановить скачивание на странице №...',
    )
    parser.add_argument(
        '--dest_folder',
        type=pathlib.Path,
        default='.',
        help='путь к каталогу с результатами парсинга: картинкам, книгам, JSON',
    )
    parser.add_argument(
        '--skip_imgs',
        action='store_true',
        help='Пропустить скачивание изображений',
    )
    parser.add_argument(
        '--skip_txt',
        action='store_true',
        help='Пропустить скачивание книг',
    )
    parser.add_argument(
        '--json_path',
        type=pathlib.Path,
        default='.',
        help='путь к каталогу с результатами в JSON',
    )
    args = parser.parse_args()
    return args


if __name__ == '__main__':
    parsed_arguments = parse_arguments()
    BASE_DIR = parsed_arguments.dest_folder
    books_path = os.path.join(BASE_DIR, BOOK_DIR)
    images_path = os.path.join(BASE_DIR, IMAGE_DIR)
    if parsed_arguments.json_path != '.':
        os.makedirs(parsed_arguments.json_path, exist_ok=True)
    os.makedirs(books_path, exist_ok=True)
    os.makedirs(images_path, exist_ok=True)
    category_url = 'https://tululu.org/l55/'
    book_url = 'https://tululu.org/txt.php'
    books_properties = {}
    end_page = parsed_arguments.end
    if not end_page:
        end_page = get_last_page(category_url) + 1
    for page in range(parsed_arguments.start, end_page):
        page_url = urljoin(category_url, str(page))
        print(f'Parsing {page_url}')
        connection = False
        while not connection:
            try:
                books_page_response = requests.get(page_url)
                books_page_response.raise_for_status()
                book_page_urls = get_urls_from_page(books_page_response)
                connection = True
            except requests.HTTPError:
                print('Errors on the client or server side')
                break
            except requests.ConnectionError:
                print('Connection error occurs! Trying to get book...')
                sleep(1)
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
                    if not parsed_arguments.skip_txt:
                        download_book(
                            book_url,
                            id_,
                            books_path,
                            book_properties['title'],
                        )
                    image_url = urljoin(
                        book_page_response.url,
                        book_properties['image_url'],
                    )
                    if not parsed_arguments.skip_imgs:
                        download_image(image_url, images_path)
                    book_properties['image_url'] = book_properties[
                        'image_url'].replace('shots', images_path)
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
    json_file_path = os.path.join(parsed_arguments.json_path, 'books.json')
    with open(json_file_path, 'w', encoding='utf8') as json_file:
        json.dump(
            books_properties,
            json_file,
            ensure_ascii=False,
        )
