# 🤖 Claude Code — Setup & Run Prompt
### Copy-paste this ENTIRE block into Claude Code when you open the project folder.

---

## THE PROMPT (copy everything below this line)

---

You are taking over a Python-based Job Application Automation Pipeline. Your job is to set it up completely and get it running. Here is the full context and your task list.

---

### WHAT THIS PROJECT DOES

A 5-agent pipeline that:
1. **Scraper Agent** — Accepts a manually pasted Job Description OR auto-scrapes LinkedIn
2. **Tailor Agent** — Calls Claude API with resume knowledge files → returns ATS-optimized resume (Markdown) + cold email
3. **PDF Agent** — Converts the Markdown resume to a styled PDF using WeasyPrint
4. **Mailer Agent** — Sends the cold email with PDF attached via Gmail SMTP
5. **Drive Agent** — Uploads the PDF to a Google Drive folder

---

### YOUR TASK LIST (execute in this order)

**STEP 1 — Read all files first**
Read these files in full before doing anything else:
- `README.md` — Full setup guide
- `config.py` — All credentials and settings (currently has placeholders)
- `main.py` — The orchestrator
- `agents/scraper_agent.py`
- `agents/tailor_agent.py`
- `agents/pdf_agent.py`
- `agents/mailer_agent.py`
- `agents/drive_agent.py`
- `knowledge/master_resume.md`
- `knowledge/detailed_projects.md`
- `knowledge/ats_rules.md`

**STEP 2 — Install all dependencies**
```bash
pip install -r requirements.txt
playwright install chromium
```
If any install fails, debug and fix it. Try alternative install methods if needed (e.g., `pip install --break-system-packages`, `apt install` for system deps like libpango for WeasyPrint).

**STEP 3 — Ask me for credentials (do NOT skip this)**
Ask me to provide the following one at a time:
1. Claude API Key (`sk-ant-...`)
2. Gmail App Password (16 characters)
3. LinkedIn Email + Password (for auto scraping mode)
4. Google Drive Folder ID (optional — skip if I don't have it yet)

Once I provide each one, update `config.py` immediately.

**STEP 4 — Create required directories**
```bash
mkdir -p output logs credentials
```

**STEP 5 — Run a dry-run test in manual mode**
```bash
python main.py --manual --dry-run
```
When prompted, paste this sample job to test:
```
JOB TITLE: Data Analyst
COMPANY: TestCompany
JD:
We are looking for a Data Analyst with strong skills in Python, SQL, Pandas, and data visualization. The candidate will build dashboards, run EDA pipelines, and present insights to stakeholders. Experience with machine learning is a plus.
HR NAME: Test HR
HR EMAIL: test@testcompany.com
END
```
- Confirm the resume and cold email output look correct
- Confirm no errors in the pipeline
- Show me the full resume and email output

**STEP 6 — Fix any errors**
If anything fails (WeasyPrint system deps, Playwright install, import errors), debug and fix autonomously. Check logs in the `logs/` folder. Try alternative approaches if the primary one fails.

**STEP 7 — Report back**
When the dry run is successful, tell me:
- ✅ What is working
- ⚠️ What still needs my input (Drive credentials, etc.)
- 🚀 The exact command to run for a real job application

---

### CONSTRAINTS
- Never hardcode my credentials anywhere except `config.py`
- Never send a real email without my explicit confirmation
- If LinkedIn scraping gets blocked by a CAPTCHA, tell me and switch to manual mode
- Keep all generated resumes and PDFs in the `output/` folder
- Log everything to `logs/`

---

### AFTER SETUP IS COMPLETE

Once working, here is the ongoing usage:

**Manual mode (I paste JD):**
```bash
python main.py --manual
```

**Auto mode (scrapes LinkedIn daily jobs):**
```bash
python main.py --auto
```

**Scheduled daily mode (runs at 9 AM):**
```bash
python main.py --schedule
```

**Test without sending email:**
```bash
python main.py --manual --dry-run
```

---

Now begin. Start with STEP 1 — read all the files.
