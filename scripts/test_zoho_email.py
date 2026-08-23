#!/usr/bin/env python3
"""Test Zoho SMTP email sending."""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover - fallback for minimal envs
    def load_dotenv():
        env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env'))
        if not os.path.exists(env_path):
            return False
        with open(env_path, 'r', encoding='utf-8') as handle:
            for line in handle:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                key, _, value = line.partition('=')
                key = key.strip()
                value = value.strip()
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                if key and key not in os.environ:
                    os.environ[key] = value
        return True

load_dotenv()

def run_zoho_email_test():
    """Send a test email via Zoho SMTP."""
    smtp_host = os.getenv("SMTP_HOST", "smtp.zoho.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "teamskiltwinhq@zohomail.com")
    smtp_pass = os.getenv("SMTP_PASS", "")
    smtp_from = os.getenv("SMTP_FROM", "teamskiltwinhq@zohomail.com")

    if not smtp_pass:
        print("ERROR: SMTP_PASS not set in .env")
        return False

    msg = MIMEMultipart()
    msg["From"] = smtp_from
    msg["To"] = "luispuldon@gmail.com"  # Receptor de pruebas
    msg["Subject"] = "SkillTwin - Test Email"

    body = """
    This is a test email from SkillTwin platform.
    
    If you received this, Zoho SMTP is working correctly!
    
    Timestamp: 2026-08-02
    """
    msg.attach(MIMEText(body, "plain"))

    try:
        print(f"Connecting to {smtp_host}:{smtp_port}...")
        server = smtplib.SMTP(smtp_host, smtp_port, timeout=30)
        server.ehlo()
        print("Starting TLS...")
        server.starttls()
        server.ehlo()
        print(f"Logging in as {smtp_user}...")
        server.login(smtp_user, smtp_pass)
        print(f"Sending email from {smtp_from} to luispuldon@gmail.com...")
        server.sendmail(smtp_from, ["luispuldon@gmail.com"], msg.as_string())
        server.quit()
        print("SUCCESS: Email sent!")
        return True
    except smtplib.SMTPAuthenticationError as e:
        print(f"AUTH ERROR: {e}")
        print("SMTP relay may still be propagating. Try again in a few minutes.")
        return False
    except smtplib.SMTPException as e:
        print(f"SMTP ERROR: {e}")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False

if __name__ == "__main__":
    success = run_zoho_email_test()
    exit(0 if success else 1)
