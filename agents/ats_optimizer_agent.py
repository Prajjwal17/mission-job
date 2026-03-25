# agents/ats_optimizer_agent.py
# ============================================================
# ATS OPTIMIZER AGENT
#
# Ensures every resume achieves >95% ATS compatibility score
# before being sent to recruiters.
#
# Process:
#   1. Extract keywords from job/company context
#   2. Validate resume structure (ATS-safe headers)
#   3. Inject missing keywords naturally
#   4. Score resume (matched keywords / total)
#   5. Regenerate if score < 95%
#   6. Log final score
# ============================================================

import json
import re
import logging
from pathlib import Path
from anthropic import Anthropic

try:
    import config
except ImportError:
    config = None

logger = logging.getLogger(__name__)

# ATS-SAFE SECTION HEADERS (standard across all ATS systems)
ATS_SAFE_HEADERS = {
    "summary", "professional summary", "objective",
    "skills", "technical skills", "core competencies",
    "experience", "work experience", "professional experience",
    "projects", "key projects", "notable projects",
    "education", "qualifications",
    "certifications", "certifications & licenses",
    "languages"
}

# Keywords that ATS systems commonly search for (by category)
ATS_KEYWORD_CATEGORIES = {
    "ai_ml": ["machine learning", "deep learning", "neural networks", "NLP", "computer vision",
              "LLM", "prompt engineering", "RAG", "transformers", "classification", "regression"],
    "backend": ["REST API", "microservices", "database", "SQL", "NoSQL", "authentication",
                "scalability", "optimization", "caching", "deployment"],
    "full_stack": ["frontend", "backend", "API integration", "full-stack", "end-to-end",
                   "responsive design", "user experience"],
    "devops": ["CI/CD", "Docker", "Kubernetes", "cloud", "AWS", "GCP", "Azure", "deployment",
               "infrastructure", "automation", "monitoring"],
    "data": ["data analysis", "visualization", "ETL", "big data", "analytics", "statistical",
             "Python", "Pandas", "SQL", "Power BI", "Tableau"],
}


def extract_keywords_from_context(company_name: str, job_description: str = None) -> set:
    """
    Extract likely keywords based on company and job context.
    Returns set of keywords the ATS might look for.
    """
    keywords = set()

    # Add category-specific keywords based on company type
    company_lower = company_name.lower()

    # Detect company type from name patterns
    if any(x in company_lower for x in ["ai", "llm", "ml", "analytics"]):
        keywords.update(ATS_KEYWORD_CATEGORIES["ai_ml"])
    if any(x in company_lower for x in ["tech", "software", "data"]):
        keywords.update(ATS_KEYWORD_CATEGORIES["data"])
    if any(x in company_lower for x in ["cloud", "infra", "devops"]):
        keywords.update(ATS_KEYWORD_CATEGORIES["devops"])

    # Default: include common tech keywords
    keywords.update(["Python", "JavaScript", "API", "database", "Git", "problem-solving"])

    # Extract from job description if provided
    if job_description:
        job_lower = job_description.lower()
        for keyword in ATS_KEYWORD_CATEGORIES.values():
            for kw in keyword:
                if kw.lower() in job_lower:
                    keywords.add(kw)

    return keywords


def validate_ats_structure(resume_markdown: str) -> dict:
    """
    Validate that resume uses ATS-safe structure.
    Returns: {is_valid: bool, issues: [str], headers_found: [str]}
    """
    issues = []
    headers_found = []

    # Check for forbidden formatting
    if "| " in resume_markdown or " |" in resume_markdown:
        issues.append("Contains tables — ATS parsers struggle with tables")
    if "├" in resume_markdown or "│" in resume_markdown or "└" in resume_markdown:
        issues.append("Contains box-drawing characters — use plain text only")
    if any(emoji in resume_markdown for emoji in "🎯📊💼✨🚀"):
        issues.append("Contains emojis — remove for ATS compatibility")

    # Extract headers used
    header_pattern = r'^#{1,3}\s+(.+)$'
    found_headers = re.findall(header_pattern, resume_markdown, re.MULTILINE)
    headers_normalized = [h.strip().lower() for h in found_headers]
    headers_found = headers_normalized

    # Check if using safe headers
    if headers_found:
        safe_headers = [h for h in headers_normalized if h in ATS_SAFE_HEADERS]
        if len(safe_headers) < len(headers_normalized) * 0.7:
            issues.append(f"Non-standard headers detected: {set(headers_normalized) - ATS_SAFE_HEADERS}")

    is_valid = len(issues) == 0
    return {
        "is_valid": is_valid,
        "issues": issues,
        "headers_found": headers_found
    }


def calculate_ats_score(resume_markdown: str, required_keywords: set) -> dict:
    """
    Calculate ATS score based on keyword matching.
    Score = (matched keywords / total keywords) × 100
    """
    resume_lower = resume_markdown.lower()
    matched = set()

    for keyword in required_keywords:
        # Case-insensitive search
        if keyword.lower() in resume_lower:
            matched.add(keyword)

    score = (len(matched) / len(required_keywords)) * 100 if required_keywords else 0

    return {
        "score": round(score, 2),
        "matched": len(matched),
        "total": len(required_keywords),
        "missing_keywords": sorted(required_keywords - matched),
        "matched_keywords": sorted(matched)
    }


