"""POST /api/analyze - the endpoint that runs the whole pipeline.

Responsibilities of this layer, and nothing else:
  - validate the upload (extension, size)
  - persist it to a temp file and ALWAYS delete it again
  - translate service exceptions into HTTP status codes
  - map service dataclasses onto the response schema

All analysis happens in app/services, which knows nothing about HTTP.
"""

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile, status
from starlette.concurrency import run_in_threadpool

from app.core.config import get_settings
from app.schemas.analysis import (
    AnalysisMeta,
    AnalysisResponse,
    GapReportOut,
    MatchedSkillOut,
    RoadmapWeekOut,
    RoleScoreOut,
    SkillGapOut,
    SkillOut,
    TierSummaryOut,
)
from app.services.exceptions import (
    EmptyResumeError,
    FileNotFoundErrorService,
    ResumeParseError,
    UnsupportedFileTypeError,
)
from app.services.gap_analyzer import GapReport, analyze_gaps, summarise_gaps
from app.services.job_matcher import RoleScore, get_role, rank_roles, score_band
from app.services.resume_parser import parse_resume
from app.services.roadmap_generator import RoadmapWeek, generate_roadmap
from app.services.section_splitter import split_sections
from app.services.skill_extractor import ExtractedSkill, extract_skills, group_by_category

logger = logging.getLogger(__name__)
router = APIRouter(tags=["analysis"])

# Upload is streamed in 1MB pieces so an oversized file is rejected after one
# megabyte rather than after the whole thing is already in memory.
_READ_CHUNK_BYTES = 1024 * 1024


@router.post(
    "/analyze",
    response_model=AnalysisResponse,
    summary="Analyse a resume against a target role",
)
async def analyze_resume(
    request: Request,
    file: UploadFile = File(..., description="Resume as PDF or DOCX"),
    target_role: str = Form(..., description="role_id from GET /api/roles"),
) -> AnalysisResponse:
    """Take a resume file and a target role_id, return the full analysis.

    The uploaded file is deleted in a finally block, on every path including
    an unhandled exception.
    """
    settings = get_settings()

    # Fail on a bad role before touching the filesystem at all.
    try:
        role = get_role(target_role)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown target_role '{target_role}'. Call GET /api/roles for valid ids.",
        ) from exc

    original_name = file.filename or "resume"
    suffix = Path(original_name).suffix.lower()
    if suffix not in settings.allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"'{suffix or original_name}' is not supported. Upload a PDF or DOCX file.",
        )

    # A random name, never the user's filename: an uploaded name like
    # "../../etc/passwd" must not be able to steer where we write.
    temp_path = settings.temp_path / f"{uuid.uuid4().hex}{suffix}"

    try:
        await _save_upload(file, temp_path, settings.max_upload_bytes, settings.max_upload_mb)

        embedding_index = getattr(request.app.state, "ml_models", {}).get("embeddings")

        # The pipeline is CPU-bound (regex, sklearn, torch). Running it in a
        # worker thread keeps the event loop free to accept other requests.
        return await run_in_threadpool(
            _run_pipeline, temp_path, original_name, role.role_id, embedding_index
        )

    except UnsupportedFileTypeError as exc:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, str(exc)) from exc
    except EmptyResumeError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    except (ResumeParseError, FileNotFoundErrorService) as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    finally:
        # Always, on every path: success, validation failure, parse error or a
        # crash we did not anticipate. A resume must never outlive its request.
        _delete_temp_file(temp_path)


async def _save_upload(
    file: UploadFile, destination: Path, max_bytes: int, max_mb: int
) -> None:
    """Take an upload and a path, stream the file to disk, enforcing the size cap."""
    written = 0
    with destination.open("wb") as handle:
        while chunk := await file.read(_READ_CHUNK_BYTES):
            written += len(chunk)
            if written > max_bytes:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File is larger than the {max_mb}MB limit.",
                )
            handle.write(chunk)

    if written == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="The uploaded file is empty."
        )


