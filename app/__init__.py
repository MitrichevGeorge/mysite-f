# app/__init__.py
from flask import Flask, request, g
from flask_login import LoginManager, current_user
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

@app.before_request
def load_user():
    g.user = current_user  # Устанавливаем текущего пользователя в g

@app.context_processor
def inject_theme():
    if g.user.is_authenticated:  # Проверяем, что пользователь аутентифицирован
        return dict(is_dark_theme=g.user.theme == 'dark')
    return dict(is_dark_theme=False)

# Импорт маршрутов
from .auth import auth_bp
from .views import views_bp
from .tasks import tasks_bp

app.register_blueprint(auth_bp)
app.register_blueprint(views_bp)
app.register_blueprint(tasks_bp)