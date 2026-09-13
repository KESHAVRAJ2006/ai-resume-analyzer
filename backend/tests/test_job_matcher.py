"""Tests for role loading, weighted coverage, the TF-IDF tier and the blend."""

import pytest

from app.services.job_matcher import (
    WEIGHT_BY_TIER,
    WEIGHT_SEMANTIC,
    WEIGHT_SKILL_COVERAGE,
    WEIGHT_TFIDF,
    get_role,
    load_job_roles,
    rank_roles,
    score_role,
    tfidf_scores,
    weighted_skill_coverage,
)

BACKEND_RESUME = (
    "Backend engineer. Built REST APIs in Python with FastAPI and PostgreSQL. "
    "Containerised services with Docker, cached with Redis, wrote unit tests "
    "and shipped through Git."
)
BACKEND_SKILLS = {
    "python", "sql", "rest_api", "git", "postgresql",
    "fastapi", "docker", "redis", "unit_testing",
}


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------

def test_loads_eight_roles() -> None:
    """All 8 roles come out of the CSV."""
    assert len(load_job_roles()) == 8


def test_tiers_become_weights() -> None:
    """must/good/nice map to 3/2/1 on every skill of a role."""
    role = get_role("backend_developer")
    assert role.weights["python"] == 3      # must_have
    assert role.weights["fastapi"] == 2     # good_to_have
    assert role.weights["graphql"] == 1     # nice_to_have


def test_total_weight_matches_the_tier_lists() -> None:
    """total_weight is the sum of every skill's importance, i.e. the denominator."""
    role = get_role("frontend_developer")
    expected = sum(
        WEIGHT_BY_TIER[tier] * len(skill_ids) for tier, skill_ids in role.tiers.items()
    )
    assert role.total_weight == expected


def test_unknown_role_raises_with_a_helpful_message() -> None:
    """A bad role id fails loudly and lists the valid ones."""
    with pytest.raises(KeyError, match="backend_developer"):
        get_role("wizard")


# --------------------------------------------------------------------------
# Weighted skill coverage - the 0.45 term
# --------------------------------------------------------------------------

def test_coverage_is_one_when_every_skill_is_present() -> None:
    """A resume with all listed skills scores full coverage."""
    role = get_role("data_analyst")
    assert weighted_skill_coverage(set(role.weights), role) == 1.0


def test_coverage_is_zero_when_no_skill_is_present() -> None:
    """An unrelated resume scores zero coverage, not a small positive number."""
    role = get_role("data_analyst")
    assert weighted_skill_coverage({"figma", "bootstrap"}, role) == 0.0


def test_must_have_is_worth_three_times_a_nice_to_have() -> None:
    """The weighting must actually bite: one must-have beats one nice-to-have."""
    role = get_role("backend_developer")
    must_only = weighted_skill_coverage({"python"}, role)      # weight 3
    nice_only = weighted_skill_coverage({"graphql"}, role)     # weight 1
    assert must_only == pytest.approx(nice_only * 3)


def test_coverage_is_the_earned_fraction_of_total_weight() -> None:
    """Coverage is arithmetic we can check by hand, not a black box."""
    role = get_role("backend_developer")
    found = {"python", "sql"}  # two must-haves, 3 + 3 = 6
    assert weighted_skill_coverage(found, role) == pytest.approx(6 / role.total_weight)


# --------------------------------------------------------------------------
# TF-IDF tier - the 0.20 term
# --------------------------------------------------------------------------

def test_tfidf_scores_every_role() -> None:
    """One pass returns a similarity for all 8 roles."""
    scores = tfidf_scores(BACKEND_RESUME)
    assert set(scores) == set(load_job_roles())
    assert all(0.0 <= value <= 1.0 for value in scores.values())


def test_tfidf_prefers_the_matching_role() -> None:
    """A backend resume is textually closer to backend than to data analyst."""
    scores = tfidf_scores(BACKEND_RESUME)
    assert scores["backend_developer"] > scores["data_analyst"]


