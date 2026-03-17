# config.example.py
# ============================================================
# Copy this file to config.py and fill in your credentials.
# NEVER commit config.py — it contains secrets.
# ============================================================

# --- Claude API ---
CLAUDE_API_KEY = "sk-ant-..."
CLAUDE_MODEL = "claude-haiku-4-5-20251001"
CLAUDE_MAX_TOKENS = 2048

# --- Gmail SMTP ---
GMAIL_ADDRESS = "your@gmail.com"
GMAIL_APP_PASSWORD = "xxxx xxxx xxxx xxxx"  # 16-char Google App Password

# --- Google Drive ---
GOOGLE_DRIVE_CREDENTIALS_PATH = "credentials/gdrive_service_account.json"
GOOGLE_DRIVE_FOLDER_ID = "YOUR_GDRIVE_FOLDER_ID_HERE"

# --- LinkedIn Scraping ---
LINKEDIN_EMAIL = "your@gmail.com"
LINKEDIN_PASSWORD = "your_password"

# --- Scheduler ---
SCRAPE_SCHEDULE = "0 9 * * *"  # Every day at 9 AM

# --- Job Search Keywords ---
JOB_KEYWORDS = [
    "Python Developer",
    "Data Analyst",
    "AI Engineer",
    "Machine Learning Engineer",
    "LangChain Developer",
    "Generative AI Engineer",
    "RAG Engineer",
    "Full Stack Developer",
    "React Developer",
    "Junior Data Scientist",
    "Prompt Engineer",
    "AI Intern",
    "Data Analyst Intern",
    "Python Intern",
]
JOB_LOCATION = "India"
MAX_JOBS_PER_RUN = 30

# --- Excel HR Outreach ---
EXCEL_FILE_PATH = r"path\to\your\HR_Contacts.xlsx"
DAILY_EMAIL_LIMIT = 50
SENT_LOG_PATH = "logs/sent_emails.json"

# --- Output Paths ---
OUTPUT_DIR = "output"
LOGS_DIR = "logs"
