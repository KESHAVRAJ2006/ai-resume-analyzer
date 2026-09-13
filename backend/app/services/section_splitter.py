"""Split raw resume text into named sections.

Why bother: a skill listed under "Skills" is a claim about ability, while the
same word under "Interests" is noise. Later phases weight sections differently,
so we separate them here.

This module works on text that still has line breaks, so it must run BEFORE
text_cleaner.clean_text().
"""

import re

from app.services.text_cleaner import clean_preserving_lines

# Canonical section name -> the headings resumes actually use for it.
SECTION_ALIASES: dict[str, tuple[str, ...]] = {
    "summary": (
        "summary", "professional summary", "career summary", "objective",
        "career objective", "profile", "about", "about me", "overview",
    ),
    "skills": (
        "skills", "technical skills", "key skills", "core skills",
        "core competencies", "competencies", "technologies", "tech stack",
        "technical proficiencies", "skills and tools", "tools and technologies",
        "areas of expertise", "expertise",
    ),
    "experience": (
        "experience", "work experience", "professional experience",
        "employment", "employment history", "work history", "career history",
        "internship", "internships", "internship experience",
    ),
    "projects": (
        "projects", "academic projects", "personal projects", "key projects",
        "selected projects", "project work", "project experience",
    ),
    "education": (
        "education", "academic background", "academic qualifications",
        "qualifications", "academics", "educational qualifications",
    ),
    "certifications": (
        "certifications", "certification", "certificates", "courses",
        "courses and certifications", "licenses and certifications", "training",
    ),
    "achievements": (
        "achievements", "awards", "honors", "honours", "accomplishments",
        "awards and achievements", "extracurricular", "activities",
    ),
    "publications": ("publications", "research", "papers", "research experience"),
    # Deliberately NO "languages" section: on a technical resume "Languages:"
    # nearly always introduces programming languages, which belong to skills.
    # Spoken languages are not scored, so nothing is lost by leaving it out.
}

# Everything above the first real heading: usually the contact block. We keep it
# because some templates list skills there, but nothing ever reads identity
# fields from it - emails and phone numbers are already redacted downstream.
HEADER_KEY = "header"

# Flat lookup built once at import: "work experience" -> "experience".
_ALIAS_TO_SECTION: dict[str, str] = {
    alias: canonical
    for canonical, aliases in SECTION_ALIASES.items()
    for alias in aliases
}

# A heading is a short line. 45 characters is above the longest real heading
# ("courses and certifications" = 26) and below a typical bullet point.
_MAX_HEADING_CHARS = 45

# Leading bullets/numbers to shave off before comparing against the alias table.
_LEADING_NOISE_RE = re.compile(r"^[\s\-*+.:#>\u2022\d)]+")
# Trailing colons, dashes and underlines used as heading decoration.
_TRAILING_NOISE_RE = re.compile(r"[\s:\-_=.]+$")
# "Skills: Python, Java" - heading and content share one line.
_INLINE_HEADING_RE = re.compile(r"^([A-Za-z][A-Za-z &/]{1,40}?)\s*[:\-]\s*(.+)$")


def split_sections(raw_text: str) -> dict[str, str]:
    """Take raw resume text, return {section_name: section_text}.

    Keys are the canonical names in SECTION_ALIASES plus "header". Only
    sections actually present are returned, so callers should fall back to the
    full text when the key they want is missing.
    """
    if not raw_text or not raw_text.strip():
        return {}

    lines = clean_preserving_lines(raw_text).split("\n")

    sections: dict[str, list[str]] = {}
    current = HEADER_KEY
    # True on the line straight after a standalone heading. Resumes very often
    # write "TECHNICAL SKILLS" and then "Certifications: AWS, Azure" as its first
    # line; without this guard that sub-label would hijack the section and leave
    # the real one empty.
    just_opened_section = False

    for line in lines:
        if not line:
            continue

        heading, inline_content = _match_heading(line)
        is_sub_label = bool(inline_content) and just_opened_section

        if heading is not None and not is_sub_label:
            current = heading
            sections.setdefault(current, [])
            # "Skills: Python, Java" - keep the part after the colon as content.
            if inline_content:
                sections[current].append(inline_content)
            just_opened_section = not inline_content
            continue

        sections.setdefault(current, []).append(line)
        just_opened_section = False

    # Join and drop sections that turned out to hold nothing but their heading.
    return {
        name: "\n".join(body).strip()
        for name, body in sections.items()
        if "\n".join(body).strip()
    }


def get_section(sections: dict[str, str], name: str, fallback: str = "") -> str:
    """Take the section dict and a name, return that section's text or a fallback."""
    return sections.get(name) or fallback


def _match_heading(line: str) -> tuple[str | None, str]:
    """Take one line, return (canonical section name or None, inline content).

    Inline content is non-empty only for lines like "Skills: Python, Java".
    """
    stripped = line.strip()
    if not stripped or len(stripped) > _MAX_HEADING_CHARS * 3:
        return None, ""

    # Case 1: the whole line is a heading, e.g. "TECHNICAL SKILLS" or "Skills:".
    if len(stripped) <= _MAX_HEADING_CHARS:
        canonical = _ALIAS_TO_SECTION.get(_normalise_heading(stripped))
        if canonical:
            return canonical, ""

    # Case 2: heading and content on one line, e.g. "Skills: Python, Java".
    inline = _INLINE_HEADING_RE.match(stripped)
    if inline:
        canonical = _ALIAS_TO_SECTION.get(_normalise_heading(inline.group(1)))
        if canonical:
            return canonical, inline.group(2).strip()

    return None, ""


def _normalise_heading(text: str) -> str:
    """Take a candidate heading, return the lowercase form used as an alias key."""
    text = _LEADING_NOISE_RE.sub("", text)
    text = _TRAILING_NOISE_RE.sub("", text)
    text = text.lower()
    text = text.replace("&", " and ")
    # Drop anything that is not a letter or space so "S K I L L S" style
    # decoration and stray punctuation do not block a match.
    text = re.sub(r"[^a-z ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()
