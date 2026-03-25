# verify_linkedin_contacts.py
# ============================================================
# Reads HR contacts with LinkedIn profile URLs from the Excel,
# logs into LinkedIn, visits each profile, checks if the person
# is still at the same company.
#
# Output: logs/linkedin_verified.csv
# Resume: automatically skips already-checked profiles
#
# Usage:
#   python verify_linkedin_contacts.py              # all contacts
#   python verify_linkedin_contacts.py --limit 50  # first 50 only
#   python verify_linkedin_contacts.py --dry-run   # print contacts, no browser
# ============================================================

import argparse
import csv
import io
import logging
import random
import sys
import time
from pathlib import Path

import pandas as pd
from playwright.sync_api import sync_playwright

# ── UTF-8 stdout (Windows fix) ──
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

Path("logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/linkedin_verify.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

import config

EXCEL_PATH    = config.EXCEL_FILE_PATH
OUTPUT_CSV    = "logs/linkedin_verified.csv"
CHECKPOINT    = "logs/linkedin_verify_progress.txt"   # stores already-checked emails


# ─────────────────────────────────────────────
# STEP 1 — Read contacts that have LinkedIn URLs
# ─────────────────────────────────────────────
def load_contacts_with_linkedin() -> list[dict]:
    contacts = []
    xl = pd.ExcelFile(EXCEL_PATH)

    # ── Sheet: 3k+ HR reach ──
    # Columns: Name | Email Address | Personal LinkedIn Profile | Designation | Company Name
    if "3k+ HR reach" in xl.sheet_names:
        df = pd.read_excel(EXCEL_PATH, sheet_name="3k+ HR reach", header=0)
        for _, row in df.iterrows():
            li_url = str(row.get("Personal LinkedIn Profile", "")).strip()
            email  = str(row.get("Email Address", "")).strip().lower()
            if "linkedin.com/in/" not in li_url or "@" not in email:
                continue
            contacts.append({
                "name":        str(row.get("Name", "")).strip(),
                "email":       email,
                "company":     str(row.get("Company Name", "")).strip(),
                "designation": str(row.get("Designation", "")).strip(),
                "linkedin_url": li_url,
                "source":      "3k+ HR reach",
            })

    # ── Sheets: New Emails - May / June / July ──
    # Columns (no header): first, last, email, nan, category, sector, linkedin_url, company
    for sheet in ["New Emails - May", "New Emails - June", "New Emails - July"]:
        if sheet not in xl.sheet_names:
            continue
        df = pd.read_excel(EXCEL_PATH, sheet_name=sheet, header=None)
        for _, row in df.iterrows():
            if len(row) < 7:
                continue
            li_url = str(row.iloc[6]).strip()
            email  = str(row.iloc[2]).strip().lower()
            if "linkedin.com/in/" not in li_url or "@" not in email:
                continue
            first = str(row.iloc[0]).strip()
            last  = str(row.iloc[1]).strip() if str(row.iloc[1]) != "nan" else ""
            contacts.append({
                "name":        f"{first} {last}".strip(),
                "email":       email,
                "company":     str(row.iloc[7]).strip() if len(row) > 7 else "",
                "designation": str(row.iloc[3]).strip() if len(row) > 3 else "",
                "linkedin_url": li_url,
                "source":      sheet,
            })

    # Deduplicate by email
    seen, unique = set(), []
    for c in contacts:
        if c["email"] not in seen and c["email"] != "nan":
            seen.add(c["email"])
            unique.append(c)

    logger.info(f"Loaded {len(unique)} contacts with LinkedIn profile URLs")
    return unique


# ─────────────────────────────────────────────
# STEP 2 — Load already-checked emails (for resume)
# ─────────────────────────────────────────────
def load_checkpoint() -> set:
    path = Path(CHECKPOINT)
    if path.exists():
        return set(path.read_text(encoding="utf-8").splitlines())
    return set()


def save_checkpoint(email: str):
    with open(CHECKPOINT, "a", encoding="utf-8") as f:
        f.write(email + "\n")


# ─────────────────────────────────────────────
# STEP 3 — LinkedIn login
# ─────────────────────────────────────────────
def linkedin_login(page):
    logger.info("Logging into LinkedIn...")
    page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")
    time.sleep(2)
    page.fill("#username", config.LINKEDIN_EMAIL)
    time.sleep(random.uniform(0.5, 1.2))
    page.fill("#password", config.LINKEDIN_PASSWORD)
    time.sleep(random.uniform(0.5, 1.0))
    page.click("[type=submit]")
    page.wait_for_load_state("domcontentloaded", timeout=15000)
    time.sleep(4)

    if "checkpoint" in page.url or "challenge" in page.url or "login" in page.url:
        logger.warning("LinkedIn CAPTCHA or login challenge detected!")
        logger.warning("Please solve it manually in the browser window, then press Enter here.")
        input("Press Enter after solving the CAPTCHA...")
        time.sleep(2)

    logger.info(f"Logged in. Current URL: {page.url}")


# ─────────────────────────────────────────────
# STEP 4 — Scrape current company from a LinkedIn profile
# ─────────────────────────────────────────────
def get_current_company(page, li_url: str, contact_name: str) -> dict:
    """
    Visits a LinkedIn profile and returns:
    { headline, current_company, status }
    status: 'confirmed' | 'moved' | 'unknown' | 'private' | 'error'
    """
    try:
        page.goto(li_url, wait_until="domcontentloaded", timeout=20000)
        time.sleep(random.uniform(2.5, 4.5))

        # Check for CAPTCHA / auth wall
        if "authwall" in page.url or "checkpoint" in page.url:
            logger.warning(f"Auth wall hit for {contact_name}. Pausing 60s...")
            time.sleep(60)
            return {"headline": "", "current_company": "", "status": "error"}

        # Try multiple selectors to get the headline (most reliable indicator)
        headline = ""
        headline_selectors = [
            ".text-body-medium.break-words",           # profile headline
            ".pv-text-details__left-panel .text-body-medium",
            "[data-generated-suggestion-target] .text-body-medium",
            "h2.mt1 + div .text-body-medium",
        ]
        for sel in headline_selectors:
            try:
                el = page.query_selector(sel)
                if el:
                    t = el.inner_text().strip()
                    if t and len(t) > 3:
                        headline = t
                        break
            except Exception:
                pass

        # Try to get current position from experience section
        current_company = ""
        experience_selectors = [
            "#experience ~ .pvs-list__container li:first-child .t-14.t-normal",
            "section[id='experience'] li:first-child span[aria-hidden='true']",
            ".pvs-entity__summary-info--background-section span[aria-hidden='true']",
        ]
        for sel in experience_selectors:
            try:
                els = page.query_selector_all(sel)
                for el in els[:5]:
                    t = el.inner_text().strip()
                    # Company name lines typically don't contain "·" year ranges
                    if t and "Present" not in t and len(t) > 1:
                        current_company = t
                        break
                if current_company:
                    break
            except Exception:
                pass

        # Fallback: page title often contains "Name - Role at Company - LinkedIn"
        if not current_company and not headline:
            try:
                title = page.title()
                if " - LinkedIn" in title:
                    parts = title.replace(" | LinkedIn", "").replace(" - LinkedIn", "").split(" - ")
                    if len(parts) >= 2:
                        headline = " - ".join(parts[1:])
            except Exception:
                pass

        return {"headline": headline, "current_company": current_company, "status": "scraped"}

    except Exception as e:
        logger.error(f"Error visiting {li_url}: {e}")
        return {"headline": "", "current_company": "", "status": "error"}


def determine_status(contact: dict, scraped: dict) -> str:
    """Compare Excel company vs scraped LinkedIn data."""
    excel_company = contact["company"].lower().strip()
    headline      = scraped["headline"].lower()
    li_company    = scraped["current_company"].lower()

    if scraped["status"] == "error":
        return "error"
    if not headline and not li_company:
        return "unknown"

    # Check if company name appears in either headline or scraped company
    # Use partial matching (e.g. "Tata Technologies" matches "Tata Technologies Ltd")
    company_words = [w for w in excel_company.split() if len(w) > 3]
    match_target  = headline + " " + li_company

    if any(w in match_target for w in company_words):
        return "confirmed"
    else:
        return "moved"


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def run(limit: int = None, dry_run: bool = False, headless: bool = True):
    contacts   = load_contacts_with_linkedin()
    done_emails = load_checkpoint()

    # Filter out already-checked
    pending = [c for c in contacts if c["email"] not in done_emails]
    if limit:
        pending = pending[:limit]

    logger.info(f"Total: {len(contacts)} | Already done: {len(done_emails)} | To check: {len(pending)}")

    if dry_run:
        print(f"\nDRY RUN — would verify {len(pending)} contacts:")
        for c in pending[:10]:
            print(f"  {c['name']:<30} {c['company']:<35} {c['linkedin_url'][:60]}")
        if len(pending) > 10:
            print(f"  ... and {len(pending) - 10} more")
        return

    if not pending:
        logger.info("Nothing to do — all contacts already verified.")
        return

    # Write CSV header if file doesn't exist
    csv_exists = Path(OUTPUT_CSV).exists()
    csv_file   = open(OUTPUT_CSV, "a", newline="", encoding="utf-8")
    writer     = csv.DictWriter(csv_file, fieldnames=[
        "name", "email", "company_excel", "designation", "linkedin_url",
        "headline_linkedin", "current_company_linkedin", "status", "source"
    ])
    if not csv_exists:
        writer.writeheader()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
        )
        page = context.new_page()

        try:
            linkedin_login(page)

            confirmed = moved = unknown = errors = 0

            for i, contact in enumerate(pending, 1):
                logger.info(f"[{i}/{len(pending)}] {contact['name']} @ {contact['company']}")

                scraped = get_current_company(page, contact["linkedin_url"], contact["name"])
                status  = determine_status(contact, scraped)

                if status == "confirmed":   confirmed += 1
                elif status == "moved":     moved += 1
                elif status == "error":     errors += 1
                else:                       unknown += 1

                writer.writerow({
                    "name":                     contact["name"],
                    "email":                    contact["email"],
                    "company_excel":            contact["company"],
                    "designation":              contact["designation"],
                    "linkedin_url":             contact["linkedin_url"],
                    "headline_linkedin":        scraped["headline"],
                    "current_company_linkedin": scraped["current_company"],
                    "status":                   status,
                    "source":                   contact["source"],
                })
                csv_file.flush()
                save_checkpoint(contact["email"])

                logger.info(f"   -> status: {status} | headline: {scraped['headline'][:80]}")

                # Human-like delay between profiles
                delay = random.uniform(3, 6)
                # Every 30 profiles, take a longer break
                if i % 30 == 0:
                    delay = random.uniform(20, 35)
                    logger.info(f"   [Rate limit pause: {delay:.0f}s]")
                time.sleep(delay)

        except KeyboardInterrupt:
            logger.info("Interrupted. Progress saved. Run again to resume.")
        finally:
            browser.close()
            csv_file.close()

    print(f"\n{'='*60}")
    print(f"VERIFICATION COMPLETE")
    print(f"  Confirmed (still there) : {confirmed}")
    print(f"  Moved / changed company : {moved}")
    print(f"  Unknown (no data)       : {unknown}")
    print(f"  Errors                  : {errors}")
    print(f"  Results saved to        : {OUTPUT_CSV}")
    print(f"{'='*60}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify HR contacts are still at their companies via LinkedIn")
    parser.add_argument("--limit",    type=int,  default=None,  help="Max profiles to check (default: all)")
    parser.add_argument("--dry-run",  action="store_true",      help="Preview contacts without opening browser")
    parser.add_argument("--visible",  action="store_true",      help="Show browser window (useful for debugging CAPTCHAs)")
    args = parser.parse_args()

    run(limit=args.limit, dry_run=args.dry_run, headless=not args.visible)
