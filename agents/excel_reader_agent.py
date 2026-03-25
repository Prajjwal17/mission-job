# agents/excel_reader_agent.py
# ============================================================
# EXCEL READER AGENT
# Reads job links + HR contacts from the master Excel file.
#
# Two outputs:
#   read_job_links()   → list of jobs with LinkedIn URLs to scrape
#   read_hr_contacts() → deduplicated list of HR email contacts
# ============================================================

import logging
import json
import re
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# JOB LINKS READER
# Reads "Internships Links" + "Full Time Jobs Links" sheets
# ─────────────────────────────────────────────
def read_job_links(excel_path: str) -> list:
    """
    Returns list of dicts:
    { company, job_title, location, experience, status, url, sheet }
    Filters: must have a valid LinkedIn/HTTP URL
    """
    try:
        import pandas as pd
    except ImportError:
        logger.error("pandas not installed. Run: pip install pandas openpyxl")
        return []

    xl = pd.ExcelFile(excel_path)
    jobs = []

    for sheet in ['Internships Links', 'Full Time Jobs Links']:
        if sheet not in xl.sheet_names:
            continue
        df = pd.read_excel(excel_path, sheet_name=sheet, header=None)

        # Find the header row that has 'Company' and 'Link'
        data_start = 5  # default fallback
        for i in range(min(10, len(df))):
            vals = [str(v).lower().strip() for v in df.iloc[i].tolist()]
            if 'company' in vals and ('link' in ' '.join(vals) or 'role' in ' '.join(vals)):
                data_start = i + 1
                break

        for i in range(data_start, len(df)):
            row = df.iloc[i].tolist()
            if len(row) < 7:
                continue
            try:
                company   = str(row[1]).strip()
                role      = str(row[3]).strip()
                location  = str(row[4]).strip()
                experience= str(row[2]).strip()
                status    = str(row[5]).strip()
                url       = str(row[6]).strip()

                if company == 'nan' or not company:
                    continue
                if url == 'nan' or 'http' not in url:
                    continue

                jobs.append({
                    'company':    company,
                    'job_title':  role if role != 'nan' else 'Not specified',
                    'location':   location if location != 'nan' else '',
                    'experience': experience if experience != 'nan' else '',
                    'status':     status,
                    'url':        url,
                    'sheet':      sheet,
                    'job_description': '',   # filled later by scraper
                    'hr_name':  '',
                    'hr_email': '',
                    'source':   'excel_links',
                    'scraped_at': datetime.now().isoformat()
                })
            except Exception:
                continue

    logger.info(f"Read {len(jobs)} job links from Excel ({excel_path})")
    return jobs


# ─────────────────────────────────────────────
# HR CONTACTS READER
# Reads all HR email sheets and deduplicates
# ─────────────────────────────────────────────
def read_hr_contacts(excel_path: str, max_total: int = None) -> list:
    """
    Reads all HR email sheets.
    Returns deduplicated list of:
    { hr_name, hr_email, company, designation }
    """
    try:
        import pandas as pd
    except ImportError:
        logger.error("pandas not installed. Run: pip install pandas openpyxl")
        return []

    xl = pd.ExcelFile(excel_path)
    all_contacts = []
    seen_emails  = set()

    def _add(name, email, company, designation=''):
        """Validate and add a contact."""
        email = str(email).strip().lower()
        if not email or email == 'nan' or '@' not in email:
            return
        if not re.match(r"[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}", email):
            return
        if email in seen_emails:
            return
        seen_emails.add(email)
        all_contacts.append({
            'hr_name':     str(name).strip()        if name        and str(name)        != 'nan' else '',
            'hr_email':    email,
            'company':     str(company).strip()     if company     and str(company)     != 'nan' else '',
            'designation': str(designation).strip() if designation and str(designation) != 'nan' else '',
            'source':      'excel_hr',
            'scraped_at':  datetime.now().isoformat()
        })

    # Sheets to skip (not HR contacts)
    SKIP_SHEETS = {'Internships Links', 'Full Time Jobs Links',
                   '1500+ HR Emails', '1700+ HR Ids'}

    for sheet in xl.sheet_names:
        if sheet in SKIP_SHEETS:
            continue
        try:
            df = pd.read_excel(excel_path, sheet_name=sheet, header=None)
            _parse_sheet(sheet, df, _add)
            logger.info(f"  Parsed [{sheet}] → {len(all_contacts)} total so far")
        except Exception as e:
            logger.warning(f"  Failed to parse [{sheet}]: {e}")
            continue

    logger.info(f"Total unique HR contacts: {len(all_contacts)}")
    return all_contacts[:max_total] if max_total else all_contacts


