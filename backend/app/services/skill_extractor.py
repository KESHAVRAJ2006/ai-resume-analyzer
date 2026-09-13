"""Find known skills in resume text.

Owns data/skill_dictionary.csv. Two problems dominate this module:

1. ALIASES. A resume says "sklearn", the job description says "scikit-learn".
   Every skill therefore carries a list of alternative spellings, and all of
   them are normalised through text_cleaner so the dictionary and the resume
   are compared in exactly the same form.

2. BOUNDARIES. Naive substring search finds "R" inside "React", "Go" inside
   "Google" and "C" inside "C++". We use explicit lookarounds instead of \\b,
   because \\b does not work for tokens that end in punctuation such as "c++",
   and we then resolve overlaps by preferring the longest match.

PRIVACY: only skills are extracted. Nothing here reads or returns name, gender,
age, photo, religion, nationality, marital status or disability.
"""

import csv
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.services.text_cleaner import clean_text

DEFAULT_DICTIONARY_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "skill_dictionary.csv"
)

# Characters that may legally appear inside a cleaned skill token. A match is
# only accepted when it is not glued to one of these on either side, which is
# what keeps "r" out of "react" and "c" out of "c++".
_TOKEN_CHARS = r"a-z0-9+#./"
_BOUNDARY_LEFT = rf"(?<![{_TOKEN_CHARS}])"
_BOUNDARY_RIGHT = rf"(?![{_TOKEN_CHARS}])"

# Sections whose text counts as evidence of a skill. "header" is included
# because compact resumes list a tech stack under the name; identity details
# were already redacted by text_cleaner before this module ever sees them.
DEFAULT_SEARCH_SECTIONS: tuple[str, ...] = (
    "header", "summary", "skills", "experience", "projects", "certifications",
)


@dataclass(frozen=True)
class Skill:
    """One row of skill_dictionary.csv, with its cleaned searchable surfaces."""

    skill_id: str
    canonical_name: str
    category: str
    surfaces: tuple[str, ...]  # cleaned canonical name + cleaned aliases


@dataclass(frozen=True)
class ExtractedSkill:
    """A skill found in a resume, with where and how often it appeared."""

    skill_id: str
    canonical_name: str
    category: str
    matched_text: str          # the spelling actually used, e.g. "sklearn"
    occurrences: int
    found_in: tuple[str, ...]  # section names, e.g. ("skills", "projects")


@lru_cache(maxsize=4)
def load_skill_dictionary(path: str | None = None) -> dict[str, Skill]:
    """Take an optional CSV path, return {skill_id: Skill}. Cached per path.

    Cached because the file never changes at runtime and every request would
    otherwise re-read and re-normalise ~93 rows.
    """
    csv_path = Path(path) if path else DEFAULT_DICTIONARY_PATH
    if not csv_path.exists():
        raise FileNotFoundError(f"Skill dictionary not found at {csv_path}")

    skills: dict[str, Skill] = {}
    with csv_path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            skill_id = row["skill_id"].strip()
            if not skill_id:
                continue

            raw_aliases = [a.strip() for a in (row["aliases"] or "").split("|")]
            raw_surfaces = [row["canonical_name"].strip(), *raw_aliases]

            # Normalising through clean_text is what makes "scikit-learn" in the
            # CSV comparable to "scikit learn" in a resume: both become the same
            # string, because both went through the same pipeline.
            cleaned = {clean_text(surface) for surface in raw_surfaces if surface}
            cleaned.discard("")

            skills[skill_id] = Skill(
                skill_id=skill_id,
                canonical_name=row["canonical_name"].strip(),
                category=row["category"].strip(),
                surfaces=tuple(sorted(cleaned, key=len, reverse=True)),
            )
    return skills


@lru_cache(maxsize=4)
def _compiled_patterns(path: str | None = None) -> tuple[tuple[str, re.Pattern[str]], ...]:
    """Take an optional CSV path, return one compiled regex per skill."""
    patterns: list[tuple[str, re.Pattern[str]]] = []
    for skill in load_skill_dictionary(path).values():
        # Longest surface first so "node js" is preferred over "node" within
        # the same skill; cross-skill conflicts are settled in _find_matches.
        alternatives = "|".join(_surface_regex(s) for s in skill.surfaces)
        patterns.append(
            (skill.skill_id, re.compile(f"{_BOUNDARY_LEFT}(?:{alternatives}){_BOUNDARY_RIGHT}"))
        )
    return tuple(patterns)


