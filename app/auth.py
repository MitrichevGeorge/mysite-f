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
from datetime import datetime, timedelta
import requests

auth_bp = Blueprint('auth', __name__)

# Email parameters
IMAP_SERVER = "imap.mail.ru"
SMTP_SERVER = "smtp.mail.ru"
SMTP_PORT = 465
USERNAME = "infsolvy@bk.ru"
PASSWORD = "CThDRiNKVM9TkRVswFVF"
ADMIN_EMAIL = "yegorim@mail.ru"

def send_email(to_email, subject, html_body):
    """Send email and return True if successful, False otherwise."""
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
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

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
    return send_email(to_email, "Подтверждение email", html_body)

def send_one_time_code(to_email, username, code):
    print(f"DEBUG: One-time code for {username} ({to_email}): {code}")
    print(f"Sending one-time code to {to_email}")
    """Send one-time code to email."""
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <body>
        <h1>Вход по одноразовому коду</h1>
        <p>Здравствуйте, {username}!</p>
        <p>Ваш одноразовый код для входа: <strong>{code}</strong></p>
        <p>Код действителен в течение 10 минут.</p>
        <p>Если вы не запрашивали код, проигнорируйте это письмо.</p>
    </body>
    </html>
    """
    return send_email(to_email, "Вход по одноразовому коду", html_body)

def send_creator_request_email(username, email, reason, request_code):
    """Send creator request email to admin with accept/decline links."""
    accept_link = url_for('auth.approve_creator', code=request_code, _external=True)
    decline_link = url_for('auth.reject_creator', code=request_code, _external=True)
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <body>
        <h1>Запрос прав создателя</h1>
        <p>Пользователь <strong>{username}</strong> (email: {email}) запрашивает права создателя.</p>
        <p><strong>Причина запроса:</strong></p>
        <p>{reason}</p>
        <p>Для принятия запроса перейдите по ссылке:</p>
        <a href="{accept_link}">Принять запрос</a>
        <p>Для отклонения запроса перейдите по ссылке:</p>
        <a href="{decline_link}">Отклонить запрос</a>
    </body>
    </html>
    """
    return send_email(ADMIN_EMAIL, "Запрос прав создателя", html_body)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            return jsonify({'status': 'error', 'message': 'Пароли не совпадают'}), 400

        if not re.match(r'^[a-zA-Z0-9_-]{3,15}$', username):
            return jsonify({'status': 'error', 'message': 'Имя пользователя должно быть от 3 до 15 символов и содержать только английские буквы, цифры, - или _'}), 400

        users = load_users()

        if any(user.username == username for user in users.values()):
            return jsonify({'status': 'error', 'message': 'Имя пользователя уже занято'}), 400

        new_user_id = len(users) + 1
        verification_code = str(uuid.uuid4())
        new_user = User(
            id=new_user_id,
            email=email,
            username=username,
            password_hash=generate_password_hash(password),
            is_verified=False,
            verification_code=verification_code,
            custom_package=None
        )

        users[new_user_id] = new_user
        save_users(users)

        if not send_verification_email(email, username, verification_code):
            return jsonify({'status': 'error', 'message': 'Ошибка отправки письма. Пожалуйста, попробуйте снова.'}), 500

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
    if current_user.is_authenticated:
        return redirect(url_for('views.index'))

    if request.method == 'POST':
        identifier = request.form.get('identifier')
        password = request.form.get('password')
        login_mode = 'password' if password else 'code'

        print(f"Login attempt with identifier: {identifier}, mode: {login_mode}")

        users = load_users()
        if login_mode == 'password':
            matching_users = [
                user for user in users.values()
                if (user.email == identifier or user.username == identifier) and user.is_verified
            ]
            if not matching_users:
                print("No verified users found for password login")
                return jsonify({'status': 'error', 'message': 'Пользователь не найден или email не подтвержден'}), 400

            if len(matching_users) == 1:
                user = matching_users[0]
                if check_password_hash(user.password_hash, password):
                    login_user(user)
                    print(f"User {user.username} logged in successfully")
                    return jsonify({'status': 'success', 'message': 'Вход успешен!', 'redirect': url_for('views.index')})
                else:
                    print("Invalid password")
                    return jsonify({'status': 'error', 'message': 'Неверный пароль'}), 400
            else:
                print("Multiple accounts found, prompting selection")
                return jsonify({
                    'status': 'select',
                    'message': 'Найдено несколько аккаунтов. Выберите один:',
                    'users': [{'id': user.id, 'username': user.username} for user in matching_users]
                })

        elif login_mode == 'code':
            user_by_username = next((user for user in users.values() if user.username == identifier), None)
            matching_users = [user for user in users.values() if user.email == identifier]

            if user_by_username:
                print(f"Found user by username: {user_by_username.username}")
                if not user_by_username.is_verified:
                    print("User email not verified")
                    return jsonify({'status': 'error', 'message': 'Пожалуйста, подтвердите ваш email перед входом.'}), 400
                one_time_code = ''.join(random.choices(string.digits, k=6))
                user_by_username.one_time_code = one_time_code
                user_by_username.one_time_code_expiration = datetime.now() + timedelta(minutes=10)
                save_users(users)
                print(f"Generated one-time code {one_time_code} for {user_by_username.email}")
                if not send_one_time_code(user_by_username.email, user_by_username.username, one_time_code):
                    return jsonify({'status': 'error', 'message': 'Ошибка отправки кода. Пожалуйста, попробуйте снова.'}), 500
                print("Called send_one_time_code")
                return jsonify({
                    'status': 'success',
                    'message': 'Код отправлен на ваш email.',
                    'email': user_by_username.email,
                    'user_id': user_by_username.id
                })

            if matching_users:
                print(f"Found {len(matching_users)} users by email")
                valid_users = [user for user in matching_users if user.is_verified]
                if not valid_users:
                    print("No verified users found")
                    return jsonify({'status': 'error', 'message': 'Все аккаунты с этим email не подтверждены.'}), 400
                if len(valid_users) == 1:
                    user = valid_users[0]
                    one_time_code = ''.join(random.choices(string.digits, k=6))
                    user.one_time_code = one_time_code
                    user.one_time_code_expiration = datetime.now() + timedelta(minutes=10)
                    save_users(users)
                    print(f"Generated one-time code {one_time_code} for {user.email}")
                    if not send_one_time_code(user.email, user.username, one_time_code):
                        return jsonify({'status': 'error', 'message': 'Ошибка отправки кода. Пожалуйста, попробуйте снова.'}), 500
                    print("Called send_one_time_code")
                    return jsonify({
                        'status': 'success',
                        'message': 'Код отправлен на ваш email.',
                        'email': user.email,
                        'user_id': user.id
                    })
                else:
                    print("Multiple accounts found, prompting selection")
                    return jsonify({
                        'status': 'select',
                        'message': 'Найдено несколько аккаунтов. Выберите один:',
                        'users': [{'id': user.id, 'username': user.username} for user in valid_users],
                        'email': identifier
                    })

            print("User not found")
            return jsonify({'status': 'error', 'message': 'Пользователь не найден'}), 400

    return render_template('login.html')

