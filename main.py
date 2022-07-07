import os

import requests


def get_book(book_id):
    url = f'https://tululu.org/txt.php?id={book_id}'
    response = requests.get(url)
    response.raise_for_status()
    return response.text


if __name__ == '__main__':
    os.makedirs('books', exist_ok=True)
    for id_ in range(1, 11):
        with open(f'books/id{id_}.txt', 'w') as file:
            file.write(get_book(id_))
