# agents/drive_agent.py
# ============================================================
# AGENT 5: GOOGLE DRIVE UPLOAD AGENT
# Uploads the generated PDF to a specified Google Drive folder
# Uses a Service Account (no OAuth flow needed)
# ============================================================

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def upload_to_drive(pdf_path: str, job_title: str, company: str, credentials_path: str, folder_id: str) -> str:
    """
    Uploads a PDF file to Google Drive.

    Setup (one-time):
    1. Go to Google Cloud Console → APIs & Services → Enable "Google Drive API"
    2. Create a Service Account → Download JSON key → Save as credentials/gdrive_service_account.json
    3. Share your target Drive folder with the service account email (Editor access)
    4. Copy the folder ID from the Drive URL

    Args:
        pdf_path: Local path to the PDF file
        job_title: Used for the Drive filename
        company: Used for the Drive filename
        credentials_path: Path to service account JSON
        folder_id: Google Drive folder ID

    Returns:
        Shareable Drive link, or empty string on failure
    """
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
    except ImportError:
        logger.error(
            "Google API libraries not installed.\n"
            "Run: pip install google-auth google-auth-httplib2 google-api-python-client"
        )
        return ""

    creds_path = Path(credentials_path)
    if not creds_path.exists():
        logger.error(f"Service account credentials not found at: {credentials_path}")
        logger.error("See setup instructions in the docstring above.")
        return ""

    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        logger.error(f"PDF not found: {pdf_path}")
        return ""

    try:
        # ── Authenticate ──
        SCOPES = ["https://www.googleapis.com/auth/drive.file"]
        credentials = service_account.Credentials.from_service_account_file(
            str(creds_path), scopes=SCOPES
        )
        service = build("drive", "v3", credentials=credentials)

        # ── Upload ──
        drive_filename = f"PRAJJWAL_PANDEY_{company}_{job_title}.pdf"
        file_metadata = {
            "name": drive_filename,
            "parents": [folder_id]
        }
        media = MediaFileUpload(str(pdf_file), mimetype="application/pdf")

        uploaded = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id, webViewLink"
        ).execute()

        file_id = uploaded.get("id")
        drive_link = uploaded.get("webViewLink", f"https://drive.google.com/file/d/{file_id}/view")

        logger.info(f"✅ Uploaded to Drive: {drive_filename}")
        logger.info(f"   Link: {drive_link}")
        return drive_link

    except Exception as e:
        logger.error(f"❌ Drive upload failed: {e}")
        return ""
