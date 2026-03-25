# agents/tailor_agent.py
# ============================================================
# AGENT 2: CLAUDE RESUME TAILOR AGENT
# Reads knowledge files → calls Claude API → returns
# tailored resume (markdown) + cold email (text)
# ============================================================

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import anthropic
import logging
import json
from pathlib import Path
from datetime import datetime
import config as _config

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Load knowledge base files
# ─────────────────────────────────────────────
def _load_knowledge() -> dict:
    base = Path(__file__).parent.parent / "knowledge"
    knowledge = {}
    for fname in ["master_resume.md", "detailed_projects.md", "ats_rules.md"]:
        fpath = base / fname
        if fpath.exists():
            knowledge[fname] = fpath.read_text()
        else:
            logger.warning(f"Knowledge file not found: {fname}")
            knowledge[fname] = ""
    return knowledge


# ─────────────────────────────────────────────
# Build the system prompt (the "brain")
# ─────────────────────────────────────────────
def _build_system_prompt(knowledge: dict) -> str:
    return f"""You are an elite Resume Architect and ATS Optimization Specialist.

Your job is to produce TWO outputs when given a Job Description:
1. A fully tailored ATS-optimized resume in clean Markdown
2. A personalized cold email to the HR contact

━━━━━━━━━━━━━━━━━━━━━━━━━━━
CANDIDATE KNOWLEDGE BASE
━━━━━━━━━━━━━━━━━━━━━━━━━━━

=== MASTER RESUME ===
{knowledge.get('master_resume.md', '')}

=== DETAILED PROJECT NOTES ===
{knowledge.get('detailed_projects.md', '')}

=== ATS RULES & TAILORING LOGIC ===
{knowledge.get('ats_rules.md', '')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT FORMAT (STRICT)
━━━━━━━━━━━━━━━━━━━━━━━━━━━

Return ONLY valid JSON with exactly these two keys:

{{
  "resume_markdown": "<full tailored resume in markdown>",
  "cold_email": "<full cold email as plain text>"
}}

Rules for the resume:
- Include a "Key Skills" section at the TOP filtered to the JD's top 5 keywords
- Every experience bullet = Google X-Y-Z formula: "Accomplished [X] as measured by [Y], by doing [Z]"
- Swap in specialized projects from Detailed Project Notes if the JD needs them
- No tables, no graphics, clean markdown only
- Keep it to one page worth of content

Rules for the cold email:
- Subject line included at the top as "Subject: ..."  
- Hook: Reference a specific detail from the JD or company
- Value Prop: Connect a specific project to a specific problem in the JD
- CTA: Clear single ask (15-minute call or reply)
- NEVER use: "I am excited to apply", "I believe I am a good fit", or any generic fluff
- ALWAYS use: "My experience in [X] and project [Y] directly solves [problem Z] at [Company]"
- Sign off with candidate's name, email, and phone
"""


# ─────────────────────────────────────────────
# Main tailor function
# ─────────────────────────────────────────────
def tailor_resume_and_email(job: dict, api_key: str) -> dict:
    """
    Takes a structured job dict, calls Claude API, returns:
    {
        "resume_markdown": str,
        "cold_email": str,
        "job_title": str,
        "company": str
    }
    """
    knowledge = _load_knowledge()
    system_prompt = _build_system_prompt(knowledge)

    # Build the user prompt with full JD context
    hr_context = ""
    if job.get("hr_name"):
        hr_context = f"\nHR Contact: {job['hr_name']}"
    if job.get("hr_email"):
        hr_context += f"\nHR Email: {job['hr_email']}"
    if job.get("hr_linkedin"):
        hr_context += f"\nHR LinkedIn: {job['hr_linkedin']}"

    user_prompt = f"""Please tailor the resume and write the cold email for this job:

JOB TITLE: {job.get('job_title', 'Not specified')}
COMPANY: {job.get('company', 'Not specified')}
{hr_context}

FULL JOB DESCRIPTION:
{job.get('job_description', '')}

Remember:
- Extract the top 5 hard skill keywords from the JD
- Use those keywords naturally throughout the resume
- Decide which projects to highlight based on JD focus
- Every bullet uses X-Y-Z formula
- Cold email references a SPECIFIC detail from this JD
"""

    logger.info(f"🤖 Calling Claude API for: {job.get('job_title')} @ {job.get('company')}")

    client = anthropic.Anthropic(api_key=api_key)

    # Use prompt caching on the system prompt (saves ~90% on input tokens for repeat calls)
    response = client.messages.create(
        model=_config.CLAUDE_MODEL,
        max_tokens=_config.CLAUDE_MAX_TOKENS,
        system=[
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"}  # Cache for 5 mins; huge saving on bulk runs
            }
        ],
        messages=[
            {"role": "user", "content": user_prompt}
        ]
    )

    raw_output = response.content[0].text.strip()

    # Parse the JSON response
    try:
        # Strip markdown code fences if Claude wrapped in ```json
        if raw_output.startswith("```"):
            raw_output = raw_output.split("```")[1]
            if raw_output.startswith("json"):
                raw_output = raw_output[4:]
        
        parsed = json.loads(raw_output.strip())
        resume_md = parsed.get("resume_markdown", "")
        cold_email = parsed.get("cold_email", "")
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Claude response as JSON: {e}")
        logger.debug(f"Raw response: {raw_output[:500]}")
        # Fallback: treat entire response as resume
        resume_md = raw_output
        cold_email = ""

    logger.info(f"✅ Tailor Agent complete for {job.get('company')}")

    return {
        "resume_markdown": resume_md,
        "cold_email": cold_email,
        "job_title": job.get("job_title", ""),
        "company": job.get("company", ""),
        "hr_name": job.get("hr_name", ""),
        "hr_email": job.get("hr_email", ""),
        "scraped_at": job.get("scraped_at", datetime.now().isoformat())
    }


