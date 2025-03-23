# app/auth.py
import imaplib
import email
import smtplib
from email.header import decode_header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import random
import string
from flask import Blueprint, request, redirect, url_for, flash, render_template
from flask_login import login_user, logout_user, login_required, current_user
from .models import User, load_users, save_users
from werkzeug.security import generate_password_hash

auth_bp = Blueprint('auth', __name__)

# Email parameters
IMAP_SERVER = "imap.mail.ru"
SMTP_SERVER = "smtp.mail.ru"
SMTP_PORT = 465  # Port for SMTP with SSL
USERNAME = "infsolvy@bk.ru"
PASSWORD = "CThDRiNKVM9TkRVswFVF"

def send_email(to_email, username, recovery_code):
    """Function to send an HTML email."""
    try:
        # Read the HTML template
        with open("password_recovery_email.html", "r", encoding="utf-8") as file:
            html_template = file.read()
        
        # Replace placeholders with actual values
        html_body = html_template.replace("{{username}}", username).replace("{{recovery_code}}", recovery_code)

        # Create a multipart message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Восстановление пароля"
        msg["From"] = USERNAME
        msg["To"] = to_email

        # Attach the HTML content to the message
        html_part = MIMEText(html_body, "html")
        msg.attach(html_part)

        # Connect to the SMTP server and send the email
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(USERNAME, PASSWORD)
            server.sendmail(USERNAME, to_email, msg.as_string())
        
        print(f"Email successfully sent to {to_email}")
    except Exception as e:
        print(f"Error sending email: {e}")

@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form['email']
        users = load_users()
        user = next((u for u in users.values() if u.email == email), None)

        if user:
            recovery_code = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
            user.set_recovery_code(recovery_code)
            send_email(email, user.username, recovery_code)
            save_users(users)  # Сохраняем изменения в users.json
            flash('Письмо с кодом для восстановления пароля отправлено на ваш email.', 'success')
            return redirect(url_for('auth.enter_recovery_code', email=email))
        else:
            flash('Пользователь с таким email не найден.', 'error')

    return render_template('forgot_password.html')
@auth_bp.route("/enter-recovery-code", methods=["GET", "POST"])
def enter_recovery_code():
    if request.method == "POST":
        email = request.form['email']
        print(f"Email: {email}")
        recovery_code = request.form['recovery_code']
        print(email, recovery_code)
        users = load_users()
        user = next((u for u in users.values() if u.email == email), None)
        if user and user.is_recovery_code_valid(recovery_code):
            return render_template('reset_password.html', email=email)  # Render password reset form
        else:
            flash('Неверный код восстановления или код истек.', 'error')

    return render_template('enter_recovery_code.html', email = request.args.get('email'))  # Render enter recovery code form

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
        user.set_password(new_password)  # Update the user's password
        user.recovery_code = None  # Clear the recovery code
        user.recovery_code_expiration = None  # Clear the expiration time
        save_users(users)  # Save updated users
        flash('Пароль успешно обновлён.', 'success')
        return redirect(url_for('auth.login'))

    flash('Ошибка при обновлении пароля.', 'error')
    return redirect(url_for('auth.enter_recovery_code', email=email))

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

