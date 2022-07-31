import json

from jinja2 import Environment, FileSystemLoader, select_autoescape
from livereload import Server


def rebuild():
    template = env.get_template('template.html')
    with open('db/books.json', 'r') as file:
        books = json.load(file)
    rendered_page = template.render(books=books.values())
    with open('index.html', 'w', encoding="utf8") as file:
        file.write(rendered_page)


if __name__ == '__main__':
    env = Environment(
        loader=FileSystemLoader('.'),
        autoescape=select_autoescape(['html']),
    )
    server = Server()
    rebuild()
    server.watch('template.html', rebuild)
    server.serve(root='.')
