from backend.services.keyword_extractor import extract_skills
from backend.services.text_preprocessing import token_retention_percent


def evaluate_retention(original: str, optimized: str) -> dict:
    original_skills = set(extract_skills(original))
    optimized_skills = set(extract_skills(optimized))
    skill_retention = 100.0 if not original_skills else round(100 * len(original_skills & optimized_skills) / len(original_skills), 1)
    return {
        "skill_retention_percent": skill_retention,
        "token_retention_percent": token_retention_percent(original, optimized),
        "preserved_skills": sorted(original_skills & optimized_skills),
    }