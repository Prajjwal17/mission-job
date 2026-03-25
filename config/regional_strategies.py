# Regional job market strategies based on deep research
REGIONAL_STRATEGIES = {
    "bangalore": {
        "focus": "Agentic AI & Multi-Agent Orchestration",
        "emphasis": ["5-agent autonomous pipeline", "LangChain orchestration", "RAG systems", "Real deployment proof"],
        "opening": "I built a production 5-agent autonomous pipeline using LangChain and Claude.",
        "why_hire": "Top 5% of ECE freshers have hands-on agentic AI experience."
    },
    "mumbai": {
        "focus": "Model Safety & Explainable AI",
        "emphasis": ["RAG grounding", "Vector space math (Cosine Similarity)", "Model interpretability", "Safety-first design"],
        "opening": "I build grounded, hallucination-free AI systems with mathematical rigor.",
        "why_hire": "FinTech needs safety. You understand the mathematical foundations."
    },
    "delhi_ncr": {
        "focus": "Computer Vision & Industrial Deployment",
        "emphasis": ["82% YOLO accuracy", "Delhi Police deployment", "Real-world impact", "Production-grade systems"],
        "opening": "I deployed an 82% accurate YOLO system to Delhi Police—real production deployment.",
        "why_hire": "Most freshers have YOLO projects. You have YOLO + government deployment."
    },
    "lucknow": {
        "focus": "Full-Stack Versatility",
        "emphasis": ["End-to-end ownership", "Multiple shipped products", "Autonomous systems", "Full-stack depth"],
        "opening": "I own complete projects end-to-end—from backend to production deployment.",
        "why_hire": "HCLTech values growth. You've already owned multiple complex systems."
    },
    "unknown": {
        "focus": "Technical Excellence",
        "emphasis": ["Agentic AI", "Computer Vision", "Full-stack development", "Data science"],
        "opening": "ECE fresher with production AI systems and computer vision expertise.",
        "why_hire": "Proven ability to build and deploy production systems."
    }
}

def get_strategy(region: str) -> dict:
    return REGIONAL_STRATEGIES.get(region, REGIONAL_STRATEGIES["unknown"])

def format_pitch(region: str) -> str:
    strategy = get_strategy(region)
    return f"{strategy['opening']} Focus: {strategy['focus']}."
