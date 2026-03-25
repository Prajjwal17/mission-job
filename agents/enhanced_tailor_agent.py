# agents/enhanced_tailor_agent.py
# ============================================================
# ENHANCED TAILOR AGENT
# Story-mode resume (STAR format) + personalized cover letter
# ============================================================

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import anthropic
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

import config as _config


def _load_knowledge() -> dict:
    """Load knowledge base files"""
    base = Path(__file__).parent.parent / "knowledge"
    knowledge = {}
    for fname in ["master_resume.md", "detailed_projects.md"]:
        fpath = base / fname
        if fpath.exists():
            knowledge[fname] = fpath.read_text()
        else:
            logger.warning(f"Knowledge file not found: {fname}")
            knowledge[fname] = ""
    return knowledge


def generate_story_mode_resume(
    company: str,
    skill_area: str = None,
    job_description: str = None,
    api_key: str = None
) -> str:
    """
    Generate a story-mode, ATS-friendly 1-page resume tailored to company/JD.

    Story Mode: "I did X to achieve Y result"
    Format: 1-page, ATS-optimized, achievement-focused

    Args:
        company: Company name
        skill_area: "Agentic AI & LLM", "Computer Vision", "Full-Stack", "Data Science"
        job_description: Full JD text (optional)
        api_key: Claude API key

    Returns:
        Markdown-formatted resume (story-mode, ATS-friendly, 1-page)
    """
    knowledge = _load_knowledge()
    master_resume = knowledge.get("master_resume.md", "")
    detailed_projects = knowledge.get("detailed_projects.md", "")

    api_key = api_key or _config.CLAUDE_API_KEY

    # Build context for resume tailoring
    jd_context = ""
    if job_description:
        jd_context = f"""
COMPANY JOB DESCRIPTION:
{job_description[:1500]}  # First 1500 chars only

EXTRACTION TASK:
- Extract 5-7 key terms/skills from the JD
- Identify company's primary pain points
- Note required experience level
"""

    skill_context = ""
    if skill_area:
        if "AI" in skill_area:
            skill_context = """
RESUME FOCUS FOR AGENTIC AI:
- Highlight: Claude API, automation, multi-step workflows, LangChain, RAG
- Story format: "I built X to automate Y, resulting in Z"
- Projects: Job Pipeline, email validation, agentic systems
"""
        elif "Computer Vision" in skill_area:
            skill_context = """
RESUME FOCUS FOR COMPUTER VISION:
- Highlight: YOLO, detection accuracy, real-world deployment, edge cases
- Story format: "I deployed X model achieving Y% accuracy, enabling Z"
- Projects: Traffic detection, Delhi Police deployment, model optimization
"""
        elif "Full-Stack" in skill_area:
            skill_context = """
RESUME FOCUS FOR FULL-STACK:
- Highlight: End-to-end systems, scalability, production deployments
- Story format: "I built X from backend to frontend, handling Y scale"
- Projects: Job Pipeline application, Docker, CI/CD
"""
        elif "Data Science" in skill_area:
            skill_context = """
RESUME FOCUS FOR DATA SCIENCE:
- Highlight: Insights, forecasting, dashboards, data-driven decisions
- Story format: "I analyzed X data to predict Y, supporting Z decisions"
- Projects: Time-series forecasting, Power BI dashboards, embeddings
"""

    system_prompt = f"""You are a professional resume architect specializing in story-mode resumes.

CANDIDATE PROFILE:
{master_resume}

DETAILED PROJECTS:
{detailed_projects}

RESUME REQUIREMENTS:
1. STORY MODE: Every bullet = "I did X so I achieved Y result"
   - Use STAR format: Situation → Action → Result
   - Emphasize achievements and impact, not just tasks
   - Include metrics where possible (accuracy %, speed, scale)

2. ATS-FRIENDLY 1-PAGE:
   - Maximum 1 page (≈750 words)
   - Use simple formatting: no tables, no graphics, clean markdown
   - Include standard sections: Summary, Experience, Skills, Projects
   - Key Skills section at TOP (scannable for ATS)
   - Clean bullet points (no emojis, no special chars)

3. COMPANY/JD-SPECIFIC:
   - Tailor key skills to match company needs
   - Lead with most relevant projects
   - Use 3-5 JD keywords naturally in context
   {jd_context}

{skill_context}

OUTPUT FORMAT:
Return ONLY valid Markdown (no JSON, no commentary):
- Start with "# Prajjwal Pandey"
- Clean, scannable structure
- Story-mode bullets with clear impact
- Exactly 1 page worth of content
"""

    user_prompt = f"""Generate a tailored story-mode resume for this application:

Company: {company}
Skill Area: {skill_area or 'General'}

Requirements:
- Story mode: "I did X to achieve Y"
- 1 page, ATS-friendly
- Company/JD-specific tailoring
- Achievement-focused, metrics included

Return ONLY the Markdown resume (no intro text, no JSON).
"""

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=_config.CLAUDE_MODEL,
        max_tokens=1200,
        system=[{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user_prompt}]
    )

    resume_markdown = response.content[0].text.strip()
    logger.info(f"✅ Story-mode resume generated for {company}")
    return resume_markdown


