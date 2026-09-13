"""Tests for the PDF report.

The assertions read the generated PDF back with pypdf rather than checking a
byte count. A PDF that is 40KB and blank passes a size check and fails a
reader; extracting the text is the only way to know the content is really there.
"""

from io import BytesIO

import pytest
from pypdf import PdfReader

from app.services.report_builder import build_report, suggested_filename


@pytest.fixture(scope="module")
def analysis() -> dict:
    """A realistic analysis payload, shaped exactly like AnalysisResponse."""
    return {
        "target_role": {
            "role_id": "backend_developer",
            "role_name": "Backend Developer",
            "category": "Software Engineering",
            "score": 62.4,
            "band": "developing",
            "skill_coverage": 0.55,
            "tfidf_score": 0.31,
            "semantic_score": 0.68,
        },
        "skills_found": [
            {
                "skill_id": "python",
                "name": "Python",
                "category": "Programming Languages",
                "matched_text": "python",
                "occurrences": 3,
                "found_in": ["skills", "experience"],
            },
            {
                "skill_id": "docker",
                "name": "Docker",
                "category": "Cloud & DevOps",
                "matched_text": "docker",
                "occurrences": 1,
                "found_in": ["skills"],
            },
        ],
        "skills_by_category": {
            "Programming Languages": [
                {
                    "skill_id": "python",
                    "name": "Python",
                    "category": "Programming Languages",
                    "matched_text": "python",
                    "occurrences": 3,
                    "found_in": ["skills", "experience"],
                }
            ],
            "Cloud & DevOps": [
                {
                    "skill_id": "docker",
                    "name": "Docker",
                    "category": "Cloud & DevOps",
                    "matched_text": "docker",
                    "occurrences": 1,
                    "found_in": ["skills"],
                }
            ],
        },
        "role_ranking": [
            {
                "role_id": "backend_developer",
                "role_name": "Backend Developer",
                "category": "Software Engineering",
                "score": 62.4,
                "band": "developing",
                "skill_coverage": 0.55,
                "tfidf_score": 0.31,
                "semantic_score": 0.68,
            },
            {
                "role_id": "devops_engineer",
                "role_name": "DevOps Engineer",
                "category": "Infrastructure",
                "score": 41.0,
                "band": "developing",
                "skill_coverage": 0.3,
                "tfidf_score": 0.2,
                "semantic_score": 0.5,
            },
        ],
        "gaps": {
            "summary": "2 must-have skills missing for Backend Developer (4 of 18 skills matched).",
            "matched": [
                {
                    "skill_id": "python",
                    "name": "Python",
                    "category": "Programming Languages",
                    "tier": "must_have",
                    "weight": 3,
                    "found_in": ["skills"],
                }
            ],
            "missing": [
                {
                    "skill_id": "postgresql",
                    "name": "PostgreSQL",
                    "category": "Databases & Data Engineering",
                    "tier": "must_have",
                    "severity": "critical",
                    "weight": 3,
                },
                {
                    "skill_id": "graphql",
                    "name": "GraphQL",
                    "category": "Backend & APIs",
                    "tier": "nice_to_have",
                    "severity": "optional",
                    "weight": 1,
                },
            ],
            "earned_weight": 9,
            "total_weight": 34,
            "tier_summary": {
                "must_have": {"have": 3, "total": 5},
                "good_to_have": {"have": 1, "total": 7},
                "nice_to_have": {"have": 0, "total": 6},
            },
        },
        "roadmap": [
            {
                "week": 1,
                "title": "Learn PostgreSQL",
                "objective": "Close 1 must-have requirement.",
                "focus_skills": ["PostgreSQL"],
                "activities": [
                    "Learn the PostgreSQL data model and load a real public dataset into it",
                    "Write ten PostgreSQL queries, from simple filters through joins to aggregates",
                ],
                "estimated_hours": 5,
            },
            {
                "week": 2,
                "title": "Deepen your strongest project",
                "objective": "Make it production-grade.",
                "focus_skills": [],
                "activities": ["Add error handling everywhere it is missing"],
                "estimated_hours": 10,
            },
            {
                "week": 3,
                "title": "Prove it with tests",
                "objective": "Testing is the fastest way to look senior.",
                "focus_skills": [],
                "activities": ["Add unit tests for the trickiest function"],
                "estimated_hours": 10,
            },
            {
                "week": 4,
                "title": "Communicate the work",
                "objective": "Unexplained work does not count.",
                "focus_skills": [],
                "activities": ["Write a short post about the hardest bug you fixed"],
                "estimated_hours": 10,
            },
        ],
        "meta": {
            "filename": "priya_sharma_resume.pdf",
            "analyzed_at": "2026-09-13T10:30:00+00:00",
            "semantic_enabled": True,
            "sections_detected": ["skills", "experience"],
            "disclaimer": "This score estimates how well your listed skills overlap.",
        },
    }