def _parse_sheet(sheet: str, df, add_fn):
    """Route each sheet to its correct parsing logic."""

    if sheet == '2300+ HR Emails':
        # Row 0: header (Email, nan, nan, Company Name)
        for i in range(1, len(df)):
            row = df.iloc[i].tolist()
            add_fn('', row[0], row[3] if len(row) > 3 else '')

    elif sheet == '3k+ HR reach':
        # Row 0: Name, Email Address, LinkedIn, Designation, Company Name
        for i in range(1, len(df)):
            row = df.iloc[i].tolist()
            add_fn(
                row[0] if len(row) > 0 else '',
                row[1] if len(row) > 1 else '',
                row[4] if len(row) > 4 else '',
                row[3] if len(row) > 3 else ''
            )

    elif sheet == 'HR Head':
        # first_name, last_name, designation, ceo_salute, email, email2, company_name
        for i in range(1, len(df)):
            row = df.iloc[i].tolist()
            name = f"{row[0]} {row[1]}" if len(row) > 1 and str(row[1]) != 'nan' else str(row[0])
            email = row[4] if len(row) > 4 else ''
            add_fn(name, email, row[6] if len(row) > 6 else '', row[2] if len(row) > 2 else '')

    elif sheet == 'HR Top Corporates':
        # Name, Current Employer, Work Experience, Email
        for i in range(1, len(df)):
            row = df.iloc[i].tolist()
            add_fn(row[0], row[3] if len(row) > 3 else '', row[1] if len(row) > 1 else '', 'HR')

    elif sheet in ['New Emails - May', 'New Emails - June', 'New Emails - July']:
        # First, Last, Email, Designation(nan), Category, ..., Company
        for i in range(len(df)):
            row = df.iloc[i].tolist()
            if len(row) < 3:
                continue
            name = f"{row[0]} {row[1]}" if len(row) > 1 and str(row[1]) != 'nan' else str(row[0])
            add_fn(name, row[2], row[7] if len(row) > 7 else '', row[3] if len(row) > 3 else '')

    elif sheet in ['Recuritment Agencies Gurgaon']:
        # email2, company_name, country
        for i in range(1, len(df)):
            row = df.iloc[i].tolist()
            add_fn('', row[0], row[1] if len(row) > 1 else '', 'Recruiter')

    elif sheet in ['Recuritment Agencies - Gurgaon', 'Recuritment Agencies - Gurgaon ']:
        # Email, Result, RoleBased, FreeDomain, Diagnosis
        for i in range(1, len(df)):
            row = df.iloc[i].tolist()
            add_fn('', row[0], '', 'Recruiter')

    elif sheet in ['HR head More', 'HR Top']:
        # Email, Verification Status, Safe to send, ...
        for i in range(1, len(df)):
            row = df.iloc[i].tolist()
            safe = str(row[2]).lower() if len(row) > 2 else 'yes'
            if 'yes' in safe or 'true' in safe:
                add_fn('', row[0], '', 'HR')

    elif sheet in ['2800+ HRs Outreach list - Recen', '5500+ HRs Outreach List', '1880+ HR Outreach List']:
        # Find header row: Company Name, Location, Email
        start = 0
        for i in range(min(10, len(df))):
            row_str = ' '.join([str(v).lower() for v in df.iloc[i].tolist()])
            if 'company' in row_str and 'email' in row_str:
                start = i + 1
                break
        for i in range(start, len(df)):
            row = df.iloc[i].tolist()
            if len(row) >= 3:
                add_fn('', row[2], row[0], 'HR')  # email is col 2, company is col 0


