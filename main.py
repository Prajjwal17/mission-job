# main.py
# ============================================================
# MAIN ORCHESTRATOR
# Runs the full pipeline: Scrape → Tailor → PDF → Mail → Drive
#
# USAGE:
#   Scrape mode:   python main.py --scrape --dry-run --limit 3
#   Manual mode:   python main.py --manual
#   Auto mode:     python main.py --auto          (LinkedIn, often blocked)
#   Schedule:      python main.py --schedule      (runs daily at 9 AM)
#   Excel HR:      python main.py --excel-hr --dry-run
#   Dry run:       add --dry-run to any mode to preview without sending
# ============================================================

import argparse
import io
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

# ── Force UTF-8 on Windows (fixes emoji/arrow encoding errors) ──
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ── Setup logging ──
Path("logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f"logs/pipeline_{datetime.now().strftime('%Y%m%d')}.log", encoding="utf-8")
    ]
)
logger = logging.getLogger(__name__)


# ── Import config ──
try:
    import config
except ImportError:
    logger.error("config.py not found. Copy config.py and fill in your credentials.")
    sys.exit(1)

# ── Import agents ──
from agents.scraper_agent import parse_manual_input, scrape_linkedin_jobs, save_jobs
from agents.tailor_agent import tailor_resume_and_email, generate_pitch_email
from agents.pdf_agent import markdown_to_pdf
from agents.mailer_agent import send_cold_email
from agents.drive_agent import upload_to_drive
from agents.excel_reader_agent import (
    read_job_links, read_hr_contacts, scrape_jd_from_url,
    load_sent_log, save_sent_log
)
from agents.job_board_scraper import scrape_all_boards


# ─────────────────────────────────────────────
# PIPELINE: Process a single job
# ─────────────────────────────────────────────
def process_job(job: dict, dry_run: bool = False) -> dict:
    """
    Runs the full pipeline for one job.
    Returns a result summary dict.
    """
    company = job.get("company", "Unknown")
    job_title = job.get("job_title", "Unknown")

    logger.info(f"\n{'='*60}")
    logger.info(f"🚀 Processing: {job_title} @ {company}")
    logger.info(f"{'='*60}")

    result = {
        "company": company,
        "job_title": job_title,
        "hr_email": job.get("hr_email", ""),
        "status": "failed",
        "pdf_path": "",
        "drive_link": "",
        "email_sent": False
    }

    # ── STEP 1: Tailor resume + generate cold email ──
    logger.info("🤖 Step 1: Tailoring resume with Claude...")
    try:
        tailored = tailor_resume_and_email(job, api_key=config.CLAUDE_API_KEY)
    except Exception as e:
        logger.error(f"❌ Tailor Agent failed: {e}")
        return result

    # Preview the tailored content
    print("\n" + "─"*60)
    print("📋 TAILORED RESUME PREVIEW (first 500 chars)")
    print("─"*60)
    print(tailored["resume_markdown"][:500] + "...")
    print("\n📧 COLD EMAIL PREVIEW (first 300 chars)")
    print("─"*60)
    print(tailored["cold_email"][:300] + "...")
    print("─"*60 + "\n")

    # ── STEP 2: Generate PDF ──
    logger.info("📄 Step 2: Generating PDF...")
    try:
        pdf_path = markdown_to_pdf(
            resume_markdown=tailored["resume_markdown"],
            job_title=job_title,
            company=company,
            output_dir=config.OUTPUT_DIR
        )
        result["pdf_path"] = pdf_path
        logger.info(f"   PDF saved: {pdf_path}")
    except Exception as e:
        logger.error(f"❌ PDF Agent failed: {e}")
        # Continue even without PDF

    # ── STEP 3: Upload to Google Drive ──
    logger.info("☁️  Step 3: Uploading to Google Drive...")
    if result["pdf_path"]:
        try:
            drive_link = upload_to_drive(
                pdf_path=result["pdf_path"],
                job_title=job_title,
                company=company,
                credentials_path=config.GOOGLE_DRIVE_CREDENTIALS_PATH,
                folder_id=config.GOOGLE_DRIVE_FOLDER_ID
            )
            result["drive_link"] = drive_link
        except Exception as e:
            logger.warning(f"⚠️  Drive upload failed (non-critical): {e}")

    # ── STEP 4: Send cold email ──
    logger.info("📧 Step 4: Sending cold email...")
    hr_email = job.get("hr_email", "")
    if hr_email or dry_run:
        try:
            sent = send_cold_email(
                hr_email=hr_email if hr_email else "test@example.com",
                cold_email_text=tailored["cold_email"],
                pdf_path=result["pdf_path"],
                sender_email=config.GMAIL_ADDRESS,
                app_password=config.GMAIL_APP_PASSWORD,
                hr_name=job.get("hr_name", ""),
                dry_run=dry_run
            )
            result["email_sent"] = sent
        except Exception as e:
            logger.error(f"❌ Mailer Agent failed: {e}")
    else:
        logger.warning("⚠️  No HR email found. Skipping email. Resume saved locally.")

    result["status"] = "success"
    logger.info(f"✅ Pipeline complete for {job_title} @ {company}")
    return result


