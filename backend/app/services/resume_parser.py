"""Turn an uploaded resume file into raw text.

Single responsibility: bytes on disk -> text. It does NOT clean, lowercase or
interpret the text; that is text_cleaner's job. Line breaks are deliberately
preserved because section_splitter needs them to find headings.

PRIVACY: this module reads the whole document, but nothing downstream extracts
or scores name, gender, age, photo, religion, nationality, marital status or
disability. Contact details are redacted in text_cleaner before any analysis.
"""

from pathlib import Path

from docx import Document
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.services.exceptions import (
    EmptyResumeError,
    FileNotFoundErrorService,
    ResumeParseError,
    UnsupportedFileTypeError,
)

SUPPORTED_EXTENSIONS: frozenset[str] = frozenset({".pdf", ".docx"})

# A real one-page resume is ~2000 characters. 120 is far below any genuine
# resume but far above a scanned/image-only PDF, which yields 0-20 characters.
MIN_MEANINGFUL_CHARS: int = 120


def parse_resume(file_path: str | Path) -> str:
    """Take a path to a .pdf or .docx file, return its raw text with line breaks.

    Raises UnsupportedFileTypeError, FileNotFoundErrorService, ResumeParseError
    or EmptyResumeError - never an HTTP exception.
    """
    path = Path(file_path)

    if not path.exists() or not path.is_file():
        raise FileNotFoundErrorService(f"No file at {path}")

    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFileTypeError(
            f"'{suffix or path.name}' is not supported. Upload a PDF or DOCX file."
        )

    text = _parse_pdf(path) if suffix == ".pdf" else _parse_docx(path)
    text = _normalise_line_endings(text)

    if len(text.strip()) < MIN_MEANINGFUL_CHARS:
        raise EmptyResumeError(
            "Almost no text could be read from this file. If your resume is a "
            "scanned image, export it as a text-based PDF and try again."
        )

    return text


def _parse_pdf(path: Path) -> str:
    """Take a PDF path, return the concatenated text of every page."""
    try:
        reader = PdfReader(str(path))

        # Some resumes are exported with an empty owner password. Trying "" lets
        # us read those instead of failing on a file the user can open fine.
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception as exc:  # pypdf raises several unrelated types here
                raise ResumeParseError("This PDF is password protected.") from exc

        pages: list[str] = []
        for page in reader.pages:
            # extract_text() returns None for pages with no text layer.
            pages.append(page.extract_text() or "")
    except ResumeParseError:
        raise
    except (PdfReadError, OSError, ValueError) as exc:
        raise ResumeParseError(f"Could not read this PDF: {exc}") from exc

    # A blank line between pages stops the last line of page 1 from being glued
    # to the first heading of page 2.
    return "\n\n".join(pages)


def _parse_docx(path: Path) -> str:
    """Take a DOCX path, return its paragraph and table text in reading order."""
    try:
        document = Document(str(path))
    except Exception as exc:  # python-docx raises PackageNotFoundError and friends
        raise ResumeParseError(f"Could not read this DOCX file: {exc}") from exc

    blocks: list[str] = [paragraph.text for paragraph in document.paragraphs]

    # Many resume templates put the entire skills list inside a table, which
    # document.paragraphs does not reach. Missing those would lose most skills.
    for table in document.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if cells:
                blocks.append(" | ".join(cells))

    return "\n".join(blocks)


def _normalise_line_endings(text: str) -> str:
    """Take text with any line endings, return it using \n only."""
    return text.replace("\r\n", "\n").replace("\r", "\n")