# ─────────────────────────────────────────────
# SENT EMAIL TRACKER
# ─────────────────────────────────────────────
def load_bounced_log(bounced_path: str = "logs/bounced_emails.json") -> set:
    """Load bounced (non-existent) email addresses — never retry these."""
    path = Path(bounced_path)
    if path.exists():
        try:
            data = json.loads(path.read_text())
            return set(data.get("bounced", []))
        except Exception:
            return set()
    return set()


def save_bounced_log(bounced_set: set, bounced_path: str = "logs/bounced_emails.json"):
    """Append newly bounced addresses to the bounced log."""
    existing = load_bounced_log(bounced_path)
    merged = existing | bounced_set
    Path(bounced_path).parent.mkdir(exist_ok=True)
    data = {
        "bounced": sorted(merged),
        "note": "These addresses bounced (mailbox does not exist). Never retry.",
    }
    Path(bounced_path).write_text(json.dumps(data, indent=2))


def load_sent_log(log_path: str = "logs/sent_emails.json") -> set:
    """Load previously sent email addresses (excludes bounced)."""
    path = Path(log_path)
    if path.exists():
        try:
            data = json.loads(path.read_text())
            sent = set(data.get("sent", []))
        except Exception:
            sent = set()
    else:
        sent = set()
    # Always exclude bounced addresses from the "sent" pool
    bounced = load_bounced_log()
    return sent | bounced


def save_sent_log(sent_set: set, log_path: str = "logs/sent_emails.json"):
    """Save the sent email log."""
    Path(log_path).parent.mkdir(exist_ok=True)
    data = {"sent": sorted(sent_set), "last_updated": datetime.now().isoformat()}
    Path(log_path).write_text(json.dumps(data, indent=2))


# ─────────────────────────────────────────────
# LINKEDIN JD SCRAPER (no login needed for public pages)
# ─────────────────────────────────────────────
def scrape_jd_from_url(url: str) -> str:
    """
    Scrapes the full job description from a LinkedIn job URL.
    Uses requests first (fast), falls back to Playwright.
    Returns JD text or empty string.
    """
    jd = _scrape_with_requests(url)
    if jd and len(jd) > 100:
        return jd

    logger.info(f"Requests failed, trying Playwright for: {url}")
    return _scrape_with_playwright(url)


def _scrape_with_requests(url: str) -> str:
    """Try scraping using requests + BeautifulSoup (no browser needed)."""
    try:
        import requests
        from bs4 import BeautifulSoup

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        }
        resp = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, "lxml")

        # Try LinkedIn job description selectors
        for selector in [
            "div.description__text",
            "div.show-more-less-html__markup",
            "section.description",
            "div[class*='description']",
        ]:
            el = soup.select_one(selector)
            if el:
                return el.get_text(separator="\n").strip()

        # Fallback: grab all paragraph text
        paragraphs = soup.find_all(['p', 'li'])
        text = "\n".join(p.get_text().strip() for p in paragraphs if p.get_text().strip())
        return text[:3000] if text else ""

    except Exception as e:
        logger.debug(f"Requests scrape failed: {e}")
        return ""


def _scrape_with_playwright(url: str) -> str:
    """Scrape using Playwright Chromium (headless)."""
    try:
        import time
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
                )
            )
            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=15000)
            time.sleep(2)

            # Try "See more" button
            try:
                page.click("button.show-more-less-html__button", timeout=3000)
                time.sleep(1)
            except Exception:
                pass

            # Extract JD
            jd = ""
            for selector in [
                ".description__text",
                ".show-more-less-html__markup",
                ".jobs-description__content",
                "section.description",
            ]:
                try:
                    el = page.query_selector(selector)
                    if el:
                        jd = el.inner_text().strip()
                        break
                except Exception:
                    pass

            browser.close()
            return jd

    except Exception as e:
        logger.warning(f"Playwright scrape failed: {e}")
        return ""