# ─────────────────────────────────────────────
# MANUAL MODE
# ─────────────────────────────────────────────
def run_manual_mode(dry_run: bool = False):
    """
    User pastes a JD block in the terminal.
    """
    print("\n" + "="*60)
    print("📋 MANUAL MODE — Paste your job data below")
    print("="*60)
    print("""Format your input like this:
JOB TITLE: Senior Data Analyst
COMPANY: Razorpay
JD:
<paste full job description here>
HR NAME: Priya Sharma
HR EMAIL: priya.sharma@razorpay.com
HR LINKEDIN: https://linkedin.com/in/priyasharma

Type END on a new line when done.
""")

    lines = []
    while True:
        try:
            line = input()
            if line.strip().upper() == "END":
                break
            lines.append(line)
        except EOFError:
            break

    raw_text = "\n".join(lines)
    if not raw_text.strip():
        logger.error("No input provided. Exiting.")
        return

    try:
        job = parse_manual_input(raw_text)
    except ValueError as e:
        logger.error(f"Input parsing error: {e}")
        return

    result = process_job(job, dry_run=dry_run)
    _print_summary([result])


# ─────────────────────────────────────────────
# AUTO MODE (LinkedIn Scraping)
# ─────────────────────────────────────────────
def run_auto_mode(dry_run: bool = False):
    """
    Automatically scrapes LinkedIn for jobs and processes each.
    """
    logger.info("🕷️  AUTO MODE — Scraping LinkedIn...")

    jobs = scrape_linkedin_jobs(
        keywords=config.JOB_KEYWORDS,
        location=config.JOB_LOCATION,
        max_jobs=config.MAX_JOBS_PER_RUN
    )

    if not jobs:
        logger.warning("No jobs found. Check your LinkedIn credentials or try again.")
        return

    # Save raw scraped data
    save_jobs(jobs, output_dir=config.OUTPUT_DIR)
    logger.info(f"📦 Found {len(jobs)} jobs. Processing...")

    results = []
    for i, job in enumerate(jobs, 1):
        logger.info(f"\n[{i}/{len(jobs)}] Starting...")
        result = process_job(job, dry_run=dry_run)
        results.append(result)
        time.sleep(5)  # Rate limit between jobs

    _print_summary(results)


