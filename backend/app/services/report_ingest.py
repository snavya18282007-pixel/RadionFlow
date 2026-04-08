from __future__ import annotations

from fastapi import UploadFile

from app.utils.pdf import extract_text_from_pdf
from app.utils.text import normalize_text
from app.utils.errors import BadRequestError


async def ingest_report(text: str | None, file: UploadFile | None) -> tuple[str, str]:
    if text:
        return normalize_text(text), "text"
    if file:
        if file.content_type not in {"application/pdf", "text/plain"}:
            raise BadRequestError("Unsupported file type")
        data = await file.read()
        if file.content_type == "application/pdf":
            extracted = extract_text_from_pdf(data)
        else:
            extracted = data.decode("utf-8", errors="ignore")
        return normalize_text(extracted), "pdf"
    raise BadRequestError("Provide text or a PDF file")
