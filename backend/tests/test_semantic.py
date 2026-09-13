"""Opt-in tests for the real embedding model.

Excluded from the default run because they download ~90MB on first execution
and take several seconds after that. Run them with:

    pytest -m slow

Everything the API needs from this module is covered in the fast suite through
StubEmbeddingIndex; these tests check that the real thing behaves the way the
stub pretends to.
"""

import numpy as np
import pytest

from app.core.embeddings import (
    CHUNK_OVERLAP,
    CHUNK_WORDS,
    _chunk_resume,
    build_embedding_index,
)
from app.services.job_matcher import load_job_roles

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

DATA_RESUME = (
    "Data science intern. Explored customer datasets, built churn prediction "
    "models, ran hypothesis tests on campaign results, and presented findings "
    "to the marketing team with charts and a written summary."
)
DEVOPS_RESUME = (
    "Platform engineer. Automated build and release pipelines, wrote "
    "infrastructure definitions, containerised services and ran the alerting "
    "stack that pages the on-call engineer."
)


# --------------------------------------------------------------------------
# Chunking - runs without the model
# --------------------------------------------------------------------------

def test_chunks_overlap_so_nothing_is_split_and_lost() -> None:
    """Consecutive windows share CHUNK_OVERLAP words."""
    words = [f"w{index}" for index in range(200)]
    chunks = _chunk_resume(" ".join(words))
    assert len(chunks) > 1
    first, second = chunks[0].split(), chunks[1].split()
    assert first[-CHUNK_OVERLAP:] == second[:CHUNK_OVERLAP]


def test_short_resume_is_a_single_chunk() -> None:
    """A resume under one window is not split."""
    assert len(_chunk_resume("Python developer with Docker experience")) == 1


def test_long_resume_is_split_into_windows() -> None:
    """A realistic 600-word resume becomes several windows, not one truncated one."""
    chunks = _chunk_resume(" ".join(["python"] * 600))
    assert len(chunks) > 1
    assert all(len(chunk.split()) <= CHUNK_WORDS for chunk in chunks)


def test_chunking_redacts_contact_details() -> None:
    """Nothing identifying is sent to the model."""
    text = _chunk_resume("Priya Sharma priya@example.com +91 98765 43210 Python")[0]
    assert "priya@example.com" not in text
    assert "98765" not in text


def test_empty_text_produces_no_chunks() -> None:
    """No text means no encode call at all."""
    assert _chunk_resume("") == []


# --------------------------------------------------------------------------
# The real model
# --------------------------------------------------------------------------

@pytest.fixture(scope="module")
def index():
    """Load the model once for this module."""
    return build_embedding_index(MODEL_NAME)


@pytest.mark.slow
def test_index_precomputes_one_vector_per_role(index) -> None:
    """Every role is embedded at startup, not per request."""
    assert len(index.role_ids) == len(load_job_roles())
    assert index.role_vectors.shape[0] == len(index.role_ids)


@pytest.mark.slow
def test_role_vectors_are_normalised(index) -> None:
    """Unit vectors are what make a dot product equal the cosine."""
    norms = np.linalg.norm(index.role_vectors, axis=1)
    assert np.allclose(norms, 1.0, atol=1e-5)


@pytest.mark.slow
def test_scores_are_in_range(index) -> None:
    """Every similarity is a usable 0-1 value for the scoring formula."""
    scores = index.score_resume(DATA_RESUME)
    assert set(scores) == set(load_job_roles())
    assert all(0.0 <= value <= 1.0 for value in scores.values())


@pytest.mark.slow
def test_semantics_beat_keywords(index) -> None:
    """The point of this tier: the data resume names no data tool by name.

    'churn prediction', 'hypothesis tests' and 'presented findings' contain no
    dictionary skill and no role keyword, so TF-IDF gains little from them.
    The embedding still places the text nearest the data roles.
    """
    scores = index.score_resume(DATA_RESUME)
    best = max(scores, key=scores.get)
    assert best in {"data_scientist", "data_analyst", "ml_engineer"}
    assert scores[best] > scores["frontend_developer"]


@pytest.mark.slow
def test_a_different_resume_moves_to_a_different_role(index) -> None:
    """The tier discriminates rather than always favouring the same role."""
    devops = index.score_resume(DEVOPS_RESUME)
    assert devops["devops_engineer"] > devops["data_scientist"]


@pytest.mark.slow
def test_empty_resume_scores_zero(index) -> None:
    """No text means no similarity, and no crash."""
    assert set(index.score_resume("").values()) == {0.0}


@pytest.mark.slow
def test_scoring_is_deterministic(index) -> None:
    """The same resume twice gives the same numbers."""
    assert index.score_resume(DATA_RESUME) == index.score_resume(DATA_RESUME)
