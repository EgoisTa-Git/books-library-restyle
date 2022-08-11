import json
import os

from jinja2 import Environment, FileSystemLoader, select_autoescape
from livereload import Server
from more_itertools import chunked

PAGES_DIR = 'pages'
COLUMNS = 2
BOOKS_PER_COLUMN = 5


def rebuild(directory=PAGES_DIR):
    template = env.get_template('template.html')
    with open('db/books.json', 'r') as file:
        books = json.load(file)
    chunks = list(chunked(books.values(), COLUMNS))
    page_chunks = list(chunked(chunks, BOOKS_PER_COLUMN))
    for page_number, book_chunk in enumerate(page_chunks, 1):
        pages = {
            'number_of_pages': len(page_chunks),
            'current_page_number': page_number,
        }
        rendered_page = template.render(
            content={'books': book_chunk, 'pages': pages}
        )
        pages_path = os.path.join(directory, f'index{page_number}.html')
        with open(pages_path, 'w', encoding="utf8") as file:
            file.write(rendered_page)


if __name__ == '__main__':
    os.makedirs(PAGES_DIR, exist_ok=True)
    env = Environment(
        loader=FileSystemLoader('.'),
        autoescape=select_autoescape(['html']),
    )
    server = Server()
    rebuild(PAGES_DIR)
    server.watch('template.html', rebuild)
    server.serve(root='.')