def test_tfidf_survives_punctuated_skills() -> None:
    """The custom analyzer keeps c++/ci-cd style tokens sklearn would discard."""
    scores = tfidf_scores("DevOps engineer running CI/CD on Linux with Docker and Bash")
    assert scores["devops_engineer"] > 0


def test_tfidf_of_empty_resume_is_zero() -> None:
    """No text means no similarity, and no crash from an empty vocabulary."""
    assert set(tfidf_scores("").values()) == {0.0}


# --------------------------------------------------------------------------
# The blended score
# --------------------------------------------------------------------------

def test_weights_sum_to_one() -> None:
    """The formula only makes sense if the three weights are a partition."""
    assert WEIGHT_SKILL_COVERAGE + WEIGHT_SEMANTIC + WEIGHT_TFIDF == pytest.approx(1.0)


def test_score_without_semantic_renormalises_to_0_100() -> None:
    """A perfect resume still scores 100 when the semantic tier is absent."""
    role = get_role("backend_developer")
    result = score_role(role, set(role.weights), tfidf_score=1.0, semantic_score=None)
    assert result.final_score == 100.0
    assert result.semantic_score is None


def test_score_with_semantic_uses_all_three_weights() -> None:
    """With the semantic tier present, the score is the spec's exact formula."""
    role = get_role("backend_developer")
    result = score_role(role, set(role.weights), tfidf_score=0.5, semantic_score=0.5)
    expected = 100 * (
        WEIGHT_SKILL_COVERAGE * 1.0 + WEIGHT_SEMANTIC * 0.5 + WEIGHT_TFIDF * 0.5
    )
    assert result.final_score == pytest.approx(round(expected, 1))


def test_score_of_nothing_is_zero() -> None:
    """An empty resume scores 0, not a floor value."""
    role = get_role("ml_engineer")
    assert score_role(role, set(), tfidf_score=0.0).final_score == 0.0


def test_matched_and_missing_partition_the_role() -> None:
    """Every skill of the role is either matched or missing, never both."""
    role = get_role("devops_engineer")
    result = score_role(role, {"docker", "linux"}, tfidf_score=0.3)
    assert set(result.matched_skill_ids) == {"docker", "linux"}
    assert set(result.matched_skill_ids) | set(result.missing_skill_ids) == set(role.weights)
    assert not set(result.matched_skill_ids) & set(result.missing_skill_ids)


# --------------------------------------------------------------------------
# Ranking
# --------------------------------------------------------------------------

def test_ranking_puts_the_right_role_first() -> None:
    """End to end, a backend resume ranks Backend Developer top."""
    ranked = rank_roles(BACKEND_RESUME, BACKEND_SKILLS)
    assert ranked[0].role_id == "backend_developer"


def test_ranking_returns_every_role_sorted_descending() -> None:
    """All 8 roles are returned, best first."""
    ranked = rank_roles(BACKEND_RESUME, BACKEND_SKILLS)
    assert len(ranked) == 8
    scores = [role.final_score for role in ranked]
    assert scores == sorted(scores, reverse=True)


def test_ranking_is_deterministic() -> None:
    """Two identical inputs produce byte-identical output, so results are stable."""
    assert rank_roles(BACKEND_RESUME, BACKEND_SKILLS) == rank_roles(
        BACKEND_RESUME, BACKEND_SKILLS
    )


def test_a_frontend_resume_ranks_frontend_first() -> None:
    """The matcher is not just biased toward one role."""
    resume = (
        "Frontend developer building accessible interfaces in React and TypeScript, "
        "styled with TailwindCSS, state in Redux, deployed from Git."
    )
    skills = {"javascript", "react", "html", "css", "git", "typescript", "tailwind", "redux"}
    assert rank_roles(resume, skills)[0].role_id == "frontend_developer"
