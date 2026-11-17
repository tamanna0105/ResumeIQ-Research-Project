from io import BytesIO

import fitz
import pytest
from docx import Document
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.ats_analyzer import analyze_ats
from backend.services.resume_compressor import compress_resume
from backend.services.resume_generator import generate_pdf
from backend.services.resume_parser import MAX_UPLOAD_BYTES, parse_resume
from backend.services.retention_evaluator import evaluate_retention
from backend.services.text_preprocessing import word_count


client = TestClient(app)
JOB_DESCRIPTION = "We need a Python data analyst with SQL, communication, and experience building dashboards."
RESUME_TEXT = """ALEX MORGAN
SUMMARY
Data analyst with Python and SQL experience. Skilled in building dashboards and communicating results.
EXPERIENCE
- Built dashboards with Python and SQL for a team of analysts.
- Improved data reporting workflows and communicated results to stakeholders.
EDUCATION
Bachelor of Computer Science
SKILLS
Python, SQL, Tableau, data analysis, communication
PROJECTS
- Created a portfolio project using Python and Tableau.
"""
MULTI_SECTION_RESUME = """JORDAN LEE

Education
North Coast University | B.S. Computer Science | 2022 | GPA: 3.8

Projects
ResumeIQ Analytics Platform
- Built a Python and FastAPI analysis service processing 1,200 records for the university research lab.
- In order to improve response times, added SQL indexes that reduced report generation time by 35%.

Internship
North Coast Research Lab | May 2023 - Aug 2023
- Built Python and SQL dashboards to report weekly laboratory results to project supervisors.

Technical Skills
Python, SQL, FastAPI, JavaScript, Git

Soft Skills
Communication, mentoring, cross-functional collaboration

Achievements
- Received the Dean's Research Award in 2022 for a project evaluated at 96%.
"""


def make_pdf(text: str = RESUME_TEXT) -> bytes:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((50, 50), text)
    content = document.tobytes()
    document.close()
    return content


def make_docx(text: str = RESUME_TEXT) -> bytes:
    document = Document()
    for line in text.splitlines():
        document.add_paragraph(line)
    output = BytesIO()
    document.save(output)
    return output.getvalue()


