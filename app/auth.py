# app/auth.py
from flask import Blueprint, request, redirect, url_for, flash, render_template
from flask_login import login_user, logout_user, login_required, current_user  # Ensure logout_user is imported
from .models import User, load_users, save_users
from werkzeug.security import generate_password_hash

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash('Пароли не совпадают')
            return redirect(url_for('auth.register'))

        users = load_users()  # Загружаем пользователей
        if any(user.email == email for user in users.values()):  # Проверяем, существует ли пользователь
            flash('Пользователь с таким email уже существует')
            return redirect(url_for('auth.register'))

        # Создаем нового пользователя
        new_user_id = len(users) + 1
        new_user = User(
            id=new_user_id,
            email=email,
            username=username,
            password_hash=generate_password_hash(password)
        )

        # Добавляем нового пользователя в словарь users
        users[new_user_id] = new_user

        # Сохраняем обновленный список пользователей
        save_users(users)

        flash('Регистрация прошла успешно!')
        return redirect(url_for('auth.login'))

    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        users = load_users()  # Загружаем пользователей
        for user in users.values():  # Итерируем по значениям словаря
            if user.email == email and user.check_password(password):
                login_user(user)
                return redirect(url_for('views.index'))

        flash('Неверный email или пароль')
        return redirect(url_for('auth.login'))

    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()  # This should now work correctly
    return redirect(url_for("views.index"))