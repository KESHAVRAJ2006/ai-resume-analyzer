"""Work out which of a role's skills the resume has, and which it lacks.

job_matcher answers "how well does this fit?" as a number. This module answers
"why?" as a list, which is the part a candidate can actually act on.

PRIVACY: gaps are computed from skills alone. No personal attribute is read
here or anywhere upstream, and the output is advice, not a hiring decision.
"""

from dataclasses import dataclass

from app.services.job_matcher import WEIGHT_BY_TIER, JobRole
from app.services.skill_extractor import ExtractedSkill, load_skill_dictionary

# How a missing skill is presented to the user. The tier already encodes
# importance; severity is the same idea in words the UI can badge.
SEVERITY_BY_TIER: dict[str, str] = {
    "must_have": "critical",
    "good_to_have": "important",
    "nice_to_have": "optional",
}

# Order used when sorting, so "critical" always sits above "important".
_SEVERITY_RANK: dict[str, int] = {"critical": 0, "important": 1, "optional": 2}


@dataclass(frozen=True)
class SkillGap:
    """One required skill the resume did not evidence."""

    skill_id: str
    canonical_name: str
    category: str
    tier: str        # must_have | good_to_have | nice_to_have
    severity: str    # critical | important | optional
    weight: int      # 3 / 2 / 1


@dataclass(frozen=True)
class MatchedSkill:
    """One required skill the resume did evidence, with where it was found."""

    skill_id: str
    canonical_name: str
    category: str
    tier: str
    weight: int
    found_in: tuple[str, ...]


@dataclass(frozen=True)
class GapReport:
    """Everything the results screen needs to explain a score."""

    role_id: str
    role_name: str
    matched: tuple[MatchedSkill, ...]
    missing: tuple[SkillGap, ...]
    earned_weight: int
    total_weight: int
    # Per-tier "3 of 7" counts, for the two-column gap table.
    tier_summary: dict[str, dict[str, int]]

    @property
    def critical_gaps(self) -> tuple[SkillGap, ...]:
        """Return only the missing must-have skills, which block the role."""
        return tuple(gap for gap in self.missing if gap.severity == "critical")

    @property
    def extra_skills_count(self) -> int:
        """Return how many required skills were matched, for a quick headline."""
        return len(self.matched)


def analyze_gaps(
    extracted_skills: list[ExtractedSkill],
    role: JobRole,
    *,
    dictionary_path: str | None = None,
) -> GapReport:
    """Take the resume's skills and a target role, return the matched/missing split.

    Skills are ordered most-important-first so the UI can render the list as-is.
    """
    dictionary = load_skill_dictionary(dictionary_path)
    by_id = {skill.skill_id: skill for skill in extracted_skills}

    matched: list[MatchedSkill] = []
    missing: list[SkillGap] = []
    tier_summary: dict[str, dict[str, int]] = {}

    for tier, skill_ids in role.tiers.items():
        weight = WEIGHT_BY_TIER[tier]
        have = 0

        for skill_id in skill_ids:
            # A role may reference a skill id; the dictionary is the source of
            # its display name. Fall back to the id so a data slip degrades to
            # an ugly label rather than a KeyError in production.
            entry = dictionary.get(skill_id)
            canonical = entry.canonical_name if entry else skill_id.replace("_", " ")
            category = entry.category if entry else "Other"

            if skill_id in by_id:
                have += 1
                matched.append(
                    MatchedSkill(
                        skill_id=skill_id,
                        canonical_name=canonical,
                        category=category,
                        tier=tier,
                        weight=weight,
                        found_in=by_id[skill_id].found_in,
                    )
                )
            else:
                missing.append(
                    SkillGap(
                        skill_id=skill_id,
                        canonical_name=canonical,
                        category=category,
                        tier=tier,
                        severity=SEVERITY_BY_TIER[tier],
                        weight=weight,
                    )
                )

        tier_summary[tier] = {"have": have, "total": len(skill_ids)}

    matched.sort(key=lambda skill: (-skill.weight, skill.canonical_name.lower()))
    missing.sort(key=lambda gap: (_SEVERITY_RANK[gap.severity], gap.canonical_name.lower()))

    return GapReport(
        role_id=role.role_id,
        role_name=role.role_name,
        matched=tuple(matched),
        missing=tuple(missing),
        earned_weight=sum(skill.weight for skill in matched),
        total_weight=role.total_weight,
        tier_summary=tier_summary,
    )


def summarise_gaps(report: GapReport) -> str:
    """Take a gap report, return a one-line summary for the PDF and the UI header."""
    critical = len(report.critical_gaps)
    matched = len(report.matched)
    total = matched + len(report.missing)

    if critical == 0 and matched == total:
        return f"You cover every skill listed for {report.role_name}."
    if critical == 0:
        return (
            f"You cover all must-have skills for {report.role_name} "
            f"({matched} of {total} skills overall)."
        )
    noun = "skill" if critical == 1 else "skills"
    return (
        f"{critical} must-have {noun} missing for {report.role_name} "
        f"({matched} of {total} skills matched)."
    )
