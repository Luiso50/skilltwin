#!/usr/bin/env python3
"""Test Zoho SMTP email sending."""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from dotenv import load_dotenv

load_dotenv()

def test_zoho_email():
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
    success = test_zoho_email()
    exit(0 if success else 1)
