import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()


def send_otp_email(to_email: str, otp: str) -> bool:
    host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")

    if not user or not password:
        print(f"[OTP - email not configured] {to_email}: {otp}")
        return False

    msg = EmailMessage()
    msg["Subject"] = "Solver AI - Your verification code"
    msg["From"] = user
    msg["To"] = to_email
    msg.set_content(
        f"Your Solver AI verification code is {otp}.\n"
        "It expires in 10 minutes. If you didn't request this, ignore this email."
    )

    try:
        with smtplib.SMTP(host, port, timeout=15) as server:
            server.starttls()
            server.login(user, password)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"[OTP email failed] {e}")
        print(f"[OTP fallback] {to_email}: {otp}")
        return False