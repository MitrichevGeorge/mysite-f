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
        users = load_users()  # Load users from your data source
        user = next((u for u in users.values() if u.email == email), None)

        if user:
            # Generate a random code for password reset
            recovery_code = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
            send_email(email, user.username, recovery_code)  # Send the email with the recovery code
            flash('Письмо с кодом для восстановления пароля отправлено на ваш email.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('Пользователь с таким email не найден.', 'error')

    return render_template('forgot_password.html')  # Render the password recovery form


@auth_bp.route("/verify-code", methods=["GET", "POST"])
def verify_code():
    if request.method == "POST":
        email = request.form['email']
        code = request.form['code']
        users = load_users()
        user = next((u for u in users.values() if u.email == email), None)

        if user and user.reset_code == code and datetime.now() < user.reset_code_expiration:
            return render_template('reset_password.html', email=email)  # Show reset password form
        else:
            flash('Неверный код или код истек.', 'error')

    return render_template('verify_code.html')  # Page to enter the reset code

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

