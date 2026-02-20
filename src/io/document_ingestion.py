"""Unified document ingestion for image/PDF inputs."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from pypdf import PdfReader

from src.models import EvidenceSource

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
PDF_EXTENSION = ".pdf"


@dataclass
class IngestedDocument:
    """Normalized ingestion output for routing and verification."""

    file_path: str
    source: EvidenceSource
    extracted_text: str = ""
    quality_score: float = 0.0
    warnings: list[str] = field(default_factory=list)
    media_path: str = ""


def _extract_pdf_text(path: Path) -> str:
    reader = PdfReader(str(path))
    texts: list[str] = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        if page_text.strip():
            texts.append(page_text.strip())
    return "\n\n".join(texts).strip()


def ingest_document(file_path: str) -> IngestedDocument:
    """Ingest a user document and return best-effort textual evidence."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Document not found: {file_path}")

    ext = path.suffix.lower()
    if ext in IMAGE_EXTENSIONS:
        return IngestedDocument(
            file_path=str(path),
            source="image",
            extracted_text="",
            quality_score=0.7,
            warnings=[],
            media_path=str(path),
        )

    if ext == PDF_EXTENSION:
        try:
            text = _extract_pdf_text(path)
        except Exception:
            return IngestedDocument(
                file_path=str(path),
                source="pdf_no_text",
                extracted_text="",
                quality_score=0.0,
                warnings=[
                    "No se pudo extraer texto del PDF. Si es escaneado, conviértalo a imagen y vuelva a intentarlo."
                ],
                media_path="",
            )

        if text:
            return IngestedDocument(
                file_path=str(path),
                source="text_pdf",
                extracted_text=text,
                quality_score=0.95,
                warnings=[],
                media_path="",
            )

        return IngestedDocument(
            file_path=str(path),
            source="pdf_no_text",
            extracted_text="",
            quality_score=0.0,
            warnings=[
                "El PDF no tiene texto digital extraíble. En esta versión no se soporta OCR de PDF escaneado."
            ],
            media_path="",
        )

    return IngestedDocument(
        file_path=str(path),
        source="unsupported",
        extracted_text="",
        quality_score=0.0,
        warnings=[
            "Formato no soportado. Use PDF con texto o imagen JPG/JPEG/PNG."
        ],
        media_path="",
    )