def _delete_temp_file(path: Path) -> None:
    """Take a path, delete it, and never let cleanup failure mask a real error."""
    try:
        path.unlink(missing_ok=True)
    except OSError:  # pragma: no cover - only on a locked or read-only volume
        logger.warning("Could not delete temp upload %s", path, exc_info=True)


def _run_pipeline(
    temp_path: Path, original_name: str, role_id: str, embedding_index: object | None
) -> AnalysisResponse:
    """Take a saved file and a role, run every service in order, return the response.

    Synchronous on purpose: it is called through run_in_threadpool.
    """
    raw_text = parse_resume(temp_path)
    sections = split_sections(raw_text)
    extracted = extract_skills(sections)
    found_ids = {skill.skill_id for skill in extracted}

    # Only the sections we searched feed the similarity tiers, so education
    # boilerplate does not drag every score toward the middle.
    searchable_text = "\n".join(sections.values())

    semantic_scores = None
    if embedding_index is not None:
        semantic_scores = embedding_index.score_resume(raw_text)

    ranking = rank_roles(searchable_text, found_ids, semantic_scores=semantic_scores)
    target = next(result for result in ranking if result.role_id == role_id)

    report = analyze_gaps(extracted, get_role(role_id))
    roadmap = generate_roadmap(report)

    return AnalysisResponse(
        target_role=_role_score_out(target),
        skills_found=[_skill_out(skill) for skill in extracted],
        skills_by_category={
            category: [_skill_out(skill) for skill in skills]
            for category, skills in group_by_category(extracted).items()
        },
        role_ranking=[_role_score_out(result) for result in ranking],
        gaps=_gap_report_out(report),
        roadmap=[_roadmap_week_out(week) for week in roadmap],
        meta=AnalysisMeta(
            filename=original_name,
            analyzed_at=datetime.now(timezone.utc),
            semantic_enabled=semantic_scores is not None,
            sections_detected=sorted(sections),
        ),
    )


def _skill_out(skill: ExtractedSkill) -> SkillOut:
    """Map an ExtractedSkill onto its wire format."""
    return SkillOut(
        skill_id=skill.skill_id,
        name=skill.canonical_name,
        category=skill.category,
        matched_text=skill.matched_text,
        occurrences=skill.occurrences,
        found_in=list(skill.found_in),
    )


def _role_score_out(result: RoleScore) -> RoleScoreOut:
    """Map a RoleScore onto its wire format, adding the UI colour band."""
    return RoleScoreOut(
        role_id=result.role_id,
        role_name=result.role_name,
        category=result.category,
        score=result.final_score,
        band=score_band(result.final_score),
        skill_coverage=result.skill_coverage,
        tfidf_score=result.tfidf_score,
        semantic_score=result.semantic_score,
    )


def _gap_report_out(report: GapReport) -> GapReportOut:
    """Map a GapReport onto its wire format."""
    return GapReportOut(
        summary=summarise_gaps(report),
        matched=[
            MatchedSkillOut(
                skill_id=skill.skill_id,
                name=skill.canonical_name,
                category=skill.category,
                tier=skill.tier,
                weight=skill.weight,
                found_in=list(skill.found_in),
            )
            for skill in report.matched
        ],
        missing=[
            SkillGapOut(
                skill_id=gap.skill_id,
                name=gap.canonical_name,
                category=gap.category,
                tier=gap.tier,
                severity=gap.severity,
                weight=gap.weight,
            )
            for gap in report.missing
        ],
        earned_weight=report.earned_weight,
        total_weight=report.total_weight,
        tier_summary={
            tier: TierSummaryOut(**counts) for tier, counts in report.tier_summary.items()
        },
    )


def _roadmap_week_out(week: RoadmapWeek) -> RoadmapWeekOut:
    """Map a RoadmapWeek onto its wire format."""
    return RoadmapWeekOut(
        week=week.week,
        title=week.title,
        objective=week.objective,
        focus_skills=list(week.focus_skills),
        activities=list(week.activities),
        estimated_hours=week.estimated_hours,
    )
