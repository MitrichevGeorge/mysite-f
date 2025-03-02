# app/__init__.py
from flask import Flask, request
from flask_login import LoginManager
from .models import load_users, save_users
import os

app = Flask(__name__, template_folder=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'templates'))
app.secret_key = "supersecretkey"

# Настройка Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "auth.login"

# Загрузка пользователей
@login_manager.user_loader
def load_user(user_id):
    users = load_users()
    user = users.get(int(user_id))  # Возвращаем пользователя по ID
    if user:
        user.add_login(request.url)  # Сохраняем информацию о заходе и текущем URL
        save_users(users)  # Сохраняем изменения в users
    return user

# Импорт маршрутов
from .auth import auth_bp
from .views import views_bp
from .tasks import tasks_bp

app.register_blueprint(auth_bp)
app.register_blueprint(views_bp)
app.register_blueprint(tasks_bp)