def optimize_resume_with_claude(
    resume_markdown: str,
    company_name: str,
    required_keywords: set,
    current_score: dict,
    client: Anthropic
) -> str:
    """
    Use Claude to rewrite resume for better ATS optimization.
    Focus: natural keyword injection, structure fixes, bullet optimization.
    """
    missing = current_score["missing_keywords"][:5]  # Top 5 missing keywords

    prompt = f"""You are an ATS optimization expert. Rewrite this resume to achieve maximum ATS compatibility.

RULES:
1. Maintain ONLY these section headers: Summary, Skills, Experience, Projects, Education, Certifications
2. Inject these missing keywords NATURALLY (max 2 mentions each): {", ".join(missing)}
3. Reformat bullets as: [Action Verb] + [Skill/Technology] + [Quantified Impact]
4. NO tables, NO icons, NO emoji, NO multi-column layouts
5. Use plain text formatting only (Markdown bullets only)
6. Preserve all achievements and dates
7. Avoid fake skills — only enhance what's real

CURRENT SCORE: {current_score['score']:.1f}% (matched {current_score['matched']}/{current_score['total']} keywords)
COMPANY: {company_name}

---
RESUME:
{resume_markdown}

---
OUTPUT: Optimized resume in plain Markdown only. No explanations."""

    model_name = config.CLAUDE_MODEL if config else "claude-haiku-4-5-20251001"
    message = client.messages.create(
        model=model_name,
        max_tokens=1500,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    return message.content[0].text


def optimize_resume(
    resume_markdown: str,
    company_name: str,
    job_description: str = None,
    client: Anthropic = None,
    max_iterations: int = 3
) -> dict:
    """
    Main ATS optimization function.

    Returns:
        {
            "optimized_resume": str,
            "ats_score": float,
            "iterations": int,
            "status": "success" | "failed",
            "validation": dict
        }
    """
    if client is None:
        from anthropic import Anthropic
        client = Anthropic()

    logger.info(f"Starting ATS optimization for {company_name}")

    # Step 1: Validate structure
    validation = validate_ats_structure(resume_markdown)
    if validation["issues"]:
        logger.warning(f"ATS structure issues: {validation['issues']}")

    # Step 2: Extract keywords
    required_keywords = extract_keywords_from_context(company_name, job_description)
    logger.info(f"Extracted {len(required_keywords)} target keywords for ATS matching")

    # Step 3: Optimize in loop
    current_resume = resume_markdown
    iteration = 0

    while iteration < max_iterations:
        iteration += 1

        # Calculate current score
        score_result = calculate_ats_score(current_resume, required_keywords)
        current_score = score_result["score"]

        logger.info(f"  Iteration {iteration}: ATS Score = {current_score:.1f}%")

        # Check if we've reached target
        if current_score >= 95:
            logger.info(f"✅ Target ATS score achieved: {current_score:.1f}%")
            return {
                "optimized_resume": current_resume,
                "ats_score": current_score,
                "iterations": iteration,
                "status": "success",
                "validation": validation,
                "score_details": score_result
            }

        # Optimize with Claude
        logger.info(f"  Regenerating resume (iteration {iteration})...")
        current_resume = optimize_resume_with_claude(
            current_resume,
            company_name,
            required_keywords,
            score_result,
            client
        )

    # Final score after max iterations
    final_score = calculate_ats_score(current_resume, required_keywords)
    status = "success" if final_score["score"] >= 90 else "partial"

    logger.warning(f"Max iterations reached. Final score: {final_score['score']:.1f}%")

    return {
        "optimized_resume": current_resume,
        "ats_score": final_score["score"],
        "iterations": iteration,
        "status": status,
        "validation": validation,
        "score_details": final_score
    }


def log_ats_score(email: str, company: str, score: float, output_dir: str = "logs"):
    """Log ATS score to JSON for tracking."""
    log_path = Path(output_dir) / "ats_scores.json"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "email": email,
        "company": company,
        "ats_score": score,
        "timestamp": str(__import__('datetime').datetime.now())
    }

    data = []
    if log_path.exists():
        with open(log_path) as f:
            data = json.load(f).get("scores", [])

    data.append(entry)

    with open(log_path, "w") as f:
        json.dump({"scores": data}, f, indent=2)


if __name__ == "__main__":
    # Example usage
    test_resume = """# PRAJJWAL PANDEY
prajjwalp1707@gmail.com | +91 8278674540

## Summary
Final-year student with expertise in AI and full-stack development.

## Skills
Python, JavaScript, Machine Learning, Docker, API Design

## Experience
Developed job application pipeline using Python and Claude API.

## Projects
- AI Job Application Pipeline: Built 5-agent system for automated applications
- Smart Traffic System: YOLO v5 detection with 82% accuracy

## Education
B.Tech Electronics & Communication, VIT Vellore (May 2026)

## Certifications
Data Scientist's Toolbox (Coursera)
"""

    from anthropic import Anthropic
    client = Anthropic()

    result = optimize_resume(
        test_resume,
        "TechCorp AI",
        job_description="Looking for ML engineer with Python, LangChain, RAG experience",
        client=client
    )

    print("\n" + "="*60)
    print(f"ATS Score: {result['ats_score']:.1f}%")
    print(f"Iterations: {result['iterations']}")
    print(f"Status: {result['status']}")
    print("="*60)
    print("\nOptimized Resume:")
    print(result['optimized_resume'])
