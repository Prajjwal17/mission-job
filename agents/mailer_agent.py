# agents/mailer_agent.py
# ============================================================
# AGENT 4: COLD MAILER AGENT
# Sends personalized cold email with PDF resume attached
# via Gmail SMTP using your App Password
# ============================================================

import smtplib
import logging
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path

logger = logging.getLogger(__name__)


def _extract_subject(cold_email_text: str) -> tuple[str, str]:
    """
    Extracts subject line from cold email text.
    Looks for "Subject: ..." at the top.
    Returns (subject, body_without_subject_line)
    """
    lines = cold_email_text.strip().split("\n")
    subject = "Application for Position – Prajjwal Pandey"  # default fallback
    body_start = 0

    for i, line in enumerate(lines):
        if line.lower().startswith("subject:"):
            subject = line.split(":", 1)[1].strip()
            body_start = i + 1
            # Skip blank line after subject
            if body_start < len(lines) and lines[body_start].strip() == "":
                body_start += 1
            break

    body = "\n".join(lines[body_start:]).strip()
    return subject, body


def send_cold_email(
    hr_email: str,
    cold_email_text: str,
    pdf_path: str,
    sender_email: str,
    app_password: str,
    hr_name: str = "",
    dry_run: bool = False
) -> bool:
    """
    Sends a cold email with the resume PDF attached.

    Args:
        hr_email: Recipient email address
        cold_email_text: Full email text (with "Subject: ..." line at top)
        pdf_path: Path to the generated PDF resume
        sender_email: Your Gmail address
        app_password: Gmail App Password (16 chars, no spaces)
        hr_name: HR contact name (for logging)
        dry_run: If True, prints email without sending

    Returns:
        True if sent successfully, False otherwise
    """

    if not hr_email:
        logger.warning("⚠️  No HR email found. Skipping email send.")
        return False

    # Validate email format
    if not re.match(r"[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}", hr_email):
        logger.warning(f"⚠️  Invalid email format: {hr_email}")
        return False

    subject, body = _extract_subject(cold_email_text)

    # ── DRY RUN: Preview without sending ──
    if dry_run:
        print("\n" + "="*60)
        print("📧 DRY RUN — EMAIL PREVIEW")
        print("="*60)
        print(f"TO:      {hr_email}")
        print(f"FROM:    {sender_email}")
        print(f"SUBJECT: {subject}")
        print(f"ATTACH:  {pdf_path}")
        print("-"*60)
        print(body)
        print("="*60 + "\n")
        return True

    # ── BUILD EMAIL ──
    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = hr_email
    msg["Subject"] = subject

    # Plain text body
    msg.attach(MIMEText(body, "plain"))

    # Attach PDF resume
    pdf_file = Path(pdf_path)
    if pdf_file.exists() and pdf_file.suffix == ".pdf":
        with open(pdf_file, "rb") as f:
            attachment = MIMEBase("application", "octet-stream")
            attachment.set_payload(f.read())
        encoders.encode_base64(attachment)
        attachment.add_header(
            "Content-Disposition",
            f'attachment; filename="{pdf_file.name}"'
        )
        msg.attach(attachment)
        logger.info(f"📎 Attached: {pdf_file.name}")
    else:
        logger.warning(f"⚠️  PDF not found at {pdf_path}. Sending without attachment.")

    # ── SEND VIA GMAIL SMTP ──
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, app_password)
            server.sendmail(sender_email, hr_email, msg.as_string())

        recipient_label = f"{hr_name} <{hr_email}>" if hr_name else hr_email
        logger.info(f"✅ Email sent to {recipient_label}")
        return True

    except smtplib.SMTPAuthenticationError:
        logger.error("❌ Gmail authentication failed. Check your App Password.")
        logger.error("   Go to: Google Account → Security → 2-Step Verification → App Passwords")
        return False
    except smtplib.SMTPRecipientsRefused:
        logger.error(f"❌ Recipient refused: {hr_email}")
        return False
    except Exception as e:
        logger.error(f"❌ Failed to send email: {e}")
        return False
