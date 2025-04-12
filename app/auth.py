# app/auth.py
import imaplib
import email
import smtplib
from email.header import decode_header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import random
import string
import re
from flask import Blueprint, request, redirect, url_for, flash, render_template, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from .models import User, load_users, save_users
from werkzeug.security import generate_password_hash
import uuid
import threading

auth_bp = Blueprint('auth', __name__)

# Email parameters
IMAP_SERVER = "imap.mail.ru"
SMTP_SERVER = "smtp.mail.ru"
SMTP_PORT = 465
USERNAME = "infsolvy@bk.ru"
PASSWORD = "CThDRiNKVM9TkRVswFVF"

def send_email_async(to_email, subject, html_body):
    """Асинхронная отправка email в отдельном потоке."""
    def send():
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = USERNAME
            msg["To"] = to_email
            html_part = MIMEText(html_body, "html")
            msg.attach(html_part)
            with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
                server.login(USERNAME, PASSWORD)
                server.sendmail(USERNAME, to_email, msg.as_string())
            print(f"Email successfully sent to {to_email}")
        except Exception as e:
            print(f"Error sending email: {e}")

    thread = threading.Thread(target=send)
    thread.start()

def send_verification_email(to_email, username, verification_code):
    """Send verification email with a unique link."""
    verification_link = url_for('auth.verify_email', code=verification_code, _external=True)
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <body>
        <h1>Подтверждение email</h1>
        <p>Здравствуйте, {username}!</p>
        <p>Пожалуйста, подтвердите ваш email, перейдя по ссылке ниже:</p>
        <a href="{verification_link}">Подтвердить email</a>
        <p>Если вы не регистрировались, проигнорируйте это письмо.</p>
    </body>
    </html>
    """
    send_email_async(to_email, "Подтверждение регистрации", html_body)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        # Проверка паролей
        if password != confirm_password:
            return jsonify({'status': 'error', 'message': 'Пароли не совпадают'}), 400

        # Проверка имени пользователя
        if not re.match(r'^[a-zA-Z0-9_-]{3,15}$', username):
            return jsonify({'status': 'error', 'message': 'Имя пользователя должно быть от 3 до 15 символов и содержать только английские буквы, цифры, - или _'}), 400

        users = load_users()

        # Проверка, не занято ли имя пользователя
        if any(user.username == username for user in users.values()):
            return jsonify({'status': 'error', 'message': 'Имя пользователя уже занято'}), 400

        # Создаем нового пользователя
        new_user_id = len(users) + 1
        verification_code = str(uuid.uuid4())
        new_user = User(
            id=new_user_id,
            email=email,
            username=username,
            password_hash=generate_password_hash(password),
            is_verified=False,
            verification_code=verification_code
        )

        users[new_user_id] = new_user
        save_users(users)

        # Асинхронная отправка письма
        send_verification_email(email, username, verification_code)
        return jsonify({'status': 'success', 'message': 'Регистрация прошла успешно! Пожалуйста, подтвердите ваш email.'})

    return render_template('register.html')

@auth_bp.route('/verify_email/<code>')
def verify_email(code):
    users = load_users()
    user = next((u for u in users.values() if u.verification_code == code), None)
    if user:
        user.is_verified = True
        user.verification_code = None
        save_users(users)
        flash('Email успешно подтвержден! Теперь вы можете войти.')
        return redirect(url_for('auth.login'))
    else:
        flash('Неверная или устаревшая ссылка для подтверждения.')
        return redirect(url_for('auth.login'))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = request.form.get('identifier')
        password = request.form.get('password')
        if not identifier or not password:
            return jsonify({'status': 'error', 'message': 'Отсутствуют данные формы'}), 400
        users = load_users()

        # Проверяем, является ли identifier username
        user_by_username = next((user for user in users.values() if user.username == identifier), None)
        if user_by_username:
            if not user_by_username.is_verified:
                return jsonify({'status': 'error', 'message': 'Пожалуйста, подтвердите ваш email перед входом.'}), 400
            if user_by_username.check_password(password):
                login_user(user_by_username)
                return jsonify({'status': 'success', 'message': 'Вход успешен!', 'redirect': url_for('views.index')})
            else:
                return jsonify({'status': 'error', 'message': 'Неверный пароль'}), 400

        # Если не username, проверяем как email
        matching_users = [user for user in users.values() if user.email == identifier]
        if not matching_users:
            return jsonify({'status': 'error', 'message': 'Неверный email или имя пользователя'}), 400

        # Фильтруем пользователей с правильным паролем и подтвержденным email
        valid_users = [user for user in matching_users if user.check_password(password) and user.is_verified]
        if not valid_users:
            return jsonify({'status': 'error', 'message': 'Неверный пароль или email не подтвержден'}), 400

        # Всегда возвращаем список аккаунтов для выбора
        return jsonify({
            'status': 'select',
            'message': 'Найдено несколько аккаунтов. Выберите один:',
            'users': [{'id': user.id, 'username': user.username} for user in valid_users]
        })

    return render_template('login.html')

@auth_bp.route('/select_account', methods=['POST'])
def select_account():
    user_id = request.form['user_id']
    users = load_users()
    user = users.get(int(user_id))
    if user:
        login_user(user)
        return jsonify({'status': 'success', 'message': 'Вход успешен!', 'redirect': url_for('views.index')})
    return jsonify({'status': 'error', 'message': 'Ошибка при выборе аккаунта'}), 400

@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form['email']
        users = load_users()
        user = next((u for u in users.values() if u.email == email), None)

        if user:
            recovery_code = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
            user.set_recovery_code(recovery_code)
            send_email_async(email, "Восстановление пароля", f"""
            <!DOCTYPE html>
            <html>
            <body>
                <h1>Восстановление пароля</h1>
                <p>Здравствуйте, {user.username}!</p>
                <p>Ваш код для восстановления пароля: <strong>{recovery_code}</strong></p>
                <p>Код действителен в течение 15 минут.</p>
                <p>Если вы не запрашивали восстановление пароля, проигнорируйте это письмо.</p>
            </body>
            </html>
            """)
            save_users(users)
            flash('Письмо с кодом для восстановления пароля отправлено на ваш email.', 'success')
            return redirect(url_for('auth.enter_recovery_code', email=email))
        else:
            flash('Пользователь с таким email не найден.', 'error')

    return render_template('forgot_password.html')

@auth_bp.route("/enter-recovery-code", methods=["GET", "POST"])
def enter_recovery_code():
    if request.method == "POST":
        email = request.form['email']
        recovery_code = request.form['recovery_code']
        users = load_users()
        user = next((u for u in users.values() if u.email == email), None)
        if user and user.is_recovery_code_valid(recovery_code):
            return render_template('reset_password.html', email=email)
        else:
            flash('Неверный код восстановления или код истек.', 'error')

    return render_template('enter_recovery_code.html', email=request.args.get('email'))

@auth_bp.route("/update-password", methods=["POST"])
def update_password():
    email = request.form['email']
    new_password = request.form['new_password']
    confirm_password = request.form['confirm_password']
    
    if new_password != confirm_password:
        flash('Пароли не совпадают.', 'error')
        return redirect(url_for('auth.enter_recovery_code', email=email))

    users = load_users()
    user = next((u for u in users.values() if u.email == email), None)

    if user:
        user.set_password(new_password)
        user.recovery_code = None
        user.recovery_code_expiration = None
        save_users(users)
        flash('Пароль успешно обновлён.', 'success')
        return redirect(url_for('auth.login'))

    flash('Ошибка при обновлении пароля.', 'error')
    return redirect(url_for('auth.enter_recovery_code', email=email))

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for("views.index"))