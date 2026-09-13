"""Every playbook template must name the skill it is talking about.

A task like "write ten queries against it" is meaningless on a timeline card
where "it" was never introduced. This test walks the whole table so a new
category cannot be added without the placeholder.
"""

from app.services.roadmap_generator import CATEGORY_PLAYBOOK, FALLBACK_PLAYBOOK
from app.services.skill_extractor import load_skill_dictionary


def test_every_template_contains_the_skill_placeholder() -> None:
    """All three steps of every playbook interpolate {skill}."""
    offenders: list[str] = []
    for category, templates in {**CATEGORY_PLAYBOOK, "_fallback": FALLBACK_PLAYBOOK}.items():
        for index, template in enumerate(templates):
            if "{skill}" not in template:
                offenders.append(f"{category}[{index}]: {template}")
    assert not offenders, offenders


def test_every_skill_category_has_a_playbook() -> None:
    """A category with no entry silently falls back to generic advice."""
    categories = {skill.category for skill in load_skill_dictionary().values()}
    missing = categories - set(CATEGORY_PLAYBOOK)
    assert not missing, f"no playbook for: {sorted(missing)}"
