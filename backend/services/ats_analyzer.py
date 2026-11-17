import re

from backend.services.similarity_engine import compare_resume_to_job


SECTION_PATTERNS = {
    "Contact": r"email|phone|linkedin|github|contact",
    "Summary": r"summary|profile|objective",
    "Experience": r"experience|employment|work history",
    "Education": r"education|academic|university|degree",
    "Skills": r"skills|technologies|technical",
    "Projects": r"projects|portfolio",
}


def analyze_ats(resume: str, job_description: str) -> dict:
    matching = compare_resume_to_job(resume, job_description)
    section_results = {name: bool(re.search(pattern, resume, re.I)) for name, pattern in SECTION_PATTERNS.items()}
    section_score = round(100 * sum(section_results.values()) / len(section_results))
    resume_words = len(resume.split())
    bullet_count = sum(1 for line in resume.splitlines() if line.strip().startswith(("-", "•", "*")))
    formatting_score = 100
    if resume_words < 120:
        formatting_score -= 25
    elif resume_words > 1100:
        formatting_score -= 20
    if bullet_count == 0:
        formatting_score -= 15
    if max((len(line) for line in resume.splitlines()), default=0) > 180:
        formatting_score -= 10
    formatting_score = max(0, formatting_score)
    overall = round(0.55 * matching["keyword_coverage"] + 0.25 * section_score + 0.20 * formatting_score)
    return {
        "overall_score": overall,
        "keyword_coverage": matching["keyword_coverage"],
        "skills_coverage": round(100 * len(matching["matched_skills"]) / max(1, len(matching["matched_skills"]) + len(matching["missing_skills"]))),
        "formatting_score": formatting_score,
        "section_score": section_score,
        "sections": section_results,
        "matching": matching,
        "score_method": "55% TF-IDF job keyword coverage + 25% section presence + 20% text-layout heuristics. This is an explainable heuristic, not an actual ATS prediction.",
        "recommendations": _recommendations(matching, section_results, formatting_score),
    }


def _recommendations(matching: dict, sections: dict, formatting_score: int) -> list[str]:
    tips = []
    if matching["missing_keywords"]:
        tips.append("Review missing job-description terms and add only those supported by your actual experience.")
    if not sections["Skills"]:
        tips.append("Add a clearly labeled skills section if it reflects your background.")
    if not sections["Experience"]:
        tips.append("Use a standard Experience heading for relevant work or internship history.")
    if formatting_score < 80:
        tips.append("Use concise bullet points and keep the resume within a role-appropriate length.")
    if not tips:
        tips.append("Keep role-specific evidence near the top and quantify outcomes where you have verified figures.")
    return tips