@pytest.fixture(scope="module")
def pdf_bytes(analysis: dict) -> bytes:
    """Build the report once for the whole module."""
    return build_report(analysis)


@pytest.fixture(scope="module")
def pdf_text(pdf_bytes: bytes) -> str:
    """Return every page's text, concatenated."""
    reader = PdfReader(BytesIO(pdf_bytes))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


# --------------------------------------------------------------------------
# It is a real PDF
# --------------------------------------------------------------------------

def test_output_is_a_pdf(pdf_bytes: bytes) -> None:
    """The bytes start with the PDF magic number."""
    assert pdf_bytes.startswith(b"%PDF-")


def test_pdf_opens_and_has_pages(pdf_bytes: bytes) -> None:
    """A reader can parse it and it is not empty."""
    reader = PdfReader(BytesIO(pdf_bytes))
    assert len(reader.pages) >= 1


def test_pdf_is_not_blank(pdf_text: str) -> None:
    """Text was actually drawn, not just a page allocated."""
    assert len(pdf_text.strip()) > 400


# --------------------------------------------------------------------------
# The content is present
# --------------------------------------------------------------------------

def test_contains_the_role_and_score(pdf_text: str) -> None:
    """The headline facts are on the page."""
    assert "Backend Developer" in pdf_text
    assert "62%" in pdf_text  # rounded from 62.4


def test_contains_the_three_tiers(pdf_text: str) -> None:
    """The score breakdown is shown, so the number is not a black box."""
    for label in ("Skill coverage", "Meaning similarity", "Keyword similarity"):
        assert label in pdf_text


def test_contains_detected_skills(pdf_text: str) -> None:
    """Skills appear under their categories."""
    assert "Python" in pdf_text
    assert "Docker" in pdf_text
    assert "Programming Languages" in pdf_text


def test_contains_the_role_ranking(pdf_text: str) -> None:
    """Every compared role is listed."""
    assert "DevOps Engineer" in pdf_text


def test_contains_missing_skills_with_severity(pdf_text: str) -> None:
    """The gap table carries both the skill and how badly it is needed."""
    assert "PostgreSQL" in pdf_text
    assert "CRITICAL" in pdf_text


def test_contains_all_four_roadmap_weeks(pdf_text: str) -> None:
    """The plan is complete, not truncated by a page break."""
    for week in range(1, 5):
        assert f"WEEK {week}" in pdf_text


def test_contains_roadmap_activities(pdf_text: str) -> None:
    """The actual tasks are printed, not just the week titles."""
    assert "load a real public dataset" in pdf_text


# --------------------------------------------------------------------------
# Privacy and safety
# --------------------------------------------------------------------------

def test_disclaimer_is_on_every_page(pdf_bytes: bytes) -> None:
    """A reader who sees only page 2 still learns what the score means."""
    reader = PdfReader(BytesIO(pdf_bytes))
    for index, page in enumerate(reader.pages):
        assert "not a hiring decision" in (page.extract_text() or ""), f"page {index + 1}"


def test_uploaded_filename_is_not_printed(pdf_text: str) -> None:
    """The resume's filename often contains a person's name, so it is omitted."""
    assert "priya_sharma_resume" not in pdf_text.lower()


def test_pdf_metadata_carries_no_personal_data(pdf_bytes: bytes) -> None:
    """Document properties are another place a name leaks in unnoticed."""
    reader = PdfReader(BytesIO(pdf_bytes))
    blob = " ".join(str(value) for value in (reader.metadata or {}).values()).lower()
    assert "priya" not in blob
    assert "sharma" not in blob


# --------------------------------------------------------------------------
# Filenames
# --------------------------------------------------------------------------

