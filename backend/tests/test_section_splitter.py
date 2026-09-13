"""Tests for heading detection and section boundaries."""

from pathlib import Path

from app.services.resume_parser import parse_resume
from app.services.section_splitter import get_section, split_sections


def test_splits_standard_headings(sample_lines: list[str]) -> None:
    """Every heading in the fixture resume becomes its own section."""
    sections = split_sections("\n".join(sample_lines))
    for expected in ("summary", "skills", "experience", "projects",
                     "education", "certifications"):
        assert expected in sections, f"missing {expected}"


def test_heading_aliases_map_to_canonical_names(sample_lines: list[str]) -> None:
    """'WORK EXPERIENCE' and 'TECHNICAL SKILLS' normalise to experience/skills."""
    sections = split_sections("\n".join(sample_lines))
    assert "Backend Intern" in sections["experience"]
    assert "C++" in sections["skills"]


def test_content_stays_in_its_own_section(sample_lines: list[str]) -> None:
    """Skills text must not bleed into the experience section, or vice versa."""
    sections = split_sections("\n".join(sample_lines))
    assert "Backend Intern" not in sections["skills"]
    assert "Languages: Python" not in sections["experience"]


def test_text_above_first_heading_goes_to_header() -> None:
    """The contact block lands in 'header' rather than contaminating a real section."""
    sections = split_sections("Priya Sharma\nBangalore\n\nSKILLS\nPython\n")
    assert "Priya Sharma" in sections["header"]
    assert "Priya Sharma" not in sections.get("skills", "")


def test_inline_heading_is_detected() -> None:
    """'Skills: Python, Java' is a heading plus content on one line."""
    sections = split_sections("Skills: Python, Java\nEDUCATION\nB.Tech")
    assert sections["skills"] == "Python, Java"


def test_resume_without_headings_falls_back_to_header() -> None:
    """Free-form resumes still return usable text instead of an empty dict."""
    sections = split_sections("I write Python and deploy with Docker every day.")
    assert sections["header"].startswith("I write Python")
    assert "skills" not in sections


def test_long_line_is_not_treated_as_a_heading() -> None:
    """A long bullet containing the word 'projects' must not start a section."""
    text = "\n".join([
        "EXPERIENCE",
        "Delivered several data projects for enterprise clients across three "
        "continents during the internship.",
    ])
    sections = split_sections(text)
    assert "projects" not in sections
    assert "enterprise clients" in sections["experience"]


def test_empty_input_returns_empty_dict() -> None:
    """No text means no sections, not a crash."""
    assert split_sections("") == {}


def test_get_section_returns_fallback() -> None:
    """get_section hands back the fallback when the key is absent."""
    assert get_section({"skills": "python"}, "projects", "none") == "none"


def test_works_on_a_real_parsed_pdf(sample_pdf: Path) -> None:
    """The parser -> splitter handoff works on an actual PDF, not just strings."""
    sections = split_sections(parse_resume(sample_pdf))
    assert "skills" in sections
    assert "C++" in sections["skills"]