@auth_bp.route('/request-one-time-code', methods=['GET'])
def request_one_time_code():
    print("Rendering request_one_time_code.html")
    return render_template('request_one_time_code.html')

@auth_bp.route('/verify-one-time-code', methods=['POST'])
def verify_one_time_code():
    email = request.form.get('email')
    code = request.form.get('code')
    user_id = request.form.get('user_id')

    print(f"Verifying code for email: {email}, user_id: {user_id}, code: {code}")

    users = load_users()
    user = users.get(int(user_id)) if user_id else None

    if not user or user.email != email:
        print("User not found or email mismatch")
        return jsonify({'status': 'error', 'message': 'Пользователь не найден'}), 400

    if user.one_time_code == code and user.one_time_code_expiration and datetime.now() < user.one_time_code_expiration:
        user.one_time_code = None
        user.one_time_code_expiration = None
        save_users(users)
        login_user(user)
        print(f"User {user.username} logged in successfully")
        return jsonify({'status': 'success', 'message': 'Вход успешен!', 'redirect': url_for('views.index')})
    else:
        print("Invalid code or expired")
        return jsonify({'status': 'error', 'message': 'Неверный код или срок действия истек'}), 400

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
            if not send_email(email, "Восстановление пароля", f"""
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
            """):
                flash('Ошибка отправки письма с кодом восстановления.', 'error')
                return redirect(url_for('auth.forgot_password'))
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

