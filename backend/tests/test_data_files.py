"""Integrity tests for the two CSVs in data/.

The CSVs are data, but a typo in one breaks scoring as surely as a bug in a
function would - so they get tested like code. Phase 4 adds the real role
loader; this reads the file directly on purpose, so the test fails if the file
itself is wrong rather than if the loader is.
"""

import csv
from pathlib import Path

import pytest

from app.services.skill_extractor import load_skill_dictionary

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
ROLES_CSV = DATA_DIR / "job_roles.csv"
TIER_COLUMNS = ("must_have", "good_to_have", "nice_to_have")


def _load_role_rows() -> list[dict[str, str]]:
    """Read job_roles.csv and return its rows as dicts."""
    with ROLES_CSV.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


@pytest.fixture(scope="module")
def role_rows() -> list[dict[str, str]]:
    """Return every row of job_roles.csv."""
    return _load_role_rows()


def test_there_are_exactly_eight_roles(role_rows: list[dict[str, str]]) -> None:
    """The product promises 8 roles; the data must actually contain 8."""
    assert len(role_rows) == 8


def test_role_ids_are_unique(role_rows: list[dict[str, str]]) -> None:
    """Duplicate ids would silently shadow each other when loaded into a dict."""
    ids = [row["role_id"] for row in role_rows]
    assert len(ids) == len(set(ids))


def test_every_role_has_a_name_and_description(role_rows: list[dict[str, str]]) -> None:
    """Descriptions feed the Phase 5 semantic tier, so none may be blank."""
    for row in role_rows:
        assert row["role_name"].strip()
        # Short descriptions produce weak embeddings and a meaningless cosine.
        assert len(row["description"].strip()) > 80, row["role_id"]


def test_every_referenced_skill_exists_in_the_dictionary(
    role_rows: list[dict[str, str]],
) -> None:
    """A typo like 'pyton' would silently count as an unachievable requirement."""
    known = set(load_skill_dictionary())
    unknown: list[str] = []
    for row in role_rows:
        for column in TIER_COLUMNS:
            for skill_id in filter(None, row[column].split("|")):
                if skill_id not in known:
                    unknown.append(f"{row['role_id']}.{column}: {skill_id}")
    assert not unknown, unknown


def test_no_skill_appears_in_two_tiers_of_the_same_role(
    role_rows: list[dict[str, str]],
) -> None:
    """A skill counted twice would inflate that role's weighted coverage."""
    for row in role_rows:
        tiers = [set(filter(None, row[column].split("|"))) for column in TIER_COLUMNS]
        assert not tiers[0] & tiers[1], row["role_id"]
        assert not tiers[0] & tiers[2], row["role_id"]
        assert not tiers[1] & tiers[2], row["role_id"]


def test_every_role_has_must_have_skills(role_rows: list[dict[str, str]]) -> None:
    """Weighted coverage divides by total weight; a role with no must-haves
    would be trivially easy to score 100% on."""
    for row in role_rows:
        assert len(list(filter(None, row["must_have"].split("|")))) >= 4, row["role_id"]


def test_roles_are_not_trivially_small(role_rows: list[dict[str, str]]) -> None:
    """Too few skills makes each one worth too much; scores become jumpy."""
    for row in role_rows:
        total = sum(len(list(filter(None, row[c].split("|")))) for c in TIER_COLUMNS)
        assert total >= 12, f"{row['role_id']} has only {total} skills"
