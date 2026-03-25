# Job Application Pipeline - Architecture Summary

## Overview
Autonomous 5-stage job application pipeline: Scrape → Tailor → PDF → Email → Track

## Tech Stack
- **Language**: Python 3.11
- **APIs**: Anthropic Claude (tailor), Gmail SMTP (email), BeautifulSoup (scrape)
- **Automation**: Windows Task Scheduler (4x daily), JSON logging
- **Tools**: Playwright (PDF), Pandas (Excel), dnspython (email validation)

## Architecture

```
main.py (orchestrator)
├── agents/
│   ├── scraper_agent.py       → Job board scraping
│   ├── tailor_agent.py        → Claude API resume tailoring
│   ├── pdf_agent.py           → Markdown → PDF conversion
│   ├── mailer_agent.py        → Gmail SMTP delivery
│   └── excel_reader_agent.py  → Excel contact management
├── tools/
│   ├── strategic_filter.py    → Company skill matching
│   ├── email_templates.py     → Skill-specific pitch templates
│   ├── email_verifier.py      → SMTP handshake validation
│   └── linkedin_email_importer.py → CSV → Excel merge
└── config/
    ├── config.py              → API keys, schedules, limits
    └── regional_strategies.py → Geographic targeting
```

## Key Files
- **config.py**: API keys, daily_limit (50), email_delay (3s), schedule (8:30/12:30/4:30/8:30 PM)
- **strategic_target_companies_clean.csv**: 129 companies, 227 HR contacts (vs 8,736)
- **knowledge/master_resume.md**: Base resume (updated with new skills)
- **logs/sent_emails.json**: Tracks sent addresses (prevent duplicates)
- **logs/bounced_emails.json**: Permanent blocklist

## Common Commands

```bash
# Test (dry-run, preview only)
python main.py --excel-hr --dry-run --limit 5

# Send strategic batch (default, 129 companies only)
python main.py --excel-hr --limit 50

# Send all contacts (disable strategic filter)
python main.py --excel-hr --all-contacts --limit 50

# Scrape job boards
python main.py --scrape --limit 10

# Verify email before sending
python tools/email_verifier.py emails.csv
```

## Current Status
- **Mode**: Strategic filtering + skill-specific templates (default)
- **Contacts**: 227 targeted (from 8,736 total)
- **Daily Volume**: 200/day (4 scheduled batches of 50)
- **Last Batch**: 1,031 total sent (March 25, 2026)
- **Response Tracking**: logs/response_log.json + logs/strategic_stats.json

## Recent Updates (March 25)
✅ Strategic filtering: 129 skill-matched companies
✅ Skill-specific templates: 4 areas (AI, CV, FS, DS)
✅ Response tracking: company + skill logging
✅ Hybrid approach: templates + Claude fallback

## Token Optimization
- .claudeignore: Excludes __pycache__, logs, output, .git
- Large files ignored: *.json, *.csv, logs/**
- Focus: Code exploration, not data files
