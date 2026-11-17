import re

from sklearn.feature_extraction.text import TfidfVectorizer


SKILLS = {
    "python", "java", "javascript", "typescript", "sql", "c++", "c#", "go", "rust",
    "react", "angular", "vue", "node.js", "fastapi", "django", "flask", "spring",
    "html", "css", "tailwind", "rest api", "graphql", "microservices", "aws", "azure",
    "gcp", "docker", "kubernetes", "terraform", "linux", "git", "ci/cd", "postgresql",
    "mysql", "mongodb", "redis", "pandas", "numpy", "scikit-learn", "machine learning",
    "deep learning", "nlp", "natural language processing", "tensorflow", "pytorch", "excel",
    "power bi", "tableau", "data analysis", "data visualization", "project management",
    "agile", "scrum", "communication", "leadership", "stakeholder management", "testing",
    "unit testing", "selenium", "playwright", "security", "networking", "salesforce",
}


def extract_skills(text: str) -> list[str]:
    lowered = text.lower()
    found = [skill for skill in SKILLS if re.search(r"(?<!\w)" + re.escape(skill) + r"(?!\w)", lowered)]
    return sorted(found)


def extract_keywords(text: str, limit: int = 24) -> list[str]:
    try:
        vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=limit)
        matrix = vectorizer.fit_transform([text])
        names = vectorizer.get_feature_names_out()
        ranked = sorted(zip(names, matrix.toarray()[0]), key=lambda item: (-item[1], item[0]))
        return [term for term, _ in ranked if len(term) > 2]
    except ValueError:
        return []