def _surface_regex(surface: str) -> str:
    """Take a cleaned surface form, return a regex matching it.

    Words are joined with \\s+ so "machine learning" still matches when a PDF
    left two spaces between the words.
    """
    return r"\s+".join(re.escape(word) for word in surface.split())


def extract_skills(
    sections: dict[str, str],
    *,
    dictionary_path: str | None = None,
    search_sections: tuple[str, ...] = DEFAULT_SEARCH_SECTIONS,
) -> list[ExtractedSkill]:
    """Take {section: raw text}, return the skills found, most-mentioned first.

    Sections outside search_sections (education, achievements) are ignored, so
    a university course title does not become a claimed skill.
    """
    if not sections:
        return []

    # skill_id -> accumulated evidence across sections
    totals: dict[str, int] = {}
    first_spelling: dict[str, str] = {}
    sections_seen: dict[str, list[str]] = {}

    for section_name in search_sections:
        text = sections.get(section_name)
        if not text:
            continue

        for skill_id, matched_text in _find_matches(clean_text(text), dictionary_path):
            totals[skill_id] = totals.get(skill_id, 0) + 1
            first_spelling.setdefault(skill_id, matched_text)
            seen = sections_seen.setdefault(skill_id, [])
            if section_name not in seen:
                seen.append(section_name)

    dictionary = load_skill_dictionary(dictionary_path)
    extracted = [
        ExtractedSkill(
            skill_id=skill_id,
            canonical_name=dictionary[skill_id].canonical_name,
            category=dictionary[skill_id].category,
            matched_text=first_spelling[skill_id],
            occurrences=count,
            found_in=tuple(sections_seen[skill_id]),
        )
        for skill_id, count in totals.items()
    ]

    # Most-mentioned first, then alphabetical so the order is stable between runs.
    extracted.sort(key=lambda skill: (-skill.occurrences, skill.canonical_name.lower()))
    return extracted


def extract_skills_from_text(
    text: str, *, dictionary_path: str | None = None
) -> list[ExtractedSkill]:
    """Take one block of raw text, return the skills found in it.

    Convenience wrapper for resumes with no detectable section headings.
    """
    return extract_skills(
        {"header": text},
        dictionary_path=dictionary_path,
        search_sections=("header",),
    )


def group_by_category(skills: list[ExtractedSkill]) -> dict[str, list[ExtractedSkill]]:
    """Take extracted skills, return them grouped by category for the UI chips."""
    grouped: dict[str, list[ExtractedSkill]] = {}
    for skill in skills:
        grouped.setdefault(skill.category, []).append(skill)
    return grouped


def _find_matches(
    cleaned_text: str, dictionary_path: str | None = None
) -> list[tuple[str, str]]:
    """Take cleaned text, return [(skill_id, matched spelling)] with overlaps resolved.

    Longest match wins. This is what stops "tf idf" being read as TensorFlow
    ("tf") and "node js" as JavaScript ("js") - the longer, more specific skill
    claims the span and the shorter one is discarded.
    """
    if not cleaned_text:
        return []

    candidates: list[tuple[int, int, str, str]] = []
    for skill_id, pattern in _compiled_patterns(dictionary_path):
        for match in pattern.finditer(cleaned_text):
            candidates.append((match.start(), match.end(), skill_id, match.group()))

    # Longest span first; ties broken by position so the result is deterministic.
    candidates.sort(key=lambda item: (item[0] - item[1], item[0]))

    accepted: list[tuple[str, str]] = []
    claimed: list[tuple[int, int]] = []
    for start, end, skill_id, matched_text in candidates:
        if any(start < taken_end and taken_start < end for taken_start, taken_end in claimed):
            continue
        claimed.append((start, end))
        accepted.append((skill_id, matched_text))

    return accepted
