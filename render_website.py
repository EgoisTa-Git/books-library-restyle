import json
import os

from jinja2 import Environment, FileSystemLoader, select_autoescape
from livereload import Server
from more_itertools import chunked

PAGES_DIR = 'pages'


def rebuild(directory=PAGES_DIR):
    template = env.get_template('template.html')
    with open('db/books.json', 'r') as file:
        books = json.load(file)
        chunked_books = list(chunked(books.values(), 2))
    book_page_chunk = list(chunked(chunked_books, 5))
    for page_number, chunk in enumerate(book_page_chunk, 1):
        rendered_page = template.render(chunked_books=chunk)
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
