import re

from backend.services.text_preprocessing import token_retention_percent, word_count


REWRITES = (
    (re.compile(r"\bdue to the fact that\b", re.I), "because"),
    (re.compile(r"\bin order to\b", re.I), "to"),
    (re.compile(r"\bat this point in time\b", re.I), "currently"),
    (re.compile(r"\bfor the purpose of\b", re.I), "for"),
    (re.compile(r"\bwith the aim of\b", re.I), "to"),
    (re.compile(r"\bin an effort to\b", re.I), "to"),
    (re.compile(r"\bmade use of\b", re.I), "used"),
    (re.compile(r"\bconduct an analysis of\b", re.I), "analyze"),
    (re.compile(r"\bconducted an analysis of\b", re.I), "analyzed"),
    (re.compile(r"\bperform an analysis of\b", re.I), "analyze"),
    (re.compile(r"\bperformed an analysis of\b", re.I), "analyzed"),
    (re.compile(r"\bconducted a review of\b", re.I), "reviewed"),
    (re.compile(r"\bprovided support for\b", re.I), "supported"),
    (re.compile(r"\butilized\b", re.I), "used"),
)
SECTION_HEADINGS = {
    "education", "academic background", "projects", "selected projects", "academic projects",
    "internship", "internships", "experience", "work experience", "professional experience",
    "technical skills", "skills", "soft skills", "achievements", "awards", "summary",
    "certifications", "certificates", "publications", "volunteer experience",
}
BULLET_LINE = re.compile(r"^(\s*(?:[-*•]|\d+[.)])\s+)(.+)$")
DUPLICATE_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "being", "by", "for", "from",
    "had", "has", "have", "in", "into", "is", "it", "its", "of", "on", "or", "that",
    "the", "their", "this", "to", "was", "were", "with", "using", "used", "built",
    "created", "developed", "designed", "implemented", "project", "projects", "worked",
}


def compress_resume(text: str, job_description: str = "") -> dict:
    del job_description
    lines = []
    content_entries = []
    wording_simplifications = 0
    section = "preamble"
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            lines.append("")
            continue

        heading = _section_heading(stripped)
        if heading:
            section = heading
            lines.append(line)
            continue

        bullet = BULLET_LINE.match(line)
        if bullet:
            prefix, content = bullet.groups()
            content_entries.append((section, content.strip()))
            content, replacements = _simplify(content)
            wording_simplifications += replacements
            lines.append(prefix + content)
            continue

        if len(stripped.split()) >= 5:
            content_entries.append((section, stripped))
        simplified, replacements = _simplify(line)
        wording_simplifications += replacements
        lines.append(simplified)

    optimized = "\n".join(lines).strip()
    duplicate_suggestions = _find_duplicate_suggestions(content_entries)
    original_words = word_count(text)
    optimized_words = word_count(optimized)
    reduction = max(0, original_words - optimized_words)
    return {
        "optimized_text": optimized,
        "original_word_count": original_words,
        "optimized_word_count": optimized_words,
        "compression_percent": round(100 * reduction / original_words, 1) if original_words else 0,
        "retention_percent": token_retention_percent(text, optimized),
        "duplicate_suggestions": duplicate_suggestions,
        "changes": {"wording_simplifications": wording_simplifications},
    }


def _section_heading(text: str) -> str | None:
    normalized = re.sub(r"[^a-z]+", " ", text.lower()).strip()
    return normalized if normalized in SECTION_HEADINGS else None


def _simplify(text: str) -> tuple[str, int]:
    count = 0
    for pattern, replacement in REWRITES:
        def preserve_case(match: re.Match) -> str:
            original = match.group(0)
            if original.isupper():
                return replacement.upper()
            if original[:1].isupper():
                return replacement.capitalize()
            return replacement

        text, replacements = pattern.subn(preserve_case, text)
        count += replacements
    return text, count


def _find_duplicate_suggestions(entries: list[tuple[str, str]]) -> list[dict[str, str]]:
    suggestions = []
    for right_index, (right_section, right_text) in enumerate(entries):
        right_tokens = _meaningful_tokens(right_text)
        if len(right_tokens) < 5:
            continue
        for left_section, left_text in entries[:right_index]:
            if left_section == right_section:
                continue
            left_tokens = _meaningful_tokens(left_text)
            if len(left_tokens) < 5:
                continue
            overlap = len(left_tokens & right_tokens) / min(len(left_tokens), len(right_tokens))
            if overlap >= 0.75:
                suggestions.append({
                    "section": right_section,
                    "related_section": left_section,
                    "text": right_text[:220],
                    "related_text": left_text[:220],
                    "message": f"This may overlap with a detail under {left_section.title()}. Review both entries; ResumeIQ kept both.",
                })
                break
        if len(suggestions) >= 8:
            break
    return suggestions


def _meaningful_tokens(text: str) -> set[str]:
    return {
        token for token in re.findall(r"[a-zA-Z0-9+#.]+", text.lower())
        if token not in DUPLICATE_STOPWORDS
    }

