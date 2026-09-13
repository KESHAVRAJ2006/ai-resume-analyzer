"""Tests for normalisation, with the punctuation-preservation rules front and centre."""

import pytest

from app.services.text_cleaner import clean_text, redact_contact_info


@pytest.mark.parametrize(
    "raw, expected_token",
    [
        ("Proficient in C++ and Java.", "c++"),
        ("Worked with C# on desktop apps.", "c#"),
        ("Built services in ASP.NET Core.", "asp.net"),
        ("Backend written in Node.js.", "node.js"),
        ("Owned the CI/CD pipeline.", "ci/cd"),
        ("Frontend in Vue.js and React.", "vue.js"),
        ("Migrated a legacy .NET app.", ".net"),
    ],
)
def test_preserves_punctuated_skills(raw: str, expected_token: str) -> None:
    """The five required tokens (and their family) survive punctuation stripping."""
    assert expected_token in clean_text(raw)


def test_ci_cd_with_spaces_normalises() -> None:
    """'CI / CD' and 'CI/CD' both come out as the single token 'ci/cd'."""
    assert "ci/cd" in clean_text("Managed CI / CD workflows")


def test_cpp_not_reduced_to_c() -> None:
    """C++ must not collapse into a bare 'c', which would match everything."""
    cleaned = clean_text("C++")
    assert cleaned == "c++"


def test_ordinary_punctuation_is_stripped() -> None:
    """Commas, brackets and slashes that carry no meaning become spaces."""
    assert clean_text("Python, Java; (SQL) - Docker!") == "python java sql docker"


def test_lowercases_and_collapses_whitespace() -> None:
    """Output is lowercase, single-spaced and trimmed."""
    assert clean_text("  PYTHON \t\n   Docker  ") == "python docker"


def test_rejoins_hyphenated_line_break() -> None:
    """A word split across lines by a PDF exporter is rejoined."""
    assert "experience" in clean_text("Five years of experi-\nence in backend")


def test_normalises_smart_quotes_and_bullets() -> None:
    """Typographic characters from Word do not leak into the output."""
    cleaned = clean_text("• Python – Django “expert”")
    assert cleaned == "python django expert"


def test_redacts_email_and_phone_and_profile() -> None:
    """Contact details are removed before anything analyses the text."""
    raw = "priya.sharma@example.com | +91 98765 43210 | linkedin.com/in/priyasharma"
    cleaned = clean_text(raw)
    assert "example.com" not in cleaned
    assert "98765" not in cleaned
    assert "priyasharma" not in cleaned


def test_date_range_is_not_mistaken_for_a_phone_number() -> None:
    """'2022 - 2026' has only 8 digits, so redaction must leave it alone."""
    assert "2022" in clean_text("B.Tech Computer Science, 2022 - 2026")


def test_redact_keeps_surrounding_words() -> None:
    """Redaction replaces only the contact token, not the whole line."""
    result = redact_contact_info("Email me at a@b.com for details")
    assert "Email me at" in result and "details" in result and "a@b.com" not in result


@pytest.mark.parametrize("raw", ["", "   ", "\n\n"])
def test_empty_input_returns_empty_string(raw: str) -> None:
    """Blank input is not an error; it is simply empty output."""
    assert clean_text(raw) == ""