# ─────────────────────────────────────────────
# SCHEDULER MODE
# ─────────────────────────────────────────────
def run_scheduled_mode():
    """
    Runs auto mode on a schedule using the cron expression in config.
    """
    try:
        from apscheduler.schedulers.blocking import BlockingScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        logger.error("APScheduler not installed. Run: pip install apscheduler")
        sys.exit(1)

    scheduler = BlockingScheduler()
    cron_parts = config.SCRAPE_SCHEDULE.split()

    if len(cron_parts) == 5:
        minute, hour, day, month, day_of_week = cron_parts
    else:
        minute, hour, day, month, day_of_week = "0", "9", "*", "*", "*"

    scheduler.add_job(
        run_auto_mode,
        CronTrigger(
            minute=minute,
            hour=hour,
            day=day,
            month=month,
            day_of_week=day_of_week
        ),
        id="job_pipeline",
        name="Daily Job Application Pipeline"
    )

    logger.info(f"⏰ Scheduler started. Running at: {config.SCRAPE_SCHEDULE}")
    logger.info("   Press Ctrl+C to stop.")
    try:
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("Scheduler stopped.")
        scheduler.shutdown()


# ─────────────────────────────────────────────
# EXCEL JOBS MODE — scrape JD from LinkedIn URLs in Excel
# ─────────────────────────────────────────────
def run_excel_jobs_mode(dry_run: bool = False):
    """
    Reads job links from the Excel file, scrapes the full JD from each
    LinkedIn URL, then runs the full tailor → PDF → email pipeline.
    """
    excel_path = config.EXCEL_FILE_PATH
    logger.info(f"Reading job links from: {excel_path}")

    jobs = read_job_links(excel_path)
    if not jobs:
        logger.error("No job links found in Excel. Check EXCEL_FILE_PATH in config.py")
        return

    # Filter active jobs only
    active = [j for j in jobs if j.get('status', '').lower() in ('active', '')]
    logger.info(f"Found {len(active)} active jobs out of {len(jobs)} total")

    results = []
    for i, job in enumerate(active, 1):
        logger.info(f"\n[{i}/{len(active)}] {job['job_title']} @ {job['company']}")

        # Scrape the JD from the LinkedIn URL
        logger.info(f"  Scraping JD from: {job['url']}")
        jd_text = scrape_jd_from_url(job['url'])

        if not jd_text or len(jd_text) < 50:
            logger.warning(f"  Could not scrape JD for {job['company']}. Skipping.")
            continue

        job['job_description'] = jd_text
        logger.info(f"  JD scraped: {len(jd_text)} chars")

        result = process_job(job, dry_run=dry_run)
        results.append(result)
        time.sleep(3)   # polite delay between jobs

    _print_summary(results)


