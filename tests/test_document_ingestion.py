"""Tests for unified document ingestion helpers."""

from pathlib import Path

from pypdf import PdfWriter

from src.io.document_ingestion import ingest_document


def test_text_pdf_extraction_success(monkeypatch, tmp_path: Path):
    pdf_path = tmp_path / "text_doc.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    with pdf_path.open("wb") as f:
        writer.write(f)

    monkeypatch.setattr(
        "src.io.document_ingestion._extract_pdf_text",
        lambda _path: "RECETA MEDICA\nMetformina 850 mg cada 12 horas",
    )

    result = ingest_document(str(pdf_path))

    assert result.source == "text_pdf"
    assert "RECETA MEDICA" in result.extracted_text
    assert result.quality_score > 0.9


def test_pdf_with_no_text(tmp_path: Path):
    pdf_path = tmp_path / "empty_doc.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    with pdf_path.open("wb") as f:
        writer.write(f)

    result = ingest_document(str(pdf_path))

    assert result.source == "pdf_no_text"
    assert result.extracted_text == ""
    assert result.quality_score == 0.0


def test_image_input_metadata_detection(tmp_path: Path):
    image_path = tmp_path / "photo.jpg"
    image_path.write_bytes(b"fake-image-bytes")

    result = ingest_document(str(image_path))

    assert result.source == "image"
    assert result.media_path == str(image_path)
    assert result.extracted_text == ""
    assert result.quality_score > 0


def test_unsupported_type_rejection(tmp_path: Path):
    txt_path = tmp_path / "notes.txt"
    txt_path.write_text("not a supported input", encoding="utf-8")

    result = ingest_document(str(txt_path))

    assert result.source == "unsupported"
    assert result.quality_score == 0.0
    assert "Formato no soportado" in result.warnings[0]
