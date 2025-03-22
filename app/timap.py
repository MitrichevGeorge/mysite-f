import imaplib
import email
import smtplib
from email.header import decode_header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Параметры подключения
IMAP_SERVER = "imap.mail.ru"
SMTP_SERVER = "smtp.mail.ru"
SMTP_PORT = 465  # Порт для SMTP с SSL
USERNAME = "infsolvy@bk.ru"
PASSWORD = "CThDRiNKVM9TkRVswFVF"
RECIPIENT = "cib_pro@mail.ru"

def send_email(subject, html_body):
    """Функция для отправки HTML-письма"""
    try:
        # Создание multipart-сообщения
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = USERNAME
        msg["To"] = RECIPIENT

        # HTML-контент письма
        html_part = MIMEText(html_body, "html")
        msg.attach(html_part)

        # Подключение к SMTP-серверу
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(USERNAME, PASSWORD)
            server.sendmail(USERNAME, RECIPIENT, msg.as_string())
        print(f"Письмо успешно отправлено на {RECIPIENT}")
    except Exception as e:
        print(f"Ошибка при отправке письма: {e}")

# HTML-дизайн письма
html_content = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f0f0f0;
        }
        .container {
            max-width: 600px;
            margin: 0 auto;
            position: relative;
        }
        .background-rect {
            background-color: #e0eaff;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
        }
        .content {
            background-color: white;
            border-radius: 10px;
            padding: 20px;
            text-align: center;
        }
        h1 {
            color: #1a73e8;
            margin: 0;
        }
        p {
            color: #333;
            line-height: 1.6;
        }
        .footer {
            margin-top: 20px;
            font-size: 12px;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="background-rect">
            <div class="content">
                <h1>Привет!</h1>
                <p>Это тестовое письмо с красивым дизайном.<br> 
                   Прямоугольник на фоне имеет скругленные края и легкую тень.</p>
                <p>Надеюсь, тебе понравится!</p>
            </div>
        </div>
        <div class="footer">
            Отправлено с помощью Python • 2025
        </div>
    </div>
</body>
</html>
"""

try:
    # Подключение к IMAP-серверу
    mail = imaplib.IMAP4_SSL(IMAP_SERVER, timeout=30)
    print("Успешное подключение к IMAP-серверу")
    
    # Аутентификация
    mail.login(USERNAME, PASSWORD)
    print("Успешная аутентификация")
    
    # Выбор почтового ящика
    mail.select("inbox")
    
    # Поиск всех писем
    status, messages = mail.search(None, "ALL")
    if status != "OK":
        raise Exception("Ошибка при поиске писем")
    
    message_ids = messages[0].split()
    
    # Чтение последних 5 писем
    for msg_id in message_ids[-5:]:
        status, msg_data = mail.fetch(msg_id, "(RFC822)")
        raw_email = msg_data[0][1]
        email_message = email.message_from_bytes(raw_email)
        
        subject, encoding = decode_header(email_message["Subject"])[0]
        if isinstance(subject, bytes):
            subject = subject.decode(encoding or "utf-8")
        print(f"Тема: {subject}")
        
        from_ = email_message.get("From")
        print(f"От: {from_}")
        
        if email_message.is_multipart():
            for part in email_message.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode()
                    print(f"Текст: {body[:100]}...")
                    break
        else:
            body = email_message.get_payload(decode=True).decode()
            print(f"Текст: {body[:100]}...")
        
        print("-" * 50)

    # Отправка HTML-письма
    send_email(
        subject="Тестовое письмо с дизайном",
        html_body=html_content
    )

except TimeoutError as e:
    print(f"Ошибка тайм-аута: {e}. Проверьте интернет-соединение или порт 993.")
except imaplib.IMAP4.error as e:
    print(f"Ошибка IMAP: {e}. Проверьте логин, пароль или настройки сервера.")
except Exception as e:
    print(f"Неизвестная ошибка: {e}")
finally:
    try:
        mail.close()
        mail.logout()
    except:
        pass