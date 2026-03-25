# 🤖 Job Application Automation Pipeline
### Prajjwal Pandey — ATS-Optimized, AI-Tailored, Auto-Mailed

---

## 🗺️ Architecture Overview

```
                        ┌─────────────────────────────────────┐
                        │           TRIGGER                   │
                        │  Manual (paste JD)  OR  Scheduled   │
                        └──────────────┬──────────────────────┘
                                       │
                        ┌──────────────▼──────────────────────┐
                        │        AGENT 1: SCRAPER             │
                        │  Playwright → LinkedIn/AmbitionBox  │
                        │  Extracts: JD + HR Name + Email     │
                        └──────────────┬──────────────────────┘
                                       │
                        ┌──────────────▼──────────────────────┐
                        │       AGENT 2: TAILOR (Claude)      │
                        │  Reads: master_resume + projects    │
                        │  Applies: ATS rules + X-Y-Z formula │
                        │  Outputs: Markdown resume + Email   │
                        └──────────────┬──────────────────────┘
                                       │
                        ┌──────────────▼──────────────────────┐
                        │       AGENT 3: PDF GENERATOR        │
                        │  Markdown → Styled PDF (WeasyPrint) │
                        └──────────────┬──────────────────────┘
                                       │
                          ┌────────────┴────────────┐
                          │                         │
           ┌──────────────▼───────┐   ┌─────────────▼──────────────┐
           │  AGENT 4: MAILER     │   │  AGENT 5: GOOGLE DRIVE     │
           │  Gmail SMTP + PDF    │   │  Auto-upload + get link     │
           │  Attach → Send HR    │   │                            │
           └──────────────────────┘   └────────────────────────────┘
```

---

## 📁 Project Structure

```
job_pipeline/
├── main.py                  # 🧠 Orchestrator — run this
├── config.py                # 🔑 Your API keys & settings
├── requirements.txt         # 📦 All dependencies
│
├── agents/
│   ├── scraper_agent.py     # Agent 1: LinkedIn scraper + manual parser
│   ├── tailor_agent.py      # Agent 2: Claude API resume tailor
│   ├── pdf_agent.py         # Agent 3: Markdown → PDF converter
│   ├── mailer_agent.py      # Agent 4: Gmail cold emailer
│   └── drive_agent.py       # Agent 5: Google Drive uploader
│
├── knowledge/
│   ├── master_resume.md     # Your base resume
│   ├── detailed_projects.md # Rich project notes (Digital Pothi, Teerth, etc.)
│   └── ats_rules.md         # No-laziness tailoring rules
│
├── output/                  # Generated PDFs and JSON job data
├── logs/                    # Daily log files
└── credentials/
    └── gdrive_service_account.json   # (You create this — see Step 4)
```

---

## ⚡ Setup Guide (Step by Step)

### Step 1: Install Python dependencies

```bash
cd job_pipeline
pip install -r requirements.txt
playwright install chromium
```

---

### Step 2: Configure your credentials

Open `config.py` and fill in:

```python
CLAUDE_API_KEY = "sk-ant-..."          # From console.anthropic.com
GMAIL_ADDRESS = "prajjwalp1707@gmail.com"
GMAIL_APP_PASSWORD = "xxxx xxxx xxxx xxxx"  # See below ↓
LINKEDIN_EMAIL = "your@email.com"
LINKEDIN_PASSWORD = "yourpassword"
```

**Getting Gmail App Password:**
1. Go to: https://myaccount.google.com/security
2. Enable 2-Step Verification (if not already on)
3. Search for "App passwords" → Select "Mail" → "Windows Computer"
4. Copy the 16-character password → paste in config.py (no spaces)

---

### Step 3: Get your Claude API Key

1. Go to: https://console.anthropic.com/
2. Click "API Keys" → Create new key
3. Copy and paste into `config.py`

---

### Step 4: Setup Google Drive (optional but recommended)

1. Go to: https://console.cloud.google.com/
2. Create a new project (or use existing)
3. Enable: **Google Drive API**
4. Go to: IAM & Admin → Service Accounts → Create Service Account
5. Download the JSON key → save as `credentials/gdrive_service_account.json`
6. Create a folder in your Google Drive called "Job Applications"
7. Share that folder with the service account email (it looks like `name@project.iam.gserviceaccount.com`) with **Editor** access
8. Copy the folder ID from the Drive URL:
   `https://drive.google.com/drive/folders/THIS_IS_THE_FOLDER_ID`
9. Paste into `config.py` as `GOOGLE_DRIVE_FOLDER_ID`

---

## 🚀 Running the Pipeline

### Option A: Manual Mode (Recommended to start)

```bash
python main.py --manual --dry-run    # Test first (no email sent)
python main.py --manual              # Real run (sends email)
```

When prompted, paste your job data in this format:

```
JOB TITLE: Senior Data Analyst
COMPANY: Razorpay
JD:
We are looking for a data analyst with expertise in Python, SQL,
Pandas, and data visualization. The ideal candidate will build
dashboards and work with cross-functional teams...
[paste the full JD here]
HR NAME: Priya Sharma
HR EMAIL: priya.sharma@razorpay.com
HR LINKEDIN: https://linkedin.com/in/priyasharma
END
```

Type `END` on a new line when done.

---

### Option B: Auto Mode (LinkedIn Scraping)

```bash
python main.py --auto --dry-run     # Test scraping + tailoring (no email)
python main.py --auto               # Full run
```

Configure which jobs to search in `config.py`:
```python
JOB_KEYWORDS = ["Data Analyst", "Python Developer", "ML Engineer"]
JOB_LOCATION = "India"
MAX_JOBS_PER_RUN = 10
```

---

### Option C: Daily Scheduled Mode

```bash
python main.py --schedule           # Runs daily at 9 AM (set in config.py)
```

To keep it running in background on Linux:
```bash
nohup python main.py --schedule > logs/scheduler.log 2>&1 &
```

---

## 🧪 Testing Checklist

Run these in order to validate the full pipeline:

```bash
# 1. Test resume tailoring only (no email, no PDF, costs ~$0.01 Claude API)
python main.py --manual --dry-run

# 2. Test full pipeline without sending email
python main.py --manual --dry-run

# 3. Full real run with one job
python main.py --manual
```

---

## 🔧 Troubleshooting

| Problem | Fix |
|---|---|
| `anthropic.AuthenticationError` | Check `CLAUDE_API_KEY` in config.py |
| `SMTPAuthenticationError` | Regenerate Gmail App Password, ensure 2FA is on |
| `playwright._impl._errors.Error` | Run `playwright install chromium` |
| LinkedIn shows CAPTCHA | Run in non-headless mode: change `headless=True` to `headless=False` in scraper_agent.py |
| WeasyPrint PDF error | Run `pip install weasyprint` or install system deps: `sudo apt install libpango-1.0-0` |
| Drive upload `credentials not found` | Check path in config.py matches your JSON file location |

---

## 💡 Pro Tips

1. **Start with `--dry-run`** every time you test a new JD format. This calls Claude API and shows you the tailored resume + email preview without actually sending anything.

2. **LinkedIn detection**: If LinkedIn blocks your scraper, switch to **AmbitionBox** (much less aggressive bot detection). The scraper logic is the same.

3. **Cheap Claude usage**: Each resume tailoring call costs ~$0.02-0.05. For 10 jobs/day that's ₹15-40/day. Very affordable.

4. **Improve the knowledge files**: The better your `detailed_projects.md`, the better Claude tailors. Add metrics, specific numbers, and technologies to each project.
