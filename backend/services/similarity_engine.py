from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from backend.services.keyword_extractor import extract_keywords, extract_skills


def compare_resume_to_job(resume: str, job_description: str) -> dict:
    try:
        matrix = TfidfVectorizer(stop_words="english", ngram_range=(1, 2)).fit_transform([resume, job_description])
        similarity = float(cosine_similarity(matrix[0:1], matrix[1:2])[0][0])
    except ValueError:
        similarity = 0.0

    job_skills = extract_skills(job_description)
    resume_skills = set(extract_skills(resume))
    matched = [skill for skill in job_skills if skill in resume_skills]
    missing = [skill for skill in job_skills if skill not in resume_skills]
    job_terms = extract_keywords(job_description)
    resume_lower = resume.lower()
    matched_terms = [term for term in job_terms if term in resume_lower]
    missing_terms = [term for term in job_terms if term not in resume_lower]
    coverage = round(100 * len(matched_terms) / len(job_terms)) if job_terms else 0
    return {
        "similarity": round(similarity * 100, 1),
        "keyword_coverage": coverage,
        "job_keywords": job_terms,
        "matched_keywords": matched_terms,
        "missing_keywords": missing_terms,
        "matched_skills": matched,
        "missing_skills": missing,
    }