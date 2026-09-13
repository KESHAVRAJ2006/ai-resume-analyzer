"""GET /api/roles - the roles a resume can be scored against."""

from fastapi import APIRouter

from app.schemas.analysis import RoleOut, RoleSkillOut
from app.services.job_matcher import WEIGHT_BY_TIER, load_job_roles
from app.services.skill_extractor import load_skill_dictionary

router = APIRouter(tags=["roles"])


@router.get("/roles", response_model=list[RoleOut], summary="List roles and requirements")
def list_roles() -> list[RoleOut]:
    """Take no input, return every role with its weighted skill requirements.

    Defined with `def` rather than `async def`: it reads cached data and does no
    awaiting, so FastAPI runs it in a worker thread and the event loop stays free.
    """
    dictionary = load_skill_dictionary()

    roles: list[RoleOut] = []
    for role in load_job_roles().values():
        skills: list[RoleSkillOut] = []
        for tier, skill_ids in role.tiers.items():
            for skill_id in skill_ids:
                entry = dictionary.get(skill_id)
                skills.append(
                    RoleSkillOut(
                        skill_id=skill_id,
                        name=entry.canonical_name if entry else skill_id.replace("_", " "),
                        category=entry.category if entry else "Other",
                        tier=tier,
                        weight=WEIGHT_BY_TIER[tier],
                    )
                )

        # Heaviest first so the UI can show the must-haves without re-sorting.
        skills.sort(key=lambda skill: (-skill.weight, skill.name.lower()))

        roles.append(
            RoleOut(
                role_id=role.role_id,
                role_name=role.role_name,
                category=role.category,
                description=role.description,
                skills=skills,
                total_weight=role.total_weight,
            )
        )

    roles.sort(key=lambda role: role.role_name)
    return roles
