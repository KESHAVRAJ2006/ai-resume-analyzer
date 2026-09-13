"""Pydantic models for the analysis API.

These are the contract between the service layer and React. Service dataclasses
never cross the wire directly - going through an explicit schema means renaming
an internal field cannot silently break the frontend.
"""

from datetime import datetime

from pydantic import BaseModel, Field

# Shown in the UI and in the PDF. Kept here so the API, the report and the
# frontend all quote the same sentence.
DISCLAIMER = (
    "This score estimates how well your listed skills overlap with a role's "
    "requirements. It is not a hiring decision, and it does not consider name, "
    "gender, age, photo, religion, nationality, marital status or disability."
)


class SkillOut(BaseModel):
    """One skill detected in the resume."""

    skill_id: str
    name: str = Field(description="Canonical display name, e.g. 'scikit-learn'")
    category: str
    matched_text: str = Field(description="The spelling the resume actually used")
    occurrences: int
    found_in: list[str] = Field(description="Section names the skill appeared in")


class MatchedSkillOut(BaseModel):
    """A required skill the candidate has."""

    skill_id: str
    name: str
    category: str
    tier: str
    weight: int
    found_in: list[str]


class SkillGapOut(BaseModel):
    """A required skill the candidate is missing."""

    skill_id: str
    name: str
    category: str
    tier: str
    severity: str = Field(description="critical | important | optional")
    weight: int


class TierSummaryOut(BaseModel):
    """How many of a tier's skills the candidate has."""

    have: int
    total: int


class GapReportOut(BaseModel):
    """The full matched/missing breakdown for the target role."""

    summary: str
    matched: list[MatchedSkillOut]
    missing: list[SkillGapOut]
    earned_weight: int
    total_weight: int
    tier_summary: dict[str, TierSummaryOut]


class RoleScoreOut(BaseModel):
    """One role's score, with the three tiers exposed for transparency."""

    role_id: str
    role_name: str
    category: str
    score: float = Field(ge=0, le=100)
    band: str = Field(description="strong | developing | early")
    skill_coverage: float = Field(ge=0, le=1)
    tfidf_score: float = Field(ge=0, le=1)
    semantic_score: float | None = Field(default=None, ge=0, le=1)


class RoadmapWeekOut(BaseModel):
    """One node of the 4-week timeline."""

    week: int
    title: str
    objective: str
    focus_skills: list[str]
    activities: list[str]
    estimated_hours: int


class AnalysisMeta(BaseModel):
    """Context about how this particular analysis was produced."""

    filename: str
    analyzed_at: datetime
    semantic_enabled: bool = Field(
        description="False means the score used the two-tier renormalised formula"
    )
    sections_detected: list[str]
    disclaimer: str = DISCLAIMER


class AnalysisResponse(BaseModel):
    """Everything the results screen renders, in one payload."""

    target_role: RoleScoreOut
    skills_found: list[SkillOut]
    skills_by_category: dict[str, list[SkillOut]]
    role_ranking: list[RoleScoreOut]
    gaps: GapReportOut
    roadmap: list[RoadmapWeekOut]
    meta: AnalysisMeta


class RoleSkillOut(BaseModel):
    """A skill required by a role, as listed on GET /api/roles."""

    skill_id: str
    name: str
    category: str
    tier: str
    weight: int


class RoleOut(BaseModel):
    """One role and its requirements, for the role selector."""

    role_id: str
    role_name: str
    category: str
    description: str
    skills: list[RoleSkillOut]
    total_weight: int
