"""Tests for the gap analyzer and the 4-week roadmap generator."""

import pytest

from app.services.gap_analyzer import analyze_gaps, summarise_gaps
from app.services.job_matcher import get_role
from app.services.roadmap_generator import (
    MAX_SKILLS_PER_WEEK,
    WEEKS,
    generate_roadmap,
)
from app.services.skill_extractor import ExtractedSkill, load_skill_dictionary


def _skills(*skill_ids: str) -> list[ExtractedSkill]:
    """Build ExtractedSkill objects for the given ids, as the extractor would."""
    dictionary = load_skill_dictionary()
    return [
        ExtractedSkill(
            skill_id=skill_id,
            canonical_name=dictionary[skill_id].canonical_name,
            category=dictionary[skill_id].category,
            matched_text=dictionary[skill_id].canonical_name.lower(),
            occurrences=1,
            found_in=("skills",),
        )
        for skill_id in skill_ids
    ]


# --------------------------------------------------------------------------
# Gap analysis
# --------------------------------------------------------------------------

def test_matched_and_missing_cover_the_whole_role() -> None:
    """Every skill of the role appears exactly once, on one side or the other."""
    role = get_role("backend_developer")
    report = analyze_gaps(_skills("python", "sql", "docker"), role)
    seen = {s.skill_id for s in report.matched} | {g.skill_id for g in report.missing}
    assert seen == set(role.weights)
    assert len(report.matched) + len(report.missing) == len(role.weights)


def test_severity_follows_the_tier() -> None:
    """must_have -> critical, good_to_have -> important, nice_to_have -> optional."""
    role = get_role("backend_developer")
    report = analyze_gaps([], role)
    by_id = {gap.skill_id: gap for gap in report.missing}
    assert by_id["python"].severity == "critical"
    assert by_id["fastapi"].severity == "important"
    assert by_id["graphql"].severity == "optional"


def test_missing_skills_are_sorted_critical_first() -> None:
    """The UI renders the list as given, so ordering is the module's job."""
    report = analyze_gaps([], get_role("data_scientist"))
    severities = [gap.severity for gap in report.missing]
    assert severities == sorted(severities, key=["critical", "important", "optional"].index)


def test_critical_gaps_property_returns_only_must_haves() -> None:
    """critical_gaps is the shortlist the roadmap starts from."""
    role = get_role("ml_engineer")
    report = analyze_gaps(_skills("python", "numpy"), role)
    assert {gap.skill_id for gap in report.critical_gaps} == set(role.tiers["must_have"]) - {
        "python",
        "numpy",
    }


def test_earned_weight_matches_the_matched_skills() -> None:
    """earned_weight is the numerator of coverage and must agree with it."""
    role = get_role("data_analyst")
    report = analyze_gaps(_skills("sql", "excel"), role)
    assert report.earned_weight == 3 + 3
    assert report.total_weight == role.total_weight


def test_tier_summary_counts_have_and_total() -> None:
    """The gap table shows 'x of y' per tier."""
    role = get_role("frontend_developer")
    report = analyze_gaps(_skills("javascript", "react"), role)
    assert report.tier_summary["must_have"] == {
        "have": 2,
        "total": len(role.tiers["must_have"]),
    }


def test_found_in_is_carried_through() -> None:
    """Where a skill was found survives into the report, for the UI tooltip."""
    role = get_role("backend_developer")
    report = analyze_gaps(_skills("python"), role)
    assert next(s for s in report.matched if s.skill_id == "python").found_in == ("skills",)


def test_summary_line_flags_critical_gaps() -> None:
    """The headline sentence names the number of blocking gaps."""
    role = get_role("backend_developer")
    assert "must-have" in summarise_gaps(analyze_gaps([], role))


def test_summary_line_celebrates_a_complete_match() -> None:
    """A resume covering everything gets a different sentence, not a zero-gap one."""
    role = get_role("backend_developer")
    report = analyze_gaps(_skills(*role.weights), role)
    assert "every skill" in summarise_gaps(report)


# --------------------------------------------------------------------------
# Roadmap
# --------------------------------------------------------------------------

def test_roadmap_is_always_four_weeks() -> None:
    """The timeline has four nodes whatever the input."""
    role = get_role("ml_engineer")
    assert len(generate_roadmap(analyze_gaps([], role))) == WEEKS
    assert len(generate_roadmap(analyze_gaps(_skills(*role.weights), role))) == WEEKS


def test_week_numbers_are_sequential() -> None:
    """Weeks are numbered 1..4 in order, so the UI can render them directly."""
    weeks = generate_roadmap(analyze_gaps([], get_role("data_scientist")))
    assert [week.week for week in weeks] == [1, 2, 3, 4]


def test_critical_skills_land_in_week_one() -> None:
    """Week 1 must attack must-haves; that is where the score moves most."""
    role = get_role("backend_developer")
    report = analyze_gaps([], role)
    week_one = generate_roadmap(report)[0]
    critical_names = {gap.canonical_name for gap in report.critical_gaps}
    assert set(week_one.focus_skills) <= critical_names


def test_no_week_exceeds_the_skill_cap() -> None:
    """Three skills a week keeps the plan achievable."""
    weeks = generate_roadmap(analyze_gaps([], get_role("full_stack_developer")))
    assert all(len(week.focus_skills) <= MAX_SKILLS_PER_WEEK for week in weeks)


def test_no_week_is_empty() -> None:
    """Every week has a title, an objective and at least one activity."""
    for role_id in ("backend_developer", "data_analyst", "devops_engineer"):
        for week in generate_roadmap(analyze_gaps([], get_role(role_id))):
            assert week.title
            assert week.objective
            assert week.activities


def test_a_skill_is_never_scheduled_twice() -> None:
    """Repeating a skill across weeks would waste a quarter of the plan."""
    weeks = generate_roadmap(analyze_gaps([], get_role("data_scientist")))
    scheduled = [name for week in weeks for name in week.focus_skills]
    assert len(scheduled) == len(set(scheduled))


def test_candidate_with_no_gaps_gets_a_depth_plan() -> None:
    """No gaps must not mean four blank cards."""
    role = get_role("data_analyst")
    weeks = generate_roadmap(analyze_gaps(_skills(*role.weights), role))
    assert all(week.activities for week in weeks)
    assert all(week.focus_skills == () for week in weeks)
    # The depth plan is about deepening existing work rather than new skills.
    assert "project" in f"{weeks[0].title} {weeks[0].objective}".lower()


def test_activities_name_the_actual_skill() -> None:
    """Generic advice is useless; each task must mention the skill by name."""
    role = get_role("frontend_developer")
    week_one = generate_roadmap(analyze_gaps([], role))[0]
    joined = " ".join(week_one.activities)
    assert any(name in joined for name in week_one.focus_skills)


def test_estimated_hours_are_proportional_to_the_workload() -> None:
    """A three-skill week is a bigger commitment than a one-skill week."""
    weeks = generate_roadmap(analyze_gaps([], get_role("data_scientist")))
    assert weeks[0].estimated_hours == pytest.approx(len(weeks[0].focus_skills) * 5)
