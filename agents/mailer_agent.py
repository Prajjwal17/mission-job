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


def validate_email_domain(email: str) -> bool:
    """
    Checks if the email domain has valid MX records via DNS lookup.
    Returns True if reachable, False if domain is dead/non-existent.
    Catches ~80% of invalid addresses before wasting an SMTP attempt.
    """
    try:
        import dns.resolver
        domain = email.split("@", 1)[1]
        dns.resolver.resolve(domain, "MX")
        return True
    except Exception:
        return False


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
) -> dict:
    """
    Sends a cold email with the resume PDF attached.

    Returns:
        dict with keys:
          "sent"    (bool) — True if email was accepted by the server
          "bounced" (bool) — True if the address/domain is definitively invalid
    """
    result = {"sent": False, "bounced": False}

    if not hr_email:
        logger.warning("⚠️  No HR email found. Skipping email send.")
        return result

    # Validate email format
    if not re.match(r"[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}", hr_email):
        logger.warning(f"⚠️  Invalid email format: {hr_email}")
        result["bounced"] = True
        return result

    # DNS MX pre-validation — skip dead domains before attempting SMTP
    if not dry_run and not validate_email_domain(hr_email):
        logger.warning(f"⚠️  No MX record for domain of {hr_email} — marking as bounced")
        result["bounced"] = True
        return result

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
        result["sent"] = True
        return result

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
        result["sent"] = True
        return result

    except smtplib.SMTPAuthenticationError:
        logger.error("❌ Gmail authentication failed. Check your App Password.")
        logger.error("   Go to: Google Account → Security → 2-Step Verification → App Passwords")
        return result
    except smtplib.SMTPRecipientsRefused:
        logger.error(f"❌ Recipient refused (mailbox does not exist): {hr_email}")
        result["bounced"] = True
        return result
    except smtplib.SMTPException as e:
        logger.error(f"❌ SMTP error for {hr_email}: {e}")
        return result
    except Exception as e:
        logger.error(f"❌ Failed to send email: {e}")
        return result
