# ResumeIQ

ResumeIQ is a research-oriented resume analysis and compression application. A FastAPI backend extracts selectable text from PDF and DOCX uploads, measures job-description alignment with TF-IDF, and proposes conservative wording simplifications. The browser interface supports review, PDF preview, and PDF download.

Scores are transparent heuristics, not predictions of an employer's or commercial ATS's decisions. Missing skills are signals to assess, not recommendations to claim. Resume text and job descriptions are processed in memory and are not stored; the SQLite experiment ledger keeps aggregate metrics only.

## Features

- PDF and DOCX parsing with an 8 MB upload limit and clear handling of empty, invalid, or image-only files.
- Explainable alignment score: 55% job keyword coverage, 25% section presence, and 20% formatting heuristics.
- TF-IDF keyword ranking and a transparent compatibility score.
- A small set of deterministic phrase simplifications and review-only suggestions for similar details across sections. Resume content is not automatically removed, and no experience or qualifications are added.
- Side-by-side before/after review, original and optimized word counts, and backend-generated PDF preview and download.
- Three measured research metrics: compression percentage, optimized keyword coverage, and information retention percentage.
- Responsive frontend and SQLite aggregate experiment history.

## Project structure

```text
backend/
	main.py
	database.py
	routes/api.py
	services/
		ats_analyzer.py
		keyword_extractor.py
		resume_compressor.py
		resume_generator.py
		resume_parser.py
		retention_evaluator.py
		similarity_engine.py
		text_preprocessing.py
frontend/
	index.html
	css/styles.css
	js/app.js
tests/test_api.py
app.py                    # original Streamlit concept page, retained
requirements.txt
render.yaml
```

## Local setup

Python 3.10 or newer is recommended. From the repository root:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

Open `http://127.0.0.1:8000`. FastAPI's interactive API documentation is at `http://127.0.0.1:8000/docs`; health check: `/api/health`.

The original Streamlit concept page remains available separately with `streamlit run app.py`.

## Testing

Run the backend tests from the repository root:

```powershell
pytest -q
```

Tests cover PDF/DOCX parsing, invalid/empty/oversized uploads, image-only PDFs, missing job description, ATS output, section-preserving compression, duplicate suggestions, occurrence-aware retention, both export formats, and aggregate-only experiment records.

## Research metric definitions

- **Compression percentage:** `(original word count - optimized word count) / original word count * 100`.
- **Keyword coverage:** `matched extracted job-description keywords / total extracted job-description keywords * 100`, calculated on the optimized resume.
- **Information retention:** `normalized word occurrences retained after optimization / total normalized word occurrences in the original * 100`. Repeated words count separately so removing repeated content cannot make retention appear artificially high.

The keyword ranking and section-heading rules are intentionally inspectable in `backend/services/keyword_extractor.py` and `backend/services/ats_analyzer.py`. These rules can miss synonyms and context. Missing terms are suggestions to review, not skills the system assumes a candidate has.

## Deployment on Render

1. Push the repository to GitHub.
2. In Render, choose **New +** then **Blueprint**, and connect the repository containing `render.yaml`.
3. Render installs `requirements.txt` and starts `uvicorn backend.main:app --host 0.0.0.0 --port $PORT` from the repository root.
4. After deploy, open the generated `https://<service>.onrender.com` address and check `/api/health`.

No external AI key or model download is required. The database uses Render's `/tmp` path by default in the blueprint; its contents are ephemeral and only store aggregate experiment records. Configure a persistent disk and set `RESUMEIQ_DB_PATH` if durable experiment history is desired. Uploaded resumes are never written to that database.

## GitHub upload

```powershell
git add backend frontend tests requirements.txt render.yaml README.md .gitignore
git commit -m "Build ResumeIQ analysis application"
git push origin main
```

Do not commit uploaded resumes, `.env` files, virtual environments, or other sensitive material.