@auth_bp.route('/request-creator', methods=['POST'])
@login_required
def request_creator():
    if current_user.is_creator:
        flash('Вы уже являетесь создателем.', 'error')
        return redirect(url_for('views.profile'))

    if current_user.creator_request_status == 'pending':
        flash('Ваш запрос уже на рассмотрении.', 'error')
        return redirect(url_for('views.profile'))

    reason = request.form.get('reason')
    agreement = request.form.get('agreement')
    token = request.form.get('cf-turnstile-response')

    if not reason or not agreement:
        flash('Пожалуйста, заполните все поля и подтвердите согласие.', 'error')
        return redirect(url_for('views.profile'))

    # Verify CAPTCHA
    response = requests.post(
        'https://challenges.cloudflare.com/turnstile/v0/siteverify',
        data={'secret': '0x4AAAAAABRQkVXmPfu99urFb80xmVf6YJ8', 'response': token}
    )
    if not response.json().get('success', False):
        flash('Неверная капча.', 'error')
        return redirect(url_for('views.profile'))

    users = load_users()
    user = users.get(current_user.id)
    if not user:
        flash('Пользователь не найден.', 'error')
        return redirect(url_for('views.profile'))

    request_code = str(uuid.uuid4())
    user.creator_request_status = 'pending'
    user.verification_code = request_code  # Reuse verification_code for creator request
    save_users(users)

    if not send_creator_request_email(user.username, user.email, reason, request_code):
        flash('Ошибка отправки запроса. Пожалуйста, попробуйте снова.', 'error')
        return redirect(url_for('views.profile'))

    flash('Запрос на получение прав создателя отправлен.', 'success')
    return redirect(url_for('views.profile'))

@auth_bp.route('/approve-creator/<code>')
def approve_creator(code):
    users = load_users()
    user = next((u for u in users.values() if u.verification_code == code and u.creator_request_status == 'pending'), None)
    if user:
        user.is_creator = True
        user.creator_request_status = 'approved'
        user.verification_code = None
        save_users(users)
        flash('Запрос на права создателя одобрен.')
        # Notify user
        send_email(user.email, "Права создателя одобрены", f"""
        <!DOCTYPE html>
        <html>
        <body>
            <h1>Права создателя одобрены</h1>
            <p>Здравствуйте, {user.username}!</p>
            <p>Ваш запрос на получение прав создателя был одобрен. Теперь вы можете создавать задачи.</p>
        </body>
        </html>
        """)
        return redirect(url_for('views.index'))
    else:
        flash('Неверная или устаревшая ссылка.')
        return redirect(url_for('views.index'))

@auth_bp.route('/reject-creator/<code>')
def reject_creator(code):
    users = load_users()
    user = next((u for u in users.values() if u.verification_code == code and u.creator_request_status == 'pending'), None)
    if user:
        user.creator_request_status = 'rejected'
        user.verification_code = None
        save_users(users)
        flash('Запрос на права создателя отклонён.')
        # Notify user
        send_email(user.email, "Права создателя отклонены", f"""
        <!DOCTYPE html>
        <html>
        <body>
            <h1>Права создателя отклонены</h1>
            <p>Здравствуйте, {user.username}!</p>
            <p>Ваш запрос на получение прав создателя был отклонён. Для уточнения причин свяжитесь с администратором.</p>
        </body>
        </html>
        """)
        return redirect(url_for('views.index'))
    else:
        flash('Неверная или устаревшая ссылка.')
        return redirect(url_for('views.index'))