# ─────────────────────────────────────────────
# COLD PITCH (no JD — HR outreach mode)
# ─────────────────────────────────────────────
def generate_pitch_email(hr_contact: dict, api_key: str, skill_area: str = None) -> str:
    """
    Generates a personalized cold pitch email to an HR contact
    when no specific JD is available.

    Uses skill-specific templates for higher relevance when available.

    Args:
        hr_contact: { hr_name, hr_email, company, designation, skill_area }
        api_key: Claude API key
        skill_area: Optional skill area ("Agentic AI & LLM", "Computer Vision", etc.)
                   If provided, uses skill-specific template instead of Claude generation

    Returns:
        Cold pitch email as plain text (with Subject: line at top)
    """
    # Try to use skill-specific templates for better performance
    if skill_area or hr_contact.get("skill_area"):
        try:
            from tools.email_templates import EmailTemplates
            skill = skill_area or hr_contact.get("skill_area")
            hr_name = hr_contact.get("hr_name", "")
            company = hr_contact.get("company", "your organisation")

            template_email = EmailTemplates.get_template(skill, hr_name, company)

            # Add subject line
            subject_line = f"Subject: Exploring Opportunities in {EmailTemplates.get_skill_area_summary(skill)}"
            email_text = f"{subject_line}\n\n{template_email}"

            logger.info(f"✅ Pitch email generated (skill-specific) for {company} [{skill}]")
            return email_text
        except Exception as e:
            logger.warning(f"Could not use skill-specific template: {e}. Falling back to Claude generation.")

    # Fallback: Generate with Claude
    knowledge = _load_knowledge()
    master_resume = knowledge.get("master_resume.md", "")

    company     = hr_contact.get("company", "your organisation")
    hr_name     = hr_contact.get("hr_name", "")
    designation = hr_contact.get("designation", "")

    greeting = f"Hi {hr_name}," if hr_name else "Hi,"

    system_prompt = f"""You are an expert cold email writer for job seekers.

Write a SHORT, punchy cold outreach email from a candidate to an HR professional.
The candidate is NOT applying to a specific open role — they are proactively introducing
themselves and asking if there are any suitable openings.

CANDIDATE PROFILE:
{master_resume}

RULES:
- Subject line first: "Subject: ..."
- 3–4 short paragraphs max
- Paragraph 1: One specific genuine compliment about the company (research it from the name)
- Paragraph 2: Candidate's strongest 2 skills + best project in one sentence
- Paragraph 3: Ask if any suitable opening exists — single clear CTA
- Sign off: Prajjwal Pandey | prajjwalp1707@gmail.com | +91 8278674540
- NEVER use: "I am excited", "I believe I am a good fit", "I hope this email finds you well"
- Tone: confident, respectful, brief
- Return ONLY the email text (no JSON, no extra commentary)
"""

    user_prompt = f"""Write the cold pitch email.

HR Contact: {greeting}
Company: {company}
Their Role: {designation if designation else 'HR/Recruiter'}
"""

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=_config.CLAUDE_MODEL,
        max_tokens=600,   # Pitch emails must be short
        system=[{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user_prompt}]
    )

    email_text = response.content[0].text.strip()
    logger.info(f"✅ Pitch email generated (Claude) for {company}")
    return email_text
