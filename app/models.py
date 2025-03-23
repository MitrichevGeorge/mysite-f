# app/models.py
import os
import json
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime, timedelta
import base64
import struct

# Путь к JSON-файлу с пользователями
USERS_FILE = "users.json"

TASKS_DIR = "tasks/"

gsl = lambda s: s[s.find('/', s.find('/', s.find('/') + 1) + 1):] if s.count('/') >= 3 else "/"

fix_tabs={"/":"Главная",
          "/profile":"Профиль"}

def getTabName(url):
    if url in fix_tabs:
        return fix_tabs[url]
    if url.startswith("/task/"):
        config_path = os.path.join(os.path.join(TASKS_DIR, url[6:]), "config.json")
        with open(config_path, 'r') as f:
            config = json.load(f)
        return config.get("title", "untitled")
    return "Contest"

class User(UserMixin):
    def __init__(self, id, email, username, password_hash, submissions=None, login_history=None, daily_requests=None, tabs=None, theme='light', reset_code=None, reset_code_expiration=None):
        self.id = id
        self.email = email
        self.username = username
        self.password_hash = password_hash
        self.submissions = submissions if submissions else []
        self.login_history = login_history if login_history else []
        self.daily_requests = daily_requests if daily_requests else [0] * 366
        self.tabs = tabs if tabs else []  # List of tabs
        self.theme = theme  # User theme
        self.recovery_code = reset_code  # Храним как значение, а не список
        self.recovery_code_expiration = reset_code_expiration  # Храним как значение, а не список

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def add_submission(self, submission):
        self.submissions.append(submission)

    def add_login(self, url):
        if not url.startswith("/api/"):  # Предполагается, что gsl() — это опечатка
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.login_history.append({"timestamp": timestamp, "url": url})
            
            # Ограничиваем количество записей в истории входа до 100
            if len(self.login_history) > 100:
                self.login_history.pop(0)

            # Увеличиваем количество запросов за текущий день
            current_day = datetime.now().timetuple().tm_yday - 1  # Получаем номер дня в году (0-365)
            self.daily_requests[current_day] += 1
            el = {"url": url, "name": getTabName(url)}  # Замените на реальную функцию getTabName
            if el not in self.tabs:
                self.tabs.append(el)
                if len(self.tabs) > 20:
                    self.tabs.pop(0)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'submissions': self.submissions
        }
    
    def __iter__(self):
        return iter(self.to_dict().items())

    def set_recovery_code(self, code):
        print(f"Set recovery code: {code}")
        self.recovery_code = code  # Присваиваем значение напрямую
        self.recovery_code_expiration = datetime.now() + timedelta(minutes=15)  # Код действителен 15 минут
        print(self.recovery_code, self.recovery_code_expiration)

    def is_recovery_code_valid(self, code):
        print(self.recovery_code, self.recovery_code_expiration)
        print(code, self.recovery_code, self.recovery_code_expiration, datetime.now())
        return self.recovery_code == code and datetime.now() < self.recovery_code_expiration

def decode_daily_requests(encoded_requests):
    daily_requests_bin = base64.b64decode(encoded_requests)
    num_requests = len(daily_requests_bin) // struct.calcsize('i')
    return list(struct.unpack(f'{num_requests}i', daily_requests_bin))

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            users_data = json.load(f)
            users = {}
            for user_data in users_data:
                # Преобразуем строку recovery_code_expiration обратно в datetime
                expiration = datetime.fromisoformat(user_data['recovery_code_expiration']) if user_data.get('recovery_code_expiration') else None

                users[user_data['id']] = User(
                    id=user_data['id'],
                    email=user_data['email'],
                    username=user_data['username'],
                    password_hash=user_data['password_hash'],
                    submissions=user_data.get('submissions', []),
                    login_history=user_data.get('login_history', []),
                    daily_requests=decode_daily_requests(user_data.get('daily_requests', base64.b64encode(struct.pack('0i')).decode('utf-8'))),
                    tabs=user_data.get('tabs', []),
                    theme=user_data.get('theme', 'light'),
                    reset_code=user_data.get('recovery_code', None),
                    reset_code_expiration=expiration  # Передаем преобразованный datetime
                )
            return users
    return {}

def save_users(users):
    users_data = []
    for user in users.values():
        daily_requests_bin = struct.pack(f'{len(user.daily_requests)}i', *user.daily_requests)
        daily_requests_encoded = base64.b64encode(daily_requests_bin).decode('utf-8')

        # Преобразуем recovery_code_expiration в строку ISO, если оно есть
        expiration_str = user.recovery_code_expiration.isoformat() if user.recovery_code_expiration else None

        users_data.append({
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "password_hash": user.password_hash,
            "submissions": user.submissions,
            "login_history": user.login_history,
            "daily_requests": daily_requests_encoded,
            "tabs": user.tabs,
            "theme": user.theme,
            "recovery_code": user.recovery_code,
            "recovery_code_expiration": expiration_str  # Сохраняем как строку
        })

    with open(USERS_FILE, 'w') as f:
        json.dump(users_data, f, ensure_ascii=True, indent=4)

    with open(USERS_FILE, 'w') as f:
        json.dump(users_data, f, ensure_ascii=True, indent=4)
