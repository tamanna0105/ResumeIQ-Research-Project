from io import BytesIO

import fitz
from docx import Document


MAX_UPLOAD_BYTES = 8 * 1024 * 1024
SUPPORTED_TYPES = {".pdf", ".docx"}


def parse_resume(filename: str, content: bytes) -> str:
    """Validate and extract text from an in-memory PDF or DOCX upload."""
    suffix = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if suffix not in SUPPORTED_TYPES:
        raise ValueError("Upload a PDF or DOCX resume.")
    if not content:
        raise ValueError("The uploaded file is empty.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValueError("The file exceeds the 8 MB upload limit.")

    try:
        if suffix == ".pdf":
            if not content.startswith(b"%PDF-"):
                raise ValueError("The file does not appear to be a valid PDF.")
            with fitz.open(stream=content, filetype="pdf") as document:
                text = "\n".join(page.get_text("text") for page in document)
        else:
            if not content.startswith(b"PK"):
                raise ValueError("The file does not appear to be a valid DOCX document.")
            document = Document(BytesIO(content))
            parts = [paragraph.text for paragraph in document.paragraphs]
            for table in document.tables:
                parts.extend(cell.text for row in table.rows for cell in row.cells)
            text = "\n".join(parts)
    except ValueError:
        raise
    except Exception as error:
        raise ValueError("We could not read this document. Try exporting it again as PDF or DOCX.") from error

    text = "\n".join(line.rstrip() for line in text.splitlines()).strip()
    if not text.strip():
        raise ValueError("No selectable text was found. Scanned image-only resumes are not supported yet.")
    return text