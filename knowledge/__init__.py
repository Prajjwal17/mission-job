# knowledge/__init__.py
from pathlib import Path

def _get_base_resume_md() -> str:
    """Returns the master resume markdown for use in cold outreach PDFs."""
    path = Path(__file__).parent / "master_resume.md"
    return path.read_text(encoding="utf-8") if path.exists() else ""