def generate_personalized_cover_letter(
    company: str,
    skill_area: str = None,
    job_description: str = None,
    hr_name: str = None,
    api_key: str = None
) -> str:
    """
    Generate a personalized cover letter tailored to company + skill area.

    Args:
        company: Company name
        skill_area: Skill area
        job_description: Full JD (optional)
        hr_name: HR person's name (optional)
        api_key: Claude API key

    Returns:
        Cover letter as plain text (no markdown, ready to send as email body or PDF)
    """
    api_key = api_key or _config.CLAUDE_API_KEY

    knowledge = _load_knowledge()
    master_resume = knowledge.get("master_resume.md", "")

    # Greeting
    greeting = f"Dear {hr_name}," if hr_name else "Dear Hiring Manager,"

    # Build skill-specific narrative
    skill_narrative = ""
    if skill_area and "AI" in skill_area:
        skill_narrative = """
Your company is at the forefront of AI-driven automation. I'm drawn to how you're
leveraging intelligence to solve real-world problems. With my hands-on experience
building production-grade agentic systems—including a 5-agent pipeline that orchestrates
resume tailoring, PDF generation, and email delivery—I'm confident I can contribute
meaningful solutions to your team's AI initiatives."""

    elif skill_area and "Computer Vision" in skill_area:
        skill_narrative = """
Your company's work in computer vision is impressive. I've deployed real-world vision
solutions: a traffic detection system using YOLO v5 that achieved 82% accuracy and was
deployed to Delhi Police for live monitoring. I understand the challenges of production
CV systems—from model optimization to edge deployment—and I'm excited to apply this
expertise to your team."""

    elif skill_area and "Full-Stack" in skill_area:
        skill_narrative = """
Your company builds products that matter. I'm passionate about full-stack development
where I can contribute across the entire stack. From Django backends and React frontends
to Docker containerization and CI/CD pipelines, I've built end-to-end systems that scale.
I'm drawn to your mission and ready to make an immediate impact."""

    elif skill_area and "Data Science" in skill_area:
        skill_narrative = """
Your company's data-driven approach aligns with my passion for turning raw data into
strategic insights. I've built time-series forecasting models, created Power BI dashboards
for business intelligence, and developed vector-based semantic analysis systems. I'm excited
to contribute to your team's mission of extracting value from data."""

    else:
        skill_narrative = """
Your company stands out for its commitment to innovation and impact. I'm impressed by your
mission and the talent on your team. I'm confident that my technical expertise and drive
for excellence make me a valuable addition."""

    system_prompt = f"""You are an expert professional cover letter writer.

Write a personalized, compelling cover letter that:
1. Opens with genuine interest in the company/mission
2. Highlights 2-3 relevant achievements with specific results
3. Shows understanding of what the company needs
4. Includes a clear call-to-action
5. Professional yet warm tone
6. Exactly 3 paragraphs (brief, scannable)
7. No clichés ("I'm excited to explore opportunities", "I believe I'd be a good fit")

CANDIDATE:
{master_resume}

STYLE GUIDE:
- Paragraph 1: Why this company/role (specific detail)
- Paragraph 2: What you bring (2-3 achievements with results)
- Paragraph 3: Call-to-action (request a conversation)
- Tone: Confident, professional, authentic
- Length: 200-250 words
"""

    user_prompt = f"""{greeting}

Write a personalized cover letter for this application.

Company: {company}
Skill Area: {skill_area or "General"}
HR Name: {hr_name or "Hiring Manager"}

COMPANY NARRATIVE (to guide tone):
{skill_narrative}

Requirements:
- 3 paragraphs only
- Specific company/role interest
- 2-3 achievements with metrics
- Clear CTA
- Professional, no clichés

Return ONLY the cover letter text (no intro, no JSON, ready to send).
"""

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=_config.CLAUDE_MODEL,
        max_tokens=400,
        system=[{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user_prompt}]
    )

    cover_letter = response.content[0].text.strip()
    logger.info(f"✅ Cover letter generated for {company}")
    return cover_letter


def generate_application_package(
    company: str,
    skill_area: str = None,
    job_description: str = None,
    hr_name: str = None,
    api_key: str = None
) -> dict:
    """
    Generate complete application package: resume + cover letter

    Args:
        company: Company name
        skill_area: Skill area
        job_description: Full JD
        hr_name: HR contact name
        api_key: Claude API key

    Returns:
        Dict with:
        {
            "resume_markdown": "...",
            "cover_letter": "...",
            "email_subject": "Application: [Role] @ [Company]"
        }
    """
    logger.info(f"Generating application package for {company}...")

    resume = generate_story_mode_resume(
        company=company,
        skill_area=skill_area,
        job_description=job_description,
        api_key=api_key
    )

    cover_letter = generate_personalized_cover_letter(
        company=company,
        skill_area=skill_area,
        job_description=job_description,
        hr_name=hr_name,
        api_key=api_key
    )

    # Generate email subject
    subject_map = {
        "Agentic AI": "AI/Automation Engineer",
        "Computer Vision": "Computer Vision Engineer",
        "Full-Stack": "Full-Stack Developer",
        "Data Science": "Data Science Engineer"
    }

    role = subject_map.get(skill_area, "Software Engineer") if skill_area else "Software Engineer"
    email_subject = f"Experienced {role} - {company} Application"

    return {
        "resume_markdown": resume,
        "cover_letter": cover_letter,
        "email_subject": email_subject,
        "company": company,
        "skill_area": skill_area or "General"
    }