# ─────────────────────────────────────────────
# EXCEL HR MODE — cold outreach to HR contacts from Excel
# ─────────────────────────────────────────────
def run_excel_hr_mode(dry_run: bool = False, daily_limit: int = None):
    """
    Reads HR contacts from the Excel file and sends a personalized
    cold pitch email + base resume PDF to each one.

    Uses a sent-email log to avoid duplicates across runs.
    Respects the DAILY_EMAIL_LIMIT in config.
    """
    excel_path  = config.EXCEL_FILE_PATH
    limit       = daily_limit or config.DAILY_EMAIL_LIMIT
    sent_log    = load_sent_log(config.SENT_LOG_PATH)

    logger.info(f"Reading HR contacts from: {excel_path}")
    contacts = read_hr_contacts(excel_path)

    # Filter out already-contacted
    fresh = [c for c in contacts if c['hr_email'] not in sent_log]
    logger.info(f"Total contacts: {len(contacts)} | Already sent: {len(sent_log)} | Fresh: {len(fresh)}")

    if not fresh:
        logger.info("All contacts already emailed. Nothing to do.")
        return

    batch = fresh[:limit]
    logger.info(f"Sending to {len(batch)} contacts today (limit={limit})")

    # Generate the base resume PDF once (used for all emails)
    from knowledge import _get_base_resume_md
    base_resume_md = _get_base_resume_md()

    results_sent = 0
    newly_sent   = set()

    for i, contact in enumerate(batch, 1):
        company  = contact.get('company') or 'your organisation'
        hr_name  = contact.get('hr_name') or ''
        hr_email = contact['hr_email']

        logger.info(f"[{i}/{len(batch)}] {hr_name or 'HR'} @ {company} <{hr_email}>")

        try:
            # Generate personalised pitch email
            pitch_email = generate_pitch_email(contact, api_key=config.CLAUDE_API_KEY)

            # Generate PDF (base resume, no tailoring for cold outreach)
            pdf_path = markdown_to_pdf(
                resume_markdown=base_resume_md,
                job_title="General Application",
                company=company,
                output_dir=config.OUTPUT_DIR
            )

            # Send (or dry-run preview)
            sent = send_cold_email(
                hr_email=hr_email,
                cold_email_text=pitch_email,
                pdf_path=pdf_path,
                sender_email=config.GMAIL_ADDRESS,
                app_password=config.GMAIL_APP_PASSWORD,
                hr_name=hr_name,
                dry_run=dry_run
            )

            if sent:
                newly_sent.add(hr_email)
                results_sent += 1

        except Exception as e:
            logger.error(f"  Failed for {hr_email}: {e}")
            continue

        time.sleep(2)   # avoid Gmail rate limits

    # Save updated sent log
    if not dry_run:
        save_sent_log(sent_log | newly_sent, config.SENT_LOG_PATH)

    print("\n" + "="*60)
    print(f"EXCEL HR MODE COMPLETE")
    print(f"  Emails sent today : {results_sent}")
    print(f"  Total ever sent   : {len(sent_log) + len(newly_sent)}")
    print(f"  Remaining contacts: {len(fresh) - results_sent}")
    print(f"  Run again tomorrow to send the next batch of {limit}")
    print("="*60)


# ─────────────────────────────────────────────
# SCRAPE MODE — Internshala job board → tailor → PDF → email
# ─────────────────────────────────────────────
def run_scrape_mode(dry_run: bool = False, limit: int = None):
    """
    Scrapes live job postings from Internshala matching your tech stack,
    tailors your resume for each one with Claude, generates a PDF,
    and either sends the cold email (if HR email found) or saves locally.
    """
    max_jobs = limit or config.MAX_JOBS_PER_RUN

    logger.info("=" * 60)
    logger.info("SCRAPE MODE — Internshala Job Board")
    logger.info(f"Keywords : {', '.join(config.JOB_KEYWORDS[:6])}... ({len(config.JOB_KEYWORDS)} total)")
    logger.info(f"Max jobs : {max_jobs}")
    logger.info("=" * 60)

    # ── Step 1: Scrape live jobs ──
    jobs_file = scrape_all_boards(
        keywords=config.JOB_KEYWORDS,
        location=config.JOB_LOCATION,
        max_per_board=max_jobs,
        output_dir=config.OUTPUT_DIR,
    )

    import json as _json
    with open(jobs_file, encoding="utf-8") as f:
        jobs = _json.load(f)

    if not jobs:
        logger.warning("No jobs scraped. Try again later or check your internet connection.")
        return

    logger.info(f"\nScraped {len(jobs)} unique jobs. Starting tailor pipeline...\n")

    results = []
    for i, job in enumerate(jobs, 1):
        logger.info(f"[{i}/{len(jobs)}] {job['job_title']} @ {job['company']} ({job['source']})")

        # Enrich the job_description with skills if snippet is thin
        if len(job.get("job_description", "")) < 80 and job.get("skills_required"):
            job["job_description"] = (
                f"Position: {job['job_title']} at {job['company']}. "
                f"Location: {job.get('location', 'India')}. "
                f"Required skills: {job['skills_required']}. "
                f"Experience: {job.get('experience', 'Fresher / Entry Level')}."
            )

        result = process_job(job, dry_run=dry_run)
        results.append(result)
        time.sleep(2)   # Respect Claude API rate limits

    _print_summary(results)

    # ── Final counts ──
    sent     = sum(1 for r in results if r["email_sent"])
    pdfs     = sum(1 for r in results if r["pdf_path"])
    success  = sum(1 for r in results if r["status"] == "success")
    no_email = sum(1 for r in results if r["status"] == "success" and not r["email_sent"])

    print(f"\nSCRAPE MODE COMPLETE")
    print(f"  Total processed  : {len(results)}")
    print(f"  Tailored + PDF   : {pdfs}")
    print(f"  Emails sent      : {sent}")
    print(f"  Saved (no email) : {no_email}  ← PDFs saved to output/ folder")
    print(f"  Failed           : {len(results) - success}")
    print(f"\nPDFs saved in: {config.OUTPUT_DIR}/")
    print("Tip: Use --manual to paste a JD with HR email and send directly.")


