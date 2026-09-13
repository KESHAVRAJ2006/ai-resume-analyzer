"""Tests for the file -> raw text layer."""

from pathlib import Path

import pytest

from app.services.exceptions import (
    EmptyResumeError,
    FileNotFoundErrorService,
    ResumeParseError,
    UnsupportedFileTypeError,
)
from app.services.resume_parser import parse_resume


def test_parses_docx(sample_docx: Path) -> None:
    """A .docx resume yields its paragraph text."""
    text = parse_resume(sample_docx)
    assert "TECHNICAL SKILLS" in text
    assert "C++" in text
    assert "Node.js" in text


def test_parses_docx_tables(sample_docx_with_table: Path) -> None:
    """Skills stored in a table are extracted, not silently dropped."""
    text = parse_resume(sample_docx_with_table)
    assert "Python, C++, JavaScript" in text
    assert "Kubernetes" in text


def test_parses_pdf(sample_pdf: Path) -> None:
    """A text-based .pdf yields its page text."""
    text = parse_resume(sample_pdf)
    assert "PROFESSIONAL SUMMARY" in text
    assert "scikit-learn" in text


def test_pdf_keeps_line_breaks(sample_pdf: Path) -> None:
    """Line structure survives parsing; section_splitter depends on it."""
    assert "\n" in parse_resume(sample_pdf)


def test_unsupported_extension_raises(tmp_path: Path) -> None:
    """A .txt upload is rejected by type, not by trying to parse it."""
    path = tmp_path / "resume.txt"
    path.write_text("hello", encoding="utf-8")
    with pytest.raises(UnsupportedFileTypeError):
        parse_resume(path)


def test_missing_file_raises(tmp_path: Path) -> None:
    """A path that does not exist raises the service-level not-found error."""
    with pytest.raises(FileNotFoundErrorService):
        parse_resume(tmp_path / "nope.pdf")


def test_scanned_pdf_raises_empty(blank_pdf: Path) -> None:
    """An image-only PDF gives a clear 'no text' error, not an empty string."""
    with pytest.raises(EmptyResumeError):
        parse_resume(blank_pdf)


def test_corrupt_pdf_raises_parse_error(tmp_path: Path) -> None:
    """A file with a .pdf name but garbage bytes raises ResumeParseError."""
    path = tmp_path / "broken.pdf"
    path.write_bytes(b"this is definitely not a pdf")
    with pytest.raises(ResumeParseError):
        parse_resume(path)
