# agents/pdf_agent.py
# ============================================================
# AGENT 3: PDF GENERATOR AGENT
# Converts tailored markdown resume → clean, ATS-friendly PDF
# ============================================================

import logging
import subprocess
import re
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


def _sanitize_filename(name: str) -> str:
    """Remove special chars for safe filenames."""
    return re.sub(r"[^\w\-_]", "_", name)


def markdown_to_pdf(resume_markdown: str, job_title: str, company: str, output_dir: str = "output") -> str:
    """
    Converts a markdown resume string to a PDF file.
    Uses WeasyPrint (best CSS support) with fallback to md-to-pdf CLI.

    Returns the path to the generated PDF.
    """
    Path(output_dir).mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_company = _sanitize_filename(company)
    safe_title = _sanitize_filename(job_title)

    md_path = Path(output_dir) / f"resume_{safe_company}_{safe_title}_{timestamp}.md"
    pdf_path = Path(output_dir) / f"PRAJJWAL_PANDEY_{safe_company}_{safe_title}_{timestamp}.pdf"

    # ── Step 1: Save markdown to file ──
    md_path.write_text(resume_markdown, encoding="utf-8")
    logger.info(f"📄 Markdown saved to {md_path}")

    # ── Step 2: Try PDF conversion (WeasyPrint → Playwright → Pandoc) ──
    try:
        _convert_with_weasyprint(resume_markdown, pdf_path)
        logger.info(f"✅ PDF created via WeasyPrint: {pdf_path}")
        return str(pdf_path)
    except Exception as e:
        logger.warning(f"WeasyPrint failed: {e}. Trying Playwright fallback...")

    try:
        _convert_with_playwright(resume_markdown, pdf_path)
        logger.info(f"✅ PDF created via Playwright: {pdf_path}")
        return str(pdf_path)
    except Exception as e:
        logger.warning(f"Playwright PDF failed: {e}. Trying pandoc fallback...")

    try:
        _convert_with_pandoc(md_path, pdf_path)
        logger.info(f"✅ PDF created via pandoc: {pdf_path}")
        return str(pdf_path)
    except Exception as e:
        logger.error(f"All PDF conversion methods failed: {e}")
        # Return the markdown path as fallback
        return str(md_path)


def _convert_with_weasyprint(markdown_text: str, pdf_path: Path):
    """
    Renders markdown to HTML then to PDF with WeasyPrint.
    Requires GTK system libraries (works on Linux; on Windows install GTK runtime).
    """
    from weasyprint import HTML, CSS
    full_html = _build_html(markdown_text)
    HTML(string=full_html).write_pdf(
        str(pdf_path),
        stylesheets=[CSS(string="@page { margin: 0; }")]
    )


def _build_html(markdown_text: str) -> str:
    """Shared HTML builder used by both WeasyPrint and Playwright."""
    import markdown as md_lib
    md_html = md_lib.markdown(markdown_text, extensions=["extra", "nl2br"])
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'Helvetica Neue', Arial, sans-serif;
            font-size: 10.5pt;
            line-height: 1.5;
            color: #1a1a1a;
            padding: 1.8cm 2cm;
        }}
        h1 {{ font-size: 20pt; font-weight: 700; color: #0a0a0a; margin-bottom: 4px; }}
        h2 {{ font-size: 11pt; font-weight: 700; text-transform: uppercase;
              letter-spacing: 0.8px; border-bottom: 1.5px solid #0a0a0a;
              padding-bottom: 3px; margin-top: 14px; margin-bottom: 6px; }}
        h3 {{ font-size: 10.5pt; font-weight: 600; margin-top: 8px; margin-bottom: 2px; }}
        p {{ margin-bottom: 4px; color: #333; }}
        ul {{ padding-left: 16px; margin-bottom: 6px; }}
        li {{ margin-bottom: 3px; color: #333; }}
        h1 + p {{ font-size: 9.5pt; color: #555; margin-bottom: 10px; }}
        strong {{ font-weight: 600; color: #111; }}
        a {{ color: #1a1a1a; text-decoration: none; }}
    </style>
</head>
<body>{md_html}</body>
</html>"""


def _convert_with_playwright(markdown_text: str, pdf_path: Path):
    """
    Renders markdown → HTML → PDF using Playwright (Chromium).
    Works natively on Windows without any system dependencies.
    Requires: playwright install chromium
    """
    from playwright.sync_api import sync_playwright
    html_content = _build_html(markdown_text)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html_content, wait_until="networkidle")
        page.pdf(
            path=str(pdf_path),
            format="A4",
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
            print_background=True
        )
        browser.close()


def _convert_with_pandoc(md_path: Path, pdf_path: Path):
    """
    Fallback: Use pandoc CLI to convert markdown → PDF.
    Install: sudo apt install pandoc texlive-xetex
    """
    result = subprocess.run(
        [
            "pandoc", str(md_path),
            "-o", str(pdf_path),
            "--pdf-engine=xelatex",
            "-V", "geometry:margin=2cm",
            "-V", "fontsize=11pt",
            "-V", "mainfont=DejaVu Sans"
        ],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"Pandoc error: {result.stderr}")