# ─────────────────────────────────────────────
# SUMMARY PRINTER
# ─────────────────────────────────────────────
def _print_summary(results: list):
    print("\n" + "="*60)
    print("📊 PIPELINE SUMMARY")
    print("="*60)
    for r in results:
        status_icon = "✅" if r["status"] == "success" else "❌"
        email_icon = "📧" if r["email_sent"] else "⏭️ "
        drive_icon = "☁️ " if r["drive_link"] else "  "
        print(f"{status_icon} {r['job_title']} @ {r['company']}")
        print(f"   {email_icon} Email: {'Sent to ' + r['hr_email'] if r['email_sent'] else 'Not sent'}")
        print(f"   {drive_icon} Drive: {r['drive_link'] or 'Not uploaded'}")
        print(f"   📄 PDF: {r['pdf_path'] or 'Not generated'}")
    print("="*60)


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Job Application Automation Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --manual              # Paste JD manually
  python main.py --auto                # Scrape LinkedIn
  python main.py --manual --dry-run    # Preview email without sending
  python main.py --schedule            # Run daily on cron schedule
        """
    )
    parser.add_argument("--manual",     action="store_true", help="Manual mode: paste JD in terminal")
    parser.add_argument("--auto",       action="store_true", help="Auto mode: scrape LinkedIn (often blocked)")
    parser.add_argument("--scrape",     action="store_true", help="Scrape mode: Internshala jobs → tailor → PDF → email")
    parser.add_argument("--schedule",   action="store_true", help="Schedule mode: run daily")
    parser.add_argument("--excel-jobs", action="store_true", help="Excel jobs mode: scrape JDs from LinkedIn URLs in Excel")
    parser.add_argument("--excel-hr",   action="store_true", help="Excel HR mode: cold outreach to HR contacts from Excel")
    parser.add_argument("--dry-run",    action="store_true", help="Preview email/PDF without actually sending")
    parser.add_argument("--limit",      type=int, default=None, help="Max jobs/emails to process (overrides config)")

    args = parser.parse_args()

    if args.schedule:
        run_scheduled_mode()
    elif args.scrape:
        run_scrape_mode(dry_run=args.dry_run, limit=args.limit)
    elif args.auto:
        run_auto_mode(dry_run=args.dry_run)
    elif args.manual:
        run_manual_mode(dry_run=args.dry_run)
    elif getattr(args, 'excel_jobs', False):
        run_excel_jobs_mode(dry_run=args.dry_run)
    elif getattr(args, 'excel_hr', False):
        run_excel_hr_mode(dry_run=args.dry_run, daily_limit=args.limit)
    else:
        parser.print_help()
        print("\nRECOMMENDED STARTING POINTS:")
        print("  python main.py --scrape --dry-run --limit 3   # Scrape 3 jobs, preview only")
        print("  python main.py --scrape --limit 10            # Scrape + tailor + save PDFs")
        print("  python main.py --manual --dry-run             # Paste a JD manually")
        print("  python main.py --excel-hr --dry-run           # Cold outreach from Excel")
