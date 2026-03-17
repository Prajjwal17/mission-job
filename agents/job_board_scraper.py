# agents/job_board_scraper.py
# ============================================================
# Job Board Scraper — Naukri API + Internshala + TimesJobs
# ============================================================

import re
import json
import time
import logging
import requests
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BASE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "application/json, text/html,*/*",
    "Referer": "https://www.naukri.com/",
}


# ─────────────────────────────────────────────
# NAUKRI  — internal JSON API
# ─────────────────────────────────────────────
def scrape_naukri(keywords: list[str], location: str = "India", max_jobs: int = 30) -> list[dict]:
    """Scrape Naukri using Playwright (site is fully JS-rendered)."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.error("Playwright not installed. Run: pip install playwright && playwright install chromium")
        return []

    jobs = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=BASE_HEADERS["User-Agent"])
        page = context.new_page()

        for keyword in keywords:
            if len(jobs) >= max_jobs:
                break

            slug_kw = re.sub(r"[^a-z0-9]+", "-", keyword.lower()).strip("-")
            slug_loc = re.sub(r"[^a-z0-9]+", "-", location.lower()).strip("-")
            url = f"https://www.naukri.com/{slug_kw}-jobs-in-{slug_loc}"

            logger.info(f"[Naukri] {keyword}")
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=20000)
                # Wait for job cards to appear
                page.wait_for_selector("div.srp-jobtuple-wrapper, article.jobTuple", timeout=10000)
                time.sleep(2)

                cards = page.query_selector_all("div.srp-jobtuple-wrapper")
                if not cards:
                    cards = page.query_selector_all("article.jobTuple")

                logger.info(f"  {len(cards)} cards")

                for card in cards:
                    if len(jobs) >= max_jobs:
                        break
                    try:
                        title_el = card.query_selector("a.title") or card.query_selector("a.jobTitle")
                        company_el = card.query_selector("a.comp-name") or card.query_selector("a.subTitle")
                        loc_el = card.query_selector("span.locWdth") or card.query_selector("li.location span")
                        exp_el = card.query_selector("span.expwdth") or card.query_selector("li.experience span")

                        if not title_el:
                            continue

                        title = title_el.inner_text().strip()
                        company = company_el.inner_text().strip() if company_el else "Unknown"
                        location_str = loc_el.inner_text().strip() if loc_el else location
                        exp = exp_el.inner_text().strip() if exp_el else ""
                        job_url = title_el.get_attribute("href") or ""

                        jobs.append({
                            "job_title": title,
                            "company": company,
                            "job_url": job_url,
                            "location": location_str,
                            "experience": exp,
                            "skills_required": keyword,
                            "job_description": f"{title} at {company}. Exp: {exp}. Location: {location_str}",
                            "hr_name": "",
                            "hr_email": "",
                            "source": "naukri",
                            "keyword": keyword,
                            "scraped_at": datetime.now().isoformat(),
                        })
                        logger.info(f"  + {title} @ {company}")

                    except Exception as e:
                        logger.debug(f"  Card error: {e}")

                time.sleep(1.5)

            except Exception as e:
                logger.warning(f"  Naukri error for '{keyword}': {e}")

        browser.close()

    return jobs


def _parse_naukri_api_item(item: dict, keyword: str) -> dict | None:
    try:
        title = item.get("title", "").strip()
        company = item.get("companyName", "").strip()
        if not title or not company:
            return None

        job_url = item.get("jdURL", "") or item.get("footerPlaceholderLabel", "")
        if job_url and not job_url.startswith("http"):
            job_url = "https://www.naukri.com" + job_url

        location = ", ".join(item.get("placeholders", [{}])[0].get("label", "India").split(",")[:2])
        experience = ""
        for ph in item.get("placeholders", []):
            if ph.get("type") == "experience":
                experience = ph.get("label", "")

        skills = ", ".join(item.get("tagsAndSkills", "").split(",")[:8])
        snippet = item.get("jobDescription", "")[:300]

        return {
            "job_title": title,
            "company": company,
            "job_url": job_url,
            "location": location,
            "experience": experience,
            "skills_required": skills,
            "job_description": snippet or f"{title} at {company}. Skills: {skills}",
            "hr_name": "",
            "hr_email": "",
            "source": "naukri",
            "keyword": keyword,
            "scraped_at": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.debug(f"  Parse error: {e}")
        return None


# ─────────────────────────────────────────────
# INTERNSHALA  — good for freshers / recent grads
# ─────────────────────────────────────────────
def scrape_internshala(keywords: list[str], max_jobs: int = 20) -> list[dict]:
    jobs = []
    session = requests.Session()
    session.headers.update({
        **BASE_HEADERS,
        "Referer": "https://internshala.com/",
        "X-Requested-With": "XMLHttpRequest",
    })

    for keyword in keywords:
        if len(jobs) >= max_jobs:
            break

        # Internshala uses slug-based URLs
        slug = re.sub(r"[^a-z0-9]+", "-", keyword.lower()).strip("-")
        url = f"https://internshala.com/jobs/{slug}-jobs"

        logger.info(f"[Internshala] {keyword}")
        try:
            resp = session.get(url, timeout=15)
            if resp.status_code != 200:
                logger.warning(f"  HTTP {resp.status_code}")
                time.sleep(2)
                continue

            soup = BeautifulSoup(resp.text, "html.parser")
            cards = soup.select("div.individual_internship")
            logger.info(f"  {len(cards)} results")

            for card in cards:
                if len(jobs) >= max_jobs:
                    break
                job = _parse_internshala_card(card, keyword)
                if job:
                    jobs.append(job)
                    logger.info(f"  + {job['job_title']} @ {job['company']}")

            time.sleep(1.5)

        except Exception as e:
            logger.error(f"  Error: {e}")

    return jobs


def _parse_internshala_card(card, keyword: str) -> dict | None:
    try:
        title_el = card.select_one("h3 a") or card.select_one(".job-title a")
        if not title_el:
            return None
        title = title_el.get_text(strip=True)
        job_url = "https://internshala.com" + (title_el.get("href", ""))

        company_el = card.select_one("p.company-name a") or card.select_one(".company-name")
        company = company_el.get_text(strip=True) if company_el else "Unknown"

        loc_el = card.select_one("span.location_link") or card.select_one(".locations span")
        location = loc_el.get_text(strip=True) if loc_el else "India"

        stipend_el = card.select_one("span.stipend") or card.select_one(".stipend")
        stipend = stipend_el.get_text(strip=True) if stipend_el else ""

        return {
            "job_title": title,
            "company": company,
            "job_url": job_url,
            "location": location,
            "experience": "Fresher / Entry Level",
            "skills_required": keyword,
            "job_description": f"{title} at {company}. Location: {location}. Stipend/Salary: {stipend}",
            "hr_name": "",
            "hr_email": "",
            "source": "internshala",
            "keyword": keyword,
            "scraped_at": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.debug(f"  Parse error: {e}")
        return None


# ─────────────────────────────────────────────
# COMBINED SCRAPE + SAVE
# ─────────────────────────────────────────────
def scrape_all_boards(
    keywords: list[str],
    location: str = "India",
    max_per_board: int = 20,
    output_dir: str = "output",
) -> str:
    all_jobs = []

    logger.info("\n" + "="*50)
    # NOTE: Naukri uses heavy bot detection — disabled by default.
    # Re-enable by passing include_naukri=True if you have a workaround.
    naukri_jobs: list = []

    logger.info("Starting Internshala scrape...")
    internshala_jobs = scrape_internshala(keywords, max_per_board)

    all_jobs = naukri_jobs + internshala_jobs

    # Deduplicate by (title lowered, company lowered)
    seen = set()
    unique_jobs = []
    for j in all_jobs:
        key = (j["job_title"].lower()[:60], j["company"].lower()[:40])
        if key not in seen:
            seen.add(key)
            unique_jobs.append(j)

    Path(output_dir).mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = f"{output_dir}/jobs_{ts}.json"

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(unique_jobs, f, indent=2, ensure_ascii=False)

    summary = (
        f"\n{'='*50}\n"
        f"SCRAPE COMPLETE\n"
        f"  Internshala : {len(internshala_jobs)}\n"
        f"  Unique total: {len(unique_jobs)}\n"
        f"  Saved to    : {filepath}\n"
        f"{'='*50}"
    )
    logger.info(summary)
    return filepath


# ─────────────────────────────────────────────
# CLI ENTRYPOINT
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s %(message)s",
        datefmt="%H:%M:%S",
    )

    from config import JOB_KEYWORDS, JOB_LOCATION

    filepath = scrape_all_boards(
        keywords=JOB_KEYWORDS,
        location=JOB_LOCATION,
        max_per_board=20,
        output_dir="output",
    )

    with open(filepath, encoding="utf-8") as f:
        jobs = json.load(f)

    print(f"\nTotal unique jobs found: {len(jobs)}\n")
    for i, j in enumerate(jobs, 1):
        print(
            f"{i:>3}. [{j['source'].upper():12}] {j['job_title']} @ {j['company']}"
            f"\n       {j.get('location','')}"
            + (f" | Exp: {j['experience']}" if j.get("experience") else "")
            + (f"\n       Skills: {j.get('skills_required','')[:80]}" if j.get("skills_required") else "")
            + (f"\n       {j['job_url'][:90]}" if j.get("job_url") else "")
            + "\n"
        )
