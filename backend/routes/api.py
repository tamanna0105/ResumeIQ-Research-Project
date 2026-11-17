from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

from backend.database import list_experiments, record_experiment
from backend.services.ats_analyzer import analyze_ats
from backend.services.resume_compressor import compress_resume
from backend.services.resume_generator import generate_docx, generate_pdf
from backend.services.resume_parser import MAX_UPLOAD_BYTES, parse_resume
from backend.services.retention_evaluator import evaluate_retention
from backend.services.similarity_engine import compare_resume_to_job


router = APIRouter(prefix="/api")


class OptimizeRequest(BaseModel):
    resume_text: str = Field(min_length=1, max_length=100_000)
    job_description: str = Field(min_length=20, max_length=30_000)


class ExportRequest(BaseModel):
    text: str = Field(min_length=1, max_length=100_000)


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "ResumeIQ"}


@router.post("/analyze")
async def analyze_resume(
    file: UploadFile = File(...),
    job_description: str = Form(...),
    target_role: str = Form(default=""),
) -> dict:
    if len(job_description.strip()) < 20:
        raise HTTPException(status_code=422, detail="Add a job description with at least 20 characters.")
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    await file.close()
    try:
        resume_text = parse_resume(file.filename or "", content)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    ats = analyze_ats(resume_text, job_description)
    compression = compress_resume(resume_text, job_description)
    optimized = compression["optimized_text"]
    after_match = compare_resume_to_job(optimized, job_description)
    retention = evaluate_retention(resume_text, optimized)
    experiment_metrics = {
        "compression_percent": compression["compression_percent"],
        "keyword_coverage_percent": after_match["keyword_coverage"],
        "information_retention_percent": retention["token_retention_percent"],
    }
    experiment_id = record_experiment(experiment_metrics)
    return {
        "target_role": target_role.strip(),
        "resume_text": resume_text,
        "ats": ats,
        "compression": compression,
        "retention": retention,
        "research": {
            "metrics": experiment_metrics,
            "experiment_id": experiment_id,
            "definitions": {
                "compression_percent": "(Original word count - optimized word count) / original word count * 100.",
                "keyword_coverage_percent": "Matched extracted job-description keywords / total extracted job-description keywords * 100, measured on the optimized resume.",
                "information_retention_percent": "Normalized word occurrences retained after optimization / total normalized word occurrences in the original * 100.",
            },
        },
    }


@router.post("/optimize")
def optimize_resume(request: OptimizeRequest) -> dict:
    result = compress_resume(request.resume_text, request.job_description)
    result["retention"] = evaluate_retention(request.resume_text, result["optimized_text"])
    return result


@router.post("/export/{format_name}")
def export_resume(format_name: str, request: ExportRequest) -> Response:
    if format_name == "docx":
        content = generate_docx(request.text)
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    elif format_name == "pdf":
        content = generate_pdf(request.text)
        media_type = "application/pdf"
    else:
        raise HTTPException(status_code=404, detail="Choose PDF or DOCX export.")
    return Response(content, media_type=media_type, headers={"Content-Disposition": f'attachment; filename="resumeiq-optimized.{format_name}"'})


@router.get("/experiments")
def experiments() -> dict:
    return {"runs": list_experiments()}