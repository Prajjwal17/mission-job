# agents/scraper_agent.py
# ============================================================
# AGENT 1: SCRAPER AGENT
# Handles both manual JD input and automated LinkedIn scraping
# ============================================================

import json
import time
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# MANUAL MODE: Parse a pasted JD block
# ─────────────────────────────────────────────
def parse_manual_input(raw_text: str) -> dict:
    """
    User pastes a raw block of text containing JD + HR contact.
    This function structures it into a clean dict.

    Expected input format (flexible):
        JOB TITLE: Senior Data Analyst
        COMPANY: Razorpay
        JD: <full job description text>
        HR NAME: Priya Sharma
        HR EMAIL: priya.sharma@razorpay.com
        HR LINKEDIN: https://linkedin.com/in/priyasharma
    """
    result = {
        "job_title": "",
        "company": "",
        "job_description": "",
        "hr_name": "",
        "hr_email": "",
        "hr_linkedin": "",
        "source": "manual",
        "scraped_at": datetime.now().isoformat()
    }

    lines = raw_text.strip().split("\n")
    jd_lines = []
    in_jd = False

    for line in lines:
        lower = line.lower().strip()

        if lower.startswith("job title:"):
            result["job_title"] = line.split(":", 1)[1].strip()
        elif lower.startswith("company:"):
            result["company"] = line.split(":", 1)[1].strip()
        elif lower.startswith("jd:") or lower.startswith("job description:"):
            in_jd = True
            jd_content = line.split(":", 1)[1].strip()
            if jd_content:
                jd_lines.append(jd_content)
        elif lower.startswith("hr name:"):
            in_jd = False
            result["hr_name"] = line.split(":", 1)[1].strip()
        elif lower.startswith("hr email:"):
            result["hr_email"] = line.split(":", 1)[1].strip()
        elif lower.startswith("hr linkedin:"):
            result["hr_linkedin"] = line.split(":", 1)[1].strip()
        elif in_jd:
            jd_lines.append(line)

    result["job_description"] = "\n".join(jd_lines).strip()

    # Validate minimum required fields
    if not result["job_description"]:
        raise ValueError("Job description is empty. Please include 'JD:' in your input.")
    if not result["company"]:
        raise ValueError("Company name missing. Please include 'COMPANY:' in your input.")

    logger.info(f"✅ Manual input parsed: {result['job_title']} @ {result['company']}")
    return result


# ─────────────────────────────────────────────
# AUTOMATED MODE: Scrape LinkedIn
# ─────────────────────────────────────────────
def scrape_linkedin_jobs(keywords: list, location: str, max_jobs: int = 10) -> list[dict]:
    """
    Uses Playwright to scrape LinkedIn job listings.
    Returns a list of structured job dicts.

    IMPORTANT: Run `playwright install chromium` before first use.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.error("Playwright not installed. Run: pip install playwright && playwright install chromium")
        return []

    from config import LINKEDIN_EMAIL, LINKEDIN_PASSWORD

    jobs = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        # ── Step 1: Login ──
        logger.info("🔐 Logging into LinkedIn...")
        page.goto("https://www.linkedin.com/login", wait_until="networkidle")
        page.fill("#username", LINKEDIN_EMAIL)
        page.fill("#password", LINKEDIN_PASSWORD)
        page.click("[type=submit]")
        page.wait_for_load_state("networkidle")
        time.sleep(3)

        if "checkpoint" in page.url or "challenge" in page.url:
            logger.warning("⚠️  LinkedIn CAPTCHA detected. Solve it manually and rerun.")
            browser.close()
            return []

        # ── Step 2: Search jobs for each keyword ──
        for keyword in keywords:
            if len(jobs) >= max_jobs:
                break

            search_url = (
                f"https://www.linkedin.com/jobs/search/"
                f"?keywords={keyword.replace(' ', '%20')}"
                f"&location={location.replace(' ', '%20')}"
                f"&f_TPR=r86400"   # Posted in last 24 hours
                f"&sortBy=DD"       # Sort by date
            )

            logger.info(f"🔍 Scraping: {keyword} in {location}")
            page.goto(search_url, wait_until="networkidle")
            time.sleep(2)

            # Scroll to load more jobs
            for _ in range(3):
                page.keyboard.press("End")
                time.sleep(1)

            job_cards = page.query_selector_all(".job-search-card")
            logger.info(f"   Found {len(job_cards)} job cards")

            for card in job_cards[:max_jobs]:
                try:
                    title_el = card.query_selector(".job-search-card__title")
                    company_el = card.query_selector(".job-search-card__company-name")
                    link_el = card.query_selector("a.job-search-card__title-link")

                    if not (title_el and company_el and link_el):
                        continue

                    job_title = title_el.inner_text().strip()
                    company = company_el.inner_text().strip()
                    job_url = link_el.get_attribute("href")

                    # ── Step 3: Open each job and scrape full JD ──
                    jd_page = context.new_page()
                    jd_page.goto(job_url, wait_until="networkidle")
                    time.sleep(2)

                    # Expand "Show more" if present
                    try:
                        jd_page.click(".jobs-description__footer-button", timeout=3000)
                        time.sleep(1)
                    except Exception:
                        pass

                    jd_el = jd_page.query_selector(".jobs-description__content")
                    jd_text = jd_el.inner_text().strip() if jd_el else ""

                    # ── Step 4: Try to find HR contact ──
                    hr_name, hr_email, hr_linkedin = _extract_hr_contact(jd_page, jd_text)
                    jd_page.close()

                    job = {
                        "job_title": job_title,
                        "company": company,
                        "job_url": job_url,
                        "job_description": jd_text,
                        "hr_name": hr_name,
                        "hr_email": hr_email,
                        "hr_linkedin": hr_linkedin,
                        "source": "linkedin_auto",
                        "scraped_at": datetime.now().isoformat()
                    }

                    jobs.append(job)
                    logger.info(f"   ✅ Scraped: {job_title} @ {company}")

                    if len(jobs) >= max_jobs:
                        break

                except Exception as e:
                    logger.warning(f"   ⚠️  Failed to scrape a card: {e}")
                    continue

        browser.close()

    logger.info(f"✅ Scraper Agent complete. Total jobs: {len(jobs)}")
    return jobs


def _extract_hr_contact(page, jd_text: str) -> tuple[str, str, str]:
    """
    Attempts to extract HR name, email, and LinkedIn from the job page.
    Falls back to empty strings if not found.
    """
    import re

    hr_name = ""
    hr_email = ""
    hr_linkedin = ""

    # Check for email in JD text
    email_match = re.search(r"[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}", jd_text)
    if email_match:
        hr_email = email_match.group()

    # Check for recruiter card on LinkedIn job page
    try:
        recruiter_el = page.query_selector(".hirer-card__hirer-information")
        if recruiter_el:
            name_el = recruiter_el.query_selector("span.hirer-card__hirer-name")
            link_el = recruiter_el.query_selector("a")
            if name_el:
                hr_name = name_el.inner_text().strip()
            if link_el:
                hr_linkedin = link_el.get_attribute("href") or ""
    except Exception:
        pass

    return hr_name, hr_email, hr_linkedin


# ─────────────────────────────────────────────
# SAVE scraped jobs to JSON
# ─────────────────────────────────────────────
def save_jobs(jobs: list[dict], output_dir: str = "output") -> str:
    Path(output_dir).mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = f"{output_dir}/scraped_jobs_{timestamp}.json"
    with open(filepath, "w") as f:
        json.dump(jobs, f, indent=2)
    logger.info(f"💾 Jobs saved to {filepath}")
    return filepath
