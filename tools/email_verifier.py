# tools/email_verifier.py
# ============================================================
# DIY EMAIL VERIFIER — SMTP Handshake (no sending, free)
#
# How it works:
#   1. DNS MX lookup → is the domain real?
#   2. SMTP RCPT TO handshake → does the mailbox exist?
#   3. Catch-all detection → does server accept *everything*?
#
# Limitations:
#   - Gmail / Outlook / Yahoo block this (returns "unknown")
#   - ISPs sometimes block outbound port 25
#   - Small company servers → works great (~70% of your list)
# ============================================================

import smtplib
import dns.resolver
import json
import csv
import time
import logging
import random
import string
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s")
logger = logging.getLogger(__name__)

TIMEOUT        = 10          # seconds per SMTP connection
MAX_WORKERS    = 10          # parallel threads (don't go too high)
FROM_EMAIL     = "verify@gmail.com"   # fake from, doesn't matter
HELO_DOMAIN    = "gmail.com"          # pretend to be gmail


# ── RESULT CODES ──────────────────────────────────────────────
# "valid"     → 250 response, mailbox confirmed
# "invalid"   → 550/551/552/553 response, mailbox doesn't exist
# "catch_all" → domain accepts ANY address (can't verify individuals)
# "unknown"   → server blocked check / timeout / no response
# "bad_domain"→ no MX record (domain is dead)
# ──────────────────────────────────────────────────────────────


def _get_mx(domain: str) -> str | None:
    """Return the highest-priority MX hostname for a domain."""
    try:
        records = dns.resolver.resolve(domain, "MX", lifetime=5)
        best = sorted(records, key=lambda r: r.preference)[0]
        return best.exchange.to_text().rstrip(".")
    except Exception:
        return None


def _random_address(domain: str) -> str:
    """Generate a random address that almost certainly doesn't exist."""
    rand = "".join(random.choices(string.ascii_lowercase, k=16))
    return f"{rand}@{domain}"


def _smtp_check(email: str, mx_host: str) -> str:
    """
    Core SMTP handshake check.
    Returns one of: valid / invalid / catch_all / unknown

    Key insight: if server rejects BOTH a random address AND the real
    address with 550, it's an anti-relay server (Office 365, Google
    Workspace etc.) that blocks all unknown IPs — NOT a missing mailbox.
    Return "unknown" in that case to avoid false positives.
    """
    try:
        with smtplib.SMTP(timeout=TIMEOUT) as smtp:
            smtp.connect(mx_host, 25)
            smtp.helo(HELO_DOMAIN)
            smtp.mail(FROM_EMAIL)

            # ── Catch-all detection ──
            # Test a random address first. If server says 250 for garbage,
            # it accepts everything → mark as catch_all.
            rand_addr    = _random_address(email.split("@")[1])
            code_rand, _ = smtp.rcpt(rand_addr)
            if code_rand == 250:
                smtp.quit()
                return "catch_all"

            # ── Real address check ──
            code, _ = smtp.rcpt(email)
            smtp.quit()

            if code == 250:
                return "valid"
            elif code in (550, 551, 552, 553):
                # Both random AND real address got 550 → anti-relay server
                # (Office 365 / Google Workspace protecting their domain)
                # We CANNOT tell if the mailbox exists → be safe, return unknown
                if code_rand in (550, 551, 552, 553):
                    return "unknown"
                return "invalid"
            else:
                return "unknown"

    except smtplib.SMTPConnectError:
        return "unknown"
    except smtplib.SMTPServerDisconnected:
        return "unknown"
    except smtplib.SMTPRecipientsRefused:
        # Server refused at connection level → likely relay block, not missing mailbox
        return "unknown"
    except ConnectionRefusedError:
        return "unknown"
    except OSError:
        # Port 25 blocked by ISP
        return "unknown"
    except Exception:
        return "unknown"


