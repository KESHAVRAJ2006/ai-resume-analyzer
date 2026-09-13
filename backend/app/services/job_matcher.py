"""Score a resume against the job roles.

Owns data/job_roles.csv and implements two of the three scoring tiers:

    final = 100 * (0.45 * weighted_skill_coverage    <- this module
                 + 0.35 * semantic_cosine            <- Phase 5
                 + 0.20 * tfidf_cosine)              <- this module

The semantic term is optional here. When it is missing the two available
weights are renormalised so a Phase 4 score is still on a 0-100 scale and
still comparable between roles; Phase 5 simply starts passing the third term.

PRIVACY: scoring reads skills and role-relevant text only. Name, gender, age,
photo, religion, nationality, marital status and disability are never
extracted, stored or scored anywhere in this pipeline. A score is an estimate
of skill overlap, not a hiring decision.
"""

import csv
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.services.text_cleaner import clean_text

DEFAULT_ROLES_PATH = Path(__file__).resolve().parents[2] / "data" / "job_roles.csv"

# The CSV stores a tier name; the tier IS the importance weight. Keeping the
# numbers here rather than in the data means one place to tune them.
WEIGHT_BY_TIER: dict[str, int] = {
    "must_have": 3,
    "good_to_have": 2,
    "nice_to_have": 1,
}

# The scoring formula. These three must sum to 1.0.
WEIGHT_SKILL_COVERAGE = 0.45
WEIGHT_SEMANTIC = 0.35
WEIGHT_TFIDF = 0.20

# Score bands drive the colour of the ring on the results screen.
# 70 = every must-have plus most good-to-haves; below 40 = most must-haves
# are missing, which is a genuinely poor fit rather than a near miss.
SCORE_BAND_STRONG = 70.0
SCORE_BAND_DEVELOPING = 40.0


@dataclass(frozen=True)
class JobRole:
    """One row of job_roles.csv with its skills flattened into weights."""

    role_id: str
    role_name: str
    category: str
    description: str
    weights: dict[str, int]          # skill_id -> 3 / 2 / 1
    tiers: dict[str, tuple[str, ...]]  # tier name -> skill_ids, for the gap table

    @property
    def total_weight(self) -> int:
        """Return the denominator of weighted coverage: every point on offer."""
        return sum(self.weights.values())


@dataclass(frozen=True)
class RoleScore:
    """The full scoring breakdown for one resume against one role."""

    role_id: str
    role_name: str
    category: str
    final_score: float               # 0-100, one decimal place
    skill_coverage: float            # 0-1
    tfidf_score: float               # 0-1
    semantic_score: float | None     # 0-1, None until Phase 5
    matched_skill_ids: tuple[str, ...]
    missing_skill_ids: tuple[str, ...]


@lru_cache(maxsize=4)
def load_job_roles(path: str | None = None) -> dict[str, JobRole]:
    """Take an optional CSV path, return {role_id: JobRole}. Cached per path."""
    csv_path = Path(path) if path else DEFAULT_ROLES_PATH
    if not csv_path.exists():
        raise FileNotFoundError(f"Job roles file not found at {csv_path}")

    roles: dict[str, JobRole] = {}
    with csv_path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            role_id = row["role_id"].strip()
            if not role_id:
                continue

            weights: dict[str, int] = {}
            tiers: dict[str, tuple[str, ...]] = {}
            for tier, weight in WEIGHT_BY_TIER.items():
                skill_ids = tuple(s.strip() for s in row[tier].split("|") if s.strip())
                tiers[tier] = skill_ids
                for skill_id in skill_ids:
                    weights[skill_id] = weight

            roles[role_id] = JobRole(
                role_id=role_id,
                role_name=row["role_name"].strip(),
                category=row["category"].strip(),
                description=row["description"].strip(),
                weights=weights,
                tiers=tiers,
            )
    return roles


def get_role(role_id: str, *, roles_path: str | None = None) -> JobRole:
    """Take a role_id, return that JobRole. Raises KeyError if it does not exist."""
    roles = load_job_roles(roles_path)
    if role_id not in roles:
        raise KeyError(f"Unknown role '{role_id}'. Known roles: {sorted(roles)}")
    return roles[role_id]


def weighted_skill_coverage(found_skill_ids: set[str], role: JobRole) -> float:
    """Take the resume's skill ids and a role, return coverage from 0 to 1.

    Each required skill contributes its importance weight, so missing one
    must-have costs three times as much as missing one nice-to-have.
    """
    if role.total_weight == 0:
        return 0.0
    earned = sum(
        weight for skill_id, weight in role.weights.items() if skill_id in found_skill_ids
    )
    return earned / role.total_weight


