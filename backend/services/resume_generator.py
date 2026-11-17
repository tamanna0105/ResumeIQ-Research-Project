from io import BytesIO
import re

import fitz
from docx import Document
from docx.shared import Inches, Pt


SECTION_HEADINGS = {
    "education", "academic background", "projects", "selected projects", "academic projects",
    "internship", "internships", "experience", "work experience", "professional experience",
    "technical skills", "skills", "soft skills", "achievements", "awards", "summary",
    "certifications", "certificates", "publications", "volunteer experience",
}
BULLET_LINE = re.compile(r"^(\s*(?:[-*•]|\d+[.)])\s+)(.+)$")


def _is_section_heading(text: str) -> bool:
    normalized = re.sub(r"[^a-z]+", " ", text.lower()).strip()
    return normalized in SECTION_HEADINGS


def _wrap_words(text: str, max_width: float, font_name: str, font_size: float) -> list[str]:
    wrapped = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if current and fitz.get_text_length(candidate, fontname=font_name, fontsize=font_size) > max_width:
            wrapped.append(current)
            current = word
        else:
            current = candidate
    if current:
        wrapped.append(current)
    return wrapped or [""]


def generate_docx(text: str) -> bytes:
    document = Document()
    section = document.sections[0]
    section.top_margin = Inches(0.65)
    section.bottom_margin = Inches(0.65)
    style = document.styles["Normal"]
    style.font.name = "Aptos"
    style.font.size = Pt(10)
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            document.add_paragraph()
            continue
        if _is_section_heading(stripped) or len(stripped) < 45 and stripped.isupper():
            document.add_heading(stripped, level=2)
        elif stripped.startswith(("-", "•", "*")):
            document.add_paragraph(stripped.lstrip("-•* "), style="List Bullet")
        else:
            document.add_paragraph(stripped)
    output = BytesIO()
    document.save(output)
    return output.getvalue()


def generate_pdf(text: str) -> bytes:
    document = fitz.open()
    page = document.new_page()
    left = 52
    right = page.rect.width - 52
    bottom = page.rect.height - 46
    y = 54

    def new_page() -> None:
        nonlocal page, y
        page = document.new_page()
        y = 54

    def insert_wrapped(content: str, x: float, max_width: float, font_name: str, font_size: float, color: tuple[float, float, float]) -> None:
        nonlocal y
        for chunk in _wrap_words(content, max_width, font_name, font_size):
            if y + font_size + 4 > bottom:
                new_page()
            page.insert_text((x, y), chunk, fontsize=font_size, fontname=font_name, color=color)
            y += font_size + 4

    for line_index, raw_line in enumerate(text.splitlines()):
        line = raw_line.strip()
        line = line.strip()
        if not line:
            y += 8
            continue
        if _is_section_heading(line) or line_index == 0 and not BULLET_LINE.match(line):
            if y + 24 > bottom:
                new_page()
            if line_index == 0 and not _is_section_heading(line):
                y += 3
                insert_wrapped(line, left, right - left, "hebo", 16, (0.12, 0.18, 0.29))
                y += 2
            else:
                y += 5
                insert_wrapped(line, left, right - left, "hebo", 11, (0.27, 0.38, 0.62))
                y += 2
            continue

        bullet = BULLET_LINE.match(line)
        if bullet:
            prefix, content = bullet.groups()
            marker = prefix.strip()
            marker_width = fitz.get_text_length(marker + " ", fontname="helv", fontsize=10)
            if y + 14 > bottom:
                new_page()
            page.insert_text((left, y), marker, fontsize=10, fontname="helv", color=(0.22, 0.29, 0.4))
            insert_wrapped(content, left + marker_width + 3, right - left - marker_width - 3, "helv", 10, (0.2, 0.24, 0.31))
            continue

        insert_wrapped(line, left, right - left, "helv", 10, (0.2, 0.24, 0.31))
    output = document.tobytes()
    document.close()
    return output