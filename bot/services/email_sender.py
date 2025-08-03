import os
import ssl
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
EMAIL_RECIPIENTS = [email.strip() for email in os.getenv("EMAIL_RECIPIENTS", "").split(",") if email.strip()]

async def send_lead_email(lead_data: dict):
    if not EMAIL_RECIPIENTS:
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Новый лид: {lead_data['name']}"
    msg["From"] = SMTP_USER
    msg["To"] = ", ".join(EMAIL_RECIPIENTS)

    text = f"""
Привет!

Зарегистрирован новый лид:

Имя: {lead_data['name']}
Telegram: {lead_data['telegram_username']}
Email: {lead_data['email']}
Телефон: {lead_data['phone']}
Сфера: {lead_data['industry']}
Дата: {lead_data['created_at']}

Источник: Telegram-бот ECOFES PRO CLIENT
    """.strip()

    part = MIMEText(text, "plain", "utf-8")
    msg.attach(part)

    try:
        context = ssl.create_default_context()
        await aiosmtplib.send(
            msg,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            username=SMTP_USER,
            password=SMTP_PASSWORD,
            use_tls=True,  # Для порта 465 — TLS при подключении
            tls_context=context,
        )
        print(f"✅  Email отправлен на {', '.join(EMAIL_RECIPIENTS)}")
        return True
    except Exception as e:
        print(f"❌  Ошибка отправки email: {e}")
        return False
