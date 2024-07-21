import http.server
import socketserver
import json
from urllib.parse import urlparse, parse_qs
import os
import datetime
import socket
from pymongo import MongoClient, errors
from multiprocessing import Process




HTTP_PORT = 3000
SOCKET_PORT = 5000


# Налаштування MongoDB
# MONGO_URI = 'mongodb://localhost:27017/'  # локально
MONGO_URI = 'mongodb://mongodb:27017/'      # у Docker
DB_NAME = 'webapp'
COLLECTION_NAME = 'messages'


# Папки для зберігання 
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = BASE_DIR
STATIC_DIR = BASE_DIR
STORAGE_DIR = os.path.join(BASE_DIR, 'storage')
DATA_FILE = os.path.join(STORAGE_DIR, 'data.json')


# Налаштування клієнта MongoDB
try:
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]
    print("Успішне підключення до MongoDB")
except errors.ConnectionFailure as e:
    print(f"Не вдалося підключитися до MongoDB: {e}")


# перевірка наявності data.json
if not os.path.exists(STORAGE_DIR):
    os.makedirs(STORAGE_DIR)

# ініціалізація data.json
if not os.path.exists(DATA_FILE) or os.stat(DATA_FILE).st_size == 0:
    with open(DATA_FILE, 'w') as f:
        json.dump([], f)

# Перевірка та перетворення data.json
with open(DATA_FILE, 'r+') as file:
    try:
        file_data = json.load(file)
        if isinstance(file_data, dict):
            file_data = []
            file.seek(0)
            json.dump(file_data, file, indent=4)
            file.truncate()
    except json.JSONDecodeError:
        file.seek(0)
        json.dump([], file, indent=4)
        file.truncate()


# HTTP-сервер
class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        if path == '/' or path == '/index.html':
            self.serve_page('index.html')
        elif path == '/message.html':
            self.serve_page('message.html')
        elif path == '/main.js':
            self.serve_static(path)
        elif path.startswith('/style.css') or path.startswith('/logo.png'):
            self.serve_static(path)
        elif path == '/favicon.ico':
            self.send_response(204)  # no content
            self.end_headers()
        else:
            self.serve_error()


    def do_POST(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        if path == '/message':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            post_params = parse_qs(post_data)

            username = post_params.get('username', [''])[0]
            message = post_params.get('message', [''])[0]

            if username and message:
                self.send_to_socket_server(username, message)
                self.serve_page('index.html')
            else:
                self.serve_error()
        else:
            self.serve_error()


    def serve_page(self, page):
        try:
            with open(os.path.join(TEMPLATE_DIR, page), 'rb') as file:
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(file.read())
        except Exception as e:
            self.serve_error()


    def serve_static(self, path):
        try:
            with open(os.path.join(STATIC_DIR, path.lstrip('/')), 'rb') as file:
                self.send_response(200)
                if path.endswith('.css'):
                    self.send_header('Content-type', 'text/css')
                elif path.endswith('.png'):
                    self.send_header('Content-type', 'image/png')
                elif path.endswith('.js'):
                    self.send_header('Content-type', 'application/javascript')
                elif path.endswith('.ico'):
                    self.send_header('Content-type', 'image/x-icon')
                self.end_headers()
                self.wfile.write(file.read())
        except Exception as e:
            self.serve_error()


    def serve_error(self):
        try:
            with open(os.path.join(TEMPLATE_DIR, 'error.html'), 'rb') as file:
                self.send_response(404)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(file.read())
        except Exception as e:
            self.send_response(500)
            self.end_headers()


    def send_to_socket_server(self, username, message):
        data = json.dumps({
            'date': datetime.datetime.now().isoformat(),
            'username': username,
            'message': message
        }).encode('utf-8')

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.sendto(data, ('localhost', SOCKET_PORT))


# Запуск HTTP-серверу
def run_http_server():
    handler = MyHTTPRequestHandler
    httpd = socketserver.TCPServer(('', HTTP_PORT), handler)
    print(f'Запуск HTTP-серверу на порту {HTTP_PORT}')
    httpd.serve_forever()

# Запуск сокет-серверу
def run_socket_server():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(('0.0.0.0', SOCKET_PORT))
        print(f'Запуск сокет-серверу на порту {SOCKET_PORT}')
        while True:
            data, _ = sock.recvfrom(4096)
            message = json.loads(data.decode('utf-8'))
            message['date'] = datetime.datetime.now().isoformat()

            print(f"Отримано повідомлення: {message}")
            # Зберігання повідомлення у MongoDB
            try:
                # result = collection.insert_one(message)
                # message['_id'] = str(result.inserted_id)  # ObjectId у строку для серіалізаціі
                print("Повідомлення збережено у MongoDB")
            except Exception as e:
                print(f"Помилка при збереженні у MongoDB: {e}")

            # Додавання повідомлення до data.json
            try:
                with open(DATA_FILE, 'r+') as file:
                    file_data = json.load(file)
                    if isinstance(file_data, dict):
                        file_data = []
                    file_data.append(message)
                    file.seek(0)
                    json.dump(file_data, file, indent=4)
                print("Повідомлення збережено у data.json")
            except Exception as e:
                print(f"Помилка при збереженні у data.json: {e}")

if __name__ == '__main__':
    http_process = Process(target=run_http_server)
    socket_process = Process(target=run_socket_server)

    http_process.start()
    socket_process.start()

    http_process.join()
    socket_process.join()