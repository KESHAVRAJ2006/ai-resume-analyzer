"""Tests for alias handling, word boundaries and overlap resolution."""

import pytest

from app.services.skill_extractor import (
    extract_skills,
    extract_skills_from_text,
    group_by_category,
    load_skill_dictionary,
)


def _ids(text: str) -> set[str]:
    """Take raw text, return the set of skill_ids extracted from it."""
    return {skill.skill_id for skill in extract_skills_from_text(text)}


# --------------------------------------------------------------------------
# Aliases - the five the spec names, plus the shapes they represent
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "written, expected_id",
    [
        ("sklearn", "scikit_learn"),
        ("scikit-learn", "scikit_learn"),
        ("scikit learn", "scikit_learn"),
        ("js", "javascript"),
        ("JavaScript", "javascript"),
        ("ml", "machine_learning"),
        ("Machine Learning", "machine_learning"),
        ("tf", "tensorflow"),
        ("TensorFlow", "tensorflow"),
        ("nlp", "nlp"),
        ("Natural Language Processing", "nlp"),
        ("k8s", "kubernetes"),
        ("postgres", "postgresql"),
        ("golang", "go_lang"),
    ],
)
def test_aliases_resolve_to_canonical_skill(written: str, expected_id: str) -> None:
    """Every alias spelling resolves to the same canonical skill id."""
    assert expected_id in _ids(f"Experienced with {written} in production.")


def test_alias_reports_canonical_name_not_the_alias() -> None:
    """The UI shows 'scikit-learn' even when the resume said 'sklearn'."""
    found = extract_skills_from_text("Built models with sklearn")
    skill = next(s for s in found if s.skill_id == "scikit_learn")
    assert skill.canonical_name == "scikit-learn"
    assert skill.matched_text == "sklearn"  # but we remember what was written


# --------------------------------------------------------------------------
# Word boundaries - the cases the spec calls out by name
# --------------------------------------------------------------------------

def test_r_does_not_match_inside_react() -> None:
    """The single-letter skill R must not fire on 'React'."""
    assert "r_lang" not in _ids("Built dashboards in React and Redux")


def test_r_matches_when_standalone() -> None:
    """R is still detected when it genuinely stands alone."""
    assert "r_lang" in _ids("Statistical work in R and Python")


def test_go_does_not_match_inside_google() -> None:
    """The skill Go must not fire on 'Google'."""
    assert "go_lang" not in _ids("Interned at Google Cloud last summer")


def test_go_matches_when_standalone() -> None:
    """Go is still detected when written on its own."""
    assert "go_lang" in _ids("Wrote microservices in Go")


def test_c_does_not_match_inside_cpp() -> None:
    """'C++' must register as C++ only, never as a stray C."""
    found = _ids("Strong in C++ and Java")
    assert "cpp" in found
    assert "c_lang" not in found


def test_c_and_cpp_both_detected_when_both_listed() -> None:
    """'C, C++' lists two distinct skills and both are picked up."""
    found = _ids("Languages: C, C++, Python")
    assert {"c_lang", "cpp", "python"} <= found


@pytest.mark.parametrize(
    "written, expected_id",
    [
        ("C++", "cpp"),
        ("C#", "csharp"),
        (".NET", "dotnet"),
        ("ASP.NET Core", "dotnet"),
        ("Node.js", "nodejs"),
        ("CI/CD", "cicd"),
        ("Next.js", "nextjs"),
    ],
)
def test_punctuated_skills_survive_cleaning(written: str, expected_id: str) -> None:
    """The tokens text_cleaner protects are the ones the extractor must find."""
    assert expected_id in _ids(f"Worked with {written} daily")


# --------------------------------------------------------------------------
# Overlap resolution - longest match wins
# --------------------------------------------------------------------------

def test_tfidf_is_not_read_as_tensorflow() -> None:
    """'TF-IDF' contains 'tf', but the longer TF-IDF match must claim the span."""
    found = _ids("Built a search ranker with TF-IDF and cosine similarity")
    assert "tfidf" in found
    assert "tensorflow" not in found


def test_node_js_is_not_also_counted_as_javascript() -> None:
    """'Node JS' is one skill, not Node plus JavaScript."""
    found = _ids("Backend in Node JS")
    assert "nodejs" in found
    assert "javascript" not in found


def test_longer_phrase_beats_its_prefix() -> None:
    """'Deep Learning' wins over a bare 'learning'-style partial match."""
    found = _ids("Deep Learning research on transformers")
    assert "deep_learning" in found


def test_machine_learning_phrase_matches_across_extra_spaces() -> None:
    """PDF extraction often doubles spaces; the phrase must still match."""
    assert "machine_learning" in _ids("Applied  machine   learning to churn data")


# --------------------------------------------------------------------------
# Section awareness and aggregation
# --------------------------------------------------------------------------

def test_records_every_section_a_skill_appears_in() -> None:
    """found_in lists each section, which Phase 4 uses to weight evidence."""
    sections = {
        "skills": "Python, Docker",
        "projects": "Dockerised the training pipeline in Python",
    }
    found = {skill.skill_id: skill for skill in extract_skills(sections)}
    assert set(found["python"].found_in) == {"skills", "projects"}
    assert found["python"].occurrences == 2


def test_education_section_is_ignored() -> None:
    """A course title is not a claimed skill, so education is not searched."""
    sections = {"education": "B.Tech with coursework in Machine Learning and Java"}
    assert extract_skills(sections) == []


def test_results_are_sorted_by_evidence() -> None:
    """The most-mentioned skill comes first so the UI can show it first."""
    sections = {
        "skills": "Python, SQL",
        "experience": "Python services",
        "projects": "Python data tooling",
    }
    found = extract_skills(sections)
    assert found[0].skill_id == "python"


def test_empty_sections_return_no_skills() -> None:
    """No text means an empty list, not a crash."""
    assert extract_skills({}) == []
    assert extract_skills({"skills": ""}) == []


def test_group_by_category_buckets_skills() -> None:
    """Grouping feeds the categorised chips on the results screen."""
    grouped = group_by_category(extract_skills_from_text("Python, React, Docker"))
    assert "Programming Languages" in grouped
    assert "Web & Frontend" in grouped
    assert "Cloud & DevOps" in grouped


# --------------------------------------------------------------------------
# Data integrity - the CSV is code too
# --------------------------------------------------------------------------

def test_dictionary_has_at_least_sixty_skills() -> None:
    """The spec requires 60+; fewer means poor coverage of real resumes."""
    assert len(load_skill_dictionary()) >= 60


def test_skill_ids_are_unique_and_populated() -> None:
    """Every row has an id, a display name and a category."""
    dictionary = load_skill_dictionary()
    for skill_id, skill in dictionary.items():
        assert skill_id == skill.skill_id
        assert skill.canonical_name
        assert skill.category
        assert skill.surfaces  # at least the canonical name survived cleaning


def test_no_surface_is_claimed_by_two_skills() -> None:
    """A spelling that maps to two skills would make matching non-deterministic."""
    owner: dict[str, str] = {}
    duplicates: list[str] = []
    for skill in load_skill_dictionary().values():
        for surface in skill.surfaces:
            if surface in owner and owner[surface] != skill.skill_id:
                duplicates.append(f"{surface!r}: {owner[surface]} vs {skill.skill_id}")
            owner[surface] = skill.skill_id
    assert not duplicates, duplicates