def verify_email(email: str) -> dict:
    """
    Full verification for a single email address.
    Returns dict: {email, status, domain, mx_host}
    """
    email  = email.strip().lower()
    domain = email.split("@")[1] if "@" in email else ""
    result = {"email": email, "domain": domain, "mx_host": None, "status": "unknown"}

    if not domain:
        result["status"] = "invalid"
        return result

    mx = _get_mx(domain)
    if not mx:
        result["status"] = "bad_domain"
        return result

    result["mx_host"] = mx
    result["status"]  = _smtp_check(email, mx)
    return result


def verify_list(emails: list[str], delay: float = 0.3) -> list[dict]:
    """
    Verify a list of emails with threading.
    Returns list of result dicts sorted by status.
    """
    results = []
    total   = len(emails)

    logger.info(f"Verifying {total} emails with {MAX_WORKERS} threads...")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(verify_email, e): e for e in emails}
        for i, future in enumerate(as_completed(futures), 1):
            res = future.result()
            results.append(res)
            status_icon = {
                "valid":     "✅",
                "invalid":   "❌",
                "catch_all": "⚠️ ",
                "unknown":   "❓",
                "bad_domain":"💀",
            }.get(res["status"], "❓")
            logger.info(f"  [{i}/{total}] {status_icon} {res['email']} → {res['status']}")
            time.sleep(delay)   # be polite to mail servers

    return results


def save_results(results: list[dict], output_path: str):
    """Save verification results to CSV."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["email", "domain", "mx_host", "status"])
        writer.writeheader()
        writer.writerows(sorted(results, key=lambda r: r["status"]))

    logger.info(f"Results saved to {path}")


def print_summary(results: list[dict]):
    counts = {}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1

    total = len(results)
    print("\n" + "="*50)
    print("EMAIL VERIFICATION SUMMARY")
    print("="*50)
    print(f"  Total checked : {total}")
    print(f"  ✅ Valid       : {counts.get('valid', 0)}")
    print(f"  ❌ Invalid     : {counts.get('invalid', 0)}")
    print(f"  ⚠️  Catch-all  : {counts.get('catch_all', 0)}  (can't verify)")
    print(f"  ❓ Unknown     : {counts.get('unknown', 0)}   (server blocked)")
    print(f"  💀 Bad domain  : {counts.get('bad_domain', 0)}")
    print("="*50)
    sendable = counts.get("valid", 0) + counts.get("catch_all", 0) + counts.get("unknown", 0)
    print(f"  📬 Safe to send: {sendable} ({sendable/total*100:.1f}%)")
    print(f"  🗑️  Skip these  : {counts.get('invalid', 0) + counts.get('bad_domain', 0)}")
    print("="*50 + "\n")


# ── CLI usage ──────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    # Load emails from bounced log to re-test, or pass a file
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        with open(input_file) as f:
            if input_file.endswith(".json"):
                data   = json.load(f)
                emails = data.get("sent", data.get("bounced", []))
            else:
                emails = [line.strip() for line in f if "@" in line]
    else:
        # Default: verify all contacts in sent_emails.json
        sent_path = Path("logs/sent_emails.json")
        if sent_path.exists():
            with open(sent_path) as f:
                emails = json.load(f).get("sent", [])
        else:
            print("Usage: python tools/email_verifier.py [emails.txt or emails.json]")
            sys.exit(1)

    results = verify_list(emails)
    print_summary(results)
    save_results(results, "logs/email_verification_results.csv")

    # Auto-add confirmed invalids to bounced log
    invalids = {r["email"] for r in results if r["status"] in ("invalid", "bad_domain")}
    if invalids:
        bounced_path = Path("logs/bounced_emails.json")
        if bounced_path.exists():
            with open(bounced_path) as f:
                data = json.load(f)
        else:
            data = {"bounced": []}

        existing = set(data["bounced"])
        new_ones  = invalids - existing
        if new_ones:
            data["bounced"] = sorted(existing | new_ones)
            with open(bounced_path, "w") as f:
                json.dump(data, f, indent=2)
            print(f"✅ Auto-added {len(new_ones)} invalid addresses to bounced_emails.json")