def test_health_route():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_analyze_pdf_returns_explainable_results():
    response = client.post(
        "/api/analyze",
        files={"file": ("resume.pdf", make_pdf(), "application/pdf")},
        data={"job_description": JOB_DESCRIPTION, "target_role": "Data analyst"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["target_role"] == "Data analyst"
    assert body["ats"]["overall_score"] >= 0
    assert body["ats"]["matching"]["matched_skills"]
    assert "not an actual ATS" in body["ats"]["score_method"]
    assert set(body["research"]["metrics"]) == {
        "compression_percent", "keyword_coverage_percent", "information_retention_percent",
    }
    assert 0 <= body["research"]["metrics"]["keyword_coverage_percent"] <= 100
    assert body["research"]["experiment_id"]


def test_analyze_docx_and_reject_bad_inputs():
    response = client.post(
        "/api/analyze",
        files={"file": ("resume.docx", make_docx(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        data={"job_description": JOB_DESCRIPTION},
    )
    assert response.status_code == 200
    assert "ALEX MORGAN" in response.json()["resume_text"]

    missing_job = client.post("/api/analyze", files={"file": ("resume.pdf", make_pdf(), "application/pdf")}, data={"job_description": "short"})
    assert missing_job.status_code == 422

    empty = client.post("/api/analyze", files={"file": ("resume.pdf", b"", "application/pdf")}, data={"job_description": JOB_DESCRIPTION})
    assert empty.status_code == 400

    invalid = client.post("/api/analyze", files={"file": ("resume.txt", b"not a resume", "text/plain")}, data={"job_description": JOB_DESCRIPTION})
    assert invalid.status_code == 400


def test_upload_size_and_image_only_pdf_validation():
    with pytest.raises(ValueError, match="8 MB"):
        parse_resume("oversized.pdf", b"x" * (MAX_UPLOAD_BYTES + 1))

    document = fitz.open()
    document.new_page()
    image_only_pdf = document.tobytes()
    document.close()
    with pytest.raises(ValueError, match="No selectable text"):
        parse_resume("scan.pdf", image_only_pdf)


def test_compression_removes_duplicate_without_inventing_facts():
    source = """Projects
Research Metrics Dashboard
- Built Python and SQL dashboards for weekly laboratory results with Tableau metrics.

Internship
North Coast Research Lab | May 2023 - Aug 2023
- Built Python and SQL dashboards for weekly laboratory results for project supervisors.
"""
    result = compress_resume(source)
    assert result["optimized_text"].count("Built Python and SQL dashboards") == 2
    assert result["optimized_text"].count("weekly laboratory results") == 2
    assert result["duplicate_suggestions"]
    suggestion = result["duplicate_suggestions"][0]
    assert {suggestion["section"], suggestion["related_section"]} == {"projects", "internship"}
    assert "kept both" in suggestion["message"]


def test_information_retention_counts_repeated_word_occurrences():
    result = evaluate_retention("Python Python SQL dashboards", "Python SQL dashboards")
    assert result["token_retention_percent"] == 75


def test_compression_simplifies_technical_sentence_without_losing_details():
    source = """Projects
Telemetry Stream Processor
- In an effort to conduct an analysis of Kafka events, we made use of Python and Apache Kafka to process 2 million events daily.
"""
    result = compress_resume(source)
    optimized = result["optimized_text"]

    assert "To analyze Kafka events, we used Python and Apache Kafka to process 2 million events daily." in optimized
    assert "Telemetry Stream Processor" in optimized
    assert "2 million events daily" in optimized
    assert result["optimized_word_count"] < result["original_word_count"]


def test_compression_preserves_resume_sections_facts_and_spacing():
    result = compress_resume(MULTI_SECTION_RESUME)
    optimized = result["optimized_text"]
    required_sections = ["Education", "Projects", "Internship", "Technical Skills", "Soft Skills", "Achievements"]
    section_positions = [optimized.index(section) for section in required_sections]

    assert section_positions == sorted(section_positions)
    assert "ResumeIQ Analytics Platform" in optimized
    assert "North Coast University" in optimized
    assert "North Coast Research Lab | May 2023 - Aug 2023" in optimized
    assert "1,200 records" in optimized and "35%" in optimized and "96%" in optimized and "GPA: 3.8" in optimized
    assert "Python, SQL, FastAPI, JavaScript, Git" in optimized
    assert "Communication, mentoring, cross-functional collaboration" in optimized
    assert "In order to" not in optimized
    assert "To improve response times" in optimized
    assert "\n\nProjects\n" in optimized
    assert "\n- Built a Python and FastAPI analysis service" in optimized
    assert result["original_word_count"] == word_count(MULTI_SECTION_RESUME)
    assert result["optimized_word_count"] == word_count(optimized)
    assert result["optimized_word_count"] < result["original_word_count"]
    assert result["compression_percent"] == round(
        100 * (result["original_word_count"] - result["optimized_word_count"]) / result["original_word_count"], 1,
    )

    parsed_docx = parse_resume("resume.docx", make_docx(MULTI_SECTION_RESUME))
    parsed_optimized = compress_resume(parsed_docx)["optimized_text"]
    assert "\n\nProjects\n" in parsed_optimized
    assert "\n\nInternship\n" in parsed_optimized

    response = client.post(
        "/api/analyze",
        files={"file": ("multi-section.docx", make_docx(MULTI_SECTION_RESUME), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        data={"job_description": JOB_DESCRIPTION},
    )
    assert response.status_code == 200
    body = response.json()
    api_optimized = body["compression"]["optimized_text"]
    assert "\n\nProjects\n" in api_optimized and "\n\nInternship\n" in api_optimized
    assert "ResumeIQ Analytics Platform" in api_optimized
    assert "North Coast University" in api_optimized and "North Coast Research Lab | May 2023 - Aug 2023" in api_optimized
    assert "1,200 records" in api_optimized and "35%" in api_optimized and "96%" in api_optimized
    assert body["compression"]["optimized_word_count"] == word_count(api_optimized)
    assert body["research"]["metrics"]["information_retention_percent"] == body["retention"]["token_retention_percent"]


def test_short_long_incomplete_and_irrelevant_resumes():
    short_result = analyze_ats("Jordan Lee\nSKILLS\nPython", "Aerospace engineer with MATLAB and aircraft design experience.")
    long_text = "SUMMARY\nPython data analyst with SQL experience.\nEXPERIENCE\n- Built reports.\n" + "Python SQL data analysis dashboards. " * 300
    long_result = analyze_ats(long_text, "Aerospace engineer with MATLAB and aircraft design experience.")

    assert short_result["sections"]["Experience"] is False
    assert short_result["sections"]["Education"] is False
    assert short_result["matching"]["matched_skills"] == []
    assert short_result["formatting_score"] < long_result["formatting_score"]


def test_optimize_and_export_formats():
    optimized = client.post("/api/optimize", json={"resume_text": RESUME_TEXT, "job_description": JOB_DESCRIPTION})
    assert optimized.status_code == 200
    assert optimized.json()["retention"]["skill_retention_percent"] == 100
    assert optimized.json()["retention"]["token_retention_percent"] == 100

    duplicate_resume = "Projects\nResearch Metrics Dashboard\n- Built Python and SQL dashboards for weekly laboratory results with Tableau metrics.\n\nInternship\nNorth Coast Research Lab\n- Built Python and SQL dashboards for weekly laboratory results for project supervisors."
    duplicate_response = client.post("/api/optimize", json={"resume_text": duplicate_resume, "job_description": JOB_DESCRIPTION})
    assert duplicate_response.status_code == 200
    assert duplicate_response.json()["optimized_text"].count("Built Python and SQL dashboards") == 2
    assert duplicate_response.json()["duplicate_suggestions"]

    pdf = client.post("/api/export/pdf", json={"text": RESUME_TEXT})
    docx = client.post("/api/export/docx", json={"text": RESUME_TEXT})
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF-")
    assert docx.status_code == 200 and docx.content.startswith(b"PK")


def test_pdf_export_formats_headings_and_wraps_bullets_without_breaking_words():
    long_bullet = "- Designed a modular Python and FastAPI platform with PostgreSQL storage, careful validation, and automated tests for research workflows."
    output = generate_pdf(MULTI_SECTION_RESUME + "\n" + long_bullet)
    document = fitz.open(stream=output, filetype="pdf")
    extracted = "\n".join(page.get_text("text") for page in document)
    spans = [span for page in document for block in page.get_text("dict")["blocks"] if "lines" in block for line in block["lines"] for span in line["spans"]]
    document.close()

    assert "ResumeIQ Analytics Platform" in extracted
    assert "North Coast University" in extracted
    assert "May 2023 - Aug 2023" in extracted
    assert "1,200 records" in extracted and "35%" in extracted and "96%" in extracted
    assert "modular Python and FastAPI platform with PostgreSQL storage" in " ".join(extracted.split())
    heading_spans = [span for span in spans if span["text"].strip() == "Projects"]
    assert heading_spans and any("bold" in span["font"].lower() or span["size"] > 10 for span in heading_spans)


def test_experiment_ledger_contains_metrics_not_resume_text():
    response = client.get("/api/experiments")
    assert response.status_code == 200
    runs = response.json()["runs"]
    assert runs
    assert "ALEX MORGAN" not in str(runs)
    assert set(runs[0]) >= {
        "compression_percent", "keyword_coverage_percent", "information_retention_percent",
    }