def test_filename_is_built_from_the_role_and_date(analysis: dict) -> None:
    """Predictable, sortable, and not derived from user input."""
    name = suggested_filename(analysis)
    assert name.startswith("resume-analysis-backend_developer-")
    assert name.endswith(".pdf")


def test_filename_strips_unsafe_characters() -> None:
    """A crafted role_id cannot inject a path into the download header."""
    name = suggested_filename({"target_role": {"role_id": "../../etc/passwd"}})
    assert "/" not in name
    assert ".." not in name


# --------------------------------------------------------------------------
# Edge cases that would otherwise 500 in production
# --------------------------------------------------------------------------

def test_handles_a_missing_semantic_tier(analysis: dict) -> None:
    """Two-tier mode prints 'n/a' rather than crashing on None."""
    payload = {**analysis, "target_role": {**analysis["target_role"], "semantic_score": None}}
    text = _text_of(build_report(payload))
    assert "n/a" in text


def test_handles_a_resume_with_no_skills(analysis: dict) -> None:
    """An empty analysis still produces a readable document."""
    payload = {**analysis, "skills_found": [], "skills_by_category": {}}
    text = _text_of(build_report(payload))
    assert "No known skills were detected" in text


def test_handles_a_perfect_match(analysis: dict) -> None:
    """No gaps means a different sentence, not an empty table."""
    payload = {
        **analysis,
        "gaps": {**analysis["gaps"], "missing": []},
    }
    text = _text_of(build_report(payload))
    assert "Every skill listed for this role was detected" in text


def test_handles_a_zero_score(analysis: dict) -> None:
    """A 0% dial draws no arc and must not raise."""
    payload = {**analysis, "target_role": {**analysis["target_role"], "score": 0.0, "band": "early"}}
    assert build_report(payload).startswith(b"%PDF-")


def test_handles_a_long_skill_list(analysis: dict) -> None:
    """Enough content to force a page break still renders every section."""
    many = [
        {
            "skill_id": f"skill_{index}",
            "name": f"Skill Number {index}",
            "category": "Programming Languages",
            "matched_text": f"skill {index}",
            "occurrences": 1,
            "found_in": ["skills"],
        }
        for index in range(60)
    ]
    payload = {
        **analysis,
        "skills_found": many,
        "skills_by_category": {"Programming Languages": many},
    }
    pdf = build_report(payload)
    reader = PdfReader(BytesIO(pdf))
    assert len(reader.pages) >= 2
    assert "WEEK 4" in _text_of(pdf)


def _text_of(pdf: bytes) -> str:
    """Take PDF bytes, return all of its text."""
    reader = PdfReader(BytesIO(pdf))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def test_roadmap_bullets_use_the_zapfdingbats_filled_circle(pdf_bytes: bytes) -> None:
    """Regression test for a silent rendering bug.

    U+2022 BULLET encodes to byte 0x7F in Helvetica, which is undefined in
    WinAnsiEncoding - the bullet simply does not appear, and no error is raised.
    The fix draws it from ZapfDingbats, where reportlab maps U+25CF onto glyph
    "l", the filled circle. This test asserts the bytes that actually reach the
    page, because nothing else catches it.
    """
    reader = PdfReader(BytesIO(pdf_bytes))

    fonts = set()
    bullet_drawn = False
    for page in reader.pages:
        resources = page.get("/Resources", {}).get("/Font", {})
        for ref in resources.values():
            fonts.add(str(ref.get_object().get("/BaseFont")))

        stream = page.get_contents().get_data().decode("latin-1")
        # "(l) Tj" preceded by a ZapfDingbats font selection is the filled circle.
        for line in stream.splitlines():
            if "ZapfDingbats" in line or ("(l) Tj" in line and "Tf" in line):
                bullet_drawn = True

    assert "/ZapfDingbats" in fonts, f"bullet font missing, got {fonts}"
    assert bullet_drawn, "no filled-circle bullet glyph was drawn"


def test_no_undefined_glyph_bytes_are_emitted(pdf_bytes: bytes) -> None:
    """Byte 0x7F is undefined in WinAnsiEncoding and renders as nothing."""
    reader = PdfReader(BytesIO(pdf_bytes))
    for index, page in enumerate(reader.pages):
        stream = page.get_contents().get_data().decode("latin-1")
        assert "\177" not in stream, f"undefined glyph on page {index + 1}"