def tfidf_scores(resume_text: str, *, roles_path: str | None = None) -> dict[str, float]:
    """Take raw resume text, return {role_id: cosine similarity 0-1} for every role.

    All roles are scored in one pass because the vectorizer must see the whole
    corpus to compute meaningful inverse document frequencies.
    """
    roles = load_job_roles(roles_path)
    cleaned_resume = clean_text(resume_text)
    if not cleaned_resume:
        return {role_id: 0.0 for role_id in roles}

    role_ids, role_documents = zip(*_role_documents(roles_path))
    corpus = [*role_documents, cleaned_resume]

    # sublinear_tf dampens repetition: a resume that says "Python" nine times is
    # not nine times better at Python than one that says it once.
    vectorizer = TfidfVectorizer(analyzer=_tokenize, sublinear_tf=True)
    matrix = vectorizer.fit_transform(corpus)

    # The resume is the last row; compare it against every role row.
    resume_row = matrix[len(role_ids)]
    similarities = cosine_similarity(resume_row, matrix[: len(role_ids)])[0]
    return {role_id: float(score) for role_id, score in zip(role_ids, similarities)}


def score_role(
    role: JobRole,
    found_skill_ids: set[str],
    tfidf_score: float,
    semantic_score: float | None = None,
) -> RoleScore:
    """Take a role, the resume's skills and the similarity tiers, return a RoleScore.

    semantic_score is None until Phase 5 loads the embedding model; the
    remaining weights are then renormalised so the result stays on 0-100.
    """
    coverage = weighted_skill_coverage(found_skill_ids, role)
    tfidf_score = _clamp(tfidf_score)

    if semantic_score is None:
        available = WEIGHT_SKILL_COVERAGE + WEIGHT_TFIDF
        blended = (WEIGHT_SKILL_COVERAGE * coverage + WEIGHT_TFIDF * tfidf_score) / available
    else:
        semantic_score = _clamp(semantic_score)
        blended = (
            WEIGHT_SKILL_COVERAGE * coverage
            + WEIGHT_SEMANTIC * semantic_score
            + WEIGHT_TFIDF * tfidf_score
        )

    matched = tuple(sorted(s for s in role.weights if s in found_skill_ids))
    missing = tuple(sorted(s for s in role.weights if s not in found_skill_ids))

    return RoleScore(
        role_id=role.role_id,
        role_name=role.role_name,
        category=role.category,
        final_score=round(100 * blended, 1),
        skill_coverage=round(coverage, 4),
        tfidf_score=round(tfidf_score, 4),
        semantic_score=None if semantic_score is None else round(semantic_score, 4),
        matched_skill_ids=matched,
        missing_skill_ids=missing,
    )


def rank_roles(
    resume_text: str,
    found_skill_ids: set[str],
    *,
    semantic_scores: dict[str, float] | None = None,
    roles_path: str | None = None,
) -> list[RoleScore]:
    """Take resume text and its skills, return every role scored, best first."""
    roles = load_job_roles(roles_path)
    tfidf = tfidf_scores(resume_text, roles_path=roles_path)

    scored = [
        score_role(
            role,
            found_skill_ids,
            tfidf.get(role_id, 0.0),
            None if semantic_scores is None else semantic_scores.get(role_id),
        )
        for role_id, role in roles.items()
    ]

    # Best first; role_name breaks ties so the order never flickers between runs.
    scored.sort(key=lambda result: (-result.final_score, result.role_name))
    return scored


@lru_cache(maxsize=4)
def _role_documents(path: str | None = None) -> tuple[tuple[str, str], ...]:
    """Take an optional CSV path, return ((role_id, tfidf document), ...).

    Each document mixes the description, which supplies natural language, with
    the skill ids, which supply the exact vocabulary a resume uses. Cached
    because the text never changes and cleaning 8 documents per request is
    pure waste.
    """
    documents: list[tuple[str, str]] = []
    for role_id, role in load_job_roles(path).items():
        skill_words = " ".join(skill_id.replace("_", " ") for skill_id in role.weights)
        documents.append(
            (role_id, clean_text(f"{role.role_name}. {role.description} {skill_words}"))
        )
    return tuple(documents)


def _tokenize(text: str) -> list[str]:
    """Take cleaned text, return unigrams plus bigrams for the vectorizer.

    A custom analyzer is required because sklearn's default token pattern
    discards single characters and splits on punctuation, which would destroy
    the c++, c#, .net and ci/cd tokens text_cleaner worked to preserve.
    """
    tokens = [word for word in text.split() if word not in ENGLISH_STOP_WORDS]
    bigrams = [f"{first} {second}" for first, second in zip(tokens, tokens[1:])]
    return tokens + bigrams


def score_band(score: float) -> str:
    """Take a 0-100 score, return 'strong', 'developing' or 'early'.

    The UI maps these to the green / amber / red ring colours.
    """
    if score >= SCORE_BAND_STRONG:
        return "strong"
    if score >= SCORE_BAND_DEVELOPING:
        return "developing"
    return "early"


def _clamp(value: float) -> float:
    """Take a similarity, return it clipped to 0-1 (floating point drift guard)."""
    return max(0.0, min(1.0, float(value)))
