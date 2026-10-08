import json
import os
import urllib.request
from dotenv import load_dotenv

load_dotenv()


def send_otp_email(to_email: str, otp: str) -> bool:
    api_key = os.getenv("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")
    sender = os.getenv("raghavxmishra@gmail.com")

    if not api_key or not sender:
        print(f"[OTP - email not configured] {to_email}: {otp}")
        return False

    payload = {
        "sender": {"name": "Solver AI", "email": sender},
        "to": [{"email": to_email}],
        "subject": "Solver AI - Your verification code",
        "textContent": (
            f"Your Solver AI verification code is {otp}.\n"
            "It expires in 10 minutes. If you didn't request this, ignore this email."
        ),
    }
    req = urllib.request.Request(
        "https://api.brevo.com/v3/smtp/email",
        data=json.dumps(payload).encode("utf-8"),
        headers={"api-key": api_key, "Content-Type": "application/json", "accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return 200 <= resp.status < 300
    except Exception as e:
        print(f"[OTP email failed] {e}")
        print(f"[OTP fallback] {to_email}: {otp}")
        return False