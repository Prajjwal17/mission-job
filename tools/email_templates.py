# tools/email_templates.py
# ============================================================
# SKILL-SPECIFIC EMAIL TEMPLATES
# Varies pitch by company's skill area for higher relevance
# ============================================================

import logging

logger = logging.getLogger(__name__)


class EmailTemplates:
    """
    Skill-specific email templates for cold outreach.
    Each template emphasizes the relevant projects and skills.
    """

    @staticmethod
    def get_template(skill_area: str = None, hr_name: str = "", company: str = "") -> str:
        """
        Get email template based on skill area.

        Args:
            skill_area: One of "Agentic AI & LLM", "Computer Vision",
                       "Full-Stack Development", "Data Science"
            hr_name: HR person's name (optional)
            company: Company name (optional)

        Returns:
            Email template with placeholders
        """

        greeting = f"Hi {hr_name}," if hr_name else "Hi there,"

        # Base closing (same for all)
        closing = """I'd love to discuss how my experience aligns with your team's goals. I'm happy to chat at your convenience—just let me know what works best.

Best regards,
Prajjwal Pandey
+91-9876543210
LinkedIn: linkedin.com/in/prajjwal-pandey
Portfolio: github.com/prajjwalpandey"""

        if skill_area and "Agentic AI" in skill_area:
            return f"""{greeting}

I hope this finds you well! I'm reaching out because {company or "your organization"} is doing cutting-edge work in AI automation, and I'd love to explore how I can contribute.

**What I've Built:**
- A 5-agent autonomous job application pipeline powered by Claude API
- RAG-based resume tailoring using LangChain and vector embeddings
- Multi-step agentic workflows that handle email validation, PDF generation, and SMTP delivery
- Integration of AI models for intelligent decision-making at each pipeline stage

**Why I'm Interested in {company or "Your Team"}:**
Your company is at the forefront of AI-driven automation. With my hands-on experience building production-grade agentic systems, I'm confident I can hit the ground running on complex AI infrastructure challenges.

**Technical Stack:**
- Claude API, LangChain, RAG fundamentals
- Python for agentic workflows
- Vector databases and embeddings
- Email validation and SMTP integration
- Prompt engineering and model optimization

{closing}"""

        elif skill_area and "Computer Vision" in skill_area:
            return f"""{greeting}

I hope this finds you well! I'm reaching out because {company or "your organization"} is leveraging computer vision for impactful solutions, and I'd love to explore opportunities to contribute my expertise.

**What I've Built:**
- A real-time traffic monitoring system using YOLO v5 with 82% accuracy
- Computer vision pipeline deployed to Delhi Police for live traffic detection
- Object detection and classification models optimized for edge deployment
- End-to-end CV solution from model training to production deployment

**Why I'm Interested in {company or "Your Team"}:**
With proven experience deploying vision models in real-world scenarios, I understand the challenges of production CV systems. I'm excited to apply this expertise to your team's computer vision initiatives.

**Technical Stack:**
- YOLO v5, OpenCV, Python
- Object detection and classification
- Real-time video processing
- Model optimization for edge devices
- Deployment and monitoring

{closing}"""

        elif skill_area and "Full-Stack Development" in skill_area:
            return f"""{greeting}

I hope this finds you well! I'm reaching out because {company or "your organization"} is building the kinds of scalable web platforms I'm passionate about, and I'd love to explore how I can contribute.

**What I've Built:**
- Full-stack web applications using Django (backend) and React (frontend)
- Containerized deployments with Docker for seamless CI/CD
- Scalable backend systems handling data processing and API management
- Complete end-to-end solutions from database design to production deployment

**Why I'm Interested in {company or "Your Team"}:**
I'm drawn to companies building real products that matter. With my full-stack experience and DevOps mindset, I can contribute across the entire tech stack—from backend architecture to frontend polish to deployment optimization.

**Technical Stack:**
- Python, Django, React, TypeScript
- Docker, CI/CD pipelines
- Database design and optimization
- Cloud deployment (AWS/GCP basics)
- Full-stack problem solving

{closing}"""

        elif skill_area and "Data Science" in skill_area:
            return f"""{greeting}

I hope this finds you well! I'm reaching out because {company or "your organization"} is doing sophisticated work in data science and analytics, and I'd love to explore how my expertise can contribute to your team.

**What I've Built:**
- Vector space modeling for semantic analysis and similarity
- Time-series forecasting models for predictive analytics
- Business intelligence dashboards with Power BI for data visualization
- End-to-end data pipelines from raw data to actionable insights

**Why I'm Interested in {company or "Your Team"}:**
I'm passionate about turning raw data into strategic insights. Your team's work in analytics aligns perfectly with my expertise in building data-driven solutions that drive business decisions.

**Technical Stack:**
- Python, Pandas, NumPy, Scikit-learn
- Time-series analysis and forecasting
- Vector embeddings and semantic search
- Power BI, Tableau for visualization
- SQL and data pipeline design

{closing}"""

        else:
            # Generic fallback template
            return f"""{greeting}

I hope this finds you well! I'm reaching out to express my interest in opportunities at {company or "your organization"}.

**About Me:**
I'm Prajjwal Pandey, a tech enthusiast with expertise in:
- Agentic AI and automation (5-agent Claude-powered pipeline)
- Computer Vision (YOLO v5, deployed to production)
- Full-Stack Development (Django, React, Docker)
- Data Science (Analytics, forecasting, embeddings)

**Why I'm Interested:**
I'm looking for roles where I can contribute my technical expertise while working on challenging, impactful problems. Your organization stands out as a place where I can make a real difference.

{closing}"""

    @staticmethod
    def get_skill_area_summary(skill_area: str) -> str:
        """Get a one-liner summary of this skill area."""
        summaries = {
            "Agentic AI & LLM": "Intelligent automation and agentic workflows",
            "Computer Vision": "Real-world computer vision deployment",
            "Full-Stack Development": "Scalable web platforms and systems",
            "Data Science": "Data-driven insights and analytics"
        }
        return summaries.get(skill_area, "Technology expertise")

    @staticmethod
    def get_relevant_projects(skill_area: str) -> list:
        """Get relevant projects to mention for each skill area."""
        projects = {
            "Agentic AI & LLM": [
                "5-agent Job Application Pipeline (Claude, LangChain, RAG)",
                "Email validation with vector-based similarity",
                "Multi-step automation workflows"
            ],
            "Computer Vision": [
                "Traffic Management System (YOLO v5, 82% accuracy)",
                "Real-time detection pipeline for Delhi Police",
                "Object detection and classification models"
            ],
            "Full-Stack Development": [
                "Job Pipeline web application (Django + React)",
                "Docker containerization and CI/CD",
                "Scalable backend architectures"
            ],
            "Data Science": [
                "Vector space modeling for semantic analysis",
                "Time-series forecasting",
                "Power BI business intelligence dashboards"
            ]
        }
        return projects.get(skill_area, [])

    @staticmethod
    def get_technical_skills(skill_area: str) -> list:
        """Get technical skills to emphasize for each skill area."""
        skills = {
            "Agentic AI & LLM": [
                "Claude API", "LangChain", "RAG", "Prompt Engineering",
                "Python", "Vector Databases", "Semantic Search"
            ],
            "Computer Vision": [
                "YOLO v5", "OpenCV", "Python", "TensorFlow/PyTorch",
                "Object Detection", "Image Processing", "Real-time Systems"
            ],
            "Full-Stack Development": [
                "Python", "Django", "React", "TypeScript", "Docker",
                "PostgreSQL", "AWS/GCP", "CI/CD Pipelines"
            ],
            "Data Science": [
                "Python", "Pandas", "NumPy", "Scikit-learn",
                "Power BI", "SQL", "Time-series Analysis", "Statistics"
            ]
        }
        return skills.get(skill_area, [])
